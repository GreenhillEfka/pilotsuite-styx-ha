"""Presence Intelligence Sensor for PilotSuite HA Integration (v7.1.0).

Displays household presence, room occupancy, and person tracking.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)


class PresenceIntelligenceSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing presence intelligence overview."""

    _attr_name = "Presence Intelligence"
    _attr_icon = "mdi:account-group"
    _attr_unique_id = "pilotsuite_presence_intelligence"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    async def _fetch(self) -> dict | None:
        import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
        try:
            url = f"{self._core_base_url()}/api/v1/hub/presence"
            session = async_get_clientsession(self.hass)
            session = async_get_clientsession(self.hass)
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception:
            logger.debug("Failed to fetch presence intelligence data")
        return None

    async def async_update(self) -> None:
        data = await self._fetch()
        if data and data.get("ok"):
            self._data = data

    @property
    def native_value(self) -> str:
        total = self._data.get("total_persons", 0)
        home = self._data.get("persons_home", 0)
        status = self._data.get("household_status", "unknown")
        if total == 0:
            return "Nicht verfügbar"
        status_map = {
            "home": "Alle zu Hause",
            "away": "Alle abwesend",
            "partial": f"{home}/{total} zu Hause",
            "unknown": "Unbekannt",
        }
        return status_map.get(status, f"{home}/{total} zu Hause")

    @property
    def icon(self) -> str:
        status = self._data.get("household_status", "unknown")
        if status == "home":
            return "mdi:home-account"
        elif status == "away":
            return "mdi:home-export-outline"
        elif status == "partial":
            return "mdi:home-clock"
        return "mdi:account-group"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "total_persons": self._data.get("total_persons", 0),
            "persons_home": self._data.get("persons_home", 0),
            "persons_away": self._data.get("persons_away", 0),
            "household_status": self._data.get("household_status", "unknown"),
            "total_rooms": self._data.get("total_rooms", 0),
            "occupied_rooms": self._data.get("occupied_rooms", 0),
            "active_triggers": self._data.get("active_triggers", 0),
        }

        rooms = self._data.get("room_occupancy", [])
        if rooms:
            attrs["rooms"] = [
                {
                    "room": r.get("room_name", r.get("room_id")),
                    "count": r.get("current_count", 0),
                    "persons": r.get("persons", []),
                }
                for r in rooms if r.get("current_count", 0) > 0
            ]

        transitions = self._data.get("recent_transitions", [])
        if transitions:
            attrs["recent_transitions"] = [
                {
                    "person": t.get("person_id"),
                    "from": t.get("from_room"),
                    "to": t.get("to_room"),
                }
                for t in transitions[:5]
            ]

        return attrs
