"""Home Alerts Sensor Entities - PilotSuite

Provides sensor entities for home alerts and health score.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Home Alerts sensors."""
    from .core.modules.home_alerts_module import get_home_alerts_module
    
    module = get_home_alerts_module(hass, entry.entry_id)
    if not module:
        _LOGGER.warning("HomeAlerts module not found for sensor setup")
        return
    
    entities = [
        HomeAlertsCountSensor(hass, entry, module),
        HomeHealthScoreSensor(hass, entry, module),
        HomeAlertsByCategorySensor(hass, entry, module, "battery"),
        HomeAlertsByCategorySensor(hass, entry, module, "climate"),
        HomeAlertsByCategorySensor(hass, entry, module, "presence"),
        HomeAlertsByCategorySensor(hass, entry, module, "system"),
    ]
    
    async_add_entities(entities, True)
    _LOGGER.info("Set up %d Home Alerts sensors", len(entities))


def create_home_alerts_sensors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    module,
) -> list:
    """Create Home Alerts sensors from module instance.
    
    Used by main sensor.py setup.
    """
    return [
        HomeAlertsCountSensor(hass, entry, module),
        HomeHealthScoreSensor(hass, entry, module),
        HomeAlertsByCategorySensor(hass, entry, module, "battery"),
        HomeAlertsByCategorySensor(hass, entry, module, "climate"),
        HomeAlertsByCategorySensor(hass, entry, module, "presence"),
        HomeAlertsByCategorySensor(hass, entry, module, "system"),
    ]


class HomeAlertsCountSensor(SensorEntity):
    """Sensor for total alert count."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:alert-circle"
    _attr_native_unit_of_measurement = "alerts"
    
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        module,
    ) -> None:
        self._hass = hass
        self._module = module
        self._entry = entry
        
        self._attr_unique_id = f"{entry.entry_id}_home_alerts_count"
        self._attr_translation_key = "home_alerts_count"
        self._attr_device_info = {
            "identifiers": {("ai_home_copilot", entry.entry_id)},
            "name": "PilotSuite",
            "manufacturer": "PilotSuite",
            "model": "Home Alerts",
        }
    
    @property
    def name(self) -> str:
        return "Home Alerts"
    
    @property
    def native_value(self) -> int:
        state = self._module.get_state()
        return len([a for a in state.alerts if not a.acknowledged])
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self._module.get_state()
        return {
            "battery_alerts": state.alerts_by_category.get("battery", 0),
            "climate_alerts": state.alerts_by_category.get("climate", 0),
            "presence_alerts": state.alerts_by_category.get("presence", 0),
            "system_alerts": state.alerts_by_category.get("system", 0),
            "last_scan": state.last_scan.isoformat() if state.last_scan else None,
        }


class HomeHealthScoreSensor(SensorEntity):
    """Sensor for home health score (0-100)."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:heart-pulse"
    _attr_native_unit_of_measurement = "%"
    
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        module,
    ) -> None:
        self._hass = hass
        self._module = module
        self._entry = entry
        
        self._attr_unique_id = f"{entry.entry_id}_home_health_score"
        self._attr_translation_key = "home_health_score"
        self._attr_device_info = {
            "identifiers": {("ai_home_copilot", entry.entry_id)},
            "name": "PilotSuite",
            "manufacturer": "PilotSuite",
            "model": "Home Alerts",
        }
    
    @property
    def name(self) -> str:
        return "Home Health Score"
    
    @property
    def native_value(self) -> int:
        state = self._module.get_state()
        return state.health_score
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self._module.get_state()
        alerts = [a for a in state.alerts if not a.acknowledged]
        
        return {
            "critical_alerts": len([a for a in alerts if a.severity == "critical"]),
            "high_alerts": len([a for a in alerts if a.severity == "high"]),
            "medium_alerts": len([a for a in alerts if a.severity == "medium"]),
            "low_alerts": len([a for a in alerts if a.severity == "low"]),
            "status": self._get_status(state.health_score),
        }
    
    def _get_status(self, score: int) -> str:
        if score >= 90:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 50:
            return "fair"
        elif score >= 30:
            return "poor"
        else:
            return "critical"


class HomeAlertsByCategorySensor(SensorEntity):
    """Sensor for alert count by category."""
    
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "alerts"
    
    CATEGORY_ICONS = {
        "battery": "mdi:battery-alert",
        "climate": "mdi:thermometer-alert",
        "presence": "mdi:account-alert",
        "system": "mdi:server-network-off",
    }
    
    CATEGORY_NAMES = {
        "battery": "Battery Alerts",
        "climate": "Climate Alerts",
        "presence": "Presence Alerts",
        "system": "System Alerts",
    }
    
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        module,
        category: str,
    ) -> None:
        self._hass = hass
        self._module = module
        self._entry = entry
        self._category = category
        
        self._attr_unique_id = f"{entry.entry_id}_home_alerts_{category}"
        self._attr_translation_key = f"home_alerts_{category}"
        self._attr_icon = self.CATEGORY_ICONS.get(category, "mdi:alert")
        self._attr_device_info = {
            "identifiers": {("ai_home_copilot", entry.entry_id)},
            "name": "PilotSuite",
            "manufacturer": "PilotSuite",
            "model": "Home Alerts",
        }
    
    @property
    def name(self) -> str:
        return self.CATEGORY_NAMES.get(self._category, f"{self._category.title()} Alerts")
    
    @property
    def native_value(self) -> int:
        state = self._module.get_state()
        alerts = [a for a in state.alerts if a.category == self._category and not a.acknowledged]
        return len(alerts)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self._module.get_state()
        alerts = [a for a in state.alerts if a.category == self._category and not a.acknowledged]
        
        return {
            "alerts": [
                {
                    "title": a.title,
                    "message": a.message,
                    "severity": a.severity,
                    "entity_id": a.entity_id,
                    "value": a.value,
                }
                for a in alerts[:5]  # Top 5 alerts
            ],
        }