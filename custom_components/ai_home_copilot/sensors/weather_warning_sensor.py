"""Weather Warning Sensor for Home Assistant (v5.16.0).

Exposes DWD/ZAMG/MeteoSchweiz weather warnings as an HA sensor
with PV impact assessment and energy recommendations.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)

_SEVERITY_ICONS = {
    0: "mdi:weather-sunny",
    1: "mdi:alert-outline",
    2: "mdi:alert",
    3: "mdi:alert-octagon",
    4: "mdi:alert-octagon-outline",
}


class WeatherWarningSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing active weather warnings and energy impact."""

    _attr_name = "Weather Warnings"
    _attr_unique_id = "copilot_weather_warnings"
    _attr_icon = "mdi:weather-lightning-rainy"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    @property
    def native_value(self) -> str:
        total = self._data.get("total", 0)
        if total == 0:
            return "Keine Warnungen"
        highest = self._data.get("highest_severity_label", "Wetterwarnung")
        return f"{total}x {highest}"

    @property
    def icon(self) -> str:
        severity = self._data.get("highest_severity", 0)
        return _SEVERITY_ICONS.get(severity, "mdi:alert")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        warnings = self._data.get("warnings", [])
        impacts = self._data.get("impacts", [])
        by_severity = self._data.get("by_severity", {})

        # Build compact warning list for attributes
        warning_list = []
        for w in warnings[:10]:  # Max 10 in attributes
            warning_list.append({
                "headline": w.get("headline", ""),
                "severity": w.get("severity_label", ""),
                "type": w.get("warning_type_label", ""),
                "region": w.get("region", ""),
                "color": w.get("color", ""),
            })

        # Aggregate PV impact
        max_pv_reduction = 0
        pv_recommendations = []
        for imp in impacts:
            red = imp.get("pv_reduction_pct", 0)
            if red > max_pv_reduction:
                max_pv_reduction = red
            rec = imp.get("recommendation_de", "")
            if rec and rec not in pv_recommendations:
                pv_recommendations.append(rec)

        return {
            "total_warnings": self._data.get("total", 0),
            "highest_severity": self._data.get("highest_severity", 0),
            "highest_severity_label": self._data.get("highest_severity_label", ""),
            "minor_count": by_severity.get("minor", 0),
            "moderate_count": by_severity.get("moderate", 0),
            "severe_count": by_severity.get("severe", 0),
            "extreme_count": by_severity.get("extreme", 0),
            "has_pv_impact": self._data.get("has_pv_impact", False),
            "has_grid_risk": self._data.get("has_grid_risk", False),
            "max_pv_reduction_pct": max_pv_reduction,
            "recommendations": pv_recommendations[:5],
            "warnings": warning_list,
            "source": self._data.get("source", ""),
            "last_updated": self._data.get("last_updated", ""),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"{self._core_base_url()}/api/v1/regional"
        headers = self._core_headers()

        try:
            async with session.get(
                f"{base}/warnings", headers=headers, timeout=15
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._data = data
        except Exception as exc:
            _LOGGER.error("Failed to fetch weather warnings: %s", exc)
