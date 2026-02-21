"""Habitus-Zonen Sensor for Home Assistant (v6.4.0)."""

from __future__ import annotations

import logging
from typing import Any

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 30


class HabitusZoneSensor(CopilotBaseEntity):
    """Sensor showing Habitus-Zonen overview."""

    _attr_icon = "mdi:home-floor-1"
    _attr_name = "PilotSuite Habitus-Zonen"
    _attr_unique_id = "pilotsuite_habitus_zones"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._zone_data: dict[str, Any] = {}

    @property
    def state(self) -> str:
        total = self._zone_data.get("total_zones", 0)
        active = self._zone_data.get("active_zones", 0)
        if total == 0:
            return "Keine Zonen"
        return f"{active}/{total} aktiv"

    @property
    def icon(self) -> str:
        modes = self._zone_data.get("modes", {})
        if modes.get("party", 0) > 0:
            return "mdi:party-popper"
        if modes.get("sleeping", 0) > 0:
            return "mdi:sleep"
        return "mdi:home-floor-1"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        zones = self._zone_data.get("zones", [])
        return {
            "total_zones": self._zone_data.get("total_zones", 0),
            "total_rooms": self._zone_data.get("total_rooms", 0),
            "total_entities": self._zone_data.get("total_entities", 0),
            "active_zones": self._zone_data.get("active_zones", 0),
            "modes": self._zone_data.get("modes", {}),
            "unassigned_rooms": self._zone_data.get("unassigned_rooms", []),
            "zones": [
                {"name": z.get("name"), "mode": z.get("mode"),
                 "rooms": z.get("room_count", 0), "entities": z.get("entity_count", 0)}
                for z in zones[:10]
            ],
        }

    async def async_update(self) -> None:
        data = await self._fetch("/api/v1/hub/zones")
        if data:
            self._zone_data = data
