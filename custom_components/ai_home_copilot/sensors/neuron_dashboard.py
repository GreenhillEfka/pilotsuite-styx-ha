"""Neuron Dashboard for PilotSuite.

Shows all neuron states, mood, and suggestions in a visual dashboard.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class NeuronDashboardSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing all neuron states as JSON."""
    
    _attr_name = "AI CoPilot Neuron Dashboard"
    _attr_unique_id = "ai_copilot_neuron_dashboard"
    _attr_icon = "mdi:brain"
    _attr_should_poll = False
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_native_value = "ok"
        self._attr_extra_state_attributes = {}
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return all neuron data."""
        if not self.coordinator.data:
            return {}
        
        neurons = self.coordinator.data.get("neurons", {})
        
        # Organize by type
        context = {}
        state = {}
        mood = {}
        
        for name, data in neurons.items():
            if isinstance(data, dict):
                if "context" in name or name.startswith(("presence", "time", "light", "weather")):
                    context[name] = data
                elif "mood" in name:
                    mood[name] = data
                else:
                    state[name] = data
        
        return {
            "context_neurons": context,
            "state_neurons": state,
            "mood_neurons": mood,
            "total_count": len(neurons),
            "active_count": sum(1 for n in neurons.values() if isinstance(n, dict) and n.get("active")),
        }
    
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class MoodHistorySensor(CoordinatorEntity, SensorEntity):
    """Sensor showing mood history for trends."""
    
    _attr_name = "AI CoPilot Mood History"
    _attr_unique_id = "ai_copilot_mood_history"
    _attr_icon = "mdi:chart-line"
    _attr_should_poll = False
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_native_value = "ok"
        self._history: List[Dict[str, Any]] = []
        self._max_history = 20
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return mood history."""
        if not self.coordinator.data:
            return {"history": []}
        
        mood = self.coordinator.data.get("dominant_mood", "unknown")
        confidence = self.coordinator.data.get("mood_confidence", 0.0)
        
        # Add to history
        from datetime import datetime, timezone
        entry = {
            "mood": mood,
            "confidence": confidence,
            "time": datetime.now(timezone.utc).isoformat(),
        }
        self._history.append(entry)
        self._history = self._history[-self._max_history:]
        
        return {
            "history": self._history,
            "current_mood": mood,
            "current_confidence": confidence,
        }
    
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class SuggestionSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing current suggestions from neural system."""
    
    _attr_name = "AI CoPilot Suggestions"
    _attr_unique_id = "ai_copilot_suggestions"
    _attr_icon = "mdi:lightbulb-outline"
    _attr_should_poll = False
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_native_value = "none"
    
    @property
    def native_value(self) -> str:
        """Return suggestion count or top suggestion."""
        if not self.coordinator.data:
            return "none"
        
        suggestions = self.coordinator.data.get("suggestions", [])
        if not suggestions:
            return "none"
        
        # Return top suggestion type
        if suggestions:
            return suggestions[0].get("action_type", "none")
        return "none"
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return all suggestions."""
        if not self.coordinator.data:
            return {"suggestions": []}
        
        suggestions = self.coordinator.data.get("suggestions", [])
        
        return {
            "suggestions": suggestions,
            "count": len(suggestions),
            "top_suggestion": suggestions[0] if suggestions else None,
        }
    
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up dashboard sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        NeuronDashboardSensor(coordinator),
        MoodHistorySensor(coordinator),
        SuggestionSensor(coordinator),
    ]
    
    async_add_entities(entities)
    _LOGGER.info("Neuron dashboard sensors set up")