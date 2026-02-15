"""
Camera Entities for AI Home CoPilot.

Provides specialized camera entities for Habitus:
- motion_detection_camera: Motion detection events
- presence_camera: Presence logging
- activity_camera: Activity tracking
- zone_camera: Zone monitoring

Privacy-first: local processing only, face blurring, configurable retention.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from dataclasses import dataclass, field

from homeassistant.components.camera import Camera
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import CopilotBaseEntity
from .coordinator import CopilotCoordinator

_LOGGER = logging.getLogger(__name__)


# Signal for camera events
SIGNAL_CAMERA_MOTION = "ai_home_copilot_camera_motion"
SIGNAL_CAMERA_PRESENCE = "ai_home_copilot_camera_presence"
SIGNAL_CAMERA_ACTIVITY = "ai_home_copilot_camera_activity"
SIGNAL_CAMERA_ZONE = "ai_home_copilot_camera_zone"


@dataclass
class CameraMotionEvent:
    """Represents a motion detection event."""
    camera_id: str
    camera_name: str
    timestamp: datetime
    confidence: float = 1.0
    zone: str | None = None
    thumbnail: str | None = None


@dataclass
class CameraPresenceEvent:
    """Represents a presence detection event."""
    camera_id: str
    camera_name: str
    timestamp: datetime
    presence_type: str = "person"  # person, vehicle, animal, unknown
    person_name: str | None = None
    confidence: float = 1.0


@dataclass
class CameraActivityEvent:
    """Represents an activity tracking event."""
    camera_id: str
    camera_name: str
    timestamp: datetime
    activity_type: str  # walking, running, sitting, etc.
    duration_seconds: int = 0
    confidence: float = 1.0


@dataclass
class CameraZoneEvent:
    """Represents a zone monitoring event."""
    camera_id: str
    camera_name: str
    timestamp: datetime
    zone_name: str
    event_type: str = "entered"  # entered, left, lingered
    object_type: str | None = None


@dataclass 
class CameraState:
    """Internal state for camera tracking."""
    motion_events: list[CameraMotionEvent] = field(default_factory=list)
    presence_events: list[CameraPresenceEvent] = field(default_factory=list)
    activity_events: list[CameraActivityEvent] = field(default_factory=list)
    zone_events: list[CameraZoneEvent] = field(default_factory=list)
    last_motion: datetime | None = None
    last_presence: datetime | None = None
    is_motion_detected: bool = False
    current_presence: str | None = None
    motion_count_24h: int = 0
    retention_hours: int = 24


class MotionDetectionCamera(CopilotBaseEntity, BinarySensorEntity):
    """Motion detection camera entity for Habitus."""
    
    _attr_has_entity_name = True
    _attr_name = "Motion Detection"
    _attr_icon = "mdi:motion-sensor"
    _attr_device_class = "motion"
    
    def __init__(
        self,
        coordinator: CopilotCoordinator,
        entry: ConfigEntry,
        camera_id: str,
        camera_name: str,
        camera_entity_id: str | None = None,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._camera_id = camera_id
        self._camera_name = camera_name
        self._camera_entity_id = camera_entity_id
        self._attr_unique_id = f"ai_home_copilot_motion_{camera_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"motion_camera_{camera_id}")},
            "name": f"Motion {camera_name}",
            "manufacturer": "AI Home CoPilot",
            "model": "Habitus Motion Camera",
        }
        
    @property
    def is_on(self) -> bool:
        """Return True if motion detected."""
        return self.coordinator.camera_state.get(self._camera_id, CameraState()).is_motion_detected
    
    @property
    def extra_state_attributes(self) -> dict | None:
        """Return extra state attributes."""
        state = self.coordinator.camera_state.get(self._camera_id, CameraState())
        return {
            "camera_id": self._camera_id,
            "camera_name": self._camera_name,
            "last_motion": state.last_motion.isoformat() if state.last_motion else None,
            "motion_count_24h": state.motion_count_24h,
            "recent_events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "confidence": e.confidence,
                    "zone": e.zone,
                }
                for e in state.motion_events[-5:]
            ],
        }


class PresenceCamera(CopilotBaseEntity, BinarySensorEntity):
    """Presence detection camera entity for Habitus."""
    
    _attr_has_entity_name = True
    _attr_name = "Presence Detected"
    _attr_icon = "mdi:account-eye"
    _attr_device_class = "presence"
    
    def __init__(
        self,
        coordinator: CopilotCoordinator,
        entry: ConfigEntry,
        camera_id: str,
        camera_name: str,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._camera_id = camera_id
        self._camera_name = camera_name
        self._attr_unique_id = f"ai_home_copilot_presence_{camera_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"presence_camera_{camera_id}")},
            "name": f"Presence {camera_name}",
            "manufacturer": "AI Home CoPilot",
            "model": "Habitus Presence Camera",
        }
        
    @property
    def is_on(self) -> bool:
        """Return True if presence detected."""
        state = self.coordinator.camera_state.get(self._camera_id, CameraState())
        return state.current_presence is not None
    
    @property
    def extra_state_attributes(self) -> dict | None:
        """Return extra state attributes."""
        state = self.coordinator.camera_state.get(self._camera_id, CameraState())
        return {
            "camera_id": self._camera_id,
            "camera_name": self._camera_name,
            "current_presence": state.current_presence,
            "last_presence": state.last_presence.isoformat() if state.last_presence else None,
            "presence_count_24h": len(state.presence_events),
            "recent_events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "type": e.presence_type,
                    "person": e.person_name,
                    "confidence": e.confidence,
                }
                for e in state.presence_events[-5:]
            ],
        }


class ActivityCamera(CopilotBaseEntity, SensorEntity):
    """Activity tracking camera entity for Habitus."""
    
    _attr_has_entity_name = True
    _attr_name = "Current Activity"
    _attr_icon = "mdi:run"
    _attr_device_class = None
    
    def __init__(
        self,
        coordinator: CopilotCoordinator,
        entry: ConfigEntry,
        camera_id: str,
        camera_name: str,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._camera_id = camera_id
        self._camera_name = camera_name
        self._attr_unique_id = f"ai_home_copilot_activity_{camera_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"activity_camera_{camera_id}")},
            "name": f"Activity {camera_name}",
            "manufacturer": "AI Home CoPilot",
            "model": "Habitus Activity Camera",
        }
        
    @property
    def native_value(self) -> str | None:
        """Return current activity."""
        state = self.coordinator.camera_state.get(self._camera_id, CameraState())
        if state.activity_events:
            return state.activity_events[-1].activity_type
        return "idle"
    
    @property
    def extra_state_attributes(self) -> dict | None:
        """Return extra state attributes."""
        state = self.coordinator.camera_state.get(self._camera_id, CameraState())
        return {
            "camera_id": self._camera_id,
            "camera_name": self._camera_name,
            "activity_count_24h": len(state.activity_events),
            "recent_activities": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "type": e.activity_type,
                    "duration": e.duration_seconds,
                    "confidence": e.confidence,
                }
                for e in state.activity_events[-5:]
            ],
        }


class ZoneCamera(CopilotBaseEntity, SensorEntity):
    """Zone monitoring camera entity for Habitus."""
    
    _attr_has_entity_name = True
    _attr_name = "Zone Status"
    _attr_icon = "mdi:map-marker-radius"
    
    def __init__(
        self,
        coordinator: CopilotCoordinator,
        entry: ConfigEntry,
        camera_id: str,
        camera_name: str,
        zones: list[str] | None = None,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._camera_id = camera_id
        self._camera_name = camera_name
        self._zones = zones or []
        self._attr_unique_id = f"ai_home_copilot_zone_{camera_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"zone_camera_{camera_id}")},
            "name": f"Zone Monitor {camera_name}",
            "manufacturer": "AI Home CoPilot",
            "model": "Habitus Zone Camera",
        }
        
    @property
    def native_value(self) -> str | None:
        """Return current zone status."""
        state = self.coordinator.camera_state.get(self._camera_id, CameraState())
        if state.zone_events:
            latest = state.zone_events[-1]
            return f"{latest.zone_name}: {latest.event_type}"
        return "clear"
    
    @property
    def extra_state_attributes(self) -> dict | None:
        """Return extra state attributes."""
        state = self.coordinator.camera_state.get(self._camera_id, CameraState())
        return {
            "camera_id": self._camera_id,
            "camera_name": self._camera_name,
            "monitored_zones": self._zones,
            "zone_events_24h": len(state.zone_events),
            "recent_zone_events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "zone": e.zone_name,
                    "event": e.event_type,
                    "object": e.object_type,
                }
                for e in state.zone_events[-5:]
            ],
        }


class CameraMotionHistorySensor(CopilotBaseEntity, SensorEntity):
    """Sensor for motion history across all cameras."""
    
    _attr_has_entity_name = True
    _attr_name = "Motion History"
    _attr_icon = "mdi:history"
    _attr_native_unit_of_measurement = "events"
    
    def __init__(self, coordinator: CopilotCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = "ai_home_copilot_camera_motion_history"
        
    @property
    def native_value(self) -> int:
        """Return total motion events in last 24h."""
        total = 0
        now = dt_util.now()
        for state in self.coordinator.camera_state.values():
            for event in state.motion_events:
                if now - event.timestamp < timedelta(hours=24):
                    total += 1
        return total
    
    @property
    def extra_state_attributes(self) -> dict | None:
        """Return per-camera breakdown."""
        now = dt_util.now()
        breakdown = {}
        for cam_id, state in self.coordinator.camera_state.items():
            count = sum(1 for e in state.motion_events if now - e.timestamp < timedelta(hours=24))
            if count > 0:
                breakdown[cam_id] = count
        return {"by_camera": breakdown}


class CameraPresenceHistorySensor(CopilotBaseEntity, SensorEntity):
    """Sensor for presence history across all cameras."""
    
    _attr_has_entity_name = True
    _attr_name = "Presence History"
    _attr_icon = "mdi:account-group"
    _attr_native_unit_of_measurement = "detections"
    
    def __init__(self, coordinator: CopilotCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = "ai_home_copilot_camera_presence_history"
        
    @property
    def native_value(self) -> int:
        """Return total presence detections in last 24h."""
        total = 0
        now = dt_util.now()
        for state in self.coordinator.camera_state.values():
            for event in state.presence_events:
                if now - event.timestamp < timedelta(hours=24):
                    total += 1
        return total
    
    @property
    def extra_state_attributes(self) -> dict | None:
        """Return presence types breakdown."""
        now = dt_util.now()
        breakdown = {}
        for cam_id, state in self.coordinator.camera_state.items():
            types = {}
            for e in state.presence_events:
                if now - e.timestamp < timedelta(hours=24):
                    types[e.presence_type] = types.get(e.presence_type, 0) + 1
            if types:
                breakdown[cam_id] = types
        return {"by_camera": breakdown}


class CameraActivityHistorySensor(CopilotBaseEntity, SensorEntity):
    """Sensor for activity history across all cameras."""
    
    _attr_has_entity_name = True
    _attr_name = "Activity History"
    _attr_icon = "mdi:animation-play"
    _attr_native_unit_of_measurement = "activities"
    
    def __init__(self, coordinator: CopilotCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = "ai_home_copilot_camera_activity_history"
        
    @property
    def native_value(self) -> int:
        """Return total activities in last 24h."""
        total = 0
        now = dt_util.now()
        for state in self.coordinator.camera_state.values():
            for event in state.activity_events:
                if now - event.timestamp < timedelta(hours=24):
                    total += 1
        return total
    
    @property
    def extra_state_attributes(self) -> dict | None:
        """Return activity types breakdown."""
        now = dt_util.now()
        breakdown = {}
        for cam_id, state in self.coordinator.camera_state.items():
            types = {}
            for e in state.activity_events:
                if now - e.timestamp < timedelta(hours=24):
                    types[e.activity_type] = types.get(e.activity_type, 0) + 1
            if types:
                breakdown[cam_id] = types
        return {"by_camera": breakdown}


class CameraZoneActivitySensor(CopilotBaseEntity, SensorEntity):
    """Sensor for zone activity across all cameras."""
    
    _attr_has_entity_name = True
    _attr_name = "Zone Activity"
    _attr_icon = "mdi:map-marker-multiple"
    _attr_native_unit_of_measurement = "events"
    
    def __init__(self, coordinator: CopilotCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = "ai_home_copilot_camera_zone_activity"
        
    @property
    def native_value(self) -> int:
        """Return total zone events in last 24h."""
        total = 0
        now = dt_util.now()
        for state in self.coordinator.camera_state.values():
            for event in state.zone_events:
                if now - event.timestamp < timedelta(hours=24):
                    total += 1
        return total
    
    @property
    def extra_state_attributes(self) -> dict | None:
        """Return zone breakdown."""
        now = dt_util.now()
        breakdown = {}
        for cam_id, state in self.coordinator.camera_state.items():
            zones = {}
            for e in state.zone_events:
                if now - e.timestamp < timedelta(hours=24):
                    zones[e.zone_name] = zones.get(e.zone_name, 0) + 1
            if zones:
                breakdown[cam_id] = zones
        return {"by_camera": breakdown}


class CameraPrivacySettings:
    """Manages camera privacy settings."""
    
    def __init__(self, hass: HomeAssistant, entry_id: str):
        self._hass = hass
        self._entry_id = entry_id
        self._face_blur_enabled = True
        self._local_processing_only = True
        self._retention_hours = 24
        
    @property
    def face_blur_enabled(self) -> bool:
        return self._face_blur_enabled
    
    @face_blur_enabled.setter
    def face_blur_enabled(self, value: bool):
        self._face_blur_enabled = value
        
    @property
    def local_processing_only(self) -> bool:
        return self._local_processing_only
    
    @local_processing_only.setter
    def local_processing_only(self, value: bool):
        self._local_processing_only = value
        
    @property
    def retention_hours(self) -> int:
        return self._retention_hours
    
    @retention_hours.setter
    def retention_hours(self, value: int):
        self._retention_hours = max(1, min(168, value))  # 1 hour to 1 week


# Export for use in coordinator
__all__ = [
    "MotionDetectionCamera",
    "PresenceCamera", 
    "ActivityCamera",
    "ZoneCamera",
    "CameraMotionHistorySensor",
    "CameraPresenceHistorySensor",
    "CameraActivityHistorySensor",
    "CameraZoneActivitySensor",
    "CameraState",
    "CameraMotionEvent",
    "CameraPresenceEvent",
    "CameraActivityEvent",
    "CameraZoneEvent",
    "CameraPrivacySettings",
    "SIGNAL_CAMERA_MOTION",
    "SIGNAL_CAMERA_PRESENCE",
    "SIGNAL_CAMERA_ACTIVITY",
    "SIGNAL_CAMERA_ZONE",
]
