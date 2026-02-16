"""Media Context v2: Extended coordinator with zone mapping and volume control."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.media_player import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
    SERVICE_VOLUME_MUTE,
)
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry, device_registry, entity_registry
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .media_context import MediaContextCoordinator, MediaContextData
from .habitus_zones_store_v2 import async_get_zones_v2

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ZoneMediaConfig:
    """Configuration for media players in a zone."""
    music: list[str] = field(default_factory=list)
    tv: list[str] = field(default_factory=list)
    tv_volume_proxy: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class VolumePolicyConfig:
    """Volume control policy configuration."""
    step: float = 0.03
    max_level: float | None = 0.60
    ramp_ms: int = 250
    big_jump_threshold: float = 0.15
    require_confirm_big_jump: bool = True
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:30"
    quiet_hours_end: str = "07:30"
    quiet_max_level: float = 0.25


@dataclass(frozen=True, slots=True)
class RoutingPolicyConfig:
    """Active target routing policy configuration."""
    prefer_tv_when_active: bool = True
    prefer_local_area_match: bool = True
    tv_active_states: list[str] = field(default_factory=lambda: ["on", "idle", "playing", "paused"])
    music_active_states: list[str] = field(default_factory=lambda: ["playing"])


@dataclass(frozen=True, slots=True)
class MediaContextV2Data:
    """Extended media context data with zone mapping and active target."""
    # Base context from v1
    base: MediaContextData
    
    # Active target info
    active_mode: str  # "tv", "music", "none", "mixed"
    active_target_entity_id: str | None
    active_target_kind: str | None  # "tv", "music"
    active_zone_id: str | None
    active_zone_name: str | None
    reason: str
    
    # Zone mapping results  
    zone_map: dict[str, ZoneMediaConfig]
    
    # Volume control state
    current_volume: float | None
    volume_muted: bool | None
    
    # Manual overrides
    manual_target_entity_id: str | None
    manual_target_expires: float | None
    manual_zone_id: str | None
    manual_zone_expires: float | None


def _normalize_zone_name(name: str) -> str:
    """Normalize zone/area name for matching."""
    # Convert umlauts and normalize case
    replacements = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        'Ä': 'AE', 'Ö': 'OE', 'Ü': 'UE'
    }
    result = name.lower().strip()
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def _entity_supports_volume_control(hass: HomeAssistant, entity_id: str) -> bool:
    """Check if entity supports volume control."""
    state = hass.states.get(entity_id)
    if not state:
        return False
    
    # Check if volume_level attribute exists
    if "volume_level" not in state.attributes:
        return False
        
    # Check domain
    if not entity_id.startswith("media_player."):
        return False
        
    return True


def _get_entity_volume(hass: HomeAssistant, entity_id: str) -> tuple[float | None, bool | None]:
    """Get current volume and mute state of entity."""
    state = hass.states.get(entity_id)
    if not state:
        return None, None
        
    volume = state.attributes.get("volume_level")
    muted = state.attributes.get("is_volume_muted", False)
    
    return volume, muted


class MediaContextV2Coordinator(DataUpdateCoordinator[MediaContextV2Data]):
    """Enhanced media context coordinator with zone mapping and volume control."""

    def __init__(
        self,
        hass: HomeAssistant,
        base_coordinator: MediaContextCoordinator,
        *,
        use_habitus_zones: bool = False,
        zone_map: dict[str, dict[str, Any]] | None = None,
        volume_policy: dict[str, Any] | None = None,
        routing_policy: dict[str, Any] | None = None,
        entry_id: str | None = None,
    ):
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-media_context_v2",
            update_interval=None,
        )
        self._base_coordinator = base_coordinator
        self._use_habitus_zones = use_habitus_zones
        self._entry_id = entry_id
        self._habitus_zones: list = []  # Cached HabitusZoneV2 list
        
        # Parse zone map
        self._zone_map = {}
        if zone_map:
            for zone_id, config in zone_map.items():
                self._zone_map[zone_id] = ZoneMediaConfig(
                    music=config.get("music", []),
                    tv=config.get("tv", []),
                    tv_volume_proxy=config.get("tv_volume_proxy", []),
                )
        
        # Parse policies
        self._volume_policy = VolumePolicyConfig(**volume_policy or {})
        self._routing_policy = RoutingPolicyConfig(**routing_policy or {})
        
        # Manual override state
        self._manual_target_entity_id = None
        self._manual_target_expires = None
        self._manual_zone_id = None
        self._manual_zone_expires = None
        
        self._unsub = None

    def set_config(
        self,
        *,
        use_habitus_zones: bool = False,
        zone_map: dict[str, dict[str, Any]] | None = None,
        volume_policy: dict[str, Any] | None = None,
        routing_policy: dict[str, Any] | None = None,
        entry_id: str | None = None,
    ) -> None:
        """Update configuration."""
        self._use_habitus_zones = use_habitus_zones
        self._entry_id = entry_id

        # Parse zone map
        self._zone_map = {}
        if zone_map:
            for zone_id, config in zone_map.items():
                self._zone_map[zone_id] = ZoneMediaConfig(
                    music=config.get("music", []),
                    tv=config.get("tv", []),
                    tv_volume_proxy=config.get("tv_volume_proxy", []),
                )

        # Parse policies
        self._volume_policy = VolumePolicyConfig(**volume_policy or {})
        self._routing_policy = RoutingPolicyConfig(**routing_policy or {})

        # Clear cached zones - will reload on next refresh
        self._habitus_zones = []

    async def async_start(self) -> None:
        """Start the coordinator."""
        if self._unsub is not None:
            return

        # Load Habitus zones if enabled
        if self._use_habitus_zones and self._entry_id:
            try:
                self._habitus_zones = await async_get_zones_v2(self.hass, self._entry_id)
                _LOGGER.debug("Loaded %d Habitus zones for media context", len(self._habitus_zones))
            except Exception as err:
                _LOGGER.warning("Failed to load Habitus zones: %s", err)
                self._habitus_zones = []
            
        # Track base coordinator updates
        @callback
        def _on_base_update() -> None:
            self.hass.async_create_task(self.async_refresh())
            
        self._unsub = self._base_coordinator.async_add_listener(_on_base_update)
        
        # Initial snapshot
        await self.async_refresh()

    async def async_stop(self) -> None:
        """Stop the coordinator."""
        if callable(self._unsub):
            self._unsub()
        self._unsub = None

    def set_manual_target(self, entity_id: str, ttl_seconds: int | None = None) -> None:
        """Set manual target override."""
        self._manual_target_entity_id = entity_id
        self._manual_target_expires = time.time() + ttl_seconds if ttl_seconds else None
        self.hass.async_create_task(self.async_refresh())

    def set_manual_zone(self, zone_id: str, ttl_seconds: int | None = None) -> None:
        """Set manual zone override."""
        self._manual_zone_id = zone_id
        self._manual_zone_expires = time.time() + ttl_seconds if ttl_seconds else None
        self.hass.async_create_task(self.async_refresh())

    def clear_manual_overrides(self) -> None:
        """Clear all manual overrides."""
        self._manual_target_entity_id = None
        self._manual_target_expires = None
        self._manual_zone_id = None
        self._manual_zone_expires = None
        self.hass.async_create_task(self.async_refresh())

    def _get_valid_manual_target(self) -> str | None:
        """Get manual target if still valid (not expired)."""
        if not self._manual_target_entity_id:
            return None
        if self._manual_target_expires and time.time() > self._manual_target_expires:
            return None
        return self._manual_target_entity_id

    def _get_valid_manual_zone(self) -> str | None:
        """Get manual zone if still valid (not expired)."""
        if not self._manual_zone_id:
            return None
        if self._manual_zone_expires and time.time() > self._manual_zone_expires:
            return None
        return self._manual_zone_id

    def _determine_active_target(self, base_data: MediaContextData) -> tuple[str | None, str | None, str | None, str]:
        """Determine active target based on routing policy."""
        # Check manual override first
        manual_target = self._get_valid_manual_target()
        if manual_target:
            target_kind = "tv" if manual_target in self._get_all_tv_targets() else "music"
            zone_id = self._get_zone_for_entity(manual_target)
            return manual_target, target_kind, zone_id, "manual_override"
            
        # Check manual zone override
        manual_zone = self._get_valid_manual_zone()
        if manual_zone:
            zone_config = self._zone_map.get(manual_zone)
            if zone_config:
                # Prefer TV if active, otherwise music
                if base_data.tv_active and zone_config.tv:
                    return zone_config.tv[0], "tv", manual_zone, "zone_selected"
                elif zone_config.music:
                    return zone_config.music[0], "music", manual_zone, "zone_selected"
        
        # Apply routing policy
        if (base_data.tv_active and self._routing_policy.prefer_tv_when_active and 
            base_data.tv_primary_entity_id):
            zone_id = self._get_zone_for_entity(base_data.tv_primary_entity_id)
            return base_data.tv_primary_entity_id, "tv", zone_id, "tv_active"
            
        if base_data.music_active and base_data.music_primary_entity_id:
            zone_id = self._get_zone_for_entity(base_data.music_primary_entity_id)
            return base_data.music_primary_entity_id, "music", zone_id, "music_active"
            
        # No activity - use last target if recent (could be implemented later)
        return None, None, None, "no_activity"

    def _get_all_tv_targets(self) -> set[str]:
        """Get all configured TV targets."""
        targets = set()
        for zone_config in self._zone_map.values():
            targets.update(zone_config.tv)
        return targets

    def _get_zone_for_entity(self, entity_id: str) -> str | None:
        """Find zone ID containing this entity."""
        for zone_id, zone_config in self._zone_map.items():
            if entity_id in zone_config.music or entity_id in zone_config.tv:
                return zone_id
        return None

    def _get_zone_name(self, zone_id: str | None) -> str | None:
        """Get display name for zone."""
        if not zone_id:
            return None

        # Use HabitusZoneV2 display name if available
        if self._use_habitus_zones and self._habitus_zones:
            for zone in self._habitus_zones:
                if zone.zone_id == zone_id:
                    return zone.name  # Use zone.name (display name)
                # Also try matching without "zone:" prefix
                if zone.zone_id == f"zone:{zone_id}":
                    return zone.name
                # Fuzzy match by zone_id or name
                if zone.zone_id.lower().replace("zone:", "") == zone_id.lower():
                    return zone.name

        # Fallback: capitalize zone_id
        return zone_id.capitalize()

    def _determine_active_mode(self, base_data: MediaContextData) -> str:
        """Determine active mode from base data."""
        if base_data.tv_active and base_data.music_active:
            return "mixed"
        elif base_data.tv_active:
            return "tv"
        elif base_data.music_active:
            return "music"
        else:
            return "none"

    async def _async_update_data(self) -> MediaContextV2Data:
        """Update the coordinator data."""
        # Get base data
        base_data = self._base_coordinator.data
        if not base_data:
            # Create empty base data if coordinator not ready
            base_data = MediaContextData(
                music_active=False,
                tv_active=False,
                music_primary_entity_id=None,
                tv_primary_entity_id=None,
                music_primary_area=None,
                tv_primary_area=None,
                music_now_playing=None,
                tv_source=None,
                music_active_count=0,
                tv_active_count=0,
            )
        
        # Determine active target
        active_target_entity_id, active_target_kind, active_zone_id, reason = self._determine_active_target(base_data)
        
        # Get current volume/mute state
        current_volume, volume_muted = None, None
        if active_target_entity_id:
            current_volume, volume_muted = _get_entity_volume(self.hass, active_target_entity_id)
        
        # Determine active mode
        active_mode = self._determine_active_mode(base_data)
        
        # Get zone name
        active_zone_name = self._get_zone_name(active_zone_id)
        
        return MediaContextV2Data(
            base=base_data,
            active_mode=active_mode,
            active_target_entity_id=active_target_entity_id,
            active_target_kind=active_target_kind,
            active_zone_id=active_zone_id,
            active_zone_name=active_zone_name,
            reason=reason,
            zone_map=self._zone_map,
            current_volume=current_volume,
            volume_muted=volume_muted,
            manual_target_entity_id=self._get_valid_manual_target(),
            manual_target_expires=self._manual_target_expires,
            manual_zone_id=self._get_valid_manual_zone(),
            manual_zone_expires=self._manual_zone_expires,
        )

    async def async_volume_up(self, entity_id: str | None = None) -> None:
        """Increase volume by configured step."""
        target = entity_id or (self.data.active_target_entity_id if self.data else None)
        if not target:
            raise HomeAssistantError("No active target for volume control")
            
        if not _entity_supports_volume_control(self.hass, target):
            raise HomeAssistantError(f"Entity {target} does not support volume control")
        
        current_volume, _ = _get_entity_volume(self.hass, target)
        if current_volume is None:
            raise HomeAssistantError(f"Cannot get current volume for {target}")
        
        new_volume = min(1.0, current_volume + self._volume_policy.step)
        
        # Apply max level limit
        if self._volume_policy.max_level is not None:
            new_volume = min(new_volume, self._volume_policy.max_level)
            
        await self.async_volume_set(new_volume, entity_id)

    async def async_volume_down(self, entity_id: str | None = None) -> None:
        """Decrease volume by configured step."""
        target = entity_id or (self.data.active_target_entity_id if self.data else None)
        if not target:
            raise HomeAssistantError("No active target for volume control")
            
        if not _entity_supports_volume_control(self.hass, target):
            raise HomeAssistantError(f"Entity {target} does not support volume control")
        
        current_volume, _ = _get_entity_volume(self.hass, target)
        if current_volume is None:
            raise HomeAssistantError(f"Cannot get current volume for {target}")
        
        new_volume = max(0.0, current_volume - self._volume_policy.step)
        await self.async_volume_set(new_volume, entity_id)

    async def async_volume_set(self, level: float, entity_id: str | None = None, *, ramp: bool = True) -> None:
        """Set volume to specific level."""
        target = entity_id or (self.data.active_target_entity_id if self.data else None)
        if not target:
            raise HomeAssistantError("No active target for volume control")
            
        if not _entity_supports_volume_control(self.hass, target):
            raise HomeAssistantError(f"Entity {target} does not support volume control")
        
        # Clamp level
        level = max(0.0, min(1.0, level))
        
        # Apply max level limit
        if self._volume_policy.max_level is not None:
            level = min(level, self._volume_policy.max_level)
        
        # Get current volume for big jump detection
        current_volume, _ = _get_entity_volume(self.hass, target)
        if current_volume is not None:
            jump_size = abs(level - current_volume)
            if (jump_size >= self._volume_policy.big_jump_threshold and 
                self._volume_policy.require_confirm_big_jump):
                # For now, just log the warning. UI should handle confirmation.
                _LOGGER.warning(
                    "Big volume jump requested: %s -> %s (entity: %s)",
                    current_volume, level, target
                )
        
        # Apply ramping if enabled and requested
        if ramp and self._volume_policy.ramp_ms > 0 and current_volume is not None:
            await self._async_volume_set_with_ramp(target, current_volume, level)
        else:
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                SERVICE_VOLUME_SET,
                {"entity_id": target, "volume_level": level},
                blocking=True,
            )

    async def _async_volume_set_with_ramp(self, entity_id: str, current: float, target: float) -> None:
        """Set volume with ramping."""
        steps = max(2, abs(target - current) / 0.05)  # At least 2 steps, more for bigger changes
        step_count = int(min(steps, 5))  # Max 5 steps to avoid too many calls
        
        if step_count <= 1:
            # No need to ramp
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                SERVICE_VOLUME_SET,
                {"entity_id": entity_id, "volume_level": target},
                blocking=True,
            )
            return
        
        delay = self._volume_policy.ramp_ms / 1000 / step_count
        step_size = (target - current) / step_count
        
        for i in range(1, step_count + 1):
            level = current + (step_size * i)
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                SERVICE_VOLUME_SET,
                {"entity_id": entity_id, "volume_level": level},
                blocking=True,
            )
            if i < step_count:  # Don't delay after last step
                await asyncio.sleep(delay)

    async def async_volume_mute_toggle(self, entity_id: str | None = None) -> None:
        """Toggle mute state."""
        target = entity_id or (self.data.active_target_entity_id if self.data else None)
        if not target:
            raise HomeAssistantError("No active target for volume control")
            
        if not _entity_supports_volume_control(self.hass, target):
            raise HomeAssistantError(f"Entity {target} does not support volume control")
        
        await self.hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_VOLUME_MUTE,
            {"entity_id": target, "is_volume_muted": True},  # Service will toggle
            blocking=True,
        )

    def validate_config(self) -> list[dict[str, Any]]:
        """Validate current configuration and return findings."""
        findings = []
        
        # Check zone mapping
        for zone_id, zone_config in self._zone_map.items():
            # Check if zone has any valid entities
            all_entities = zone_config.music + zone_config.tv + zone_config.tv_volume_proxy
            if not all_entities:
                findings.append({
                    "severity": "warn",
                    "code": "MC201",
                    "message": f"Zone '{zone_id}' has no media entities configured",
                    "details": {"zone_id": zone_id},
                })
                continue
            
            # Check TV volume proxy without TV entity
            if zone_config.tv_volume_proxy and not zone_config.tv:
                findings.append({
                    "severity": "error",
                    "code": "MC202",
                    "message": f"Zone '{zone_id}' has TV volume proxy but no TV entity",
                    "details": {"zone_id": zone_id},
                })
            
            # Check entity existence and capabilities
            for entity_id in all_entities:
                state = self.hass.states.get(entity_id)
                if not state:
                    findings.append({
                        "severity": "warn",
                        "code": "MC203",
                        "message": f"Entity '{entity_id}' not found",
                        "details": {"entity_id": entity_id, "zone_id": zone_id},
                    })
                elif not _entity_supports_volume_control(self.hass, entity_id):
                    findings.append({
                        "severity": "warn",
                        "code": "MC204",
                        "message": f"Entity '{entity_id}' does not support volume control",
                        "details": {"entity_id": entity_id, "zone_id": zone_id},
                    })
        
        # Check volume policy
        if not (0.0 < self._volume_policy.step <= 0.2):
            findings.append({
                "severity": "error",
                "code": "MC205", 
                "message": f"Volume step {self._volume_policy.step} is outside valid range (0, 0.2]",
                "details": {"step": self._volume_policy.step},
            })
        
        return findings

    async def async_suggest_zone_mapping(self) -> dict[str, dict[str, list[str]]]:
        """Auto-suggest zone mapping based on area matching."""
        er = entity_registry.async_get(self.hass)
        dr = device_registry.async_get(self.hass)
        ar = area_registry.async_get(self.hass)
        
        suggestions = {}
        
        # Get all media_player entities
        media_entities = [
            ent for ent in er.entities.values()
            if ent.domain == "media_player" and not ent.hidden_by
        ]
        
        # Group by normalized area name
        area_groups = {}
        for ent in media_entities:
            area_name = None
            
            # Get area from entity or device
            if ent.area_id:
                area = ar.async_get_area(ent.area_id)
                area_name = area.name if area else None
            elif ent.device_id:
                dev = dr.async_get(ent.device_id)
                if dev and dev.area_id:
                    area = ar.async_get_area(dev.area_id)
                    area_name = area.name if area else None
            
            if not area_name:
                continue
                
            normalized_area = _normalize_zone_name(area_name)
            if normalized_area not in area_groups:
                area_groups[normalized_area] = {"music": [], "tv": []}
            
            # Categorize by integration/domain heuristics
            if ent.platform == "sonos":
                area_groups[normalized_area]["music"].append(ent.entity_id)
            elif ent.platform in ["apple_tv", "androidtv", "webostv"]:
                area_groups[normalized_area]["tv"].append(ent.entity_id)
            elif "spotify" in ent.entity_id.lower():
                area_groups[normalized_area]["music"].append(ent.entity_id)
            elif any(keyword in ent.entity_id.lower() for keyword in ["tv", "fernseher", "apple_tv"]):
                area_groups[normalized_area]["tv"].append(ent.entity_id)
            else:
                # Default to music for unknown entities
                area_groups[normalized_area]["music"].append(ent.entity_id)
        
        return area_groups