"""Energy Advisor Sensor for PilotSuite HA Integration (v6.8.0).

Displays eco-score, savings potential, and energy overview.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)

_GRADE_ICONS = {
    "A+": "mdi:leaf",
    "A": "mdi:leaf",
    "B": "mdi:tree",
    "C": "mdi:flash",
    "D": "mdi:flash-alert",
    "E": "mdi:flash-alert-outline",
    "F": "mdi:lightning-bolt",
}


class EnergyAdvisorSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing energy advisor eco-score and savings."""

    _attr_name = "Energy Advisor"
    _attr_icon = "mdi:leaf"
    _attr_unique_id = "pilotsuite_energy_advisor"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    async def _fetch(self) -> dict | None:
        import aiohttp
        try:
            url = f"{self._core_base_url()}/api/v1/hub/energy"
            headers = self._core_headers()
            session = async_get_clientsession(self.hass)
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            logger.debug("Failed to fetch energy advisor data")
        return None

    async def async_update(self) -> None:
        data = await self._fetch()
        if data and data.get("ok"):
            self._data = data

    @property
    def native_value(self) -> str:
        eco = self._data.get("eco_score", {})
        grade = eco.get("grade", "?")
        score = eco.get("score", 0)
        if not eco:
            return "Nicht verfügbar"
        return f"Eco-Score {grade} ({score}/100)"

    @property
    def icon(self) -> str:
        eco = self._data.get("eco_score", {})
        grade = eco.get("grade", "C")
        return _GRADE_ICONS.get(grade, "mdi:flash")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        eco = self._data.get("eco_score", {})
        attrs: dict[str, Any] = {
            "eco_score": eco.get("score", 0),
            "eco_grade": eco.get("grade", "?"),
            "eco_trend": eco.get("trend", "stabil"),
            "total_daily_kwh": self._data.get("total_daily_kwh", 0),
            "total_monthly_kwh": self._data.get("total_monthly_kwh", 0),
            "total_monthly_eur": self._data.get("total_monthly_eur", 0),
            "savings_potential_eur": self._data.get("savings_potential_eur", 0),
        }

        breakdown = self._data.get("breakdown", [])
        if breakdown:
            attrs["breakdown"] = [
                {"category": b.get("name_de"), "kwh": b.get("kwh"), "pct": b.get("pct")}
                for b in breakdown
            ]

        top = self._data.get("top_consumers", [])
        if top:
            attrs["top_consumers"] = [
                {"name": c.get("name"), "monthly_kwh": c.get("monthly_kwh")}
                for c in top[:5]
            ]

        recs = self._data.get("recommendations", [])
        if recs:
            attrs["recommendations"] = [
                {
                    "title": r.get("title_de"),
                    "savings_eur": r.get("potential_savings_eur"),
                    "difficulty": r.get("difficulty"),
                    "applied": r.get("applied"),
                }
                for r in recs[:5]
            ]

        return attrs
