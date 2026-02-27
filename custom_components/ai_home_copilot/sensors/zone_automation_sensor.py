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


class ZoneHeatingStatusSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing zone heating automation status."""

    _attr_name = "Zonenheizung Status"
    _attr_unique_id = f"{DOMAIN}_zone_heating_status"
    _attr_icon = "mdi:radiator"

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return "Unbekannt"
        za = self.coordinator.data.get("zone_automation", {})
        zones = za.get("zones", [])
        heating_zones = 0
        for z in zones:
            if isinstance(z, dict):
                last_eval = z.get("last_evaluation", {})
                if isinstance(last_eval, dict) and last_eval.get("heating_action") == "set_temp":
                    heating_zones += 1
        if heating_zones > 0:
            return f"Aktiv ({heating_zones} Zonen)"
        return "Idle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        za = self.coordinator.data.get("zone_automation", {})
        zones = za.get("zones", [])
        heating_details = []
        for z in zones:
            if isinstance(z, dict):
                last_eval = z.get("last_evaluation", {})
                if isinstance(last_eval, dict) and last_eval.get("heating_action") == "set_temp":
                    heating_details.append({
                        "zone_id": z.get("zone_id", ""),
                        "target_temp_c": last_eval.get("heating_target_temp_c", 0),
                        "climate_entities": last_eval.get("climate_entities", []),
                    })
        return {
            "heating_zones": len(heating_details),
            "details": heating_details,
        }


class ZoneBrightnessThresholdSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing zone brightness threshold and ratio status."""

    _attr_name = "Zonen-Helligkeit"
    _attr_unique_id = f"{DOMAIN}_zone_brightness_threshold"
    _attr_icon = "mdi:brightness-6"
    _attr_native_unit_of_measurement = "lux"

    @property
    def native_value(self) -> float:
        if not self.coordinator.data:
            return 0.0
        za = self.coordinator.data.get("zone_automation", {})
        zones = za.get("zones", [])
        if not zones:
            return 0.0
        total_indoor = 0.0
        count = 0
        for z in zones:
            if isinstance(z, dict):
                last_eval = z.get("last_evaluation", {})
                if isinstance(last_eval, dict):
                    lux = last_eval.get("indoor_lux", 0)
                    if lux > 0:
                        total_indoor += lux
                        count += 1
        return round(total_indoor / max(count, 1), 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        za = self.coordinator.data.get("zone_automation", {})
        zones = za.get("zones", [])
        zone_brightness = []
        for z in zones:
            if isinstance(z, dict):
                last_eval = z.get("last_evaluation", {})
                if isinstance(last_eval, dict):
                    zone_brightness.append({
                        "zone_id": z.get("zone_id", ""),
                        "indoor_lux": last_eval.get("indoor_lux", 0),
                        "outdoor_lux": last_eval.get("outdoor_lux", 0),
                        "brightness_ratio": last_eval.get("brightness_ratio", 0),
                        "artificial_light_needed": last_eval.get("artificial_light_needed", False),
                        "deficit_lux": last_eval.get("deficit_lux", 0),
                    })
        return {
            "zone_brightness": zone_brightness,
            "total_zones_tracked": len(zone_brightness),
        }


ZONE_AUTOMATION_SENSORS = [
    ZoneAutomationSensor,
    ZoneAutomationOccupancySensor,
    ZoneHeatingStatusSensor,
    ZoneBrightnessThresholdSensor,
]
