"""Media sensors for AI Home CoPilot Neurons.

Sensors:
- MediaActivitySensor: Media activity detection
- MediaIntensitySensor: Media intensity/volume
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class MediaActivitySensor(CoordinatorEntity, SensorEntity):
    """Sensor for media activity."""
    
    _attr_name = "AI CoPilot Media Activity"
    _attr_unique_id = "ai_copilot_media_activity"
    _attr_icon = "mdi:play-circle"
    _attr_should_poll = True
    
    def __init__(
        self,
        coordinator: CopilotDataUpdateCoordinator,
        hass: HomeAssistant,
    ) -> None:
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
        
        # Mood integration
        # Active: media playing indicates activity
        is_active: bool = len(playing) > 0
        # Social: multiple players or TV could indicate social gathering
        is_social: bool = len(playing) > 1 or any(
            p.attributes.get("friendly_name", "").lower() in ("tv", "fernseher", "living room tv", "wohnzimmer tv")
            for p in playing
        )
        
        self._attr_native_value = activity
        self._attr_extra_state_attributes = {
            "playing": len(playing),
            "paused": len(paused),
            "idle": len(idle),
            "players_playing": [p.name for p in playing],
            # Mood integration
            "active": is_active,
            "social": is_social,
            "active_score": min(len(playing) / 3, 1.0),
            "social_score": 1.0 if is_social else 0.0,
        }


class MediaIntensitySensor(CoordinatorEntity, SensorEntity):
    """Sensor for media intensity/volume."""
    
    _attr_name = "AI CoPilot Media Intensity"
    _attr_unique_id = "ai_copilot_media_intensity"
    _attr_icon = "mdi:volume-high"
    _attr_native_unit_of_measurement: str = "%"
    _attr_should_poll = True
    
    def __init__(
        self,
        coordinator: CopilotDataUpdateCoordinator,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Calculate media intensity."""
        media_states = self._hass.states.async_all("media_player")
        
        total_volume: float = 0.0
        playing_count: int = 0
        
        for media in media_states:
            if media.state == "playing":
                playing_count += 1
                volume = media.attributes.get("volume_level", 0.5)
                total_volume += volume
        
        avg_volume: float = (total_volume / playing_count * 100) if playing_count > 0 else 0.0
        
        if playing_count == 0:
            intensity = "off"
        elif avg_volume < 30:
            intensity = "low"
        elif avg_volume < 60:
            intensity = "medium"
        else:
            intensity = "high"
        
        # Mood integration
        # Active: higher intensity = more active
        active_score: float = avg_volume / 100.0 if playing_count > 0 else 0.0
        
        self._attr_native_value = intensity
        self._attr_extra_state_attributes = {
            "avg_volume": round(avg_volume, 1),
            "playing": playing_count,
            # Mood integration
            "active": playing_count > 0,
            "active_score": active_score,
        }
