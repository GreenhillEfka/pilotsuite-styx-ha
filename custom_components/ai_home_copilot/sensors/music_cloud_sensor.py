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
        groups = mc.get("active_groups", [])
        if groups:
            source = groups[0].get("source_zone", "unknown") if isinstance(groups[0], dict) else "unknown"
            return f"Following: {source}"
        config = mc.get("config", {})
        if not config.get("enabled", True):
            return "disabled"
        return "idle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        mc = self.coordinator.data.get("music_cloud", {})
        groups = mc.get("active_groups", [])
        config = mc.get("config", {})
        status = mc.get("status", {})
        return {
            "active_groups": len(groups),
            "coordinator_zone": groups[0].get("coordinator_zone", "") if groups and isinstance(groups[0], dict) else "",
            "grouped_zones": [
                z for g in groups
                for z in (g.get("grouped_zones", []) if isinstance(g, dict) else [])
            ],
            "is_following": len(groups) > 0,
            "enabled": config.get("enabled", True),
            "follow_timeout_sec": config.get("follow_timeout_sec", 300),
            "total_zones": status.get("zone_count", 0),
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
        status = mc.get("status", {})
        zones = status.get("zones", {})
        if isinstance(zones, dict):
            return len(zones)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        mc = self.coordinator.data.get("music_cloud", {})
        status = mc.get("status", {})
        zones = status.get("zones", {})
        zone_ids = list(zones.keys()) if isinstance(zones, dict) else []
        return {
            "zones": zone_ids,
            "active_groups": len(mc.get("active_groups", [])),
        }
