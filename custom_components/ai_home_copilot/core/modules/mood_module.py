"""Mood Module v0.1 - HA Integration for local mood inference.

Implements the mood_module v0.1 spec as a CopilotModule.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, Event
from homeassistant.helpers.event import async_track_time_interval, async_track_state_change_event
import voluptuous as vol

from ...const import DOMAIN
from ..module import CopilotModule, ModuleContext
from ..performance import get_entity_state_cache, get_mood_score_cache, invalidate_caches_for_entity

_LOGGER = logging.getLogger(__name__)


class MoodModule:
    """Mood Module v0.1 implementation."""

    @property
    def name(self) -> str:
        return "mood_module"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the mood module for this config entry."""
        hass = ctx.hass
        entry = ctx.entry
        
        # Initialize module data
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        
        if entry.entry_id not in hass.data[DOMAIN]:
            hass.data[DOMAIN][entry.entry_id] = {}
        
        entry_data = hass.data[DOMAIN][entry.entry_id]
        entry_data["mood_module"] = {
            "config": self._create_default_config(hass),
            "tracked_entities": set(),
            "last_orchestration": {},
            "polling_unsub": None,
            "event_unsubs": []
        }
        
        mood_data = entry_data["mood_module"]
        
        # Register services
        await self._register_services(hass, entry.entry_id)
        
        # Set up entity tracking
        await self._setup_entity_tracking(hass, entry.entry_id, mood_data)
        
        # Set up polling fallback
        await self._setup_polling(hass, entry.entry_id, mood_data)
        
        _LOGGER.info("Mood module v0.1 initialized for entry %s", entry.entry_id)

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the mood module."""
        hass = ctx.hass
        entry = ctx.entry
        
        try:
            entry_data = hass.data[DOMAIN][entry.entry_id]
            mood_data = entry_data.get("mood_module", {})
            
            # Cancel polling
            polling_unsub = mood_data.get("polling_unsub")
            if polling_unsub:
                polling_unsub()
            
            # Cancel event tracking
            for unsub in mood_data.get("event_unsubs", []):
                unsub()
            
            # Clear data
            if "mood_module" in entry_data:
                del entry_data["mood_module"]
            
            _LOGGER.info("Mood module unloaded for entry %s", entry.entry_id)
            return True
            
        except Exception as e:
            _LOGGER.error("Error unloading mood module: %s", e)
            return False

    def _create_default_config(self, hass: HomeAssistant) -> Dict[str, Any]:
        """Create default configuration based on available entities."""
        
        # Discover relevant entities (simplified)
        config = {
            "zones": {
                "wohnbereich": {
                    "motion_entities": ["binary_sensor.motion_wohnzimmer"],
                    "light_entities": ["light.wohnzimmer"], 
                    "media_entities": ["media_player.wohnbereich"],
                    "illuminance_entity": "sensor.illuminance_wohnzimmer"
                }
            },
            "min_dwell_time_seconds": 600,
            "action_cooldown_seconds": 120,
            "polling_interval_seconds": 300  # 5 minutes
        }
        
        return config

    async def _register_services(self, hass: HomeAssistant, entry_id: str) -> None:
        """Register mood module services."""
        
        async def _handle_orchestrate_zone(call: ServiceCall) -> None:
            zone_name = call.data.get("zone_name")
            dry_run = call.data.get("dry_run", False)
            force_actions = call.data.get("force_actions", False)
            
            if not zone_name:
                _LOGGER.error("zone_name parameter required")
                return
            
            await self._orchestrate_zone(hass, entry_id, zone_name, dry_run, force_actions)

        async def _handle_orchestrate_all(call: ServiceCall) -> None:
            dry_run = call.data.get("dry_run", False)
            force_actions = call.data.get("force_actions", False)
            
            await self._orchestrate_all_zones(hass, entry_id, dry_run, force_actions)

        async def _handle_force_mood(call: ServiceCall) -> None:
            zone_name = call.data.get("zone_name")
            mood_state = call.data.get("mood_state")
            duration_minutes = call.data.get("duration_minutes")
            
            if not zone_name or not mood_state:
                _LOGGER.error("zone_name and mood_state parameters required")
                return
            
            await self._force_mood(hass, entry_id, zone_name, mood_state, duration_minutes)

        # Register services (idempotent)
        service_name = f"mood_orchestrate_zone_{entry_id}"
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN,
                service_name,
                _handle_orchestrate_zone,
                schema=vol.Schema({
                    vol.Required("zone_name"): str,
                    vol.Optional("dry_run", default=False): bool,
                    vol.Optional("force_actions", default=False): bool
                })
            )

        service_name = f"mood_orchestrate_all_{entry_id}"
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN,
                service_name,
                _handle_orchestrate_all,
                schema=vol.Schema({
                    vol.Optional("dry_run", default=False): bool,
                    vol.Optional("force_actions", default=False): bool
                })
            )

        service_name = f"mood_force_mood_{entry_id}"
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN,
                service_name, 
                _handle_force_mood,
                schema=vol.Schema({
                    vol.Required("zone_name"): str,
                    vol.Required("mood_state"): str,
                    vol.Optional("duration_minutes"): int
                })
            )

    async def _setup_entity_tracking(self, hass: HomeAssistant, entry_id: str, mood_data: Dict[str, Any]) -> None:
        """Set up state change event tracking for relevant entities."""
        
        config = mood_data["config"]
        tracked_entities = set()
        
        # Collect all entities that should trigger mood re-evaluation
        for zone_config in config["zones"].values():
            tracked_entities.update(zone_config.get("motion_entities", []))
            tracked_entities.update(zone_config.get("light_entities", []))
            tracked_entities.update(zone_config.get("media_entities", []))
            
            if zone_config.get("illuminance_entity"):
                tracked_entities.add(zone_config["illuminance_entity"])
        
        mood_data["tracked_entities"] = tracked_entities
        
        async def _handle_state_change(event: Event) -> None:
            """Handle state change events for tracked entities."""
            entity_id = event.data.get("entity_id")
            
            if entity_id in tracked_entities:
                _LOGGER.debug("State change detected for %s, triggering mood evaluation", entity_id)
                # Invalidate caches for this entity
                await invalidate_caches_for_entity(entity_id)
                # Delay slightly to allow state to stabilize
                await asyncio.sleep(2)
                await self._orchestrate_all_zones(hass, entry_id, dry_run=False, force_actions=False)
        
        # Track state changes
        unsub = async_track_state_change_event(hass, list(tracked_entities), _handle_state_change)
        mood_data["event_unsubs"].append(unsub)

    async def _setup_polling(self, hass: HomeAssistant, entry_id: str, mood_data: Dict[str, Any]) -> None:
        """Set up polling fallback to catch missed events."""
        
        config = mood_data["config"]
        interval_seconds = config.get("polling_interval_seconds", 300)
        
        async def _handle_poll(now: datetime) -> None:
            """Periodic polling handler."""
            _LOGGER.debug("Mood module polling trigger")
            await self._orchestrate_all_zones(hass, entry_id, dry_run=False, force_actions=False)
        
        # Set up polling
        unsub = async_track_time_interval(hass, _handle_poll, timedelta(seconds=interval_seconds))
        mood_data["polling_unsub"] = unsub

    async def _orchestrate_zone(
        self, 
        hass: HomeAssistant, 
        entry_id: str, 
        zone_name: str, 
        dry_run: bool = False,
        force_actions: bool = False
    ) -> None:
        """Orchestrate mood inference and actions for a specific zone."""
        
        try:
            entry_data = hass.data[DOMAIN][entry_id]
            config = entry_data["mood_module"]["config"]
            
            if zone_name not in config["zones"]:
                _LOGGER.error("Unknown zone: %s", zone_name)
                return
            
            zone_config = config["zones"][zone_name]
            
            # Check cache for existing mood score (if not forcing)
            mood_cache = get_mood_score_cache()
            if not force_actions and not dry_run:
                cached_mood = await mood_cache.get_mood(zone_name)
                if cached_mood and cached_mood.get("valid", True):
                    _LOGGER.debug("Using cached mood for zone %s: %s", zone_name, cached_mood.get("mood"))
                    return
            
            # Collect sensor data
            sensor_data = await self._collect_sensor_data(hass, zone_config)
            
            # Call Core Add-on API for mood inference
            result = await self._call_core_api(
                "POST", 
                f"/api/v1/mood/zones/{zone_name}/orchestrate",
                {
                    "sensor_data": sensor_data,
                    "dry_run": dry_run,
                    "force_actions": force_actions
                }
            )
            
            if result and result.get("ok"):
                orchestration_result = result.get("result", {})
                
                # Execute actions locally if not dry run
                if not dry_run and not orchestration_result.get("skipped_reason"):
                    actions = orchestration_result.get("actions", {})
                    service_calls = actions.get("service_calls", [])
                    
                    if service_calls:
                        await self._execute_service_calls(hass, service_calls)
                
                # Store result
                entry_data["mood_module"]["last_orchestration"][zone_name] = orchestration_result
                
                # Cache the mood score
                mood_data = orchestration_result.get("mood", {})
                if mood_data:
                    await mood_cache.set_mood(zone_name, {
                        "mood": mood_data.get("mood"),
                        "confidence": mood_data.get("confidence", 0.0),
                        "valid": True,
                        "timestamp": datetime.now().isoformat()
                    }, ttl_seconds=30.0)
                
                _LOGGER.info("Zone %s mood orchestration completed: %s", 
                           zone_name, orchestration_result.get("mood", {}).get("mood"))
            else:
                _LOGGER.error("Mood orchestration API call failed: %s", result)
                
        except Exception as e:
            _LOGGER.error("Mood orchestration failed for zone %s: %s", zone_name, e)

    async def _orchestrate_all_zones(
        self, 
        hass: HomeAssistant, 
        entry_id: str, 
        dry_run: bool = False,
        force_actions: bool = False
    ) -> None:
        """Orchestrate mood inference for all configured zones."""
        
        try:
            entry_data = hass.data[DOMAIN][entry_id]
            config = entry_data["mood_module"]["config"]
            
            for zone_name in config["zones"].keys():
                await self._orchestrate_zone(hass, entry_id, zone_name, dry_run, force_actions)
                
        except Exception as e:
            _LOGGER.error("Mood orchestration failed for all zones: %s", e)

    async def _force_mood(
        self, 
        hass: HomeAssistant, 
        entry_id: str, 
        zone_name: str, 
        mood_state: str,
        duration_minutes: Optional[int] = None
    ) -> None:
        """Force a specific mood for a zone."""
        
        try:
            result = await self._call_core_api(
                "POST",
                f"/api/v1/mood/zones/{zone_name}/force_mood",
                {
                    "mood": mood_state,
                    "duration_minutes": duration_minutes
                }
            )
            
            if result and result.get("ok"):
                _LOGGER.info("Forced mood %s for zone %s", mood_state, zone_name)
            else:
                _LOGGER.error("Force mood API call failed: %s", result)
                
        except Exception as e:
            _LOGGER.error("Failed to force mood for zone %s: %s", zone_name, e)

    async def _collect_sensor_data(self, hass: HomeAssistant, zone_config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect current sensor data for a zone using cache."""
        
        sensor_data = {}
        entity_cache = get_entity_state_cache()
        
        # Collect all relevant entity IDs
        entity_ids = []
        entity_ids.extend(zone_config.get("motion_entities", []))
        entity_ids.extend(zone_config.get("light_entities", []))
        entity_ids.extend(zone_config.get("media_entities", []))
        
        if zone_config.get("illuminance_entity"):
            entity_ids.append(zone_config["illuminance_entity"])
        
        # Use cache for entity states
        for entity_id in entity_ids:
            state = await entity_cache.get_state(hass, entity_id)
            if state:
                sensor_data[entity_id] = state
        
        return sensor_data

    async def _execute_service_calls(self, hass: HomeAssistant, service_calls: List[Dict[str, Any]]) -> None:
        """Execute HA service calls."""
        
        for call_data in service_calls:
            try:
                domain = call_data.get("domain")
                service = call_data.get("service")
                target = call_data.get("target", {})
                service_data = call_data.get("service_data", {})
                
                if not domain or not service:
                    _LOGGER.warning("Invalid service call data: %s", call_data)
                    continue
                
                await hass.services.async_call(
                    domain, 
                    service, 
                    service_data,
                    target=target
                )
                
                _LOGGER.debug("Executed service call: %s.%s", domain, service)
                
            except Exception as e:
                _LOGGER.error("Failed to execute service call %s: %s", call_data, e)

    async def _call_core_api(self, method: str, path: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Call the Core Add-on API."""
        
        # In a real implementation, this would connect to the Core Add-on
        # For now, we'll simulate the response
        _LOGGER.debug("Would call Core API: %s %s with data: %s", method, path, data)
        
        # Simulate successful response
        return {
            "ok": True,
            "result": {
                "mood": {"mood": "relax", "confidence": 0.8},
                "skipped_reason": "Simulated response - Core API not connected"
            }
        }