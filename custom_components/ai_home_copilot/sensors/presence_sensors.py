"""Presence sensors for AI Home CoPilot Neurons.

Sensors:
- PresenceRoomSensor: Primary room with presence
- PresencePersonSensor: Person presence count
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Maximum persons for social score normalization
_MAX_SOCIAL_PERSONS: int = 3
_MAX_ACTIVE_SOURCES: int = 3


async def _fetch_all_states_async(
    hass: HomeAssistant,
    entity_types: tuple[str, ...],
) -> dict[str, list[State]]:
    """Fetch states for multiple entity types in parallel.
    
    Args:
        hass: Home Assistant instance
        entity_types: Tuple of entity types to fetch
        
    Returns:
        Dictionary mapping entity type to list of states
    """
    import asyncio
    
    async def fetch_type(entity_type: str) -> tuple[str, list[State]]:
        return (entity_type, hass.states.async_all(entity_type))
    
    try:
        results = await asyncio.gather(
            *[fetch_type(etype) for etype in entity_types],
            return_exceptions=True,
        )
        
        state_dict: dict[str, list[State]] = {}
        for result in results:
            if isinstance(result, Exception):
                _LOGGER.warning("Failed to fetch states: %s", result)
                continue
            entity_type, states = result
            state_dict[entity_type] = states
            
        return state_dict
    except Exception as err:
        _LOGGER.error("Failed to batch fetch states: %s", err)
        return {etype: [] for etype in entity_types}


class PresenceRoomSensor(CoordinatorEntity, SensorEntity):
    """Sensor for primary room with presence.
    
    Connected to:
    - Person entities (home/away)
    - Device trackers
    - Motion sensors (area detection)
    - Camera presence events (via module connector)
    - Camera zone events (spatial context)
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
        """Update presence room based on HA states.
        
        Priority:
        1. Person zone (from person entities)
        2. Device tracker zone
        3. Camera zone events (spatial context)
        4. Motion sensor area
        """
        # Batch fetch all entity types in parallel
        states_by_type = await _fetch_all_states_async(
            self._hass,
            ("person", "device_tracker", "binary_sensor"),
        )
        
        person_states: list[State] = states_by_type.get("person", [])
        device_tracker_states: list[State] = states_by_type.get("device_tracker", [])
        binary_sensor_states: list[State] = states_by_type.get("binary_sensor", [])
        
        # Find binary sensors related to motion/presence
        motion_active: list[State] = [
            s for s in binary_sensor_states 
            if s.attributes.get("device_class") == "motion" and s.state == "on"
        ]
        
        # Check for camera presence/zone events via module connector
        camera_room: str | None = None
        person_detected: bool = False
        
        try:
            from ..module_connector import get_module_connector
            
            entry_id: str = "default"
            if hasattr(self.coordinator, 'config_entry'):
                entry_id = self.coordinator.config_entry.entry_id
            
            connector = await get_module_connector(self._hass, entry_id)
            activity_context = connector.activity_context
            
            # Get room from camera zone events
            if activity_context.room:
                camera_room = activity_context.room
            
            # Check if person was detected by camera
            if activity_context.person_detected:
                person_detected = True
                
        except ImportError as err:
            _LOGGER.debug("Module connector not available: %s", err)
        except Exception as err:
            _LOGGER.debug("Failed to get camera context: %s", err)
        
        # Determine primary room with presence
        # Priority: person zone > device_tracker zone > camera zone > motion sensor area
        primary_room: str = "none"
        
        for person in person_states:
            if person.state != "home":
                continue
            zone = person.attributes.get("zone")
            if zone:
                primary_room = str(zone)
                break
        
        if primary_room == "none":
            for tracker in device_tracker_states:
                if tracker.state == "home":
                    zone = tracker.attributes.get("zone")
                    if zone:
                        primary_room = str(zone)
                        break
        
        # Use camera zone if no room found yet
        if primary_room == "none" and camera_room:
            primary_room = camera_room
        
        if primary_room == "none" and motion_active:
            # Use first motion sensor's area
            area_id = motion_active[0].attributes.get("area_id")
            if area_id:
                try:
                    area_reg = self._hass.data.get("area_registry")
                    if area_reg:
                        area = area_reg.async_get_area(area_id)
                        if area:
                            primary_room = area.name
                except Exception as err:
                    _LOGGER.debug("Failed to get area: %s", err)
        
        self._attr_native_value = primary_room
        self._camera_detected_room = camera_room
        self._camera_person_detected = person_detected
        
        # Calculate presence metrics for mood integration
        home_count: int = sum(1 for p in person_states if p.state == "home")
        
        # Social mood factor: multiple people = more social
        is_social: bool = home_count > 1
        
        # Active mood factor: motion detected = active
        is_active: bool = len(motion_active) > 0 or person_detected
        
        # Set extra attributes
        self._attr_extra_state_attributes = {
            "active_persons": home_count,
            "motion_sensors_active": len(motion_active),
            "device_trackers_home": len([t for t in device_tracker_states if t.state == "home"]),
            "camera_room": camera_room,
            "camera_person_detected": person_detected,
            "sources": ["person", "device_tracker", "camera_zone", "motion_sensor"],
            # Mood integration
            "social": is_social,
            "active": is_active,
            "social_score": min(home_count / _MAX_SOCIAL_PERSONS, 1.0),
            "active_score": min((len(motion_active) + int(person_detected)) / _MAX_ACTIVE_SOURCES, 1.0),
        }


class PresencePersonSensor(CoordinatorEntity, SensorEntity):
    """Sensor for person presence count."""
    
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
        """Update person presence count."""
        # Use cached states from coordinator or fetch directly
        person_states: list[State] = self._hass.states.async_all("person")
        
        home_count: int = sum(1 for p in person_states if p.state == "home")
        away_count: int = sum(1 for p in person_states if p.state == "not_home")
        
        # Social mood factor: multiple people = more social
        is_social: bool = home_count > 1
        
        # Get names safely
        persons_home: list[str] = []
        try:
            persons_home = [p.name for p in person_states if p.state == "home"]
        except Exception as err:
            _LOGGER.debug("Failed to get person names: %s", err)
        
        self._attr_native_value = home_count
        self._attr_extra_state_attributes = {
            "home": home_count,
            "away": away_count,
            "total": len(person_states),
            "persons_home": persons_home,
            # Mood integration
            "social": is_social,
            "social_score": min(home_count / _MAX_SOCIAL_PERSONS, 1.0),
        }
