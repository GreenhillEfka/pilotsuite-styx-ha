"""Comfort Index Sensor for PilotSuite (v6.0.0).

Exposes a composite comfort score (0-100) and lighting suggestions
as a Home Assistant sensor with rich attributes.

The underlying v6.0 comfort model uses:
- Gaussian bell curves for temperature/humidity scoring (ISO 7730 inspired)
- Steadman heat index for thermal interaction
- Sigmoid decay for CO2 (WHO guidelines)
- Circadian sine-wave model for light targets
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
        self._attr_unique_id = "copilot_comfort_index"
        self._comfort_data: dict[str, Any] | None = None

    @property
    def available(self) -> bool:
        """Only available when comfort data has been fetched successfully."""
        return self._comfort_data is not None and self._comfort_data.get("ok", False)

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
        """Return comfort details with per-factor breakdown."""
        attrs: dict[str, Any] = {
            "comfort_url": (
                f"{self._core_base_url()}/api/v1/comfort"
            ),
            "lighting_url": (
                f"{self._core_base_url()}/api/v1/comfort/lighting"
            ),
        }

        if self._comfort_data and self._comfort_data.get("ok"):
            attrs["grade"] = self._comfort_data.get("grade")
            attrs["zone_id"] = self._comfort_data.get("zone_id")
            attrs["suggestions"] = self._comfort_data.get("suggestions", [])
            attrs["model_version"] = "6.0"

            # Per-factor breakdown (temperature, humidity, thermal_interaction,
            # air_quality, light)
            worst_factor = None
            worst_score = 101.0
            for reading in self._comfort_data.get("readings", []):
                factor = reading.get("factor", "unknown")
                score = reading.get("score", 0)
                attrs[f"{factor}_score"] = score
                attrs[f"{factor}_status"] = reading.get("status", "unknown")
                attrs[f"{factor}_weight"] = reading.get("weight", 0)
                if reading.get("raw_value") is not None:
                    attrs[f"{factor}_value"] = reading["raw_value"]
                # Track worst factor for quick diagnostics
                if score < worst_score:
                    worst_score = score
                    worst_factor = factor

            if worst_factor:
                attrs["limiting_factor"] = worst_factor
                attrs["limiting_factor_score"] = worst_score

        return attrs

    async def async_update(self) -> None:
        """Fetch comfort index from Core API."""
        try:
            session = self.coordinator._session
            if session is None:
                return

            url = f"{self._core_base_url()}/api/v1/comfort"
            headers = self._core_headers()

            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    self._comfort_data = await resp.json()
                else:
                    _LOGGER.debug("Comfort API returned %s", resp.status)
        except Exception as e:
            _LOGGER.debug("Failed to fetch comfort data: %s", e)
