"""Mood sensor entities for PilotSuite.

Exposes the neural system's mood state to Home Assistant for visibility
and automation purposes.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class MoodSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the current mood from the neural system."""

    _attr_name = "PilotSuite Mood"
    _attr_unique_id = "ai_home_copilot_mood"
    _attr_icon = "mdi:robot-happy"
    _attr_should_poll = False

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        """Initialize the mood sensor."""
        super().__init__(coordinator)
        self._attr_native_value = "unknown"

    @property
    def native_value(self) -> str:
        """Return the current mood."""
        if not self.coordinator.data:
            return "unknown"

        # Get mood from coordinator data
        mood_data = self.coordinator.data.get("mood", {})
        return mood_data.get("mood", "unknown")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes (including emotions for Lovelace card)."""
        if not self.coordinator.data:
            return {}

        mood_data = self.coordinator.data.get("mood", {})

        # Build emotions list for ha-copilot-mood-card
        emotions = mood_data.get("emotions", [])
        if not emotions and mood_data.get("contributing_neurons"):
            emotions = [
                {"name": n.get("name", "unknown"), "value": n.get("value", 0.0)}
                for n in mood_data.get("contributing_neurons", [])
                if isinstance(n, dict)
            ]

        return {
            "confidence": mood_data.get("confidence", 0.0),
            "emotions": emotions,
            "zone": mood_data.get("zone", "unknown"),
            "last_updated": mood_data.get("last_update"),
            "last_update": mood_data.get("last_update"),
            "contributing_neurons": mood_data.get("contributing_neurons", []),
        }
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class MoodConfidenceSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the confidence level of the current mood."""
    
    _attr_name = "PilotSuite Mood Confidence"
    _attr_unique_id = "ai_home_copilot_mood_confidence"
    _attr_icon = "mdi:gauge"
    _attr_native_unit_of_measurement = "%"
    _attr_should_poll = False
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        """Initialize the confidence sensor."""
        super().__init__(coordinator)
        self._attr_native_value = 0
    
    @property
    def native_value(self) -> int:
        """Return the confidence as percentage."""
        if not self.coordinator.data:
            return 0
        
        mood_data = self.coordinator.data.get("mood", {})
        confidence = mood_data.get("confidence", 0.0)
        return int(confidence * 100)
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}
        
        mood_data = self.coordinator.data.get("mood", {})
        return {
            "mood": mood_data.get("mood", "unknown"),
            "factors": mood_data.get("factors", {}),
        }
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class NeuronActivitySensor(CoordinatorEntity, SensorEntity):
    """Sensor showing active neurons count and activity grid for Lovelace card."""

    _attr_name = "PilotSuite Neuron Activity"
    _attr_unique_id = "ai_home_copilot_neuron_activity"
    _attr_icon = "mdi:brain"
    _attr_should_poll = False

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        """Initialize the neuron activity sensor."""
        super().__init__(coordinator)
        self._attr_native_value = 0
        self._history: list[dict] = []

    @property
    def native_value(self) -> int:
        """Return the count of active neurons."""
        if not self.coordinator.data:
            return 0

        neurons = self.coordinator.data.get("neurons", {})
        active_count = sum(
            1 for n in neurons.values()
            if isinstance(n, dict) and n.get("active", False)
        )
        return active_count

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return neuron details (including activity grid for Lovelace card)."""
        if not self.coordinator.data:
            return {}

        neurons = self.coordinator.data.get("neurons", {})

        # Build activity list for ha-copilot-neurons-card
        activity = [
            {
                "name": name,
                "active": bool(n.get("active", False)),
                "value": n.get("value", 0),
                "confidence": n.get("confidence", 0),
            }
            for name, n in neurons.items()
            if isinstance(n, dict)
        ]

        active_neurons = [a for a in activity if a["active"]]

        # Maintain rolling history for the chart
        current_active = len(active_neurons)
        self._history.append({"value": current_active})
        if len(self._history) > 24:
            self._history = self._history[-24:]

        return {
            "activity": activity,
            "active_neurons": active_neurons,
            "total_neurons": len(neurons),
            "history": list(self._history),
        }
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up mood sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    sensors = [
        MoodSensor(coordinator),
        MoodConfidenceSensor(coordinator),
        NeuronActivitySensor(coordinator),
    ]
    
    async_add_entities(sensors)
    
    _LOGGER.info("Mood sensors set up for entry %s", entry.entry_id)