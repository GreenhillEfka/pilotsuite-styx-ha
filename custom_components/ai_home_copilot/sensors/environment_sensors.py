"""Environment sensors for AI Home CoPilot Neurons.

Sensors:
- LightLevelSensor: Ambient light level
- NoiseLevelSensor: Ambient noise level
- WeatherContextSensor: Weather context
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


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
