"""Cognitive sensors for AI Home CoPilot Neurons.

Sensors:
- AttentionLoadSensor: Attention/mental load estimation
- StressProxySensor: Stress proxy estimation
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class AttentionLoadSensor(CoordinatorEntity, SensorEntity):
    """Sensor for attention/mental load estimation.
    
    Connected to:
    - Calendar events (meeting load)
    - Media players (active content)
    - Smart speakers
    - Module Connector signals
    """
    
    _attr_name = "AI CoPilot Attention Load"
    _attr_unique_id = "ai_copilot_attention_load"
    _attr_icon = "mdi:brain"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Estimate attention load based on device activity and calendar.
        
        Uses:
        1. Calendar events (meetings = high attention demand)
        2. Media players (active content)
        3. Smart speakers
        4. Module Connector calendar context
        """
        # Count active devices that indicate user attention
        # TVs, computers, phones
        
        # Media players with active content
        media_states = self._hass.states.async_all("media_player")
        media_active = sum(1 for m in media_states if m.state == "playing")
        
        # Smart speakers playing
        speaker_states = self._hass.states.async_all("media_player")
        speakers_playing = sum(1 for s in speaker_states 
                              if s.attributes.get("device_class") == "speaker" 
                              and s.state == "playing")
        
        # Get calendar context for meeting load
        calendar_focus_weight = 0.0
        calendar_meetings_today = 0
        try:
            from ..module_connector import get_module_connector
            
            entry_id = coordinator.config_entry.entry_id if hasattr(coordinator, 'config_entry') else "default"
            connector = await get_module_connector(self._hass, entry_id)
            calendar_context = connector.calendar_context
            
            calendar_focus_weight = calendar_context.focus_weight
            calendar_meetings_today = calendar_context.event_count
            
        except Exception:  # noqa: BLE001
            pass

        # Calculate load
        # Device-based score
        load_score = media_active * 2 + speakers_playing
        
        # Add calendar-based score (meetings increase attention demand)
        if calendar_focus_weight > 0.5:
            load_score += 3  # High meeting load
        elif calendar_focus_weight > 0.2:
            load_score += 1  # Moderate meeting load
        
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
            "calendar_focus_weight": calendar_focus_weight,
            "calendar_meetings_today": calendar_meetings_today,
            "sources": ["media", "speakers", "calendar"],
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
