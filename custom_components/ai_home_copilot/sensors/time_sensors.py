"""Time sensors for AI Home CoPilot Neurons.

Sensors:
- TimeOfDaySensor: Time of day classification
- DayTypeSensor: Day type (weekday, weekend, holiday)
- RoutineStabilitySensor: Routine stability detection
"""
from __future__ import annotations

import logging
from datetime import datetime, time
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Time of day thresholds
MORNING_START = time(6, 0)
AFTERNOON_START = time(12, 0)
EVENING_START = time(18, 0)
NIGHT_START = time(22, 0)


class TimeOfDaySensor(CoordinatorEntity, SensorEntity):
    """Sensor for time of day classification."""
    
    _attr_name = "AI CoPilot Time of Day"
    _attr_unique_id = "ai_copilot_time_of_day"
    _attr_icon = "mdi:clock"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
    
    async def async_update(self) -> None:
        """Update time of day classification."""
        now = dt_util.now()
        current_time = now.time()
        
        if now.weekday() < 5:
            day_type = "weekday"
        else:
            day_type = "weekend"
        
        if MORNING_START <= current_time < AFTERNOON_START:
            time_of_day = "morning"
        elif AFTERNOON_START <= current_time < EVENING_START:
            time_of_day = "afternoon"
        elif EVENING_START <= current_time < NIGHT_START:
            time_of_day = "evening"
        else:
            time_of_day = "night"
        
        self._attr_native_value = time_of_day
        self._attr_extra_state_attributes = {
            "day_type": day_type,
            "hour": now.hour,
            "minute": now.minute,
            "is_weekend": day_type == "weekend",
        }


class DayTypeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for day type (weekday, weekend, holiday)."""
    
    _attr_name = "AI CoPilot Day Type"
    _attr_unique_id = "ai_copilot_day_type"
    _attr_icon = "mdi:calendar"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Determine day type."""
        now = dt_util.now()
        
        # Check calendar for holidays (if available)
        calendar_states = self._hass.states.async_all("calendar")
        is_holiday = False
        
        for cal in calendar_states:
            # Check for holiday events
            if cal.attributes.get("all_day"):
                is_holiday = True
                break
        
        # Check for weekend
        is_weekend = now.weekday() >= 5
        
        if is_holiday:
            day_type = "holiday"
        elif is_weekend:
            day_type = "weekend"
        else:
            day_type = "weekday"
        
        self._attr_native_value = day_type
        self._attr_extra_state_attributes = {
            "weekday": now.strftime("%A"),
            "is_weekend": is_weekend,
            "is_holiday": is_holiday,
        }


class RoutineStabilitySensor(CoordinatorEntity, SensorEntity):
    """Sensor for routine stability detection."""
    
    _attr_name = "AI CoPilot Routine Stability"
    _attr_unique_id = "ai_copilot_routine_stability"
    _attr_icon = "mdi:scale-balance"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._last_update: Optional[datetime] = None
        self._routine_history: list[dict] = []
    
    async def async_update(self) -> None:
        """Calculate routine stability based on typical patterns."""
        now = dt_util.now()
        
        # Get current day of week and time
        day_of_week = now.weekday()
        current_time = now.time()
        
        # Simple stability check based on time patterns
        # In a full implementation, this would compare against learned patterns
        
        # Check if current time matches expected patterns
        # Morning (6-9), Day (9-17), Evening (17-22), Night (22-6)
        if MORNING_START <= current_time < time(9, 0):
            expected = "morning_routine"
        elif time(9, 0) <= current_time < time(17, 0):
            expected = "work_routine"
        elif time(17, 0) <= current_time < EVENING_START:
            expected = "evening_routine"
        elif EVENING_START <= current_time < time(23, 0):
            expected = "leisure_routine"
        else:
            expected = "night_routine"
        
        # For now, return a basic stability score
        # Full implementation would require historical data
        stability = "stable"  # Default to stable, would need ML for actual detection
        
        self._attr_native_value = stability
        self._attr_extra_state_attributes = {
            "expected_routine": expected,
            "day_of_week": day_of_week,
            "current_time": current_time.isoformat(),
        }
