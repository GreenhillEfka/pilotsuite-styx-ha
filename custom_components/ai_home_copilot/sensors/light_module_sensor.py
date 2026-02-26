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
        if lm.get("enabled"):
            active_zones = lm.get("active_zones", 0)
            return f"Active ({active_zones} zones)"
        return "disabled"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        lm = self.coordinator.data.get("light_module", {})
        return {
            "enabled": lm.get("enabled", False),
            "active_zones": lm.get("active_zones", 0),
            "color_temp_k": lm.get("color_temp_k"),
            "brightness_pct": lm.get("brightness_pct"),
            "mode": lm.get("mode", "circadian"),
            "presence_active": lm.get("presence_active", False),
            "outdoor_lux": lm.get("outdoor_lux"),
            "indoor_lux": lm.get("indoor_lux"),
            "ratio": lm.get("ratio"),
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
        return {
            "zones": lm.get("zones", []),
            "circadian_enabled": lm.get("circadian_enabled", True),
            "presence_mode": lm.get("presence_mode", "auto"),
        }
