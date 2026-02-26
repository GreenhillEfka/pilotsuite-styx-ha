"""Override Mode sensors for PilotSuite Styx.

Provides sensors that reflect the state of override modes:
- Active Override Mode: Shows the highest-priority active mode
- Override Mode Count: Number of active modes
- Music Allowed: Whether automatic music control is allowed
- Light Allowed: Whether automatic light control is allowed
- Heating Allowed: Whether automatic heating control is allowed
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class OverrideModeSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing the active override mode with highest priority."""

    _attr_icon = "mdi:toggle-switch"
    _attr_name = "Override Mode"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_override_mode_active"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        modes = self.coordinator.data.get("override_modes", {})
        active = modes.get("active_modes", [])
        if not active:
            return "Keine"
        # Return highest priority mode name
        highest = active[-1] if active else {}
        definition = highest.get("definition", {})
        return definition.get("name", highest.get("mode_id", "Unbekannt"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        modes = self.coordinator.data.get("override_modes", {})
        active = modes.get("active_modes", [])
        return {
            "active_count": len(active),
            "active_mode_ids": [m.get("mode_id", "") for m in active],
            "active_mode_names": [
                m.get("definition", {}).get("name", m.get("mode_id", ""))
                for m in active
            ],
        }


class OverrideModeCountSensor(CopilotBaseEntity, SensorEntity):
    """Sensor counting active override modes."""

    _attr_icon = "mdi:counter"
    _attr_name = "Override Modes Active"
    _attr_native_unit_of_measurement = "modes"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_override_mode_count"

    @property
    def native_value(self) -> int:
        if not self.coordinator.data:
            return 0
        modes = self.coordinator.data.get("override_modes", {})
        return len(modes.get("active_modes", []))


class MusicAllowedSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing whether automatic music control is allowed."""

    _attr_icon = "mdi:music-note"
    _attr_name = "Music Cloud Erlaubt"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_music_allowed"

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return "Ja"
        consequences = self.coordinator.data.get("zone_consequences", {})
        allowed = consequences.get("music_allowed", True)
        return "Ja" if allowed else "Nein"

    @property
    def icon(self) -> str:
        if self.native_value == "Nein":
            return "mdi:music-note-off"
        return "mdi:music-note"


class LightAllowedSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing whether automatic light control is allowed."""

    _attr_icon = "mdi:lightbulb"
    _attr_name = "Licht Auto Erlaubt"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_light_allowed"

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return "Ja"
        consequences = self.coordinator.data.get("zone_consequences", {})
        allowed = consequences.get("light_allowed", True)
        return "Ja" if allowed else "Nein"

    @property
    def icon(self) -> str:
        if self.native_value == "Nein":
            return "mdi:lightbulb-off"
        return "mdi:lightbulb-auto"


class VolumePresetSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing the current time-of-day volume preset."""

    _attr_icon = "mdi:volume-medium"
    _attr_name = "Volume Preset"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_volume_preset"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        music_cloud = self.coordinator.data.get("music_cloud", {})
        preset = music_cloud.get("volume_preset", {})
        period = preset.get("time_period", "")
        volume = preset.get("current_volume", 0)
        if period:
            labels = {"morning": "Morgen", "day": "Tag", "evening": "Abend", "night": "Nacht"}
            return f"{labels.get(period, period)} ({int(volume * 100)}%)"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        music_cloud = self.coordinator.data.get("music_cloud", {})
        preset = music_cloud.get("volume_preset", {})
        return {
            "time_period": preset.get("time_period", ""),
            "current_volume": preset.get("current_volume", 0),
            "presets": preset.get("presets", {}),
        }


class MusicCloudCoordinatorSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing the current Music Cloud coordinator zone."""

    _attr_icon = "mdi:speaker-group"
    _attr_name = "Musikwolke Koordinator"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_music_cloud_coordinator"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        music_cloud = self.coordinator.data.get("music_cloud", {})
        groups = music_cloud.get("active_groups", [])
        if groups:
            first_group = groups[0] if isinstance(groups[0], dict) else {}
            return first_group.get("coordinator_zone", first_group.get("source_zone", "Keine"))
        return "Keine"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        music_cloud = self.coordinator.data.get("music_cloud", {})
        groups = music_cloud.get("active_groups", [])
        return {
            "active_groups": len(groups),
            "grouped_zones": [
                z for g in groups
                for z in (g.get("grouped_zones", []) if isinstance(g, dict) else [])
            ],
        }


class MusicCloudStatusSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing overall Music Cloud status."""

    _attr_icon = "mdi:cloud-outline"
    _attr_name = "Musikwolke Status"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_music_cloud_status"

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return "Unbekannt"
        music_cloud = self.coordinator.data.get("music_cloud", {})
        config = music_cloud.get("config", {})
        if not config.get("enabled", True):
            return "Deaktiviert"
        groups = music_cloud.get("active_groups", [])
        if groups:
            return f"Aktiv ({len(groups)} Gruppen)"
        return "Bereit"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        mc = self.coordinator.data.get("music_cloud", {})
        config = mc.get("config", {})
        return {
            "enabled": config.get("enabled", True),
            "follow_timeout_sec": config.get("follow_timeout_sec", 300),
            "overtime_sec": config.get("overtime_sec", 60),
            "coordinator_handoff": config.get("coordinator_handoff", True),
            "default_favorite": config.get("default_favorite", ""),
            "max_dashboard_favorites": config.get("max_dashboard_favorites", 15),
        }


OVERRIDE_MODE_SENSORS = [
    OverrideModeSensor,
    OverrideModeCountSensor,
    MusicAllowedSensor,
    LightAllowedSensor,
    VolumePresetSensor,
    MusicCloudCoordinatorSensor,
    MusicCloudStatusSensor,
]
