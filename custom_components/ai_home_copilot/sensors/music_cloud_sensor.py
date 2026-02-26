"""Music Cloud sensor — tracks zone-following music state from Core."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class MusicCloudSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing active music zone following status."""

    _attr_name = "Music Cloud"
    _attr_unique_id = "ai_home_copilot_music_cloud"
    _attr_icon = "mdi:music-circle"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        mc = self.coordinator.data.get("music_cloud", {})
        active_zone = mc.get("active_zone")
        if active_zone:
            return f"Following: {active_zone}"
        return "idle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        mc = self.coordinator.data.get("music_cloud", {})
        return {
            "active_zone": mc.get("active_zone"),
            "grouped_speakers": mc.get("grouped_speakers", []),
            "is_following": mc.get("is_following", False),
            "last_transition": mc.get("last_transition"),
            "follow_mode": mc.get("follow_mode", "presence"),
            "zone_count": mc.get("zone_count", 0),
        }


class MusicCloudZonesSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing Music Cloud configured zone count."""

    _attr_name = "Music Cloud Zones"
    _attr_unique_id = "ai_home_copilot_music_cloud_zones"
    _attr_icon = "mdi:speaker-group"
    _attr_native_unit_of_measurement = "zones"

    @property
    def native_value(self) -> int:
        if not self.coordinator.data:
            return 0
        mc = self.coordinator.data.get("music_cloud", {})
        return mc.get("zone_count", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        mc = self.coordinator.data.get("music_cloud", {})
        return {
            "zones": mc.get("zones", []),
            "primary_speaker": mc.get("primary_speaker"),
        }
