"""Presence sensors for AI Home CoPilot Neurons.

Sensors:
- PresenceRoomSensor: Primary room with presence
- PresencePersonSensor: Person presence count

REFACTORED (2026-02-16): Now uses Add-on API instead of direct HA states.
The Add-on NeuronManager evaluates presence and returns structured data.

Architecture:
  HA States → Add-on Neurons → API → This Sensor
  (not: HA States → This Sensor directly)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Maximum persons for social score normalization
_MAX_SOCIAL_PERSONS: int = 3
_MAX_ACTIVE_SOURCES: int = 3


async def _get_presence_from_api(
    coordinator: CopilotDataUpdateCoordinator,
) -> Dict[str, Any]:
    """Get presence data from Add-on Neuron API.
    
    Calls /api/v1/neurons endpoint which returns evaluated neuron states.
    The Add-on NeuronManager handles all the complex presence logic.
    
    Returns:
        {
            "room": str,           # Primary room with presence
            "person_count": int,   # Number of persons home
            "confidence": float,   # Detection confidence
            "sources": list,       # Detection sources used
            "social_score": float, # Social mood factor
            "active_score": float, # Activity mood factor
        }
    """
    try:
        # Get neuron evaluation from Add-on API
        neurons_data = await coordinator.async_get_neurons()
        
        # Extract presence/context data from neurons
        context = neurons_data.get("context", {})
        presence_data = context.get("presence", {})
        
        # Default result
        result = {
            "room": "unknown",
            "person_count": 0,
            "confidence": 0.0,
            "sources": [],
            "social_score": 0.0,
            "active_score": 0.0,
            "camera_room": None,
            "camera_person_detected": False,
            "motion_sensors_active": 0,
            "device_trackers_home": 0,
        }
        
        # Extract values from neuron data
        if presence_data:
            # The presence neuron returns structured data
            result["room"] = presence_data.get("room", "unknown")
            result["person_count"] = presence_data.get("count", 0)
            result["confidence"] = presence_data.get("value", 0.0)
            result["sources"] = presence_data.get("sources", [])
            
        # Also check for activity/motion data
        activity = context.get("activity", {})
        if activity:
            result["active_score"] = activity.get("value", 0.0)
            result["motion_sensors_active"] = activity.get("motion_count", 0)
        
        # Calculate social score from person count
        result["social_score"] = min(result["person_count"] / _MAX_SOCIAL_PERSONS, 1.0)
        result["social"] = result["person_count"] > 1
        
        return result
        
    except Exception as err:
        _LOGGER.warning("Failed to get presence from API: %s", err)
        # Return fallback - try direct HA states as backup
        return await _fallback_direct_states(coordinator)


async def _fallback_direct_states(
    coordinator: CopilotDataUpdateCoordinator,
) -> Dict[str, Any]:
    """Fallback: Read HA states directly if API is unavailable.
    
    This is a safety net for when the Add-on is not running.
    Should not be used in normal operation.
    """
    _LOGGER.debug("Using fallback direct state reading")
    hass = coordinator.hass
    
    result = {
        "room": "none",
        "person_count": 0,
        "confidence": 0.0,
        "sources": ["fallback"],
        "social_score": 0.0,
        "active_score": 0.0,
        "camera_room": None,
        "camera_person_detected": False,
        "motion_sensors_active": 0,
        "device_trackers_home": 0,
    }
    
    try:
        # Get person states
        person_states = hass.states.async_all("person")
        home_count = sum(1 for p in person_states if p.state == "home")
        
        result["person_count"] = home_count
        result["social_score"] = min(home_count / _MAX_SOCIAL_PERSONS, 1.0)
        result["social"] = home_count > 1
        
        # Try to find room from person zone
        for person in person_states:
            if person.state == "home":
                zone = person.attributes.get("zone")
                if zone:
                    result["room"] = str(zone)
                    result["confidence"] = 0.8
                    break
        
        # Check motion sensors
        binary_states = hass.states.async_all("binary_sensor")
        motion_active = [
            s for s in binary_states
            if s.attributes.get("device_class") == "motion" and s.state == "on"
        ]
        result["motion_sensors_active"] = len(motion_active)
        result["active_score"] = min(len(motion_active) / _MAX_ACTIVE_SOURCES, 1.0)
        
        # Device trackers
        tracker_states = hass.states.async_all("device_tracker")
        result["device_trackers_home"] = sum(
            1 for t in tracker_states if t.state == "home"
        )
        
    except Exception as err:
        _LOGGER.error("Fallback state reading failed: %s", err)
    
    return result


class PresenceRoomSensor(CoordinatorEntity, SensorEntity):
    """Sensor for primary room with presence.
    
    Uses Add-on Neuron API for presence evaluation.
    The Add-on handles:
    - Person entity states (home/away)
    - Device tracker zones
    - Motion sensor areas
    - Camera presence events
    - mmWave radar detection
    
    This sensor just displays the result.
    """
    
    _attr_name: str = "AI CoPilot Presence Room"
    _attr_unique_id: str = "ai_copilot_presence_room"
    _attr_icon: str = "mdi:door"
    _attr_should_poll: bool = False  # Using coordinator
    
    def __init__(
        self,
        coordinator: CopilotDataUpdateCoordinator,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(coordinator)
        self._hass: HomeAssistant = hass
        self._attr_native_value: str = "unknown"
        self._camera_detected_room: str | None = None
        self._camera_person_detected: bool = False
    
    async def async_update(self) -> None:
        """Update presence room from Add-on Neuron API."""
        # Get presence data from Add-on API
        data = await _get_presence_from_api(self.coordinator)
        
        self._attr_native_value = data.get("room", "unknown")
        self._camera_detected_room = data.get("camera_room")
        self._camera_person_detected = data.get("camera_person_detected", False)
        
        # Set extra attributes for mood integration
        self._attr_extra_state_attributes = {
            "active_persons": data.get("person_count", 0),
            "motion_sensors_active": data.get("motion_sensors_active", 0),
            "device_trackers_home": data.get("device_trackers_home", 0),
            "camera_room": data.get("camera_room"),
            "camera_person_detected": data.get("camera_person_detected", False),
            "sources": data.get("sources", []),
            # Mood integration
            "social": data.get("social", False),
            "active": data.get("active_score", 0) > 0,
            "social_score": data.get("social_score", 0.0),
            "active_score": data.get("active_score", 0.0),
            "confidence": data.get("confidence", 0.0),
        }


class PresencePersonSensor(CoordinatorEntity, SensorEntity):
    """Sensor for person presence count.
    
    Uses Add-on Neuron API for person counting.
    """
    
    _attr_name: str = "AI CoPilot Presence Person"
    _attr_unique_id: str = "ai_copilot_presence_person"
    _attr_icon: str = "mdi:account-group"
    _attr_native_unit_of_measurement: str = "persons"
    _attr_should_poll: bool = False  # Using coordinator
    
    def __init__(
        self,
        coordinator: CopilotDataUpdateCoordinator,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(coordinator)
        self._hass: HomeAssistant = hass
    
    async def async_update(self) -> None:
        """Update person presence count from Add-on API."""
        # Get presence data from Add-on API
        data = await _get_presence_from_api(self.coordinator)
        
        home_count = data.get("person_count", 0)
        
        self._attr_native_value = home_count
        self._attr_extra_state_attributes = {
            "home": home_count,
            "social": data.get("social", False),
            "social_score": data.get("social_score", 0.0),
            "confidence": data.get("confidence", 0.0),
            "sources": data.get("sources", []),
        }