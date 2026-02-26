"""Adaptive Light Module sensor — tracks zone-based adaptive lighting state."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class LightModuleSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing adaptive light module status."""

    _attr_name = "Light Module"
    _attr_unique_id = "ai_home_copilot_light_module"
    _attr_icon = "mdi:lightbulb-auto"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        lm = self.coordinator.data.get("light_module", {})
        if not lm:
            return "Nicht verfügbar"
        if lm.get("enabled"):
            active_zones = lm.get("active_zones", 0)
            return f"Aktiv ({active_zones} Zonen)"
        return "Deaktiviert"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        lm = self.coordinator.data.get("light_module", {})
        config = lm.get("config", {})
        presets = lm.get("presets", {})
        return {
            "enabled": lm.get("enabled", False),
            "active_zones": lm.get("active_zones", 0),
            "circadian_enabled": config.get("circadian_enabled", True),
            "brightness_ratio_enabled": config.get("brightness_ratio_enabled", True),
            "presence_enabled": config.get("presence_enabled", True),
            "available_presets": list(presets.keys()) if isinstance(presets, dict) else [],
        }


class LightModuleZonesSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing Light Module configured zone count."""

    _attr_name = "Light Module Zones"
    _attr_unique_id = "ai_home_copilot_light_module_zones"
    _attr_icon = "mdi:lightbulb-group"
    _attr_native_unit_of_measurement = "zones"

    @property
    def native_value(self) -> int:
        if not self.coordinator.data:
            return 0
        lm = self.coordinator.data.get("light_module", {})
        return lm.get("active_zones", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        lm = self.coordinator.data.get("light_module", {})
        zones = lm.get("zones", [])
        zone_ids = []
        for z in zones:
            if isinstance(z, dict):
                zone_ids.append(z.get("zone_id", ""))
            elif isinstance(z, str):
                zone_ids.append(z)
        return {
            "zones": zone_ids,
            "total": len(zone_ids),
        }
