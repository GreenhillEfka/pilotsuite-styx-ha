"""Tariff Sensor for Home Assistant (v5.18.0).

Exposes dynamic electricity pricing with aWATTar/EPEX integration
as an HA sensor with optimal window and recommendations.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)

_LEVEL_ICONS = {
    "very_low": "mdi:lightning-bolt",
    "low": "mdi:flash",
    "normal": "mdi:flash-outline",
    "high": "mdi:flash-alert",
    "very_high": "mdi:flash-alert-outline",
}


class TariffSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing current electricity tariff and optimal windows."""

    _attr_name = "Electricity Tariff"
    _attr_unique_id = "copilot_electricity_tariff"
    _attr_icon = "mdi:currency-eur"
    _attr_native_unit_of_measurement = "ct/kWh"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        return self._data.get("current_price_ct_kwh")

    @property
    def icon(self) -> str:
        level = self._data.get("current_level", "normal")
        return _LEVEL_ICONS.get(level, "mdi:flash-outline")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "current_price_eur_kwh": self._data.get("current_price_eur_kwh"),
            "current_level": self._data.get("current_level", ""),
            "avg_price_ct_kwh": round(
                (self._data.get("avg_price_eur_kwh") or 0) * 100, 2
            ),
            "min_price_ct_kwh": round(
                (self._data.get("min_price_eur_kwh") or 0) * 100, 2
            ),
            "max_price_ct_kwh": round(
                (self._data.get("max_price_eur_kwh") or 0) * 100, 2
            ),
            "min_hour": self._data.get("min_hour", ""),
            "max_hour": self._data.get("max_hour", ""),
            "spread_ct_kwh": round(
                (self._data.get("spread_eur_kwh") or 0) * 100, 2
            ),
            "tariff_type": self._data.get("tariff_type", ""),
            "source": self._data.get("source", ""),
            "hours_available": self._data.get("hours_available", 0),
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
                f"{base}/tariff/summary", headers=headers, timeout=15
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._data = data
        except Exception as exc:
            _LOGGER.error("Failed to fetch tariff data: %s", exc)
