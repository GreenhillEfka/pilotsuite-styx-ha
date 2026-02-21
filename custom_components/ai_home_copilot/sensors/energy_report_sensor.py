"""Energy Report Sensor for Home Assistant (v5.13.0).

Exposes weekly energy report highlights as an HA sensor.
State shows the weekly net cost in EUR.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class EnergyReportSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing latest energy report highlights."""

    _attr_name = "Energy Report"
    _attr_unique_id = "copilot_energy_report"
    _attr_icon = "mdi:file-chart-outline"
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        costs = self._data.get("costs", {})
        return costs.get("net_cost_eur")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "report_type": self._data.get("report_type", "weekly"),
            "period_start": self._data.get("period_start", ""),
            "period_end": self._data.get("period_end", ""),
            "consumption_kwh": self._data.get("consumption", {}).get("total_consumption_kwh", 0),
            "production_kwh": self._data.get("consumption", {}).get("total_production_kwh", 0),
            "autarky_pct": self._data.get("consumption", {}).get("autarky_ratio_pct", 0),
            "solar_savings_eur": self._data.get("costs", {}).get("solar_savings_eur", 0),
            "trend": self._data.get("comparison", {}).get("trend", "stable"),
            "highlights": self._data.get("highlights", []),
            "recommendations_count": len(self._data.get("recommendations", [])),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        url = f"http://{self._host}:{self._port}/api/v1/energy/reports/generate"
        headers = {"Content-Type": "application/json"}
        token = self.coordinator._config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            import json
            async with session.post(
                url, headers=headers,
                data=json.dumps({"report_type": "weekly"}),
                timeout=15,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._data = data.get("report", {})
                else:
                    _LOGGER.warning("Energy report API returned %s", resp.status)
        except Exception as exc:
            _LOGGER.error("Failed to fetch energy report: %s", exc)
