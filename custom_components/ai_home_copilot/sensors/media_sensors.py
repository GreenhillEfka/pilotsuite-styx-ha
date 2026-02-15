"""Media sensors for AI Home CoPilot Neurons.

Sensors:
- MediaActivitySensor: Media activity detection
- MediaIntensitySensor: Media intensity/volume
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Cache duration in seconds
_MEDIA_CACHE_DURATION: float = 5.0

# Volume thresholds
_VOLUME_LOW: float = 30.0
_VOLUME_MEDIUM: float = 60.0
_DEFAULT_VOLUME: float = 0.5

# Social detection keywords
_TV_KEYWORDS: tuple[str, ...] = ("tv", "fernseher", "living room tv", "wohnzimmer tv", "fernseher im wohnzimmer")

# Max values for scoring
_MAX_PLAYING_FOR_SCORE: int = 3


@dataclass
class MediaCache:
    """Cache for media player states to reduce repeated state fetches."""
    states: list[State]
    timestamp: float


class MediaStateCache:
    """Simple cache for media player states."""
    
    def __init__(self) -> None:
        self._cache: MediaCache | None = None
    
    def get_states(self, hass: HomeAssistant, max_age: float = _MEDIA_CACHE_DURATION) -> list[State]:
        """Get media player states, using cache if fresh enough."""
        now: float = time.time()
        
        if self._cache is not None and (now - self._cache.timestamp) < max_age:
            return self._cache.states
        
        # Fetch fresh states
        states: list[State] = hass.states.async_all("media_player")
        self._cache = MediaCache(states=states, timestamp=now)
        return states
    
    def invalidate(self) -> None:
        """Invalidate the cache."""
        self._cache = None


# Global cache instance
_media_cache = MediaStateCache()


class MediaActivitySensor(CoordinatorEntity, SensorEntity):
    """Sensor for media activity."""
    
    _attr_name: str = "AI CoPilot Media Activity"
    _attr_unique_id: str = "ai_copilot_media_activity"
    _attr_icon: str = "mdi:play-circle"
    _attr_should_poll: bool = False  # Using coordinator
    
    def __init__(
        self,
        coordinator: CopilotDataUpdateCoordinator,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(coordinator)
        self._hass: HomeAssistant = hass
    
    async def async_update(self) -> None:
        """Detect media activity."""
        # Use cached media player states
        media_states: list[State] = _media_cache.get_states(self._hass)
        
        playing: list[State] = []
        paused: list[State] = []
        idle: list[State] = []
        
        try:
            for media in media_states:
                state = media.state
                if state == "playing":
                    playing.append(media)
                elif state == "paused":
                    paused.append(media)
                elif state == "idle":
                    idle.append(media)
        except Exception as err:
            _LOGGER.error("Error categorizing media states: %s", err)
        
        # Determine activity level
        activity: str
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
        is_social: bool = self._check_social_media(playing)
        
        # Get player names safely
        players_playing: list[str] = []
        try:
            players_playing = [p.name for p in playing]
        except Exception as err:
            _LOGGER.debug("Failed to get player names: %s", err)
        
        self._attr_native_value = activity
        self._attr_extra_state_attributes = {
            "playing": len(playing),
            "paused": len(paused),
            "idle": len(idle),
            "players_playing": players_playing,
            # Mood integration
            "active": is_active,
            "social": is_social,
            "active_score": min(len(playing) / _MAX_PLAYING_FOR_SCORE, 1.0),
            "social_score": 1.0 if is_social else 0.0,
        }
    
    def _check_social_media(self, playing: list[State]) -> bool:
        """Check if any playing media indicates social gathering."""
        if len(playing) > 1:
            return True
        
        # Check for TV keywords in player names
        for player in playing:
            try:
                friendly_name = player.attributes.get("friendly_name", "").lower()
                for keyword in _TV_KEYWORDS:
                    if keyword in friendly_name:
                        return True
            except Exception:
                continue
        
        return False


class MediaIntensitySensor(CoordinatorEntity, SensorEntity):
    """Sensor for media intensity/volume."""
    
    _attr_name: str = "AI CoPilot Media Intensity"
    _attr_unique_id: str = "ai_copilot_media_intensity"
    _attr_icon: str = "mdi:volume-high"
    _attr_native_unit_of_measurement: str = "%"
    _attr_should_poll: bool = False  # Using coordinator
    
    def __init__(
        self,
        coordinator: CopilotDataUpdateCoordinator,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(coordinator)
        self._hass: HomeAssistant = hass
    
    async def async_update(self) -> None:
        """Calculate media intensity."""
        # Use cached media player states
        media_states: list[State] = _media_cache.get_states(self._hass)
        
        total_volume: float = 0.0
        playing_count: int = 0
        
        try:
            for media in media_states:
                if media.state == "playing":
                    playing_count += 1
                    volume: float = media.attributes.get("volume_level")
                    if volume is not None:
                        try:
                            total_volume += float(volume)
                        except (TypeError, ValueError):
                            total_volume += _DEFAULT_VOLUME
                    else:
                        total_volume += _DEFAULT_VOLUME
        except Exception as err:
            _LOGGER.error("Error calculating media intensity: %s", err)
        
        # Calculate average volume with proper division handling
        avg_volume: float = 0.0
        if playing_count > 0:
            avg_volume = (total_volume / playing_count) * 100.0
        
        # Determine intensity level
        intensity: str
        if playing_count == 0:
            intensity = "off"
        elif avg_volume < _VOLUME_LOW:
            intensity = "low"
        elif avg_volume < _VOLUME_MEDIUM:
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
