"""Predictive Automation Sensor for PilotSuite.

Shows ML-based automation suggestions from the habitus mining system.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class PredictiveAutomationSensor(SensorEntity):
    """Sensor showing ML-based automation suggestions."""
    
    _attr_name = "PilotSuite Predictive Automation"
    _attr_unique_id = "ai_copilot_predictive_automation"
    _attr_icon = "mdi:auto-mode"
    _attr_should_poll = False
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        """Initialize the predictive automation sensor."""
        super().__init__()
        self.coordinator = coordinator
        self._attr_native_value = "idle"
        self._attr_extra_state_attributes = {}
    
    @property
    def native_value(self) -> str:
        """Return the current automation suggestion count or status."""
        if not self.coordinator.data:
            return "idle"
        
        suggestions = self.coordinator.data.get("suggestions", [])
        return str(len(suggestions))
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return automation suggestions as attributes."""
        if not self.coordinator.data:
            return {}
        
        suggestions = self.coordinator.data.get("suggestions", [])
        
        return {
            "suggestion_count": len(suggestions),
            "suggestions": suggestions,
            "last_update": self.coordinator.data.get("last_update"),
        }
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class PredictiveAutomationDetailsSensor(SensorEntity):
    """Sensor showing detailed automation suggestions."""
    
    _attr_name = "PilotSuite Predictive Automation Details"
    _attr_unique_id = "ai_copilot_predictive_automation_details"
    _attr_icon = "mdi:file-document-outline"
    _attr_should_poll = False
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        """Initialize the predictive automation details sensor."""
        super().__init__()
        self.coordinator = coordinator
        self._attr_native_value = "none"
        self._attr_extra_state_attributes = {}
    
    @property
    def native_value(self) -> str:
        """Return the highest confidence suggestion."""
        if not self.coordinator.data:
            return "none"
        
        suggestions = self.coordinator.data.get("suggestions", [])
        if not suggestions:
            return "none"
        
        # Return highest confidence suggestion
        best = max(suggestions, key=lambda s: s.get("confidence", 0))
        return best.get("pattern", "unknown")
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return all suggestions with details."""
        if not self.coordinator.data:
            return {}
        
        suggestions = self.coordinator.data.get("suggestions", [])
        
        return {
            "suggestions": [
                {
                    "pattern": s.get("pattern", ""),
                    "confidence": s.get("confidence", 0),
                    "lift": s.get("lift", 1.0),
                    "support": s.get("support", 0),
                    "zone": s.get("zone", ""),
                    "mood_type": s.get("mood_type", ""),
                }
                for s in suggestions
            ],
            "count": len(suggestions),
        }
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up predictive automation sensors from a config entry."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("coordinator")
    if coordinator is None:
        return
    
    sensors = [
        PredictiveAutomationSensor(coordinator),
        PredictiveAutomationDetailsSensor(coordinator),
    ]
    
    async_add_entities(sensors)
    
    _LOGGER.info("Predictive automation sensors set up for entry %s", entry.entry_id)
