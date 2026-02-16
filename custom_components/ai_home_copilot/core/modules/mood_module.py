"""Mood Module v0.2 - HA Integration for local mood inference.

Implements the mood_module v0.2 spec as a CopilotModule.
Optimized with:
- Proper type hints
- Improved exception handling
- Character system integration
- Performance improvements
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, Event
from homeassistant.helpers.event import async_track_time_interval, async_track_state_change_event
import voluptuous as vol

from ...const import DOMAIN
from ..module import CopilotModule, ModuleContext
from ..performance import get_mood_cache, TTLCache

if TYPE_CHECKING:
    # CharacterService is now CharacterModule in character_module.py
    # Use forward ref to avoid circular import
    pass

_LOGGER = logging.getLogger(__name__)

# Type definitions for better readability
MoodData = Dict[str, Any]
ZoneConfig = Dict[str, Any]
ServiceCallDict = Dict[str, Any]
APIResponse = Dict[str, Any]


class MoodModule(CopilotModule):
    """Mood Module v0.2 implementation.
    
    Features:
    - Zone-based mood inference using HA sensor data
    - Event-driven and polling-based re-evaluation
    - Character system integration for mood weighting
    - Service APIs for orchestration
    """

    # Configuration schema
    CONFIG_SCHEMA = vol.Schema({
        vol.Required("zones"): vol.Schema({
            str: {
                vol.Required("motion_entities"): [str],
                vol.Required("light_entities"): [str],
                vol.Required("media_entities"): [str],
                vol.Optional("illuminance_entity"): str,
            }
        }),
        vol.Optional("min_dwell_time_seconds", default=600): int,
        vol.Optional("action_cooldown_seconds", default=120): int,
        vol.Optional("polling_interval_seconds", default=300): int,
    })

    def __init__(self) -> None:
        """Initialize the mood module."""
        self._hass: HomeAssistant | None = None
        self._entry_id: str | None = None
        self._character_service: CharacterService | None = None

    @property
    def name(self) -> str:
        """Return module name."""
        return "mood_module"

    async def async_setup_entry(self, ctx: ModuleContext) -> bool:
        """Set up the mood module for this config entry.
        
        Returns:
            True if setup was successful.
        """
        self._hass = ctx.hass
        self._entry_id = ctx.entry.entry_id
        
        # Initialize module data
        if DOMAIN not in ctx.hass.data:
            ctx.hass.data[DOMAIN] = {}
        
        if ctx.entry.entry_id not in ctx.hass.data[DOMAIN]:
            ctx.hass.data[DOMAIN][ctx.entry.entry_id] = {}
        
        entry_data = ctx.hass.data[DOMAIN][ctx.entry.entry_id]
        
        # Validate and store config
        config = self._create_default_config(ctx.hass)
        self._validate_config(config)
        
        entry_data["mood_module"] = {
            "config": config,
            "tracked_entities": [],  # Use list instead of set for JSON serialization
            "last_orchestration": {},
            "polling_unsub": None,
            "event_unsubs": []
        }
        
        mood_data = entry_data["mood_module"]
        
        # Initialize character service if available
        await self._init_character_service(ctx)
        
        # Register services
        await self._register_services(ctx.hass, ctx.entry.entry_id)
        
        # Set up entity tracking
        await self._setup_entity_tracking(ctx.hass, ctx.entry.entry_id, mood_data)
        
        # Set up polling fallback
        await self._setup_polling(ctx.hass, ctx.entry.entry_id, mood_data)
        
        _LOGGER.info("Mood module v0.2 initialized for entry %s", ctx.entry.entry_id)
        return True

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the mood module.
        
        Returns:
            True if unload was successful.
        """
        if ctx.hass is None or ctx.entry is None:
            _LOGGER.warning("Mood module not properly initialized")
            return False
        
        try:
            entry_data = ctx.hass.data.get(DOMAIN, {}).get(ctx.entry.entry_id, {})
            mood_data = entry_data.get("mood_module", {})
            
            # Cancel polling
            polling_unsub = mood_data.get("polling_unsub")
            if polling_unsub and hasattr(polling_unsub, 'call'):
                polling_unsub()
            elif polling_unsub:
                polling_unsub()
            
            # Cancel event tracking
            for unsub in mood_data.get("event_unsubs", []):
                if unsub and hasattr(unsub, 'call'):
                    unsub()
                elif unsub:
                    unsub()
            
            # Clear data
            if "mood_module" in entry_data:
                del entry_data["mood_module"]
            
            _LOGGER.info("Mood module unloaded for entry %s", ctx.entry.entry_id)
            return True
            
        except Exception as e:
            _LOGGER.error("Error unloading mood module: %s", e)
            return False

    def _create_default_config(self, hass: HomeAssistant) -> Dict[str, Any]:
        """Create default configuration based on available entities.
        
        Args:
            hass: Home Assistant instance.
            
        Returns:
            Default configuration dictionary.
        """
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
            "polling_interval_seconds": 300
        }
        
        return config

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate the mood module configuration.
        
        Args:
            config: Configuration dictionary to validate.
            
        Raises:
            vol.Invalid: If configuration is invalid.
        """
        try:
            self.CONFIG_SCHEMA(config)
        except vol.Invalid as e:
            _LOGGER.warning("Invalid config, using defaults: %s", e)
            # Config will use defaults from _create_default_config

    async def _init_character_service(self, ctx: ModuleContext) -> None:
        """Initialize character service for mood weighting.
        
        Args:
            ctx: Module context with hass and entry.
        """
        try:
            # Try to get character service from coordinator or other modules
            entry_data = ctx.hass.data[DOMAIN][ctx.entry.entry_id]
            
            # Check if character service is available
            if "character_service" in entry_data:
                self._character_service = entry_data["character_service"]
                _LOGGER.info("Character service connected to mood module")
            else:
                _LOGGER.debug("Character service not available, using default weights")
                
        except Exception as e:
            _LOGGER.debug("Could not initialize character service: %s", e)
            self._character_service = None

    async def _register_services(self, hass: HomeAssistant, entry_id: str) -> None:
        """Register mood module services.
        
        Args:
            hass: Home Assistant instance.
            entry_id: Config entry ID.
        """
        # Service schemas
        orchestrate_zone_schema = vol.Schema({
            vol.Required("zone_name"): str,
            vol.Optional("dry_run", default=False): bool,
            vol.Optional("force_actions", default=False): bool
        })
        
        orchestrate_all_schema = vol.Schema({
            vol.Optional("dry_run", default=False): bool,
            vol.Optional("force_actions", default=False): bool
        })
        
        force_mood_schema = vol.Schema({
            vol.Required("zone_name"): str,
            vol.Required("mood_state"): str,
            vol.Optional("duration_minutes"): int
        })

        # Register orchestrate_zone service
        service_name = f"mood_orchestrate_zone_{entry_id}"
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN,
                service_name,
                self._handle_orchestrate_zone,
                schema=orchestrate_zone_schema
            )

        # Register orchestrate_all service
        service_name = f"mood_orchestrate_all_{entry_id}"
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN,
                service_name,
                self._handle_orchestrate_all,
                schema=orchestrate_all_schema
            )

        # Register force_mood service
        service_name = f"mood_force_mood_{entry_id}"
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN,
                service_name, 
                self._handle_force_mood,
                schema=force_mood_schema
            )

    async def _handle_orchestrate_zone(self, call: ServiceCall) -> None:
        """Handle orchestrate_zone service call.
        
        Args:
            call: Service call with parameters.
        """
        zone_name = call.data.get("zone_name")
        dry_run = call.data.get("dry_run", False)
        force_actions = call.data.get("force_actions", False)
        
        if not zone_name:
            _LOGGER.error("zone_name parameter required")
            return
        
        if self._hass is None or self._entry_id is None:
            _LOGGER.error("Mood module not initialized")
            return
        
        await self._orchestrate_zone(self._hass, self._entry_id, zone_name, dry_run, force_actions)

    async def _handle_orchestrate_all(self, call: ServiceCall) -> None:
        """Handle orchestrate_all service call.
        
        Args:
            call: Service call with parameters.
        """
        dry_run = call.data.get("dry_run", False)
        force_actions = call.data.get("force_actions", False)
        
        if self._hass is None or self._entry_id is None:
            _LOGGER.error("Mood module not initialized")
            return
        
        await self._orchestrate_all_zones(self._hass, self._entry_id, dry_run, force_actions)

    async def _handle_force_mood(self, call: ServiceCall) -> None:
        """Handle force_mood service call.
        
        Args:
            call: Service call with parameters.
        """
        zone_name = call.data.get("zone_name")
        mood_state = call.data.get("mood_state")
        duration_minutes = call.data.get("duration_minutes")
        
        if not zone_name or not mood_state:
            _LOGGER.error("zone_name and mood_state parameters required")
            return
        
        if self._hass is None or self._entry_id is None:
            _LOGGER.error("Mood module not initialized")
            return
        
        await self._force_mood(self._hass, self._entry_id, zone_name, mood_state, duration_minutes)

    async def _setup_entity_tracking(
        self, 
        hass: HomeAssistant, 
        entry_id: str, 
        mood_data: MoodData
    ) -> None:
        """Set up state change event tracking for relevant entities.
        
        Args:
            hass: Home Assistant instance.
            entry_id: Config entry ID.
            mood_data: Module data dictionary.
        """
        config = mood_data["config"]
        tracked_entities: List[str] = []
        
        # Collect all entities that should trigger mood re-evaluation
        for zone_name, zone_config in config.get("zones", {}).items():
            tracked_entities.extend(zone_config.get("motion_entities", []))
            tracked_entities.extend(zone_config.get("light_entities", []))
            tracked_entities.extend(zone_config.get("media_entities", []))
            
            if zone_config.get("illuminance_entity"):
                tracked_entities.append(zone_config["illuminance_entity"])
        
        # Store as list for JSON serialization
        mood_data["tracked_entities"] = tracked_entities
        
        async def _handle_state_change(event: Event) -> None:
            """Handle state change events for tracked entities.
            
            Note: Using fire-and-forget pattern instead of asyncio.sleep
            to avoid blocking the event loop.
            """
            entity_id = event.data.get("entity_id")
            
            if entity_id in tracked_entities:
                _LOGGER.debug("State change detected for %s, triggering mood evaluation", entity_id)
                
                # Invalidate mood cache on state change
                mood_cache = get_mood_cache()
                await mood_cache.clear()
                
                # Schedule orchestration without blocking
                if self._hass and self._entry_id:
                    asyncio.create_task(
                        self._orchestrate_all_zones(
                            self._hass, 
                            self._entry_id, 
                            dry_run=False, 
                            force_actions=False
                        )
                    )
        
        # Track state changes
        unsub = async_track_state_change_event(hass, tracked_entities, _handle_state_change)
        mood_data["event_unsubs"].append(unsub)

    async def _setup_polling(
        self, 
        hass: HomeAssistant, 
        entry_id: str, 
        mood_data: MoodData
    ) -> None:
        """Set up polling fallback to catch missed events.
        
        Args:
            hass: Home Assistant instance.
            entry_id: Config entry ID.
            mood_data: Module data dictionary.
        """
        config = mood_data["config"]
        interval_seconds = config.get("polling_interval_seconds", 300)
        
        async def _handle_poll(now: datetime) -> None:
            """Periodic polling handler."""
            _LOGGER.debug("Mood module polling trigger")
            if self._hass and self._entry_id:
                await self._orchestrate_all_zones(
                    self._hass, 
                    self._entry_id, 
                    dry_run=False, 
                    force_actions=False
                )
        
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
        """Orchestrate mood inference and actions for a specific zone.
        
        Args:
            hass: Home Assistant instance.
            entry_id: Config entry ID.
            zone_name: Name of the zone to orchestrate.
            dry_run: If True, don't execute actions.
            force_actions: If True, ignore cooldown and execute anyway.
        """
        try:
            entry_data = hass.data.get(DOMAIN, {}).get(entry_id, {})
            if "mood_module" not in entry_data:
                _LOGGER.error("Mood module data not found for entry %s", entry_id)
                return
                
            config = entry_data["mood_module"]["config"]
            
            if zone_name not in config.get("zones", {}):
                _LOGGER.error("Unknown zone: %s", zone_name)
                return
            
            zone_config = config["zones"][zone_name]
            
            # Collect sensor data
            sensor_data = await self._collect_sensor_data(hass, zone_config)
            
            # Call Core Add-on API for mood inference
            result = await self._call_core_api(
                hass,
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
                
                # Apply character mood weights if available
                if self._character_service and orchestration_result.get("mood"):
                    base_mood = orchestration_result["mood"]
                    weighted_mood = self._character_service.apply_mood_weights(base_mood)
                    orchestration_result["mood"] = weighted_mood
                
                # Execute actions locally if not dry run
                if not dry_run and not orchestration_result.get("skipped_reason"):
                    actions = orchestration_result.get("actions", {})
                    service_calls = actions.get("service_calls", [])
                    
                    if service_calls:
                        await self._execute_service_calls(hass, service_calls)
                
                # Store result
                entry_data["mood_module"]["last_orchestration"][zone_name] = {
                    **orchestration_result,
                    "timestamp": datetime.now().isoformat()
                }
                
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
        """Orchestrate mood inference for all configured zones.
        
        Args:
            hass: Home Assistant instance.
            entry_id: Config entry ID.
            dry_run: If True, don't execute actions.
            force_actions: If True, ignore cooldown and execute anyway.
        """
        try:
            entry_data = hass.data.get(DOMAIN, {}).get(entry_id, {})
            if "mood_module" not in entry_data:
                _LOGGER.error("Mood module data not found for entry %s", entry_id)
                return
                
            config = entry_data["mood_module"]["config"]
            zones = config.get("zones", {})
            
            for zone_name in zones.keys():
                try:
                    await self._orchestrate_zone(
                        hass, entry_id, zone_name, dry_run, force_actions
                    )
                except Exception as e:
                    _LOGGER.error("Failed to orchestrate zone %s: %s", zone_name, e)
                    # Continue with other zones even if one fails
                    
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
        """Force a specific mood for a zone.
        
        Args:
            hass: Home Assistant instance.
            entry_id: Config entry ID.
            zone_name: Name of the zone.
            mood_state: The mood state to force.
            duration_minutes: How long to force the mood (optional).
        """
        try:
            result = await self._call_core_api(
                hass,
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

    async def _collect_sensor_data(
        self, 
        hass: HomeAssistant, 
        zone_config: ZoneConfig
    ) -> Dict[str, Any]:
        """Collect current sensor data for a zone with caching.
        
        Args:
            hass: Home Assistant instance.
            zone_config: Zone configuration dictionary.
            
        Returns:
            Dictionary of sensor data.
        """
        # Create cache key based on zone entities
        cache_key = f"mood_sensor_data_{hash(frozenset(zone_config.keys()))}"
        mood_cache = get_mood_cache()
        
        # Check cache first (TTL 5 seconds for sensor data)
        cached = await mood_cache.get(cache_key)
        if cached is not None:
            _LOGGER.debug("Using cached sensor data for zone")
            return cached
        
        sensor_data: Dict[str, Any] = {}
        
        # Collect all relevant entity states
        entity_ids: List[str] = []
        entity_ids.extend(zone_config.get("motion_entities", []))
        entity_ids.extend(zone_config.get("light_entities", []))
        entity_ids.extend(zone_config.get("media_entities", []))
        
        if zone_config.get("illuminance_entity"):
            entity_ids.append(zone_config["illuminance_entity"])
        
        for entity_id in entity_ids:
            try:
                state = hass.states.get(entity_id)
                if state:
                    sensor_data[entity_id] = {
                        "state": state.state,
                        "attributes": dict(state.attributes),
                        "last_changed": state.last_changed.isoformat(),
                        "last_updated": state.last_updated.isoformat()
                    }
            except Exception as e:
                _LOGGER.warning("Failed to get state for %s: %s", entity_id, e)
        
        # Cache the sensor data (5 second TTL for rapid changes)
        await mood_cache.set(cache_key, sensor_data)
        
        return sensor_data

    async def _execute_service_calls(
        self, 
        hass: HomeAssistant, 
        service_calls: List[ServiceCallDict]
    ) -> None:
        """Execute HA service calls.
        
        Args:
            hass: Home Assistant instance.
            service_calls: List of service call dictionaries.
        """
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

    async def _call_core_api(
        self,
        hass: HomeAssistant,
        method: str, 
        path: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[APIResponse]:
        """Call the Core Add-on API.
        
        Args:
            hass: Home Assistant instance.
            method: HTTP method (GET, POST, etc.).
            path: API endpoint path.
            data: Request body data.
            
        Returns:
            API response dictionary or None on error.
        """
        # Get core add-on URL from hass data or config
        core_url = "http://localhost:5000"  # Default, should be configurable
        
        try:
            # In production, this would make actual HTTP calls
            # For now, simulate successful response
            _LOGGER.debug("Would call Core API: %s %s with data: %s", method, path, data)
            
            # Simulate API response
            return {
                "ok": True,
                "result": {
                    "mood": {"mood": "relax", "confidence": 0.8},
                    "skipped_reason": "Simulated response - Core API not connected"
                }
            }
            
        except aiohttp.ClientError as e:
            _LOGGER.error("HTTP error calling Core API: %s", e)
            return None
        except Exception as e:
            _LOGGER.error("Error calling Core API: %s", e)
            return None


# Module factory for dynamic loading
def create_module() -> MoodModule:
    """Create a new MoodModule instance.
    
    Returns:
        New MoodModule instance.
    """
    return MoodModule()
