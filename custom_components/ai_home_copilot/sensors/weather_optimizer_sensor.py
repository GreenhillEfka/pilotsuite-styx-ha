"""Weather-Aware Optimizer Sensor for Home Assistant (v5.11.0).

Exposes the 48-hour weather-aware optimization plan as an HA sensor entity.
State shows the number of optimal consumption windows found.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class WeatherOptimizerSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing weather-aware energy optimization status."""

    _attr_name = "Weather Optimizer"
    _attr_unique_id = "copilot_weather_optimizer"
    _attr_icon = "mdi:weather-sunny-alert"
    _attr_native_unit_of_measurement = "windows"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    @property
    def native_value(self) -> int:
        return self._data.get("optimal_windows_count", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        summary = self._data.get("summary", {})
        return {
            "total_pv_kwh": summary.get("total_pv_kwh", 0),
            "avg_price_eur_kwh": summary.get("avg_price_eur_kwh", 0),
            "best_hours": summary.get("best_hours", []),
            "worst_hours": summary.get("worst_hours", []),
            "pv_self_consumption_pct": summary.get("pv_self_consumption_potential_pct", 0),
            "alerts": self._data.get("alerts", []),
            "top_windows": self._data.get("top_windows", [])[:3],
            "battery_actions": self._data.get("battery_plan_count", 0),
            "horizon_hours": self._data.get("horizon_hours", 0),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        url = f"{self._core_base_url()}/api/v1/predict/weather-optimize"
        try:
            headers = self._core_headers()
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._data = data
                        self._data["optimal_windows_count"] = (
                            data.get("summary", {}).get("optimal_windows_count", 0)
                        )
                else:
                    _LOGGER.warning("Weather optimizer API returned %s", resp.status)
        except Exception as exc:
            _LOGGER.error("Failed to fetch weather optimizer data: %s", exc)
