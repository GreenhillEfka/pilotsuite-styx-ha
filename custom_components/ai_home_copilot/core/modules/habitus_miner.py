"""Habitus Miner module for A→B pattern discovery in Home Assistant."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from ...const import DOMAIN
from ..module import ModuleContext

_LOGGER = logging.getLogger(__name__)


class HabitusMinerModule:
    """Module for discovering A→B behavioral patterns from HA events."""

    name = "habitus_miner"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the Habitus Miner module."""
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        _LOGGER.info("Setting up Habitus Miner module")

        # Store module data
        module_data = {
            "event_buffer": [],
            "buffer_max_size": 1000,
            "buffer_max_age_hours": 24,
            "last_mining_ts": None,
            "auto_mining_enabled": False,
            "listeners": [],
        }
        
        # Store under entry data
        if entry.entry_id not in hass.data[DOMAIN]:
            hass.data[DOMAIN][entry.entry_id] = {}
        
        hass.data[DOMAIN][entry.entry_id]["habitus_miner"] = module_data

        # Register services
        await self._register_services(hass, entry)

        # Set up event listener (optional, for auto-mining)
        await self._setup_event_listener(hass, entry)

        _LOGGER.info("Habitus Miner module setup completed")

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the Habitus Miner module."""
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        _LOGGER.info("Unloading Habitus Miner module")

        # Unregister listeners
        module_data = hass.data[DOMAIN].get(entry.entry_id, {}).get("habitus_miner", {})
        listeners = module_data.get("listeners", [])
        
        for unsub in listeners:
            if callable(unsub):
                unsub()

        # Remove services (they are global, so check if other entries exist)
        entry_count = len([e for e in hass.config_entries.async_entries(DOMAIN)])
        if entry_count <= 1:  # This is the last entry
            services_to_remove = [
                "habitus_mine_rules",
                "habitus_get_rules", 
                "habitus_reset_cache",
                "habitus_configure_mining",
            ]
            
            for service in services_to_remove:
                if hass.services.has_service(DOMAIN, service):
                    hass.services.async_remove(DOMAIN, service)

        # Clean up module data
        if "habitus_miner" in hass.data[DOMAIN].get(entry.entry_id, {}):
            del hass.data[DOMAIN][entry.entry_id]["habitus_miner"]

        return True

    async def _register_services(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Register Habitus Miner services."""
        
        if not hass.services.has_service(DOMAIN, "habitus_mine_rules"):
            
            async def handle_mine_rules(call: ServiceCall) -> None:
                """Handle rule mining service call."""
                await self._handle_mine_rules(hass, entry, call)

            hass.services.async_register(
                DOMAIN,
                "habitus_mine_rules",
                handle_mine_rules,
                schema=vol.Schema({
                    vol.Optional("days_back", default=7): vol.Range(min=1, max=365),
                    vol.Optional("domains"): [str],
                    vol.Optional("exclude_domains"): [str],
                    vol.Optional("min_confidence", default=0.5): vol.Range(min=0.0, max=1.0),
                    vol.Optional("min_lift", default=1.2): vol.Range(min=0.0, max=10.0),
                    vol.Optional("max_rules", default=100): vol.Range(min=1, max=1000),
                }),
            )

        if not hass.services.has_service(DOMAIN, "habitus_get_rules"):
            
            async def handle_get_rules(call: ServiceCall) -> None:
                """Handle get rules service call."""
                await self._handle_get_rules(hass, entry, call)

            hass.services.async_register(
                DOMAIN,
                "habitus_get_rules",
                handle_get_rules,
                schema=vol.Schema({
                    vol.Optional("limit", default=20): vol.Range(min=1, max=200),
                    vol.Optional("domain_filter"): str,
                    vol.Optional("min_score", default=0.0): vol.Range(min=0.0, max=10.0),
                }),
            )

        if not hass.services.has_service(DOMAIN, "habitus_reset_cache"):
            
            async def handle_reset_cache(call: ServiceCall) -> None:
                """Handle cache reset service call."""
                await self._handle_reset_cache(hass, entry, call)

            hass.services.async_register(
                DOMAIN,
                "habitus_reset_cache", 
                handle_reset_cache,
            )

        if not hass.services.has_service(DOMAIN, "habitus_configure_mining"):
            
            async def handle_configure_mining(call: ServiceCall) -> None:
                """Handle mining configuration service call."""
                await self._handle_configure_mining(hass, entry, call)

            hass.services.async_register(
                DOMAIN,
                "habitus_configure_mining",
                handle_configure_mining,
                schema=vol.Schema({
                    vol.Optional("auto_mining_enabled"): bool,
                    vol.Optional("buffer_max_size"): vol.Range(min=100, max=10000),
                    vol.Optional("buffer_max_age_hours"): vol.Range(min=1, max=168),
                }),
            )

    async def _setup_event_listener(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Set up event listener for collecting HA events."""
        module_data = hass.data[DOMAIN][entry.entry_id]["habitus_miner"]
        
        @callback
        def event_listener(event: Event) -> None:
            """Listen for state_changed events and buffer them."""
            if event.event_type != "state_changed":
                return
                
            try:
                # Add to buffer
                event_data = {
                    "time_fired": event.time_fired.isoformat(),
                    "event_type": event.event_type,
                    "data": dict(event.data) if event.data else {},
                    "context": {
                        "id": event.context.id,
                        "user_id": event.context.user_id,
                    } if event.context else {},
                }
                
                buffer = module_data["event_buffer"]
                buffer.append(event_data)
                
                # Trim buffer if too large
                max_size = module_data["buffer_max_size"]
                if len(buffer) > max_size:
                    buffer[:] = buffer[-max_size:]
                
                # Age-based trimming
                max_age_hours = module_data["buffer_max_age_hours"]
                cutoff_time = time.time() - (max_age_hours * 3600)
                
                # Remove old events (simplified - assumes chronological order)
                while buffer and hasattr(event, 'time_fired'):
                    try:
                        from datetime import datetime
                        event_ts = datetime.fromisoformat(
                            buffer[0]["time_fired"].replace('Z', '+00:00')
                        ).timestamp()
                        if event_ts < cutoff_time:
                            buffer.pop(0)
                        else:
                            break
                    except Exception:
                        break
                        
            except Exception as e:
                _LOGGER.debug("Error buffering event: %s", e)

        # Register listener
        unsub = hass.bus.async_listen("state_changed", event_listener)
        module_data["listeners"].append(unsub)

    async def _handle_mine_rules(self, hass: HomeAssistant, entry: ConfigEntry, call: ServiceCall) -> None:
        """Handle the mine_rules service call."""
        try:
            from ...coordinator import CopilotDataUpdateCoordinator
            
            # Get coordinator from legacy module 
            legacy_data = hass.data[DOMAIN].get(entry.entry_id, {})
            coordinator: CopilotDataUpdateCoordinator = legacy_data.get("coordinator")
            
            if not coordinator:
                _LOGGER.error("No coordinator found - legacy module may not be loaded")
                return

            # Get parameters
            days_back = call.data.get("days_back", 7)
            domains = call.data.get("domains")
            exclude_domains = call.data.get("exclude_domains")
            min_confidence = call.data.get("min_confidence", 0.5)
            min_lift = call.data.get("min_lift", 1.2)
            max_rules = call.data.get("max_rules", 100)
            
            _LOGGER.info("Mining rules with days_back=%d, domains=%s", days_back, domains)

            # Get events from buffer or fetch from HA
            module_data = hass.data[DOMAIN][entry.entry_id]["habitus_miner"]
            events = module_data["event_buffer"]
            
            if not events:
                _LOGGER.info("No buffered events found, fetching from HA history")
                events = await self._fetch_ha_history(hass, days_back, domains, exclude_domains)
            
            if not events:
                _LOGGER.warning("No events found for mining")
                return

            # Call Core API for mining
            mining_result = await coordinator.api.post_with_auth(
                "habitus/mine",
                data={
                    "events": events,
                    "config": {
                        "min_confidence": min_confidence,
                        "min_lift": min_lift,
                        "max_rules": max_rules,
                        "include_domains": domains,
                        "exclude_domains": exclude_domains,
                    }
                },
            )

            if mining_result:
                module_data["last_mining_ts"] = time.time()
                _LOGGER.info(
                    "Successfully mined rules: %d rules from %d events",
                    mining_result.get("discovered_rules", 0),
                    mining_result.get("total_input_events", 0)
                )
                
                # Send notification
                hass.bus.async_fire(
                    "ai_home_copilot_notification",
                    {
                        "title": "Habitus Mining Complete",
                        "message": f"Discovered {mining_result.get('discovered_rules', 0)} behavioral patterns from {mining_result.get('total_input_events', 0)} events",
                        "notification_id": "habitus_mining_complete",
                    },
                )
            else:
                _LOGGER.error("Mining failed - no result from Core API")

        except Exception as e:
            _LOGGER.error("Error mining rules: %s", e)

    async def _handle_get_rules(self, hass: HomeAssistant, entry: ConfigEntry, call: ServiceCall) -> None:
        """Handle the get_rules service call."""
        try:
            from ...coordinator import CopilotDataUpdateCoordinator
            
            # Get coordinator
            legacy_data = hass.data[DOMAIN].get(entry.entry_id, {})
            coordinator: CopilotDataUpdateCoordinator = legacy_data.get("coordinator")
            
            if not coordinator:
                _LOGGER.error("No coordinator found")
                return

            # Get parameters
            limit = call.data.get("limit", 20)
            domain_filter = call.data.get("domain_filter")
            min_score = call.data.get("min_score", 0.0)

            # Build query parameters
            params = {"limit": limit}
            if domain_filter:
                params["domain_filter"] = domain_filter
            if min_score > 0:
                params["min_score"] = min_score

            # Fetch rules from Core API
            rules_result = await coordinator.api.get_with_auth("habitus/rules", params=params)

            if rules_result and "rules" in rules_result:
                rules = rules_result["rules"]
                _LOGGER.info("Retrieved %d rules", len(rules))
                
                # Create a detailed notification with top rules
                if rules:
                    top_rule = rules[0]
                    message = (
                        f"Found {len(rules)} behavioral patterns. "
                        f"Top rule: {top_rule.get('A', '')} → {top_rule.get('B', '')} "
                        f"(confidence: {top_rule.get('confidence', 0):.1%})"
                    )
                else:
                    message = "No behavioral patterns found matching criteria"
                
                hass.bus.async_fire(
                    "ai_home_copilot_notification",
                    {
                        "title": "Habitus Rules Retrieved",
                        "message": message,
                        "notification_id": "habitus_rules_retrieved",
                    },
                )
            else:
                _LOGGER.warning("No rules found or API error")

        except Exception as e:
            _LOGGER.error("Error getting rules: %s", e)

    async def _handle_reset_cache(self, hass: HomeAssistant, entry: ConfigEntry, call: ServiceCall) -> None:
        """Handle the reset_cache service call."""
        try:
            from ...coordinator import CopilotDataUpdateCoordinator
            
            # Get coordinator
            legacy_data = hass.data[DOMAIN].get(entry.entry_id, {})
            coordinator: CopilotDataUpdateCoordinator = legacy_data.get("coordinator")
            
            if coordinator:
                # Reset Core cache
                await coordinator.api.post_with_auth("habitus/reset")
            
            # Reset local buffer
            module_data = hass.data[DOMAIN][entry.entry_id]["habitus_miner"]
            module_data["event_buffer"].clear()
            module_data["last_mining_ts"] = None
            
            _LOGGER.info("Reset Habitus Miner cache")
            
            hass.bus.async_fire(
                "ai_home_copilot_notification",
                {
                    "title": "Habitus Cache Reset",
                    "message": "All cached rules and events have been cleared",
                    "notification_id": "habitus_cache_reset",
                },
            )

        except Exception as e:
            _LOGGER.error("Error resetting cache: %s", e)

    async def _handle_configure_mining(self, hass: HomeAssistant, entry: ConfigEntry, call: ServiceCall) -> None:
        """Handle the configure_mining service call."""
        try:
            module_data = hass.data[DOMAIN][entry.entry_id]["habitus_miner"]
            
            # Update configuration
            config_updated = False
            
            if "auto_mining_enabled" in call.data:
                module_data["auto_mining_enabled"] = call.data["auto_mining_enabled"]
                config_updated = True
            
            if "buffer_max_size" in call.data:
                module_data["buffer_max_size"] = call.data["buffer_max_size"]
                config_updated = True
            
            if "buffer_max_age_hours" in call.data:
                module_data["buffer_max_age_hours"] = call.data["buffer_max_age_hours"]
                config_updated = True
            
            if config_updated:
                _LOGGER.info("Updated Habitus Miner configuration")
                
                hass.bus.async_fire(
                    "ai_home_copilot_notification",
                    {
                        "title": "Habitus Configuration Updated",
                        "message": "Mining configuration has been updated successfully",
                        "notification_id": "habitus_config_updated",
                    },
                )

        except Exception as e:
            _LOGGER.error("Error configuring mining: %s", e)

    async def _fetch_ha_history(
        self, 
        hass: HomeAssistant, 
        days_back: int, 
        domains: list[str] | None = None,
        exclude_domains: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch events from HA history (simplified for v0.1)."""
        try:
            from datetime import datetime, timedelta
            
            # For v0.1, we use a simple approach
            # In production, this would use HA's history API
            _LOGGER.info(
                "History fetching not implemented in v0.1 - using event buffer only"
            )
            return []
            
        except Exception as e:
            _LOGGER.error("Error fetching HA history: %s", e)
            return []