"""Zone Automation sensors — tracks per-zone automation state from Core."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity

from ..const import DOMAIN
from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class ZoneAutomationSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing overall Zone Automation status."""

    _attr_name = "Zone Automation"
    _attr_unique_id = f"{DOMAIN}_zone_automation"
    _attr_icon = "mdi:home-automation"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        za = self.coordinator.data.get("zone_automation", {})
        if not za:
            return "Nicht verfügbar"
        total = za.get("total_zones", 0)
        if total > 0:
            return f"Aktiv ({total} Zonen)"
        return "Keine Zonen"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        za = self.coordinator.data.get("zone_automation", {})
        zones = za.get("zones", [])
        configs = za.get("configs", [])
        occupied = 0
        for z in zones:
            if isinstance(z, dict):
                presence = z.get("presence", {})
                if isinstance(presence, dict) and presence.get("state") == "occupied":
                    occupied += 1
        return {
            "total_zones": za.get("total_zones", 0),
            "configured_zones": len(configs),
            "occupied_zones": occupied,
            "zone_ids": [
                z.get("zone_id", "") for z in zones if isinstance(z, dict)
            ],
        }


class ZoneAutomationOccupancySensor(CopilotBaseEntity, SensorEntity):
    """Sensor counting how many zones are currently occupied."""

    _attr_name = "Belegte Zonen"
    _attr_unique_id = f"{DOMAIN}_zones_occupied"
    _attr_icon = "mdi:account-group"
    _attr_native_unit_of_measurement = "zones"

    @property
    def native_value(self) -> int:
        if not self.coordinator.data:
            return 0
        za = self.coordinator.data.get("zone_automation", {})
        zones = za.get("zones", [])
        occupied = 0
        for z in zones:
            if isinstance(z, dict):
                presence = z.get("presence", {})
                if isinstance(presence, dict) and presence.get("state") == "occupied":
                    occupied += 1
        return occupied

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        za = self.coordinator.data.get("zone_automation", {})
        zones = za.get("zones", [])
        occupied_zones = []
        vacant_zones = []
        for z in zones:
            if isinstance(z, dict):
                zid = z.get("zone_id", "")
                presence = z.get("presence", {})
                if isinstance(presence, dict) and presence.get("state") == "occupied":
                    occupied_zones.append(zid)
                else:
                    vacant_zones.append(zid)
        return {
            "occupied_zones": occupied_zones,
            "vacant_zones": vacant_zones,
            "total": len(zones),
        }


ZONE_AUTOMATION_SENSORS = [
    ZoneAutomationSensor,
    ZoneAutomationOccupancySensor,
]
