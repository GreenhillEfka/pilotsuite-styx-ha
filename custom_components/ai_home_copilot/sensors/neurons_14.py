"""Neuron sensors for AI Home CoPilot - 14 Neurons from Original Plan.

Implements the missing neurons:
- presence.room, presence.person
- activity.level, activity.stillness
- time.of_day, day.type, routine.stability
- light.level, noise.level, weather.context
- calendar.load, attention.load, stress.proxy
- energy.proxy, media.activity, media.intensity
"""
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State
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


class PresenceRoomSensor(CoordinatorEntity, SensorEntity):
    """Sensor for primary room with presence."""
    
    _attr_name = "AI CoPilot Presence Room"
    _attr_unique_id = "ai_copilot_presence_room"
    _attr_icon = "mdi:door"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._attr_native_value = "unknown"
    
    async def async_update(self) -> None:
        """Update presence room based on HA states."""
        # Find person entities and their states
        person_states = self._hass.states.async_all("person")
        
        # Find device_tracker entities
        device_tracker_states = self._hass.states.async_all("device_tracker")
        
        # Find binary sensors related to motion/presence
        motion_states = self._hass.states.async_all("binary_sensor")
        motion_active = [
            s for s in motion_states 
            if s.attributes.get("device_class") == "motion" and s.state == "on"
        ]
        
        # Determine primary room with presence
        # Priority: person zone > device_tracker zone > motion sensor area
        primary_room = "none"
        
        for person in person_states:
            if person.state != "home":
                continue
            zone = person.attributes.get("zone")
            if zone:
                primary_room = zone
                break
        
        if primary_room == "none" and device_tracker_states:
            for tracker in device_tracker_states:
                if tracker.state == "home":
                    zone = tracker.attributes.get("zone")
                    if zone:
                        primary_room = zone
                        break
        
        if primary_room == "none" and motion_active:
            # Use first motion sensor's area
            area_id = motion_active[0].attributes.get("area_id")
            if area_id:
                area_reg = self._hass.data.get("area_registry")
                if area_reg:
                    area = area_reg.async_get_area(area_id)
                    if area:
                        primary_room = area.name
        
        self._attr_native_value = primary_room
        
        # Set extra attributes
        self._attr_extra_state_attributes = {
            "active_persons": len([p for p in person_states if p.state == "home"]),
            "motion_sensors_active": len(motion_active),
            "device_trackers_home": len([t for t in device_tracker_states if t.state == "home"]),
        }


class PresencePersonSensor(CoordinatorEntity, SensorEntity):
    """Sensor for person presence count."""
    
    _attr_name = "AI CoPilot Presence Person"
    _attr_unique_id = "ai_copilot_presence_person"
    _attr_icon = "mdi:account-group"
    _attr_native_unit_of_measurement = "persons"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Update person presence count."""
        person_states = self._hass.states.async_all("person")
        
        home_count = sum(1 for p in person_states if p.state == "home")
        away_count = sum(1 for p in person_states if p.state == "not_home")
        
        self._attr_native_value = home_count
        self._attr_extra_state_attributes = {
            "home": home_count,
            "away": away_count,
            "total": len(person_states),
            "persons_home": [p.name for p in person_states if p.state == "home"],
        }


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


class LightLevelSensor(CoordinatorEntity, SensorEntity):
    """Sensor for ambient light level."""
    
    _attr_name = "AI CoPilot Light Level"
    _attr_unique_id = "ai_copilot_light_level"
    _attr_icon = "mdi:brightness-6"
    _attr_native_unit_of_measurement = "lx"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Calculate average light level from sensors."""
        # Get illuminance sensors
        illuminance_states = [
            s for s in self._hass.states.async_all("sensor")
            if s.attributes.get("device_class") == "illuminance"
        ]
        
        # Also check light entities
        light_states = self._hass.states.async_all("light")
        lights_on = sum(1 for l in light_states if l.state == "on")
        
        # Get actual illuminance values
        total_lux = 0
        sensor_count = 0
        for sensor in illuminance_states:
            try:
                val = float(sensor.state)
                if val > 0:
                    total_lux += val
                    sensor_count += 1
            except (ValueError, TypeError):
                pass
        
        avg_lux = total_lux / sensor_count if sensor_count > 0 else 0
        
        # Classify light level
        if avg_lux < 10:
            level = "dark"
        elif avg_lux < 100:
            level = "dim"
        elif avg_lux < 1000:
            level = "normal"
        else:
            level = "bright"
        
        self._attr_native_value = level
        self._attr_extra_state_attributes = {
            "avg_lux": round(avg_lux, 1),
            "lights_on": lights_on,
            "sensor_count": sensor_count,
        }


class NoiseLevelSensor(CoordinatorEntity, SensorEntity):
    """Sensor for ambient noise level."""
    
    _attr_name = "AI CoPilot Noise Level"
    _attr_unique_id = "ai_copilot_noise_level"
    _attr_icon = "mdi:volume-high"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Calculate noise level from available sensors."""
        # Look for noise/sound sensors
        noise_sensors = [
            s for s in self._hass.states.async_all("sensor")
            if s.attributes.get("device_class") in ["noise", "sound"]
        ]
        
        # Also check for microphones that might report noise
        # This is a simplified version
        
        # Check media players - playing media indicates higher noise
        media_states = self._hass.states.async_all("media_player")
        media_playing = sum(1 for m in media_states if m.state == "playing")
        
        # Check for vacuum robots (noise source)
        vacuum_states = self._hass.states.async_all("vacuum")
        vacuums_active = sum(1 for v in vacuum_states if v.state == "cleaning")
        
        # Simple classification
        if vacuums_active > 0:
            noise_level = "loud"
        elif media_playing > 0:
            noise_level = "moderate"
        else:
            noise_level = "quiet"
        
        self._attr_native_value = noise_level
        self._attr_extra_state_attributes = {
            "media_playing": media_playing,
            "vacuums_active": vacuums_active,
            "noise_sensors": len(noise_sensors),
        }


class WeatherContextSensor(CoordinatorEntity, SensorEntity):
    """Sensor for weather context."""
    
    _attr_name = "AI CoPilot Weather Context"
    _attr_unique_id = "ai_copilot_weather_context"
    _attr_icon = "mdi:weather-partly-cloudy"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Get weather context."""
        weather_states = self._hass.states.async_all("weather")
        
        if not weather_states:
            self._attr_native_value = "unknown"
            return
        
        # Use first weather entity
        weather = weather_states[0]
        condition = weather.state
        
        # Map to context
        if condition in ["clear", "sunny"]:
            context = "clear"
        elif condition in ["cloudy", "partlycloudy"]:
            context = "cloudy"
        elif condition in ["rain", "drizzle", "pouring"]:
            context = "rainy"
        elif condition in ["snow", "blizzard", "sleet"]:
            context = "snowy"
        elif condition in ["fog", "hail", "thunderstorm"]:
            context = "severe"
        else:
            context = "unknown"
        
        self._attr_native_value = context
        
        # Get temperature
        temp = weather.attributes.get("temperature")
        
        self._attr_extra_state_attributes = {
            "condition": condition,
            "temperature": temp,
            "entity_id": weather.entity_id,
        }


class CalendarLoadSensor(CoordinatorEntity, SensorEntity):
    """Sensor for calendar load (busyness).
    
    Connected to:
    - calendar_context module for event data
    - Module Connector for calendar.load Neuron
    """
    
    _attr_name = "AI CoPilot Calendar Load"
    _attr_unique_id = "ai_copilot_calendar_load"
    _attr_icon = "mdi:calendar-clock"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Calculate calendar load for today.
        
        Uses data from:
        1. Calendar entities state
        2. Calendar context module (if available)
        3. Module connector signals
        """
        calendar_states = self._hass.states.async_all("calendar")
        
        now = dt_util.now()
        event_count = 0
        meetings_today = 0
        is_weekend = now.weekday() >= 5
        
        # Try to get calendar context from module connector
        calendar_context_data = None
        try:
            from ..module_connector import get_module_connector
            entry_id = coordinator.config_entry.entry_id if hasattr(coordinator, 'config_entry') else "default"
            connector = await get_module_connector(self._hass, entry_id)
            calendar_context_data = connector.calendar_context.to_dict()
        except Exception:
            pass
        
        # Try to get calendar events via service
        try:
            for cal in calendar_states:
                if cal.state != "unknown":
                    event_count += 1
                    
                # Get actual events if available
                try:
                    result = await self._hass.services.async_call(
                        "calendar",
                        "get_events",
                        {
                            "entity_id": cal.entity_id,
                            "start_date_time": now.isoformat(),
                            "end_date_time": (now + timedelta(days=1)).isoformat(),
                        },
                        blocking=False,
                    )
                    if result and cal.entity_id in result:
                        events = result[cal.entity_id].get("events", [])
                        meetings_today += len(events)
                except Exception:
                    pass
        except Exception as err:
            _LOGGER.debug("Error fetching calendar events: %s", err)
        
        # Use data from calendar context if available
        if calendar_context_data:
            event_count = calendar_context_data.get("event_count", event_count)
            meetings_today = calendar_context_data.get("meetings_today", meetings_today)
            is_weekend = calendar_context_data.get("is_weekend", is_weekend)
            focus_weight = calendar_context_data.get("focus_weight", 0.0)
            social_weight = calendar_context_data.get("social_weight", 0.0)
            relax_weight = calendar_context_data.get("relax_weight", 0.0)
            has_conflicts = calendar_context_data.get("has_conflicts", False)
            next_meeting_in_minutes = calendar_context_data.get("next_meeting_in_minutes")
        else:
            focus_weight = 0.0
            social_weight = 0.0
            relax_weight = 0.0
            has_conflicts = False
            next_meeting_in_minutes = None
        
        # Classify load based on event count
        if meetings_today == 0:
            load = "free"
        elif meetings_today < 3:
            load = "light"
        elif meetings_today < 6:
            load = "moderate"
        else:
            load = "busy"
        
        # Adjust based on focus weight (meetings = more load)
        if focus_weight > 0.5:
            if load == "light":
                load = "moderate"
            elif load == "moderate":
                load = "busy"
        
        self._attr_native_value = load
        self._attr_extra_state_attributes = {
            "event_count": event_count,
            "meetings_today": meetings_today,
            "hour": now.hour,
            "is_weekend": is_weekend,
            "focus_weight": focus_weight,
            "social_weight": social_weight,
            "relax_weight": relax_weight,
            "has_conflicts": has_conflicts,
            "next_meeting_in_minutes": next_meeting_in_minutes,
            "source": "calendar_context_module" if calendar_context_data else "calendar_entities",
        }


class AttentionLoadSensor(CoordinatorEntity, SensorEntity):
    """Sensor for attention/mental load estimation."""
    
    _attr_name = "AI CoPilot Attention Load"
    _attr_unique_id = "ai_copilot_attention_load"
    _attr_icon = "mdi:brain"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Estimate attention load based on device activity."""
        # Count active devices that indicate user attention
        # TVs, computers, phones
        
        # Media players with active content
        media_states = self._hass.states.async_all("media_player")
        media_active = sum(1 for m in media_states if m.state == "playing")
        
        # Computers (if available)
        # Smart speakers playing
        speaker_states = self._hass.states.async_all("media_player")
        speakers_playing = sum(1 for s in speaker_states 
                              if s.attributes.get("device_class") == "speaker" 
                              and s.state == "playing")
        
        # Calculate load
        load_score = media_active * 2 + speakers_playing
        
        if load_score == 0:
            attention = "idle"
        elif load_score < 2:
            attention = "low"
        elif load_score < 5:
            attention = "moderate"
        else:
            attention = "high"
        
        self._attr_native_value = attention
        self._attr_extra_state_attributes = {
            "media_active": media_active,
            "speakers_playing": speakers_playing,
        }


class StressProxySensor(CoordinatorEntity, SensorEntity):
    """Sensor for stress proxy estimation."""
    
    _attr_name = "AI CoPilot Stress Proxy"
    _attr_unique_id = "ai_copilot_stress_proxy"
    _attr_icon = "mdi:heart-pulse"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Estimate stress proxy based on available sensors."""
        # This is a proxy estimation - in reality would use
        # heart rate sensors, cortisol levels, etc.
        
        # Factors that might indicate stress:
        # - Many devices active late at night
        # - Unusual activity patterns
        # - Multiple alerts
        
        now = dt_util.now()
        is_late_night = now.hour >= 23 or now.hour < 6
        
        # Media activity late at night might indicate stress
        media_states = self._hass.states.async_all("media_player")
        media_playing = sum(1 for m in media_states if m.state == "playing")
        
        # Count alerts
        alert_states = self._hass.states.async_all("alert")
        active_alerts = sum(1 for a in alert_states if a.state == "on")
        
        # Calculate stress proxy
        stress_score = 0
        
        if is_late_night and media_playing > 0:
            stress_score += 2
        
        if active_alerts > 0:
            stress_score += active_alerts
        
        if stress_score == 0:
            stress = "relaxed"
        elif stress_score < 2:
            stress = "low"
        elif stress_score < 4:
            stress = "moderate"
        else:
            stress = "high"
        
        self._attr_native_value = stress
        self._attr_extra_state_attributes = {
            "late_night_media": is_late_night and media_playing > 0,
            "active_alerts": active_alerts,
            "score": stress_score,
        }


class EnergyProxySensor(CoordinatorEntity, SensorEntity):
    """Sensor for energy usage proxy."""
    
    _attr_name = "AI CoPilot Energy Proxy"
    _attr_unique_id = "ai_copilot_energy_proxy"
    _attr_icon = "mdi:lightning-bolt"
    _attr_native_unit_of_measurement = "W"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Calculate energy proxy from sensors."""
        # Get power sensors
        power_sensors = [
            s for s in self._hass.states.async_all("sensor")
            if s.attributes.get("device_class") == "power"
        ]
        
        total_power = 0
        for sensor in power_sensors:
            try:
                val = float(sensor.state)
                if val > 0:
                    total_power += val
            except (ValueError, TypeError):
                pass
        
        # Count high-power devices
        light_states = self._hass.states.async_all("light")
        lights_on = sum(1 for l in light_states if l.state == "on")
        
        switch_states = self._hass.states.async_all("switch")
        switches_on = sum(1 for s in switch_states if s.state == "on")
        
        # Classify
        if total_power < 100:
            usage = "low"
        elif total_power < 500:
            usage = "moderate"
        elif total_power < 1500:
            usage = "high"
        else:
            usage = "very_high"
        
        self._attr_native_value = usage
        self._attr_extra_state_attributes = {
            "total_power_w": round(total_power, 1),
            "lights_on": lights_on,
            "switches_on": switches_on,
        }


class MediaActivitySensor(CoordinatorEntity, SensorEntity):
    """Sensor for media activity."""
    
    _attr_name = "AI CoPilot Media Activity"
    _attr_unique_id = "ai_copilot_media_activity"
    _attr_icon = "mdi:play-circle"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Detect media activity."""
        media_states = self._hass.states.async_all("media_player")
        
        playing = [m for m in media_states if m.state == "playing"]
        paused = [m for m in media_states if m.state == "paused"]
        idle = [m for m in media_states if m.state == "idle"]
        
        if len(playing) == 0:
            activity = "idle"
        elif len(playing) == 1:
            activity = "single"
        else:
            activity = "multi"
        
        self._attr_native_value = activity
        self._attr_extra_state_attributes = {
            "playing": len(playing),
            "paused": len(paused),
            "idle": len(idle),
            "players_playing": [p.name for p in playing],
        }


class MediaIntensitySensor(CoordinatorEntity, SensorEntity):
    """Sensor for media intensity/volume."""
    
    _attr_name = "AI CoPilot Media Intensity"
    _attr_unique_id = "ai_copilot_media_intensity"
    _attr_icon = "mdi:volume-high"
    _attr_native_unit_of_measurement = "%"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Calculate media intensity."""
        media_states = self._hass.states.async_all("media_player")
        
        total_volume = 0
        playing_count = 0
        
        for media in media_states:
            if media.state == "playing":
                playing_count += 1
                volume = media.attributes.get("volume_level", 0.5)
                total_volume += volume
        
        avg_volume = (total_volume / playing_count * 100) if playing_count > 0 else 0
        
        if playing_count == 0:
            intensity = "off"
        elif avg_volume < 30:
            intensity = "low"
        elif avg_volume < 60:
            intensity = "medium"
        else:
            intensity = "high"
        
        self._attr_native_value = intensity
        self._attr_extra_state_attributes = {
            "avg_volume": round(avg_volume, 1),
            "playing": playing_count,
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the 14 neuron sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        PresenceRoomSensor(coordinator, hass),
        PresencePersonSensor(coordinator, hass),
        ActivityLevelSensor(coordinator, hass),
        ActivityStillnessSensor(coordinator, hass),
        TimeOfDaySensor(coordinator),
        DayTypeSensor(coordinator, hass),
        RoutineStabilitySensor(coordinator, hass),
        LightLevelSensor(coordinator, hass),
        NoiseLevelSensor(coordinator, hass),
        WeatherContextSensor(coordinator, hass),
        CalendarLoadSensor(coordinator, hass),
        AttentionLoadSensor(coordinator, hass),
        StressProxySensor(coordinator, hass),
        EnergyProxySensor(coordinator, hass),
        MediaActivitySensor(coordinator, hass),
        MediaIntensitySensor(coordinator, hass),
    ]
    
    async_add_entities(entities)
    
    _LOGGER.info("Created %d neuron sensors", len(entities))
