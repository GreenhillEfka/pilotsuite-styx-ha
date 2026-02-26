"""Override Mode sensors for PilotSuite Styx.

Provides sensors that reflect the state of override modes:
- Active Override Mode: Shows the highest-priority active mode
- Override Mode Count: Number of active modes
- Music Allowed: Whether automatic music control is allowed
- Light Allowed: Whether automatic light control is allowed
- Heating Allowed: Whether automatic heating control is allowed
- Volume Preset: Current time-of-day volume setting
- Music Cloud Coordinator: Current Musikwolke coordinator zone
- Music Cloud Status: Overall Musikwolke system status
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


def _get_active_modes(data: dict[str, Any] | None) -> list[dict]:
    """Extract active modes list from coordinator data."""
    if not data:
        return []
    modes = data.get("override_modes", {})
    return modes.get("active_modes", [])


def _get_all_definitions(data: dict[str, Any] | None) -> list[dict]:
    """Extract mode definitions from coordinator data."""
    if not data:
        return []
    modes = data.get("override_modes", {})
    return modes.get("definitions", modes.get("modes", []))


def _get_merged_consequences(data: dict[str, Any] | None) -> dict[str, Any]:
    """Merge consequences from all active modes (highest priority wins)."""
    active = _get_active_modes(data)
    if not active:
        return {}
    merged: dict[str, Any] = {}
    for mode in active:
        consequences = mode.get("consequences", {})
        if isinstance(consequences, dict):
            merged.update(consequences)
    return merged


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
        active = _get_active_modes(self.coordinator.data)
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
        active = _get_active_modes(self.coordinator.data)
        definitions = _get_all_definitions(self.coordinator.data)
        return {
            "active_count": len(active),
            "active_mode_ids": [m.get("mode_id", "") for m in active],
            "active_mode_names": [
                m.get("definition", {}).get("name", m.get("mode_id", ""))
                for m in active
            ],
            "available_modes": len(definitions),
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
        return len(_get_active_modes(self.coordinator.data))


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
        consequences = _get_merged_consequences(self.coordinator.data)
        if not consequences:
            return "Ja"
        allowed = consequences.get("music_allowed", True)
        return "Ja" if allowed else "Nein"

    @property
    def icon(self) -> str:
        if self.native_value == "Nein":
            return "mdi:music-note-off"
        return "mdi:music-note"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        consequences = _get_merged_consequences(self.coordinator.data)
        blocking_modes = []
        for mode in _get_active_modes(self.coordinator.data):
            mc = mode.get("consequences", {})
            if isinstance(mc, dict) and not mc.get("music_allowed", True):
                blocking_modes.append(mode.get("mode_id", ""))
        return {
            "music_mute": consequences.get("music_mute", False),
            "volume_max_pct": consequences.get("volume_max_pct"),
            "blocking_modes": blocking_modes,
        }


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
        consequences = _get_merged_consequences(self.coordinator.data)
        if not consequences:
            return "Ja"
        allowed = consequences.get("light_allowed", True)
        return "Ja" if allowed else "Nein"

    @property
    def icon(self) -> str:
        if self.native_value == "Nein":
            return "mdi:lightbulb-off"
        return "mdi:lightbulb-auto"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        consequences = _get_merged_consequences(self.coordinator.data)
        return {
            "light_max_brightness_pct": consequences.get("light_max_brightness_pct"),
            "light_force_color_temp_k": consequences.get("light_force_color_temp_k"),
        }


class HeatingAllowedSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing whether automatic heating is being overridden."""

    _attr_icon = "mdi:thermometer"
    _attr_name = "Heizung Override"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_heating_allowed"

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return "Normal"
        consequences = _get_merged_consequences(self.coordinator.data)
        if not consequences:
            return "Normal"
        target = consequences.get("heating_target_temp_c", 0)
        if target and float(target) > 0:
            return f"Override: {float(target):.1f}°C"
        return "Normal"

    @property
    def icon(self) -> str:
        if "Override" in (self.native_value or ""):
            return "mdi:thermometer-alert"
        return "mdi:thermometer"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        consequences = _get_merged_consequences(self.coordinator.data)
        return {
            "heating_target_temp_c": consequences.get("heating_target_temp_c", 0),
            "presence_alarm": consequences.get("presence_alarm", False),
            "notify_on_presence": consequences.get("notify_on_presence", False),
        }


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
        config = music_cloud.get("config", {})
        presets = config.get("volume_presets", {})
        if not presets:
            return None
        # Determine current time period from Python
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        hour = now.hour + now.minute / 60.0
        if 6.0 <= hour < 10.0:
            period = "morning"
        elif 10.0 <= hour < 17.0:
            period = "day"
        elif 17.0 <= hour < 22.0:
            period = "evening"
        else:
            period = "night"
        volume = presets.get(period, 0.5)
        labels = {"morning": "Morgen", "day": "Tag", "evening": "Abend", "night": "Nacht"}
        return f"{labels.get(period, period)} ({int(float(volume) * 100)}%)"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        music_cloud = self.coordinator.data.get("music_cloud", {})
        config = music_cloud.get("config", {})
        return {
            "volume_presets": config.get("volume_presets", {}),
            "default_favorite": config.get("default_favorite", ""),
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
    HeatingAllowedSensor,
    VolumePresetSensor,
    MusicCloudCoordinatorSensor,
    MusicCloudStatusSensor,
]
