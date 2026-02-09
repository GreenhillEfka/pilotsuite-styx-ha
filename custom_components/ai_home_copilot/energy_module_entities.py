"""Energy Module sensor entities for Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfPower

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

MODULE_KEY = "energy_module"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Energy Module sensor entities."""
    
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    
    # Check if energy module is loaded
    if MODULE_KEY not in entry_data:
        return
    
    entities = [
        EnergyModuleBaseloadSensor(hass, entry),
        EnergyModuleAnomalyLevelSensor(hass, entry),
        EnergyModuleLastEventSensor(hass, entry),
    ]
    
    async_add_entities(entities)


class EnergyModuleBaseloadSensor(SensorEntity):
    """Sensor for estimated baseload power."""

    _attr_has_entity_name = True
    _attr_name = "Baseload"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_energy_module_baseload"

    @property
    def native_value(self) -> float | None:
        """Return the baseload value."""
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
        module_data = entry_data.get(MODULE_KEY, {})
        baselines = module_data.get("baselines", {})
        return baselines.get("baseload_w")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
        module_data = entry_data.get(MODULE_KEY, {})
        baselines = module_data.get("baselines", {})
        
        return {
            "last_computed": baselines.get("last_computed"),
        }


class EnergyModuleAnomalyLevelSensor(SensorEntity):
    """Sensor for current anomaly level (0-100)."""

    _attr_has_entity_name = True
    _attr_name = "Anomaly Level"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:alert-circle"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_energy_module_anomaly_level"

    @property
    def native_value(self) -> int:
        """Return the anomaly level (0-100)."""
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
        module_data = entry_data.get(MODULE_KEY, {})
        events = module_data.get("events", [])
        
        # Calculate max severity from recent events (last 5)
        if not events:
            return 0
        
        recent_events = events[-5:]
        max_severity = max((e.get("severity", 0) for e in recent_events), default=0)
        return int(max_severity * 100)


class EnergyModuleLastEventSensor(SensorEntity):
    """Sensor for last energy event/anomaly."""

    _attr_has_entity_name = True
    _attr_name = "Last Event"
    _attr_icon = "mdi:information"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_energy_module_last_event"

    @property
    def native_value(self) -> str:
        """Return the event type."""
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
        module_data = entry_data.get(MODULE_KEY, {})
        events = module_data.get("events", [])
        
        if not events:
            return "none"
        
        last_event = events[-1]
        return last_event.get("subtype", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return full event details as attributes."""
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
        module_data = entry_data.get(MODULE_KEY, {})
        events = module_data.get("events", [])
        
        if not events:
            return {}
        
        last_event = events[-1]
        
        return {
            "type": last_event.get("type"),
            "subtype": last_event.get("subtype"),
            "severity": last_event.get("severity"),
            "confidence": last_event.get("explanation", {}).get("confidence"),
            "summary": last_event.get("explanation", {}).get("summary"),
            "recommendation": last_event.get("recommendation", {}).get("title"),
            "evidence_count": len(last_event.get("evidence", [])),
        }
