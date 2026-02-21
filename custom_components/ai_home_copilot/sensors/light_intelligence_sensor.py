"""Light Intelligence Sensor for Home Assistant (v6.5.0)."""

from __future__ import annotations

import logging
from typing import Any

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 30


class LightIntelligenceSensor(CopilotBaseEntity):
    """Sensor showing light intelligence status and scene suggestions."""

    _attr_icon = "mdi:brightness-auto"
    _attr_name = "PilotSuite Licht-Intelligence"
    _attr_unique_id = "pilotsuite_light_intelligence"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._light_data: dict[str, Any] = {}

    @property
    def state(self) -> str:
        suggested = self._light_data.get("suggested_scene_name")
        if suggested:
            return suggested
        sun = self._light_data.get("sun", {})
        phase = sun.get("phase", "unknown")
        phase_map = {
            "day": "Tag", "night": "Nacht", "dawn": "Dämmerung",
            "dusk": "Abenddämmerung", "sunrise": "Sonnenaufgang",
            "sunset": "Sonnenuntergang",
        }
        return phase_map.get(phase, phase)

    @property
    def icon(self) -> str:
        sun = self._light_data.get("sun", {})
        phase = sun.get("phase", "day")
        icons = {
            "day": "mdi:white-balance-sunny",
            "night": "mdi:weather-night",
            "dawn": "mdi:weather-sunset-up",
            "dusk": "mdi:weather-sunset-down",
            "sunrise": "mdi:weather-sunset-up",
            "sunset": "mdi:weather-sunset-down",
        }
        return icons.get(phase, "mdi:brightness-auto")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        sun = self._light_data.get("sun", {})
        zones = self._light_data.get("zones", [])
        return {
            "sun_elevation": sun.get("elevation", 0),
            "sun_azimuth": sun.get("azimuth", 0),
            "sun_phase": sun.get("phase", "unknown"),
            "outdoor_lux": self._light_data.get("global_outdoor_lux", 0),
            "suggested_scene": self._light_data.get("suggested_scene"),
            "active_scene": self._light_data.get("active_scene"),
            "cloud_filter_active": self._light_data.get("cloud_filter_active", False),
            "zone_count": len(zones),
            "zones_needing_light": sum(1 for z in zones if z.get("needs_light")),
        }

    async def async_update(self) -> None:
        data = await self._fetch("/api/v1/hub/light")
        if data:
            self._light_data = data
