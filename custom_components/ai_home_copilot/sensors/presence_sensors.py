"""Presence sensors for AI Home CoPilot Neurons.

Sensors:
- PresenceRoomSensor: Primary room with presence
- PresencePersonSensor: Person presence count
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class PresenceRoomSensor(CoordinatorEntity, SensorEntity):
    """Sensor for primary room with presence.
    
    Connected to:
    - Person entities (home/away)
    - Device trackers
    - Motion sensors (area detection)
    - Camera presence events (via module connector)
    - Camera zone events (spatial context)
    """
    
    _attr_name = "AI CoPilot Presence Room"
    _attr_unique_id = "ai_copilot_presence_room"
    _attr_icon = "mdi:door"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
        self._attr_native_value = "unknown"
        self._camera_detected_room = None
        self._camera_person_detected = False
    
    async def async_update(self) -> None:
        """Update presence room based on HA states.
        
        Priority:
        1. Person zone (from person entities)
        2. Device tracker zone
        3. Camera zone events (spatial context)
        4. Motion sensor area
        """
        # Find person entities and their States
        person_states = self._hass.states.async_all("person")
        
        # Find device_tracker entities
        device_tracker_states = self._hass.states.async_all("device_tracker")
        
        # Find binary sensors related to motion/presence
        motion_states = self._hass.states.async_all("binary_sensor")
        motion_active = [
            s for s in motion_states 
            if s.attributes.get("device_class") == "motion" and s.state == "on"
        ]
        
        # Check for camera presence/zone events via module connector
        camera_room = None
        person_detected = False
        try:
            from ..module_connector import get_module_connector
            
            entry_id = coordinator.config_entry.entry_id if hasattr(coordinator, 'config_entry') else "default"
            connector = await get_module_connector(self._hass, entry_id)
            activity_context = connector.activity_context
            
            # Get room from camera zone events
            if activity_context.room:
                camera_room = activity_context.room
            
            # Check if person was detected by camera
            if activity_context.person_detected:
                person_detected = True
                
        except Exception:
            pass
        
        # Determine primary room with presence
        # Priority: person zone > device_tracker zone > camera zone > motion sensor area
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
        
        # Use camera zone if no room found yet
        if primary_room == "none" and camera_room:
            primary_room = camera_room
        
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
        self._camera_detected_room = camera_room
        self._camera_person_detected = person_detected
        
        # Set extra attributes
        self._attr_extra_state_attributes = {
            "active_persons": len([p for p in person_states if p.state == "home"]),
            "motion_sensors_active": len(motion_active),
            "device_trackers_home": len([t for t in device_tracker_states if t.state == "home"]),
            "camera_room": camera_room,
            "camera_person_detected": person_detected,
            "sources": ["person", "device_tracker", "camera_zone", "motion_sensor"],
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
