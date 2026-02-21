"""Heat Pump Sensor for Home Assistant (v5.24.0).

Exposes heat pump COP-optimized scheduling as an HA sensor.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class HeatPumpSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing heat pump COP and scheduling status."""

    _attr_name = "Heat Pump"
    _attr_unique_id = "copilot_heat_pump"
    _attr_icon = "mdi:heat-pump-outline"
    _attr_native_unit_of_measurement = "COP"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._status: dict[str, Any] = {}
        self._schedule: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        return self._status.get("current_cop")

    @property
    def icon(self) -> str:
        action = self._status.get("current_action", "off")
        if action == "heat":
            return "mdi:heat-pump"
        elif action == "dhw":
            return "mdi:water-boiler"
        elif action == "solar_boost":
            return "mdi:solar-power-variant"
        elif action == "defrost":
            return "mdi:snowflake-melt"
        return "mdi:heat-pump-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = {
            "pump_type": self._status.get("pump_type", "air_water"),
            "current_action": self._status.get("current_action", "off"),
            "current_cop": self._status.get("current_cop", 0),
            "current_power_kw": self._status.get("current_power_kw", 0),
            "room_temp_c": self._status.get("room_temp_c", 0),
            "target_room_temp_c": self._status.get("target_room_temp_c", 21),
            "hot_water_temp_c": self._status.get("hot_water_temp_c", 0),
            "hot_water_target_c": self._status.get("hot_water_target_c", 55),
            "outdoor_temp_c": self._status.get("outdoor_temp_c", 0),
            "runtime_today_h": self._status.get("runtime_today_h", 0),
            "heat_today_kwh": self._status.get("heat_today_kwh", 0),
            "electricity_today_kwh": self._status.get("electricity_today_kwh", 0),
            "cost_today_eur": self._status.get("cost_today_eur", 0),
            "avg_cop_today": self._status.get("avg_cop_today", 0),
            "strategy": self._status.get("strategy", "cop_optimized"),
            "next_action": self._status.get("next_action", ""),
            "next_action_at": self._status.get("next_action_at", ""),
        }

        if self._schedule:
            attrs["total_heat_kwh"] = self._schedule.get("total_heat_kwh", 0)
            attrs["total_electricity_kwh"] = self._schedule.get("total_electricity_kwh", 0)
            attrs["total_cost_eur"] = self._schedule.get("total_cost_eur", 0)
            attrs["avg_cop"] = self._schedule.get("avg_cop", 0)
            attrs["runtime_hours"] = self._schedule.get("runtime_hours", 0)
            attrs["dhw_cycles"] = self._schedule.get("dhw_cycles", 0)
            attrs["defrost_hours"] = self._schedule.get("defrost_hours", 0)

        return attrs

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"http://{self._host}:{self._port}/api/v1/regional"
        headers = {}
        token = self.coordinator._config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with session.get(
                f"{base}/heatpump/status", headers=headers, timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._status = data

            async with session.get(
                f"{base}/heatpump/schedule", headers=headers, timeout=30
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._schedule = data
        except Exception as exc:
            _LOGGER.debug("Failed to fetch heat pump data: %s", exc)
