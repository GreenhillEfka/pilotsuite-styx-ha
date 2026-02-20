"""Energy Insights Sensor for AI Home CoPilot.

Shows energy consumption insights and optimization recommendations.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class EnergyInsightSensor(SensorEntity):
    """Sensor showing current energy insights."""
    
    _attr_name = "AI CoPilot Energy Insights"
    _attr_unique_id = "ai_copilot_energy_insights"
    _attr_icon = "mdi:lightning-bolt"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"
    _attr_should_poll = False
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        """Initialize the energy insight sensor."""
        super().__init__()
        self.coordinator = coordinator
        self._attr_native_value = 0.0
        self._attr_extra_state_attributes = {}
    
    @property
    def native_value(self) -> float:
        """Return the total energy consumption."""
        if not self.coordinator.data:
            return 0.0
        
        energy_summary = self.coordinator.data.get("energy_summary", {})
        return round(energy_summary.get("total_kwh", 0.0), 3)
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return energy insights and recommendations."""
        if not self.coordinator.data:
            return {}
        
        energy_summary = self.coordinator.data.get("energy_summary", {})
        recommendations = self.coordinator.data.get("energy_recommendations", [])
        
        return {
            "total_kwh": energy_summary.get("total_kwh", 0.0),
            "device_consumption": energy_summary.get("device_consumption", {}),
            "recommendations": recommendations,
            "recommendation_count": len(recommendations),
            "hours": energy_summary.get("hours", 24),
        }
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class EnergyRecommendationSensor(SensorEntity):
    """Sensor showing active energy recommendations."""
    
    _attr_name = "AI CoPilot Energy Recommendations"
    _attr_unique_id = "ai_copilot_energy_recommendations"
    _attr_icon = "mdi:idea"
    _attr_should_poll = False
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        """Initialize the energy recommendation sensor."""
        super().__init__()
        self.coordinator = coordinator
        self._attr_native_value = "none"
        self._attr_extra_state_attributes = {}
    
    @property
    def native_value(self) -> str:
        """Return the number of active recommendations."""
        if not self.coordinator.data:
            return "none"
        
        recommendations = self.coordinator.data.get("energy_recommendations", [])
        if not recommendations:
            return "none"
        
        # Return highest priority recommendation
        best = max(recommendations, key=lambda r: r.get("priority", "low"))
        return best.get("title", "unknown")
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return all recommendations."""
        if not self.coordinator.data:
            return {}
        
        recommendations = self.coordinator.data.get("energy_recommendations", [])
        
        return {
            "recommendations": [
                {
                    "title": r.get("title", ""),
                    "priority": r.get("priority", "low"),
                    "description": r.get("description", ""),
                    "savings_potential_wh": r.get("savings_potential_wh", 0),
                }
                for r in recommendations
            ],
            "count": len(recommendations),
        }
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up energy insights sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    sensors = [
        EnergyInsightSensor(coordinator),
        EnergyRecommendationSensor(coordinator),
    ]
    
    async_add_entities(sensors)
    
    _LOGGER.info("Energy insights sensors set up for entry %s", entry.entry_id)
