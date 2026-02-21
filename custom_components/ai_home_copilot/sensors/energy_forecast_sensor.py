"""Energy Forecast Sensor for Home Assistant (v5.20.0).

Exposes 48h energy forecast with PV, prices, and recommendations
as an HA sensor for dashboard integration.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class EnergyForecastSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing 48h energy forecast summary."""

    _attr_name = "Energy Forecast"
    _attr_unique_id = "copilot_energy_forecast"
    _attr_icon = "mdi:chart-timeline-variant"
    _attr_native_unit_of_measurement = "kWh"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        summary = self._data.get("summary", {})
        return summary.get("total_pv_kwh_estimated")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        summary = self._data.get("summary", {})
        cards = self._data.get("cards", [])

        return {
            "total_hours": summary.get("total_hours", 0),
            "avg_price_ct_kwh": summary.get("avg_price_ct", 0),
            "min_price_ct_kwh": summary.get("min_price_ct", 0),
            "max_price_ct_kwh": summary.get("max_price_ct", 0),
            "cheapest_hour": summary.get("cheapest_hour", ""),
            "most_expensive_hour": summary.get("most_expensive_hour", ""),
            "daylight_hours": summary.get("daylight_hours", 0),
            "avg_pv_factor": summary.get("avg_pv_factor", 0),
            "best_charge_window": summary.get("best_charge_window", ""),
            "best_consume_window": summary.get("best_consume_window", ""),
            "weather_impacted_hours": summary.get("weather_impacted_hours", 0),
            "card_count": len(cards),
            "generated_at": self._data.get("generated_at", ""),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"http://{self._host}:{self._port}/api/v1/regional"
        headers = {}
        token = self.coordinator._config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with session.get(
                f"{base}/forecast/dashboard", headers=headers, timeout=30
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._data = data
        except Exception as exc:
            _LOGGER.error("Failed to fetch energy forecast: %s", exc)
