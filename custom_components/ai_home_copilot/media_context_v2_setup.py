"""Setup and configuration for Media Context v2."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .media_context import MediaContextCoordinator
from .media_context_v2 import MediaContextV2Coordinator

_LOGGER = logging.getLogger(__name__)

# Config store version
MEDIA_CONTEXT_V2_STORE_VERSION = 1
MEDIA_CONTEXT_V2_STORE_KEY = "media_context_v2_config"

# Default configuration
DEFAULT_MEDIA_CONTEXT_V2_CONFIG = {
    "use_habitus_zones": False,
    "zone_map": {},
    "volume_policy": {
        "step": 0.03,
        "max_level": 0.60,
        "ramp_ms": 250,
        "big_jump_threshold": 0.15,
        "require_confirm_big_jump": True,
        "quiet_hours_enabled": False,
        "quiet_hours_start": "22:30",
        "quiet_hours_end": "07:30",
        "quiet_max_level": 0.25,
    },
    "routing_policy": {
        "prefer_tv_when_active": True,
        "prefer_local_area_match": True,
        "tv_active_states": ["on", "idle", "playing", "paused"],
        "music_active_states": ["playing"],
    },
}


async def async_setup_media_context_v2(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up Media Context v2 coordinator."""
    
    # Get base media coordinator
    domain_data = hass.data[DOMAIN].get(entry.entry_id, {})
    base_coordinator = domain_data.get("media_coordinator")
    
    if not base_coordinator:
        _LOGGER.error("Base media coordinator not found - cannot setup media_context_v2")
        return
    
    # Load configuration from store
    store = Store[dict[str, Any]](
        hass,
        MEDIA_CONTEXT_V2_STORE_VERSION,
        f"{DOMAIN}.{entry.entry_id}.{MEDIA_CONTEXT_V2_STORE_KEY}",
    )
    
    stored_config = await store.async_load()
    if stored_config is None:
        stored_config = DEFAULT_MEDIA_CONTEXT_V2_CONFIG.copy()
        await store.async_save(stored_config)
    
    # Merge with defaults for any missing keys
    config = DEFAULT_MEDIA_CONTEXT_V2_CONFIG.copy()
    config.update(stored_config)
    
    # Create v2 coordinator
    coordinator_v2 = MediaContextV2Coordinator(
        hass,
        base_coordinator,
        use_habitus_zones=config.get("use_habitus_zones", False),
        zone_map=config.get("zone_map", {}),
        volume_policy=config.get("volume_policy", {}),
        routing_policy=config.get("routing_policy", {}),
        entry_id=entry.entry_id,
    )
    
    # Start coordinator
    await coordinator_v2.async_start()
    
    # Store coordinator and config store
    if isinstance(domain_data, dict):
        domain_data["media_coordinator_v2"] = coordinator_v2
        domain_data["media_context_v2_store"] = store


async def async_unload_media_context_v2(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unload Media Context v2."""
    domain_data = hass.data[DOMAIN].get(entry.entry_id, {})
    
    coordinator_v2 = domain_data.get("media_coordinator_v2")
    if coordinator_v2:
        try:
            await coordinator_v2.async_stop()
        except Exception as err:
            _LOGGER.exception("Error stopping media_context_v2 coordinator: %s", err)
        
        if isinstance(domain_data, dict):
            domain_data.pop("media_coordinator_v2", None)
            domain_data.pop("media_context_v2_store", None)


async def async_update_media_context_v2_config(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    config_update: dict[str, Any]
) -> None:
    """Update Media Context v2 configuration."""
    
    domain_data = hass.data[DOMAIN].get(entry.entry_id, {})
    coordinator_v2 = domain_data.get("media_coordinator_v2")
    store = domain_data.get("media_context_v2_store")
    
    if not coordinator_v2 or not store:
        _LOGGER.error("Media Context v2 not properly initialized")
        return
    
    # Load current config
    current_config = await store.async_load() or DEFAULT_MEDIA_CONTEXT_V2_CONFIG.copy()
    
    # Update with new values
    current_config.update(config_update)
    
    # Save to store
    await store.async_save(current_config)
    
    # Update coordinator
    coordinator_v2.set_config(
        use_habitus_zones=current_config.get("use_habitus_zones", False),
        zone_map=current_config.get("zone_map", {}),
        volume_policy=current_config.get("volume_policy", {}),
        routing_policy=current_config.get("routing_policy", {}),
        entry_id=entry.entry_id,
    )
    
    # Refresh coordinator data
    await coordinator_v2.async_refresh()


async def async_get_media_context_v2_config(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Get current Media Context v2 configuration."""
    domain_data = hass.data[DOMAIN].get(entry.entry_id, {})
    store = domain_data.get("media_context_v2_store")
    
    if not store:
        return DEFAULT_MEDIA_CONTEXT_V2_CONFIG.copy()
    
    stored_config = await store.async_load()
    if stored_config is None:
        return DEFAULT_MEDIA_CONTEXT_V2_CONFIG.copy()
    
    # Merge with defaults
    config = DEFAULT_MEDIA_CONTEXT_V2_CONFIG.copy()
    config.update(stored_config)
    return config


async def async_suggest_zone_mapping(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Generate auto-suggestions for zone mapping."""
    domain_data = hass.data[DOMAIN].get(entry.entry_id, {})
    coordinator_v2 = domain_data.get("media_coordinator_v2")
    
    if not coordinator_v2:
        _LOGGER.error("Media Context v2 coordinator not found")
        return {}
    
    suggestions = await coordinator_v2.async_suggest_zone_mapping()
    return suggestions


class MediaContextV2ConfigManager:
    """Helper class for managing Media Context v2 configuration."""
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        
    @property
    def domain_data(self) -> dict[str, Any]:
        return self.hass.data[DOMAIN].get(self.entry.entry_id, {})
    
    @property
    def coordinator_v2(self) -> MediaContextV2Coordinator | None:
        return self.domain_data.get("media_coordinator_v2")
    
    @property
    def store(self) -> Store | None:
        return self.domain_data.get("media_context_v2_store")
    
    async def async_get_config(self) -> dict[str, Any]:
        """Get current configuration."""
        return await async_get_media_context_v2_config(self.hass, self.entry)
    
    async def async_update_config(self, config_update: dict[str, Any]) -> None:
        """Update configuration."""
        await async_update_media_context_v2_config(self.hass, self.entry, config_update)
    
    async def async_get_zone_suggestions(self) -> dict[str, Any]:
        """Get zone mapping suggestions."""
        return await async_suggest_zone_mapping(self.hass, self.entry)
    
    async def async_validate_config(self) -> list[dict[str, Any]]:
        """Validate current configuration."""
        coordinator_v2 = self.coordinator_v2
        if not coordinator_v2:
            return [{
                "severity": "error",
                "code": "MC101",
                "message": "Media Context v2 coordinator not initialized",
                "details": {},
            }]
        
        return coordinator_v2.validate_config()
    
    async def async_update_zone_mapping(self, zone_map: dict[str, dict[str, Any]]) -> None:
        """Update zone mapping configuration."""
        await self.async_update_config({"zone_map": zone_map})
    
    async def async_update_volume_policy(self, volume_policy: dict[str, Any]) -> None:
        """Update volume policy configuration."""
        current_config = await self.async_get_config()
        updated_policy = current_config.get("volume_policy", {}).copy()
        updated_policy.update(volume_policy)
        
        await self.async_update_config({"volume_policy": updated_policy})
    
    async def async_update_routing_policy(self, routing_policy: dict[str, Any]) -> None:
        """Update routing policy configuration."""
        current_config = await self.async_get_config()
        updated_policy = current_config.get("routing_policy", {}).copy()
        updated_policy.update(routing_policy)
        
        await self.async_update_config({"routing_policy": updated_policy})
    
    async def async_reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        if self.store:
            await self.store.async_save(DEFAULT_MEDIA_CONTEXT_V2_CONFIG.copy())
        
        if self.coordinator_v2:
            config = DEFAULT_MEDIA_CONTEXT_V2_CONFIG
            self.coordinator_v2.set_config(
                use_habitus_zones=config.get("use_habitus_zones", False),
                zone_map=config.get("zone_map", {}),
                volume_policy=config.get("volume_policy", {}),
                routing_policy=config.get("routing_policy", {}),
            )
            await self.coordinator_v2.async_refresh()
    
    async def async_apply_zone_suggestions(self, suggestions: dict[str, dict[str, list[str]]] | None = None) -> None:
        """Apply auto-suggested zone mapping."""
        if suggestions is None:
            suggestions = await self.async_get_zone_suggestions()
        
        # Convert suggestions to zone_map format
        zone_map = {}
        for zone_id, zone_data in suggestions.items():
            zone_map[zone_id] = {
                "music": zone_data.get("music", []),
                "tv": zone_data.get("tv", []),
                "tv_volume_proxy": [],  # Not auto-suggested
            }
        
        await self.async_update_zone_mapping(zone_map)