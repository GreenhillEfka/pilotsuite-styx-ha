"""Activity sensors for AI Home CoPilot Neurons.

Sensors:
- ActivityLevelSensor: Overall activity level in the home
- ActivityStillnessSensor: Stillness/quiet detection

REFACTORED (2026-02-16): Now uses Add-on API instead of direct HA states.
The Add-on NeuronManager evaluates activity and returns structured data.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def _get_activity_from_api(
    coordinator: CopilotDataUpdateCoordinator,
    hass: HomeAssistant,
) -> Dict[str, Any]:
    """Get activity data from Add-on Neuron API.
    
    Calls /api/v1/neurons endpoint which returns evaluated neuron states.
    The Add-on NeuronManager handles all the activity evaluation logic.
    
    Returns:
        {
            "level": str,           # idle, low, moderate, high
            "score": int,           # Activity score
            "motion_count": int,    # Active motion sensors
            "media_playing": int,   # Playing media players
            "lights_on": int,       # Lights on
            "camera_motion": bool,  # Camera detected motion
            "stillness": str,       # sleeping, still, quiet, active
        }
    """
    result = {
        "level": "unknown",
        "score": 0,
        "motion_count": 0,
        "media_playing": 0,
        "lights_on": 0,
        "camera_motion": False,
        "stillness": "unknown",
    }
    
    try:
        # Get neuron evaluation from Add-on API (cached data, sync call)
        neurons_data = coordinator.async_get_neurons()
        
        # Extract activity/context data from neurons
        context = neurons_data.get("context", {})
        activity_data = context.get("activity", {})
        
        if activity_data:
            result["level"] = activity_data.get("level", "unknown")
            result["score"] = activity_data.get("value", 0)
            result["motion_count"] = activity_data.get("motion_count", 0)
            result["camera_motion"] = activity_data.get("camera_motion", False)
        else:
            # Fallback to direct HA states
            result = await _fallback_activity_states(hass)
            
        # Get media and lights from coordinator cache or HA states
        media_states = hass.states.async_all("media_player")
        result["media_playing"] = sum(1 for m in media_states if m.state == "playing")
        
        light_states = hass.states.async_all("light")
        result["lights_on"] = sum(1 for l in light_states if l.state == "on")
        
        # Calculate stillness based on activity
        now = dt_util.now()
        is_night = now.hour >= 23 or now.hour < 6
        
        if result["motion_count"] == 0 and result["media_playing"] == 0:
            if is_night:
                result["stillness"] = "sleeping"
            else:
                result["stillness"] = "still"
        elif result["motion_count"] == 0:
            result["stillness"] = "quiet"
        else:
            result["stillness"] = "active"
            
        return result
        
    except Exception as err:
        _LOGGER.warning("Failed to get activity from API: %s", err)
        return await _fallback_activity_states(hass)


async def _fallback_activity_states(hass: HomeAssistant) -> Dict[str, Any]:
    """Fallback: Calculate activity from direct HA states."""
    result = {
        "level": "unknown",
        "score": 0,
        "motion_count": 0,
        "media_playing": 0,
        "lights_on": 0,
        "camera_motion": False,
        "stillness": "unknown",
    }
    
    try:
        # Motion sensors
        motion_states = hass.states.async_all("binary_sensor")
        motion_on = sum(1 for s in motion_states 
                       if s.attributes.get("device_class") == "motion" and s.state == "on")
        result["motion_count"] = motion_on
        result["score"] += motion_on * 3
        
        # Media players
        media_states = hass.states.async_all("media_player")
        media_playing = sum(1 for m in media_states if m.state == "playing")
        result["media_playing"] = media_playing
        result["score"] += media_playing * 2
        
        # Lights
        light_states = hass.states.async_all("light")
        lights_on = sum(1 for l in light_states if l.state == "on")
        result["lights_on"] = lights_on
        result["score"] += lights_on
        
        # Determine level
        if result["score"] == 0:
            result["level"] = "idle"
        elif result["score"] < 5:
            result["level"] = "low"
        elif result["score"] < 15:
            result["level"] = "moderate"
        else:
            result["level"] = "high"
            
    except Exception as err:
        _LOGGER.error("Fallback activity calculation failed: %s", err)
    
    return result


class ActivityLevelSensor(CoordinatorEntity, SensorEntity):
    """Sensor for overall activity level in the home.
    
    Uses Add-on Neuron API for activity evaluation.
    The Add-on handles:
    - Motion sensor aggregation
    - Camera motion detection
    - Media player state
    - Light state
    
    This sensor just displays the result.
    """
    
    _attr_name = "AI CoPilot Activity Level"
    _attr_unique_id = "ai_copilot_activity_level"
    _attr_icon = "mdi:run"
    _attr_should_poll = False  # Using coordinator
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Update activity level from Add-on Neuron API."""
        data = await _get_activity_from_api(self.coordinator, self._hass)
        
        self._attr_native_value = data["level"]
        self._attr_extra_state_attributes = {
            "score": data["score"],
            "motion_active": data["motion_count"],
            "camera_motion_active": data["camera_motion"],
            "media_playing": data["media_playing"],
            "lights_on": data["lights_on"],
            "sources": ["api", "motion_sensors", "camera", "media", "lights"],
        }


class ActivityStillnessSensor(CoordinatorEntity, SensorEntity):
    """Sensor for stillness/quiet detection.
    
    Uses Add-on Neuron API for activity evaluation.
    """
    
    _attr_name = "AI CoPilot Activity Stillness"
    _attr_unique_id = "ai_copilot_activity_stillness"
    _attr_icon = "mdi:meditation"
    _attr_should_poll = False  # Using coordinator
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Update stillness from Add-on Neuron API."""
        data = await _get_activity_from_api(self.coordinator, self._hass)
        
        now = dt_util.now()
        is_night = now.hour >= 23 or now.hour < 6
        
        self._attr_native_value = data["stillness"]
        self._attr_extra_state_attributes = {
            "motion_detected": data["motion_count"] > 0,
            "media_active": data["media_playing"] > 0,
            "is_night": is_night,
            "activity_level": data["level"],
            "activity_score": data["score"],
        }