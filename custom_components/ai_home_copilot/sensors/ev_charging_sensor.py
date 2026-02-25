"""EV Charging Sensor for Home Assistant (v5.25.0).

Exposes EV charging planner state as an HA sensor.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class EVChargingSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing EV charging status and schedule."""

    _attr_name = "EV Charging"
    _attr_unique_id = "copilot_ev_charging"
    _attr_icon = "mdi:ev-station"
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._status: dict[str, Any] = {}
        self._schedule: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        return self._status.get("current_soc_pct")

    @property
    def icon(self) -> str:
        action = self._status.get("current_action", "idle")
        if action == "charge":
            return "mdi:ev-station"
        elif action == "solar_charge":
            return "mdi:solar-power-variant"
        elif self._status.get("departure_ready"):
            return "mdi:car-electric"
        return "mdi:car-electric-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = {
            "vehicle_name": self._status.get("vehicle_name", "EV"),
            "connector_type": self._status.get("connector_type", "type2"),
            "current_soc_pct": self._status.get("current_soc_pct", 0),
            "target_soc_pct": self._status.get("target_soc_pct", 80),
            "current_action": self._status.get("current_action", "idle"),
            "current_power_kw": self._status.get("current_power_kw", 0),
            "energy_charged_kwh": self._status.get("energy_charged_kwh", 0),
            "cost_so_far_eur": self._status.get("cost_so_far_eur", 0),
            "estimated_range_km": self._status.get("estimated_range_km", 0),
            "time_to_target_h": self._status.get("time_to_target_h", 0),
            "next_departure": self._status.get("next_departure", ""),
            "departure_ready": self._status.get("departure_ready", False),
            "strategy": self._status.get("strategy", "cost_optimized"),
        }

        if self._schedule:
            attrs["total_energy_kwh"] = self._schedule.get("total_energy_kwh", 0)
            attrs["total_cost_eur"] = self._schedule.get("total_cost_eur", 0)
            attrs["solar_energy_kwh"] = self._schedule.get("solar_energy_kwh", 0)
            attrs["grid_energy_kwh"] = self._schedule.get("grid_energy_kwh", 0)
            attrs["solar_share_pct"] = self._schedule.get("solar_share_pct", 0)
            attrs["avg_price_ct"] = self._schedule.get("avg_price_ct", 0)
            attrs["charge_hours"] = self._schedule.get("charge_hours", 0)

        return attrs

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"{self._core_base_url()}/api/v1/regional"
        headers = self._core_headers()

        try:
            async with session.get(
                f"{base}/ev/status", headers=headers, timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._status = data

            async with session.get(
                f"{base}/ev/schedule", headers=headers, timeout=30
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._schedule = data
        except Exception as exc:
            _LOGGER.debug("Failed to fetch EV charging data: %s", exc)
