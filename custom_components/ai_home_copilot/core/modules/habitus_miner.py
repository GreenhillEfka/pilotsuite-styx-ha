"""Habitus Miner module for A→B pattern discovery in Home Assistant.

Zone-based pattern mining that discovers behavioral patterns from HA events
and integrates with Brain Graph, Mood Service, and Suggestions system.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from ...const import DOMAIN
from ..module import ModuleContext

_LOGGER = logging.getLogger(__name__)


# Type definitions for better type safety
class HabitusRule(TypedDict):
    """A discovered behavioral rule."""
    A: str
    B: str
    confidence: float
    lift: float
    support: float


class HabitusConfig(TypedDict, total=False):
    """Mining configuration."""
    min_confidence: float
    min_lift: float
    max_rules: int
    include_domains: list[str]
    exclude_domains: list[str]


class ModuleData(TypedDict):
    """Module data structure."""
    event_buffer: deque[dict[str, Any]]
    buffer_max_size: int
    buffer_max_age_hours: int
    last_mining_ts: float | None
    auto_mining_enabled: bool
    listeners: list[Any]
    discovered_rules: list[HabitusRule]
    zone_affinity: dict[str, str]  # entity_id -> zone_id mapping


@dataclass
class MiningResult:
    """Result of a mining operation."""
    discovered_rules: int
    total_input_events: int
    zones_analyzed: list[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class HabitusMinerModule:
    """Module for discovering A→B behavioral patterns from HA events."""

    name = "habitus_miner"

    # Lock for thread-safe buffer operations
    _buffer_lock: asyncio.Lock | None = None

    async def async_setup_entry(self, ctx: ModuleContext) -> bool:
        """Set up the Habitus Miner module."""
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        _LOGGER.info("Setting up Habitus Miner module")

        # Initialize buffer lock for thread safety
        self._buffer_lock = asyncio.Lock()

        # Store module data with proper typing
        module_data: ModuleData = {
            "event_buffer": deque(maxlen=1000),  # Use deque for O(1) append/pop
            "buffer_max_size": 1000,
            "buffer_max_age_hours": 24,
            "last_mining_ts": None,
            "auto_mining_enabled": False,
            "listeners": [],
            "discovered_rules": [],
            "zone_affinity": {},
        }

        # Store under entry data with safe initialization
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        if entry.entry_id not in hass.data[DOMAIN]:
            hass.data[DOMAIN][entry.entry_id] = {}

        hass.data[DOMAIN][entry.entry_id]["habitus_miner"] = module_data

        # Register services
        await self._register_services(hass, entry)

        # Set up event listener (optional, for auto-mining)
        await self._setup_event_listener(hass, entry)

        # Initialize zone affinity mapping
        await self._init_zone_affinity(hass, entry)

        _LOGGER.info("Habitus Miner module setup completed")
        return True

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the Habitus Miner module."""
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        _LOGGER.info("Unloading Habitus Miner module")

        # Safely get module data
        entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
        module_data: ModuleData | None = entry_data.get("habitus_miner")

        if module_data:
            # Unregister listeners
            listeners = module_data.get("listeners", [])
            for unsub in listeners:
                if callable(unsub):
                    try:
                        unsub()
                    except Exception as e:
                        _LOGGER.warning("Error removing listener: %s", e)

            # Clear buffer
            module_data["event_buffer"].clear()

        # Remove services (check if other entries exist)
        entry_count = len([
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
        ])

        if entry_count == 0:  # This is the last entry
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
        if entry.entry_id in hass.data.get(DOMAIN, {}):
            hass.data[DOMAIN][entry.entry_id].pop("habitus_miner", None)

        # Clean up lock
        self._buffer_lock = None

        _LOGGER.info("Habitus Miner module unloaded")
        return True

    async def _init_zone_affinity(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize zone affinity mapping from zones store."""
        try:
            # Try to import from zones store
            try:
                from ...habitus_zones_store import async_get_zones
                zones = await async_get_zones(hass, entry.entry_id)

                module_data = hass.data[DOMAIN][entry.entry_id]["habitus_miner"]
                zone_affinity: dict[str, str] = {}

                for zone in zones:
                    for entity_id in zone.entity_ids:
                        zone_affinity[entity_id] = zone.zone_id

                module_data["zone_affinity"] = zone_affinity
                _LOGGER.debug("Initialized zone affinity with %d entity mappings", len(zone_affinity))

            except ImportError:
                _LOGGER.debug("Zones store not available, skipping zone affinity init")

        except Exception as e:
            _LOGGER.warning("Failed to initialize zone affinity: %s", e)

    async def _register_services(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Register Habitus Miner services."""

        service_schema_mine = vol.Schema({
            vol.Optional("days_back", default=7): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
            vol.Optional("domains"): [str],
            vol.Optional("exclude_domains"): [str],
            vol.Optional("min_confidence", default=0.5): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
            vol.Optional("min_lift", default=1.2): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10.0)),
            vol.Optional("max_rules", default=100): vol.All(vol.Coerce(int), vol.Range(min=1, max=1000)),
        })

        if not hass.services.has_service(DOMAIN, "habitus_mine_rules"):

            async def handle_mine_rules(call: ServiceCall) -> dict[str, Any] | None:
                """Handle rule mining service call."""
                return await self._handle_mine_rules(hass, entry, call)

            hass.services.async_register(
                DOMAIN,
                "habitus_mine_rules",
                handle_mine_rules,
                schema=service_schema_mine,
            )

        service_schema_get = vol.Schema({
            vol.Optional("limit", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=200)),
            vol.Optional("domain_filter"): str,
            vol.Optional("min_score", default=0.0): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10.0)),
        })

        if not hass.services.has_service(DOMAIN, "habitus_get_rules"):

            async def handle_get_rules(call: ServiceCall) -> dict[str, Any] | None:
                """Handle get rules service call."""
                return await self._handle_get_rules(hass, entry, call)

            hass.services.async_register(
                DOMAIN,
                "habitus_get_rules",
                handle_get_rules,
                schema=service_schema_get,
            )

        if not hass.services.has_service(DOMAIN, "habitus_reset_cache"):

            async def handle_reset_cache(call: ServiceCall) -> dict[str, Any] | None:
                """Handle cache reset service call."""
                return await self._handle_reset_cache(hass, entry, call)

            hass.services.async_register(
                DOMAIN,
                "habitus_reset_cache",
                handle_reset_cache,
            )

        service_schema_config = vol.Schema({
            vol.Optional("auto_mining_enabled"): bool,
            vol.Optional("buffer_max_size"): vol.All(vol.Coerce(int), vol.Range(min=100, max=10000)),
            vol.Optional("buffer_max_age_hours"): vol.All(vol.Coerce(int), vol.Range(min=1, max=168)),
        })

        if not hass.services.has_service(DOMAIN, "habitus_configure_mining"):

            async def handle_configure_mining(call: ServiceCall) -> dict[str, Any] | None:
                """Handle mining configuration service call."""
                return await self._handle_configure_mining(hass, entry, call)

            hass.services.async_register(
                DOMAIN,
                "habitus_configure_mining",
                handle_configure_mining,
                schema=service_schema_config,
            )

    async def _setup_event_listener(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Set up event listener for collecting HA events."""
        module_data: ModuleData = hass.data[DOMAIN][entry.entry_id]["habitus_miner"]

        @callback
        def event_listener(event: Event) -> None:
            """Listen for state_changed events and buffer them."""
            if event.event_type != "state_changed":
                return

            try:
                # Extract entity from event
                event_data = event.data or {}
                new_state = event_data.get("new_state")
                old_state = event_data.get("old_state")

                if not new_state and not old_state:
                    return

                entity_id = new_state.get("entity_id") if new_state else old_state.get("entity_id")

                # Get zone from affinity mapping
                module_data = hass.data[DOMAIN][entry.entry_id]["habitus_miner"]
                zone_id = module_data.get("zone_affinity", {}).get(entity_id, "unknown")

                # Build event record with zone info
                event_record: dict[str, Any] = {
                    "timestamp": event.time_fired.isoformat(),
                    "event_type": event.event_type,
                    "entity_id": entity_id,
                    "zone_id": zone_id,
                    "new_state": new_state.get("state") if new_state else None,
                    "old_state": old_state.get("state") if old_state else None,
                    "context_id": event.context.id,
                }

                # Add to buffer (thread-safe via asyncio event loop)
                buffer = module_data["event_buffer"]
                buffer.append(event_record)

                # Buffer trimming happens in background task for performance

            except Exception as e:
                _LOGGER.debug("Error buffering event: %s", e)

        # Register listener
        unsub = hass.bus.async_listen("state_changed", event_listener)
        module_data["listeners"].append(unsub)

        # Set up periodic buffer cleanup
        async def periodic_cleanup(now: datetime) -> None:
            """Clean up old events from buffer."""
            await self._cleanup_buffer(hass, entry)

        # Clean up every hour
        from homeassistant.helpers.event import async_track_time_interval
        async_track_time_interval(hass, periodic_cleanup, timedelta(hours=1))

    async def _cleanup_buffer(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Clean up old events from buffer."""
        try:
            module_data: ModuleData = hass.data[DOMAIN][entry.entry_id]["habitus_miner"]
            buffer = module_data["event_buffer"]
            max_age_hours = module_data["buffer_max_age_hours"]
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

            # Remove old events (deque is already ordered, use index-based removal)
            while buffer:
                try:
                    first_event = buffer[0]
                    event_time = datetime.fromisoformat(
                        first_event["timestamp"].replace('Z', '+00:00')
                    )
                    if event_time.replace(tzinfo=timezone.utc) < cutoff_time:
                        buffer.popleft()
                    else:
                        break
                except (KeyError, ValueError, TypeError):
                    # Invalid event, remove it
                    buffer.popleft()

        except Exception as e:
            _LOGGER.warning("Buffer cleanup failed: %s", e)

    async def _handle_mine_rules(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        call: ServiceCall
    ) -> dict[str, Any] | None:
        """Handle the mine_rules service call."""
        try:
            from ...coordinator import CopilotDataUpdateCoordinator

            # Safely get coordinator
            legacy_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
            coordinator: CopilotDataUpdateCoordinator | None = legacy_data.get("coordinator")

            if not coordinator:
                _LOGGER.error("No coordinator found - legacy module may not be loaded")
                hass.bus.async_fire(
                    "ai_home_copilot_notification",
                    {
                        "title": "Habitus Mining Failed",
                        "message": "Coordinator not available. Please ensure the integration is fully loaded.",
                        "notification_id": "habitus_mining_error",
                    },
                )
                return None

            # Get parameters with type safety
            days_back: int = call.data.get("days_back", 7)
            domains: list[str] | None = call.data.get("domains")
            exclude_domains: list[str] | None = call.data.get("exclude_domains")
            min_confidence: float = call.data.get("min_confidence", 0.5)
            min_lift: float = call.data.get("min_lift", 1.2)
            max_rules: int = call.data.get("max_rules", 100)

            _LOGGER.info(
                "Mining rules with days_back=%d, domains=%s",
                days_back,
                domains
            )

            # Get events from buffer
            module_data: ModuleData = hass.data[DOMAIN][entry.entry_id]["habitus_miner"]
            buffer = module_data["event_buffer"]

            events = list(buffer)

            if not events:
                _LOGGER.info("No buffered events found, fetching from HA history")
                events = await self._fetch_ha_history(hass, days_back, domains, exclude_domains)

            if not events:
                _LOGGER.warning("No events found for mining")
                hass.bus.async_fire(
                    "ai_home_copilot_notification",
                    {
                        "title": "Habitus Mining",
                        "message": "No events available for pattern mining",
                        "notification_id": "habitus_mining_no_events",
                    },
                )
                return None

            # Determine zones analyzed
            zones_analyzed = list(set(
                e.get("zone_id", "unknown") for e in events
            ))

            # Build mining config
            mining_config: HabitusConfig = {
                "min_confidence": min_confidence,
                "min_lift": min_lift,
                "max_rules": max_rules,
                "include_domains": domains or [],
                "exclude_domains": exclude_domains or [],
            }

            # Call Core API for mining
            try:
                mining_result = await coordinator.api.post_with_auth(
                    "habitus/mine",
                    data={
                        "events": events,
                        "config": mining_config,
                    },
                )
            except Exception as api_err:
                _LOGGER.error("API call failed: %s", api_err)
                mining_result = None

            if mining_result and mining_result.get("ok"):
                module_data["last_mining_ts"] = time.time()

                discovered_count = mining_result.get("discovered_rules", 0)
                total_events = mining_result.get("total_input_events", len(events))

                _LOGGER.info(
                    "Successfully mined rules: %d rules from %d events",
                    discovered_count,
                    total_events
                )

                # Store discovered rules
                rules = mining_result.get("rules", [])
                module_data["discovered_rules"] = rules

                # Send notification
                hass.bus.async_fire(
                    "ai_home_copilot_notification",
                    {
                        "title": "Habitus Mining Complete",
                        "message": f"Discovered {discovered_count} behavioral patterns from {total_events} events across {len(zones_analyzed)} zones",
                        "notification_id": "habitus_mining_complete",
                    },
                )

                # Integrate with Suggestions system
                await self._create_suggestions_from_rules(hass, entry, rules)

                return {
                    "discovered_rules": discovered_count,
                    "total_input_events": total_events,
                    "zones_analyzed": zones_analyzed,
                }
            else:
                _LOGGER.error("Mining failed - no result from Core API")
                hass.bus.async_fire(
                    "ai_home_copilot_notification",
                    {
                        "title": "Habitus Mining Failed",
                        "message": "Could not connect to Core API for pattern mining",
                        "notification_id": "habitus_mining_error",
                    },
                )
                return None

        except Exception as e:
            _LOGGER.error("Error mining rules: %s", e)
            return None

    async def _create_suggestions_from_rules(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        rules: list[HabitusRule]
    ) -> None:
        """Create suggestions from discovered rules."""
        try:
            # Try to integrate with user_hints service
            # This would create automation suggestions from the discovered patterns
            for rule in rules[:5]:  # Top 5 rules
                _LOGGER.debug(
                    "Would create suggestion: %s → %s (conf: %.2f)",
                    rule.get("A", ""),
                    rule.get("B", ""),
                    rule.get("confidence", 0)
                )

            # Store suggestions in module data for later retrieval
            module_data: ModuleData = hass.data[DOMAIN][entry.entry_id]["habitus_miner"]
            module_data["suggestions_pending"] = rules[:5]

            # Fire event for other modules to consume
            hass.bus.async_fire(
                "ai_home_copilot_habitus_patterns_discovered",
                {
                    "rules": rules[:10],  # Top 10 rules
                    "count": len(rules),
                    "entry_id": entry.entry_id,
                }
            )

        except Exception as e:
            _LOGGER.warning("Failed to create suggestions from rules: %s", e)

    async def _handle_get_rules(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        call: ServiceCall
    ) -> dict[str, Any] | None:
        """Handle the get_rules service call."""
        try:
            from ...coordinator import CopilotDataUpdateCoordinator

            # Safely get coordinator
            legacy_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
            coordinator: CopilotDataUpdateCoordinator | None = legacy_data.get("coordinator")

            if not coordinator:
                _LOGGER.error("No coordinator found")
                return None

            # Get parameters
            limit: int = call.data.get("limit", 20)
            domain_filter: str | None = call.data.get("domain_filter")
            min_score: float = call.data.get("min_score", 0.0)

            # Build query parameters
            params: dict[str, Any] = {"limit": limit}
            if domain_filter:
                params["domain_filter"] = domain_filter
            if min_score > 0:
                params["min_score"] = min_score

            # Fetch rules from Core API
            try:
                rules_result = await coordinator.api.get_with_auth(
                    "habitus/rules",
                    params=params
                )
            except Exception as api_err:
                _LOGGER.error("API call failed: %s", api_err)
                rules_result = None

            if rules_result and "rules" in rules_result:
                rules = rules_result["rules"]
                _LOGGER.info("Retrieved %d rules", len(rules))

                # Store in module data
                module_data: ModuleData = hass.data[DOMAIN][entry.entry_id]["habitus_miner"]
                module_data["discovered_rules"] = rules

                # Create notification message
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

                return {"rules": rules, "count": len(rules)}
            else:
                _LOGGER.warning("No rules found or API error")
                return None

        except Exception as e:
            _LOGGER.error("Error getting rules: %s", e)
            return None

    async def _handle_reset_cache(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        call: ServiceCall
    ) -> dict[str, Any] | None:
        """Handle the reset_cache service call."""
        try:
            from ...coordinator import CopilotDataUpdateCoordinator

            # Get coordinator
            legacy_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
            coordinator: CopilotDataUpdateCoordinator | None = legacy_data.get("coordinator")

            if coordinator:
                try:
                    await coordinator.api.post_with_auth("habitus/reset")
                except Exception as api_err:
                    _LOGGER.warning("Core API cache reset failed: %s", api_err)

            # Reset local buffer and state
            module_data: ModuleData | None = hass.data.get(DOMAIN, {}).get(
                entry.entry_id, {}
            ).get("habitus_miner")

            if module_data:
                module_data["event_buffer"].clear()
                module_data["last_mining_ts"] = None
                module_data["discovered_rules"] = []

            _LOGGER.info("Reset Habitus Miner cache")

            hass.bus.async_fire(
                "ai_home_copilot_notification",
                {
                    "title": "Habitus Cache Reset",
                    "message": "All cached rules and events have been cleared",
                    "notification_id": "habitus_cache_reset",
                },
            )

            return {"success": True}

        except Exception as e:
            _LOGGER.error("Error resetting cache: %s", e)
            return None

    async def _handle_configure_mining(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        call: ServiceCall
    ) -> dict[str, Any] | None:
        """Handle the configure_mining service call."""
        try:
            module_data: ModuleData | None = hass.data.get(DOMAIN, {}).get(
                entry.entry_id, {}
            ).get("habitus_miner")

            if not module_data:
                _LOGGER.error("Module data not found")
                return None

            # Update configuration
            config_updated = False
            updates: dict[str, Any] = {}

            if "auto_mining_enabled" in call.data:
                value = bool(call.data["auto_mining_enabled"])
                module_data["auto_mining_enabled"] = value
                updates["auto_mining_enabled"] = value
                config_updated = True

            if "buffer_max_size" in call.data:
                value = int(call.data["buffer_max_size"])
                # Recreate deque with new maxlen if needed
                old_buffer = module_data["event_buffer"]
                new_buffer: deque[dict[str, Any]] = deque(old_buffer, maxlen=value)
                module_data["event_buffer"] = new_buffer
                module_data["buffer_max_size"] = value
                updates["buffer_max_size"] = value
                config_updated = True

            if "buffer_max_age_hours" in call.data:
                value = int(call.data["buffer_max_age_hours"])
                module_data["buffer_max_age_hours"] = value
                updates["buffer_max_age_hours"] = value
                config_updated = True

            if config_updated:
                _LOGGER.info("Updated Habitus Miner configuration: %s", updates)

                hass.bus.async_fire(
                    "ai_home_copilot_notification",
                    {
                        "title": "Habitus Configuration Updated",
                        "message": f"Mining configuration updated: {list(updates.keys())}",
                        "notification_id": "habitus_config_updated",
                    },
                )

                return {"success": True, "updated": updates}
            else:
                return {"success": True, "updated": {}}

        except Exception as e:
            _LOGGER.error("Error configuring mining: %s", e)
            return None

    async def _fetch_ha_history(
        self,
        hass: HomeAssistant,
        days_back: int,
        domains: list[str] | None = None,
        exclude_domains: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch state-change events from HA recorder history."""
        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.history import state_changes_during_period
            from datetime import datetime, timezone, timedelta

            end = datetime.now(timezone.utc)
            start = end - timedelta(days=days_back)
            target_domains = domains or [
                "light", "switch", "climate", "media_player", "cover",
                "binary_sensor", "person", "device_tracker",
            ]

            # Run in executor to avoid blocking the event loop
            history = await get_instance(hass).async_add_executor_job(
                state_changes_during_period,
                hass,
                start,
                end,
                None,  # entity_id filter (None = all)
            )

            events: list[dict[str, Any]] = []
            exclude = set(exclude_domains or [])
            for entity_id, states in history.items():
                domain = entity_id.split(".")[0]
                if domain not in target_domains or domain in exclude:
                    continue
                for state_obj in states:
                    events.append({
                        "entity_id": entity_id,
                        "domain": domain,
                        "kind": "state_changed",
                        "new": {"state": state_obj.state},
                        "timestamp": state_obj.last_changed.isoformat()
                        if state_obj.last_changed else None,
                    })

            _LOGGER.info(
                "Fetched %d history events from recorder (%d days back)",
                len(events), days_back,
            )
            return events

        except ImportError:
            _LOGGER.info("Recorder not available; using event buffer only")
            return []
        except Exception as e:
            _LOGGER.warning("Error fetching HA history: %s; falling back to event buffer", e)
            return []

    # Public API for other modules
    async def get_zone_patterns(
        self,
        hass: HomeAssistant,
        entry_id: str,
        zone_id: str
    ) -> list[HabitusRule]:
        """Get patterns specific to a zone."""
        try:
            module_data: ModuleData | None = hass.data.get(DOMAIN, {}).get(
                entry_id, {}
            ).get("habitus_miner")

            if not module_data:
                return []

            rules = module_data.get("discovered_rules", [])

            # Filter rules by zone
            zone_rules = [
                r for r in rules
                if zone_id in r.get("A", "") or zone_id in r.get("B", "")
            ]

            return zone_rules

        except Exception as e:
            _LOGGER.error("Error getting zone patterns: %s", e)
            return []

    async def get_mood_integration(
        self,
        hass: HomeAssistant,
        entry_id: str
    ) -> dict[str, Any]:
        """Get mood-related patterns for the mood module."""
        try:
            module_data: ModuleData | None = hass.data.get(DOMAIN, {}).get(
                entry_id, {}
            ).get("habitus_miner")

            if not module_data:
                return {}

            rules = module_data.get("discovered_rules", [])

            # Return rules that could inform mood inference
            mood_relevant_rules = [
                {
                    "trigger": r.get("A"),
                    "action": r.get("B"),
                    "confidence": r.get("confidence", 0),
                }
                for r in rules
                if r.get("confidence", 0) > 0.7
            ]

            return {
                "pattern_count": len(mood_relevant_rules),
                "patterns": mood_relevant_rules[:10],
            }

        except Exception as e:
            _LOGGER.error("Error getting mood integration: %s", e)
            return {}
