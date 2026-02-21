"""Scene Intelligence Sensor for PilotSuite HA Integration (v7.0.0).

Displays active scene, suggestions, cloud status, and pattern learning info.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)

_ICON_MAP = {
    "morning_routine": "mdi:weather-sunny",
    "work_focus": "mdi:head-lightbulb",
    "lunch_break": "mdi:food",
    "afternoon_relax": "mdi:sofa",
    "dinner_time": "mdi:silverware-fork-knife",
    "movie_night": "mdi:movie-open",
    "romantic_evening": "mdi:heart",
    "bedtime": "mdi:bed",
    "party": "mdi:party-popper",
    "away": "mdi:home-export-outline",
}


class SceneIntelligenceSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing scene intelligence overview."""

    _attr_name = "Scene Intelligence"
    _attr_icon = "mdi:palette"
    _attr_unique_id = "pilotsuite_scene_intelligence"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    async def _fetch(self) -> dict | None:
        import aiohttp
        try:
            url = f"http://{self._host}:{self._port}/api/v1/hub/scenes"
            headers = {"Authorization": f"Bearer {self.coordinator._config.get('token', '')}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception:
            logger.debug("Failed to fetch scene intelligence data")
        return None

    async def async_update(self) -> None:
        data = await self._fetch()
        if data and data.get("ok"):
            self._data = data

    @property
    def native_value(self) -> str:
        active = self._data.get("active_scene")
        if active:
            return active.get("name_de", "Aktive Szene")
        total = self._data.get("total_scenes", 0)
        if total == 0:
            return "Nicht verfügbar"
        return f"{total} Szenen verfügbar"

    @property
    def icon(self) -> str:
        active = self._data.get("active_scene")
        if active:
            return _ICON_MAP.get(active.get("scene_id", ""), "mdi:palette")
        return "mdi:palette"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "total_scenes": self._data.get("total_scenes", 0),
            "learned_patterns": self._data.get("learned_patterns", 0),
        }

        active = self._data.get("active_scene")
        if active:
            attrs["active_scene_id"] = active.get("scene_id")
            attrs["active_scene_name"] = active.get("name_de")
            attrs["active_zone"] = active.get("zone_id")

        suggestions = self._data.get("suggestions", [])
        if suggestions:
            attrs["suggestions"] = [
                {
                    "scene": s.get("name_de"),
                    "confidence": s.get("confidence"),
                    "reason": s.get("reason_de"),
                    "icon": s.get("icon"),
                }
                for s in suggestions[:3]
            ]

        cloud = self._data.get("cloud_status", {})
        if cloud:
            attrs["cloud_connected"] = cloud.get("connected", False)
            attrs["cloud_shared_scenes"] = cloud.get("shared_scenes", 0)

        categories = self._data.get("categories", {})
        if categories:
            attrs["categories"] = categories

        return attrs
