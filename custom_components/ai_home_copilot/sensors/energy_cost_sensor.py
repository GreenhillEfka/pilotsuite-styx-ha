"""Energy Cost Sensor for PilotSuite (v5.10.0).

Exposes energy cost data as a HA sensor with daily cost, budget status,
and period comparison in attributes.
"""
from __future__ import annotations

import logging
from typing import Any

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class EnergyCostSensor(CopilotBaseEntity):
    """Sensor exposing energy cost tracking from Core."""

    _attr_name = "Energy Cost"
    _attr_icon = "mdi:currency-eur"
    _attr_native_unit_of_measurement = "EUR"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._host}:{self._port}_energy_cost"
        self._summary_data: dict[str, Any] | None = None
        self._budget_data: dict[str, Any] | None = None

    @property
    def native_value(self) -> float | None:
        """Return weekly cost as state."""
        if self._summary_data and self._summary_data.get("ok"):
            return self._summary_data.get("total_cost_eur")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return cost details."""
        attrs: dict[str, Any] = {
            "costs_url": f"http://{self._host}:{self._port}/api/v1/energy/costs",
            "budget_url": f"http://{self._host}:{self._port}/api/v1/energy/costs/budget",
        }

        if self._summary_data and self._summary_data.get("ok"):
            attrs["period"] = self._summary_data.get("period")
            attrs["avg_daily_cost_eur"] = self._summary_data.get("avg_daily_cost_eur")
            attrs["total_consumption_kwh"] = self._summary_data.get("total_consumption_kwh")
            attrs["total_savings_eur"] = self._summary_data.get("total_savings_eur")
            attrs["days_count"] = self._summary_data.get("days_count")

        if self._budget_data and self._budget_data.get("ok"):
            attrs["budget_eur"] = self._budget_data.get("budget_eur")
            attrs["budget_spent_eur"] = self._budget_data.get("spent_eur")
            attrs["budget_remaining_eur"] = self._budget_data.get("remaining_eur")
            attrs["budget_percent_used"] = self._budget_data.get("percent_used")
            attrs["budget_on_track"] = self._budget_data.get("on_track")
            attrs["budget_projected_eur"] = self._budget_data.get("projected_total_eur")

        return attrs

    async def async_update(self) -> None:
        """Fetch cost data from Core API."""
        try:
            session = self.coordinator._session
            if session is None:
                return

            headers = {}
            token = self.coordinator._config.get("token") or self.coordinator._config.get("auth_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
                headers["X-Auth-Token"] = token

            base = f"http://{self._host}:{self._port}"

            async with session.get(
                f"{base}/api/v1/energy/costs/summary?period=weekly",
                headers=headers, timeout=10,
            ) as resp:
                if resp.status == 200:
                    self._summary_data = await resp.json()

            async with session.get(
                f"{base}/api/v1/energy/costs/budget",
                headers=headers, timeout=10,
            ) as resp:
                if resp.status == 200:
                    self._budget_data = await resp.json()

        except Exception as e:
            _LOGGER.debug("Failed to fetch cost data: %s", e)
