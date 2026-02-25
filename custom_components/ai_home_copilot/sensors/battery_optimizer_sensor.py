"""Battery Optimizer Sensor for Home Assistant (v5.23.0).

Exposes battery charge/discharge strategy as an HA sensor.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class BatteryOptimizerSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing battery optimization strategy and status."""

    _attr_name = "Battery Strategy"
    _attr_unique_id = "copilot_battery_strategy"
    _attr_icon = "mdi:battery-charging"
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._status: dict[str, Any] = {}
        self._schedule: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        return self._status.get("soc_pct")

    @property
    def icon(self) -> str:
        soc = self._status.get("soc_pct", 50)
        action = self._status.get("current_action", "hold")
        if action == "charge" or action == "charge_solar":
            return "mdi:battery-charging"
        elif action == "discharge":
            return "mdi:battery-arrow-down"
        elif soc >= 80:
            return "mdi:battery-high"
        elif soc >= 30:
            return "mdi:battery-medium"
        return "mdi:battery-low"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = {
            "soc_pct": self._status.get("soc_pct", 0),
            "soc_kwh": self._status.get("soc_kwh", 0),
            "capacity_kwh": self._status.get("capacity_kwh", 0),
            "current_action": self._status.get("current_action", "hold"),
            "current_power_kw": self._status.get("current_power_kw", 0),
            "strategy": self._status.get("strategy", "none"),
            "cycles_today": self._status.get("cycles_today", 0),
            "next_charge_at": self._status.get("next_charge_at", ""),
            "next_discharge_at": self._status.get("next_discharge_at", ""),
            "health_pct": self._status.get("health_pct", 100),
        }

        if self._schedule:
            attrs["estimated_savings_eur"] = self._schedule.get("estimated_savings_eur", 0)
            attrs["total_charge_kwh"] = self._schedule.get("total_charge_kwh", 0)
            attrs["total_discharge_kwh"] = self._schedule.get("total_discharge_kwh", 0)
            attrs["total_solar_charge_kwh"] = self._schedule.get("total_solar_charge_kwh", 0)
            attrs["estimated_cycles"] = self._schedule.get("estimated_cycles", 0)
            attrs["avg_charge_price_ct"] = self._schedule.get("avg_charge_price_ct", 0)
            attrs["avg_discharge_price_ct"] = self._schedule.get("avg_discharge_price_ct", 0)

        return attrs

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"{self._core_base_url()}/api/v1/regional"
        headers = self._core_headers()

        try:
            async with session.get(
                f"{base}/battery/status", headers=headers, timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._status = data

            async with session.get(
                f"{base}/battery/schedule", headers=headers, timeout=30
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._schedule = data
        except Exception as exc:
            _LOGGER.debug("Failed to fetch battery data: %s", exc)
