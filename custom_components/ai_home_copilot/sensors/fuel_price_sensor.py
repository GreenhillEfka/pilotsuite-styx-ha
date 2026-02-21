"""Fuel Price Sensor for Home Assistant (v5.17.0).

Exposes fuel price comparison (Strom vs Diesel vs Benzin) as an HA sensor
with cost-per-100km calculations and Tankerkoenig integration.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class FuelPriceSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing fuel vs electricity cost comparison."""

    _attr_name = "Fuel Price Comparison"
    _attr_unique_id = "copilot_fuel_price_comparison"
    _attr_icon = "mdi:gas-station"
    _attr_native_unit_of_measurement = "EUR/100km"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}
        self._compare: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        if not self._compare:
            return None
        return self._compare.get("electric_eur")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        prices = self._data
        compare = self._compare

        attrs = {
            "electric_eur_100km": compare.get("electric_eur"),
            "diesel_eur_100km": compare.get("diesel_eur"),
            "benzin_eur_100km": compare.get("benzin_eur"),
            "e10_eur_100km": compare.get("e10_eur"),
            "cheapest": compare.get("cheapest", ""),
            "savings_vs_diesel_eur": compare.get("savings_vs_diesel_eur"),
            "savings_vs_benzin_eur": compare.get("savings_vs_benzin_eur"),
            "co2_electric_kg": compare.get("co2_electric_kg"),
            "co2_diesel_kg": compare.get("co2_diesel_kg"),
            "co2_benzin_kg": compare.get("co2_benzin_kg"),
        }

        # Add raw fuel prices if available
        if prices:
            attrs.update({
                "diesel_avg_eur_l": prices.get("diesel_avg"),
                "diesel_min_eur_l": prices.get("diesel_min"),
                "e5_avg_eur_l": prices.get("e5_avg"),
                "e5_min_eur_l": prices.get("e5_min"),
                "e10_avg_eur_l": prices.get("e10_avg"),
                "e10_min_eur_l": prices.get("e10_min"),
                "station_count": prices.get("station_count", 0),
                "cheapest_diesel_station": prices.get("cheapest_diesel", ""),
                "cheapest_e5_station": prices.get("cheapest_e5", ""),
                "radius_km": prices.get("radius_km"),
            })

        return attrs

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"http://{self._host}:{self._port}/api/v1/regional"
        headers = {}
        token = self.coordinator._config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Fetch prices and comparison in parallel
        try:
            async with session.get(
                f"{base}/fuel/prices", headers=headers, timeout=15
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok") and data.get("diesel_avg") is not None:
                        self._data = data
        except Exception as exc:
            _LOGGER.debug("Failed to fetch fuel prices: %s", exc)

        try:
            async with session.get(
                f"{base}/fuel/compare", headers=headers, timeout=15
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok") and data.get("electric_eur") is not None:
                        self._compare = data
        except Exception as exc:
            _LOGGER.debug("Failed to fetch fuel comparison: %s", exc)
