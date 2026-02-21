"""Gas Meter Sensor for Home Assistant (v6.3.0)."""

from __future__ import annotations

import logging
from typing import Any

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 60


class GasMeterSensor(CopilotBaseEntity):
    """Sensor showing gas consumption and costs."""

    _attr_icon = "mdi:meter-gas"
    _attr_name = "PilotSuite Gaszähler"
    _attr_unique_id = "pilotsuite_gas_meter"
    _attr_native_unit_of_measurement = "m³"
    _attr_device_class = "gas"
    _attr_state_class = "total_increasing"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._gas_data: dict[str, Any] = {}

    @property
    def state(self) -> float | None:
        return self._gas_data.get("current_meter_m3")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        today = self._gas_data.get("today", {})
        month = self._gas_data.get("month", {})
        forecast = self._gas_data.get("forecast_month", {})
        return {
            "total_impulses": self._gas_data.get("total_impulses", 0),
            "today_m3": today.get("consumption_m3", 0),
            "today_kwh": today.get("consumption_kwh", 0),
            "today_cost_eur": today.get("cost_eur", 0),
            "month_m3": month.get("consumption_m3", 0),
            "month_kwh": month.get("consumption_kwh", 0),
            "month_cost_eur": month.get("cost_eur", 0),
            "forecast_month_eur": forecast.get("estimated_cost_eur", 0),
            "forecast_trend": forecast.get("trend", "stabil"),
            "gas_price_ct_kwh": self._gas_data.get("gas_price_ct_kwh", 0),
            "gas_price_eur_m3": self._gas_data.get("gas_price_eur_m3", 0),
            "calorific_value": self._gas_data.get("calorific_value", 0),
        }

    async def async_update(self) -> None:
        data = await self._fetch("/api/v1/regional/gas")
        if data:
            self._gas_data = data
