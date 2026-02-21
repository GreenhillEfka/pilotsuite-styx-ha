"""Comfort Index Sensor for PilotSuite (v5.7.0).

Exposes a composite comfort score (0-100) and lighting suggestions
as a Home Assistant sensor with rich attributes.
"""
from __future__ import annotations

import logging
from typing import Any

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)

GRADE_ICONS = {
    "A": "mdi:emoticon-happy",
    "B": "mdi:emoticon",
    "C": "mdi:emoticon-neutral",
    "D": "mdi:emoticon-sad",
    "F": "mdi:emoticon-dead",
}


class ComfortIndexSensor(CopilotBaseEntity):
    """Sensor exposing comfort index from Core."""

    _attr_name = "Comfort Index"
    _attr_icon = "mdi:home-thermometer"
    _attr_native_unit_of_measurement = "points"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._host}:{self._port}_comfort_index"
        self._comfort_data: dict[str, Any] | None = None

    @property
    def native_value(self) -> float | None:
        """Return comfort score as state."""
        if self._comfort_data and self._comfort_data.get("ok"):
            return self._comfort_data.get("score")
        return None

    @property
    def icon(self) -> str:
        """Return icon based on comfort grade."""
        if self._comfort_data and self._comfort_data.get("ok"):
            grade = self._comfort_data.get("grade", "C")
            return GRADE_ICONS.get(grade, "mdi:home-thermometer")
        return "mdi:home-thermometer"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return comfort details."""
        attrs: dict[str, Any] = {
            "comfort_url": (
                f"http://{self._host}:{self._port}/api/v1/comfort"
            ),
            "lighting_url": (
                f"http://{self._host}:{self._port}/api/v1/comfort/lighting"
            ),
        }

        if self._comfort_data and self._comfort_data.get("ok"):
            attrs["grade"] = self._comfort_data.get("grade")
            attrs["zone_id"] = self._comfort_data.get("zone_id")
            attrs["suggestions"] = self._comfort_data.get("suggestions", [])

            for reading in self._comfort_data.get("readings", []):
                factor = reading["factor"]
                attrs[f"{factor}_score"] = reading["score"]
                attrs[f"{factor}_status"] = reading["status"]
                if reading["raw_value"] is not None:
                    attrs[f"{factor}_value"] = reading["raw_value"]

        return attrs

    async def async_update(self) -> None:
        """Fetch comfort index from Core API."""
        try:
            session = self.coordinator._session
            if session is None:
                return

            url = f"http://{self._host}:{self._port}/api/v1/comfort"
            headers = {}
            token = self.coordinator._config.get("auth_token")
            if token:
                headers["X-Auth-Token"] = token

            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    self._comfort_data = await resp.json()
                else:
                    _LOGGER.debug("Comfort API returned %s", resp.status)
        except Exception as e:
            _LOGGER.debug("Failed to fetch comfort data: %s", e)
