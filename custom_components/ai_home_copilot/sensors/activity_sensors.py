"""Activity sensors for AI Home CoPilot Neurons.

Sensors:
- ActivityLevelSensor: Overall activity level in the home
- ActivityStillnessSensor: Stillness/quiet detection
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


class ActivityLevelSensor(CoordinatorEntity, SensorEntity):
    """Sensor for overall activity level in the home.
    
    Connected to:
    - Motion sensors (binary_sensor)
    - Camera motion events
    - Media players
    - Lights
    - Module Connector signals
    """
    
    _attr_name = "AI CoPilot Activity Level"
    _attr_unique_id = "ai_copilot_activity_level"
    _attr_icon = "mdi:run"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._last_motion_time: datetime | None = None
        self._camera_motion_active = False
    
    async def async_update(self) -> None:
        """Calculate activity level based on various sensors.
        
        Uses:
        1. Motion sensors (binary_sensor)
        2. Camera motion events (via module connector)
        3. Media players
        4. Lights
        """
        # Factors: motion sensors, media players, lights, switches
        score = 0
        
        # Motion sensors (weight: 3)
        motion_states = self._hass.states.async_all("binary_sensor")
        motion_on = sum(1 for s in motion_states 
                       if s.attributes.get("device_class") == "motion" and s.state == "on")
        score += motion_on * 3
        
        # Check for camera motion events via module connector
        try:
            from ..module_connector import get_module_connector
            
            entry_id = coordinator.config_entry.entry_id if hasattr(coordinator, 'config_entry') else "default"
            connector = await get_module_connector(self._hass, entry_id)
            activity_context = connector.activity_context
            
            # Use camera motion if recent (within last 2 minutes)
            if activity_context.motion_detected and activity_context.timestamp:
                time_since_motion = (dt_util.utcnow() - activity_context.timestamp).total_seconds()
                if time_since_motion < 120:  # 2 minutes
                    self._camera_motion_active = True
                    score += 5  # Add camera motion score
            else:
                self._camera_motion_active = False
                
        except Exception:
            pass
        
        # Media players active (weight: 2)
        media_states = self._hass.states.async_all("media_player")
        media_playing = sum(1 for m in media_states if m.state == "playing")
        score += media_playing * 2
        
        # Lights on (weight: 1)
        light_states = self._hass.states.async_all("light")
        lights_on = sum(1 for l in light_states if l.state == "on")
        score += lights_on
        
        # Determine level
        if score == 0:
            level = "idle"
        elif score < 5:
            level = "low"
        elif score < 15:
            level = "moderate"
        else:
            level = "high"
        
        self._attr_native_value = level
        self._attr_extra_state_attributes = {
            "score": score,
            "motion_active": motion_on,
            "camera_motion_active": self._camera_motion_active,
            "media_playing": media_playing,
            "lights_on": lights_on,
            "sources": ["motion_sensors", "camera", "media", "lights"],
        }


class ActivityStillnessSensor(CoordinatorEntity, SensorEntity):
    """Sensor for stillness/quiet detection."""
    
    _attr_name = "AI CoPilot Activity Stillness"
    _attr_unique_id = "ai_copilot_activity_stillness"
    _attr_icon = "mdi:meditation"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Detect stillness based on lack of activity."""
        # Inverse of activity level - check for absence of movement
        motion_states = self._hass.states.async_all("binary_sensor")
        motion_on = sum(1 for s in motion_states 
                       if s.attributes.get("device_class") == "motion" and s.state == "on")
        
        media_states = self._hass.states.async_all("media_player")
        media_playing = sum(1 for m in media_states if m.state == "playing")
        
        # Check time - nighttime is more likely to be still
        now = dt_util.now()
        is_night = now.hour >= 23 or now.hour < 6
        
        if motion_on == 0 and media_playing == 0:
            if is_night:
                stillness = "sleeping"
            else:
                stillness = "still"
        elif motion_on == 0:
            stillness = "quiet"
        else:
            stillness = "active"
        
        self._attr_native_value = stillness
        self._attr_extra_state_attributes = {
            "motion_detected": motion_on > 0,
            "media_active": media_playing > 0,
            "is_night": is_night,
        }
