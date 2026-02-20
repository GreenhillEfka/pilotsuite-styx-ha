"""Media Context v2 Entities: Sensors and controls for enhanced media context."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import PERCENTAGE
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .media_context_v2 import MediaContextV2Coordinator

_LOGGER = logging.getLogger(__name__)


class _MediaContextV2Base(CoordinatorEntity[MediaContextV2Coordinator]):
    """Base class for Media Context v2 entities."""
    _attr_has_entity_name = False

    def __init__(self, coordinator: MediaContextV2Coordinator, *, unique_id: str, name: str, icon: str | None = None):
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_name = name
        if icon:
            self._attr_icon = icon


# Status Sensors
class ActiveModeSensor(_MediaContextV2Base, SensorEntity):
    """Sensor showing current active mode (tv/music/none/mixed)."""
    
    def __init__(self, coordinator: MediaContextV2Coordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_media_active_mode",
            name="PilotSuite media active mode",
            icon="mdi:television-play",
        )

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.active_mode if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        return {
            "active_target_entity_id": self.coordinator.data.active_target_entity_id,
            "active_target_kind": self.coordinator.data.active_target_kind,
            "active_zone_id": self.coordinator.data.active_zone_id,
            "active_zone_name": self.coordinator.data.active_zone_name,
            "reason": self.coordinator.data.reason,
        }


class ActiveTargetSensor(_MediaContextV2Base, SensorEntity):
    """Sensor showing current active target entity."""
    
    def __init__(self, coordinator: MediaContextV2Coordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_media_active_target",
            name="PilotSuite media active target",
            icon="mdi:target",
        )

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.active_target_entity_id if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        return {
            "kind": self.coordinator.data.active_target_kind,
            "zone_id": self.coordinator.data.active_zone_id,
            "zone_name": self.coordinator.data.active_zone_name,
            "reason": self.coordinator.data.reason,
            "current_volume": self.coordinator.data.current_volume,
            "volume_muted": self.coordinator.data.volume_muted,
        }


class ActiveZoneSensor(_MediaContextV2Base, SensorEntity):
    """Sensor showing current active zone."""
    
    def __init__(self, coordinator: MediaContextV2Coordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_media_active_zone",
            name="PilotSuite media active zone",
            icon="mdi:map-marker",
        )

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.active_zone_name if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        return {
            "zone_id": self.coordinator.data.active_zone_id,
            "target_entity_id": self.coordinator.data.active_target_entity_id,
            "target_kind": self.coordinator.data.active_target_kind,
        }


# Volume Controls
class VolumeControlNumber(_MediaContextV2Base, NumberEntity):
    """Number entity for volume control."""
    
    def __init__(self, coordinator: MediaContextV2Coordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_media_volume",
            name="PilotSuite media volume",
            icon="mdi:volume-high",
        )
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 1.0
        self._attr_native_step = 0.01
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_mode = NumberMode.SLIDER

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data or not self.coordinator.data.current_volume:
            return None
        return self.coordinator.data.current_volume * 100

    @property
    def available(self) -> bool:
        return (
            self.coordinator.data is not None and
            self.coordinator.data.active_target_entity_id is not None and
            self.coordinator.data.current_volume is not None
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set volume level."""
        if not self.coordinator.data or not self.coordinator.data.active_target_entity_id:
            raise ServiceValidationError("No active target for volume control")
        
        try:
            await self.coordinator.async_volume_set(value / 100)
            # Force refresh to update state
            await self.coordinator.async_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set volume: %s", err)
            raise ServiceValidationError(f"Failed to set volume: {err}") from err


class VolumeUpButton(_MediaContextV2Base, ButtonEntity):
    """Button to increase volume."""
    
    def __init__(self, coordinator: MediaContextV2Coordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_media_volume_up",
            name="PilotSuite media volume up",
            icon="mdi:volume-plus",
        )

    @property
    def available(self) -> bool:
        return (
            self.coordinator.data is not None and
            self.coordinator.data.active_target_entity_id is not None
        )

    async def async_press(self) -> None:
        """Press the button."""
        try:
            await self.coordinator.async_volume_up()
            await self.coordinator.async_refresh()
        except Exception as err:
            _LOGGER.error("Failed to increase volume: %s", err)
            raise ServiceValidationError(f"Failed to increase volume: {err}") from err


class VolumeDownButton(_MediaContextV2Base, ButtonEntity):
    """Button to decrease volume."""
    
    def __init__(self, coordinator: MediaContextV2Coordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_media_volume_down", 
            name="PilotSuite media volume down",
            icon="mdi:volume-minus",
        )

    @property
    def available(self) -> bool:
        return (
            self.coordinator.data is not None and
            self.coordinator.data.active_target_entity_id is not None
        )

    async def async_press(self) -> None:
        """Press the button."""
        try:
            await self.coordinator.async_volume_down()
            await self.coordinator.async_refresh()
        except Exception as err:
            _LOGGER.error("Failed to decrease volume: %s", err)
            raise ServiceValidationError(f"Failed to decrease volume: {err}") from err


class VolumeMuteButton(_MediaContextV2Base, ButtonEntity):
    """Button to toggle mute."""
    
    def __init__(self, coordinator: MediaContextV2Coordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_media_volume_mute",
            name="PilotSuite media volume mute",
            icon="mdi:volume-mute",
        )

    @property
    def available(self) -> bool:
        return (
            self.coordinator.data is not None and
            self.coordinator.data.active_target_entity_id is not None
        )

    async def async_press(self) -> None:
        """Press the button."""
        try:
            await self.coordinator.async_volume_mute_toggle()
            await self.coordinator.async_refresh()
        except Exception as err:
            _LOGGER.error("Failed to toggle mute: %s", err)
            raise ServiceValidationError(f"Failed to toggle mute: {err}") from err


# Zone Selection
class ZoneSelectEntity(_MediaContextV2Base, SelectEntity):
    """Select entity for zone quick picks."""
    
    def __init__(self, coordinator: MediaContextV2Coordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_media_zone_select",
            name="PilotSuite media zone select",
            icon="mdi:map-marker-multiple",
        )

    @property
    def options(self) -> list[str]:
        """Return available zone options."""
        if not self.coordinator.data or not self.coordinator.data.zone_map:
            return ["None"]
        
        zones = ["Auto"] + list(self.coordinator.data.zone_map.keys())
        return zones

    @property
    def current_option(self) -> str | None:
        """Return current selected zone."""
        if not self.coordinator.data:
            return None
            
        # Check for manual zone override
        if self.coordinator.data.manual_zone_id:
            return self.coordinator.data.manual_zone_id
            
        # Check for active zone
        if self.coordinator.data.active_zone_id:
            return self.coordinator.data.active_zone_id
            
        return "Auto"

    async def async_select_option(self, option: str) -> None:
        """Select zone option."""
        try:
            if option == "Auto":
                self.coordinator.clear_manual_overrides()
            else:
                # Set manual zone with 30 minute TTL
                self.coordinator.set_manual_zone(option, ttl_seconds=30 * 60)
            
            await self.coordinator.async_refresh()
        except Exception as err:
            _LOGGER.error("Failed to select zone: %s", err)
            raise ServiceValidationError(f"Failed to select zone: {err}") from err


# Manual Override Controls  
class ManualTargetSelectEntity(_MediaContextV2Base, SelectEntity):
    """Select entity for manual target override."""
    
    def __init__(self, coordinator: MediaContextV2Coordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_media_manual_target",
            name="PilotSuite media manual target",
            icon="mdi:target-account",
        )

    @property
    def options(self) -> list[str]:
        """Return available target options."""
        if not self.coordinator.data or not self.coordinator.data.zone_map:
            return ["Auto"]
        
        # Collect all entities from zone map
        entities = ["Auto"]
        for zone_config in self.coordinator.data.zone_map.values():
            entities.extend(zone_config.music)
            entities.extend(zone_config.tv)
        
        return sorted(list(set(entities)))

    @property
    def current_option(self) -> str | None:
        """Return current manual target."""
        if not self.coordinator.data:
            return None
            
        if self.coordinator.data.manual_target_entity_id:
            return self.coordinator.data.manual_target_entity_id
            
        return "Auto"

    async def async_select_option(self, option: str) -> None:
        """Select manual target option."""
        try:
            if option == "Auto":
                self.coordinator.clear_manual_overrides()
            else:
                # Set manual target with 30 minute TTL
                self.coordinator.set_manual_target(option, ttl_seconds=30 * 60)
            
            await self.coordinator.async_refresh()
        except Exception as err:
            _LOGGER.error("Failed to select manual target: %s", err)
            raise ServiceValidationError(f"Failed to select manual target: {err}") from err


class ClearOverridesButton(_MediaContextV2Base, ButtonEntity):
    """Button to clear all manual overrides."""
    
    def __init__(self, coordinator: MediaContextV2Coordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_media_clear_overrides",
            name="PilotSuite media clear overrides",
            icon="mdi:restore",
        )

    async def async_press(self) -> None:
        """Press the button."""
        try:
            self.coordinator.clear_manual_overrides()
            await self.coordinator.async_refresh()
        except Exception as err:
            _LOGGER.error("Failed to clear overrides: %s", err)
            raise ServiceValidationError(f"Failed to clear overrides: {err}") from err


# Diagnostic Sensors
class ConfigValidationSensor(_MediaContextV2Base, SensorEntity):
    """Sensor showing configuration validation status."""
    
    def __init__(self, coordinator: MediaContextV2Coordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_media_config_validation",
            name="PilotSuite media config validation",
            icon="mdi:check-circle",
        )

    @property
    def native_value(self) -> str | None:
        """Return validation status."""
        if not self.coordinator.data:
            return "unknown"
            
        findings = self.coordinator.validate_config()
        
        if not findings:
            return "valid"
        
        # Count by severity
        errors = sum(1 for f in findings if f.get("severity") == "error")
        warnings = sum(1 for f in findings if f.get("severity") == "warn")
        
        if errors > 0:
            return "error"
        elif warnings > 0:
            return "warning"
        else:
            return "info"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return validation findings as attributes."""
        if not self.coordinator.data:
            return None
            
        findings = self.coordinator.validate_config()
        return {
            "findings_count": len(findings),
            "findings": findings,
        }

    @property
    def icon(self) -> str:
        """Return icon based on validation status."""
        status = self.native_value
        if status == "valid":
            return "mdi:check-circle"
        elif status == "warning":
            return "mdi:alert-circle"
        elif status == "error":
            return "mdi:close-circle"
        else:
            return "mdi:help-circle"


class DebugInfoSensor(_MediaContextV2Base, SensorEntity):
    """Sensor with detailed debug information."""
    
    def __init__(self, coordinator: MediaContextV2Coordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_media_debug_info",
            name="PilotSuite media debug info",
            icon="mdi:information",
        )

    @property
    def native_value(self) -> str | None:
        return "debug" if self.coordinator.data else "no_data"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return detailed debug information."""
        if not self.coordinator.data:
            return None
            
        data = self.coordinator.data
        
        return {
            # Base context
            "music_active": data.base.music_active,
            "tv_active": data.base.tv_active,
            "music_primary_entity": data.base.music_primary_entity_id,
            "tv_primary_entity": data.base.tv_primary_entity_id,
            "music_primary_area": data.base.music_primary_area,
            "tv_primary_area": data.base.tv_primary_area,
            "music_now_playing": data.base.music_now_playing,
            "tv_source": data.base.tv_source,
            "music_active_count": data.base.music_active_count,
            "tv_active_count": data.base.tv_active_count,
            
            # v2 additions
            "active_mode": data.active_mode,
            "active_target_entity_id": data.active_target_entity_id,
            "active_target_kind": data.active_target_kind,
            "active_zone_id": data.active_zone_id,
            "active_zone_name": data.active_zone_name,
            "reason": data.reason,
            
            # Volume state
            "current_volume": data.current_volume,
            "volume_muted": data.volume_muted,
            
            # Manual overrides
            "manual_target_entity_id": data.manual_target_entity_id,
            "manual_target_expires": data.manual_target_expires,
            "manual_zone_id": data.manual_zone_id,
            "manual_zone_expires": data.manual_zone_expires,
            
            # Zone mapping summary
            "zone_count": len(data.zone_map),
            "zones": list(data.zone_map.keys()),
        }