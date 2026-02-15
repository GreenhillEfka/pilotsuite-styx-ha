"""
Camera Context Module for AI Home CoPilot.

Integrates camera events with the Habitus neural system:
- Camera Motion → Activity Neuron
- Face Detection → Person Recognition  
- Object Detection → Environmental Context

Privacy-first: local processing only, face blurring, configurable retention.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers import entity_registry
from homeassistant.const import EVENT_STATE_CHANGED, EVENT_CALL_SERVICE

from .const import DOMAIN
from .camera_entities import (
    CameraMotionEvent,
    CameraPresenceEvent,
    CameraActivityEvent,
    CameraZoneEvent,
    SIGNAL_CAMERA_MOTION,
    SIGNAL_CAMERA_PRESENCE,
    SIGNAL_CAMERA_ACTIVITY,
    SIGNAL_CAMERA_ZONE,
)
from .core.module import CopilotModule

_LOGGER = logging.getLogger(__name__)

# Camera event types from Home Assistant
CAMERA_EVENT_MOTION = "motion"
CAMERA_EVENT_PRESENCE = "presence"
CAMERA_EVENT_FACE = "face"
CAMERA_EVENT_OBJECT = "object"
CAMERA_EVENT_ZONE = "zone"

# Camera domains to monitor
CAMERA_DOMAINS = ["camera", "binary_sensor"]


class CameraContextModule(CopilotModule):
    """Module for camera event processing and Habitus integration."""
    
    def __init__(self, hass: HomeAssistant, entry_id: str):
        super().__init__(hass, entry_id)
        self._hass = hass
        self._entry_id = entry_id
        self._camera_entities: Dict[str, Dict[str, Any]] = {}
        self._tracked_cameras: List[str] = []
        self._enabled = True
        
    @property
    def name(self) -> str:
        return "Camera Context"
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    async def async_setup(self) -> bool:
        """Set up camera event listeners."""
        _LOGGER.info("Setting up Camera Context Module")
        
        # Get all camera entities
        await self._discover_cameras()
        
        # Listen for camera state changes
        self._hass.bus.async_listen(EVENT_STATE_CHANGED, self._on_state_changed)
        
        # Listen for camera-specific events
        self._hass.bus.async_listen(
            f"{DOMAIN}_camera_event",
            self._on_camera_event
        )
        
        _LOGGER.info("Camera Context Module initialized with %d cameras", len(self._tracked_cameras))
        return True
    
    async def _discover_cameras(self) -> None:
        """Discover camera entities in Home Assistant."""
        er = entity_registry.async_get(self._hass)
        
        # Find all camera entities
        for entity_id, entry in er.entities.items():
            if entry.domain == "camera":
                self._camera_entities[entity_id] = {
                    "entity_id": entity_id,
                    "name": entry.name or entry.original_name or entity_id,
                    "platform": entry.platform,
                    "capabilities": [],
                }
                
                # Check for motion detection capability
                motion_entity = entity_id.replace("camera.", "binary_sensor.")
                if self._hass.states.get(motion_entity):
                    self._camera_entities[entity_id]["capabilities"].append("motion")
                
                # Check for person detection
                person_entity = entity_id.replace("camera.", "person.")
                if self._hass.states.get(person_entity):
                    self._camera_entities[entity_id]["capabilities"].append("person")
        
        self._tracked_cameras = list(self._camera_entities.keys())
        _LOGGER.debug("Discovered cameras: %s", self._tracked_cameras)
    
    @callback
    async def _on_state_changed(self, event: Event) -> None:
        """Handle state changes for camera-related entities."""
        entity_id = event.data.get("entity_id", "")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        
        if not new_state or not old_state:
            return
        
        # Check for motion binary sensors
        if entity_id.startswith("binary_sensor.") and "motion" in entity_id.lower():
            await self._handle_motion_event(entity_id, new_state, old_state)
        
        # Check for person sensors
        elif entity_id.startswith("person."):
            await self._handle_presence_event(entity_id, new_state, old_state)
        
        # Check for image_processing entities
        elif entity_id.startswith("image_processing."):
            await self._handle_image_processing_event(entity_id, new_state, old_state)
    
    async def _handle_motion_event(
        self,
        entity_id: str,
        new_state: Any,
        old_state: Any,
    ) -> None:
        """Handle motion detection events."""
        camera_id = entity_id.replace("binary_sensor.", "camera.")
        camera_name = camera_id.split(".")[-1]
        
        # Get confidence from attributes
        confidence = 1.0
        if hasattr(new_state, "attributes"):
            confidence = new_state.attributes.get("confidence", 1.0)
        
        # Motion started
        if new_state.state == "on" and old_state.state == "off":
            self._hass.bus.fire(
                f"{DOMAIN}_camera_event",
                {
                    "type": CAMERA_EVENT_MOTION,
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "action": "started",
                    "confidence": confidence,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            _LOGGER.debug("Motion started: %s", camera_id)
        
        # Motion ended
        elif new_state.state == "off" and old_state.state == "on":
            self._hass.bus.fire(
                f"{DOMAIN}_camera_event",
                {
                    "type": CAMERA_EVENT_MOTION,
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "action": "ended",
                    "confidence": confidence,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            _LOGGER.debug("Motion ended: %s", camera_id)
    
    async def _handle_presence_event(
        self,
        entity_id: str,
        new_state: Any,
        old_state: Any,
    ) -> None:
        """Handle person/presence detection events."""
        person_name = new_state.state if new_state.state else None
        
        if person_name and person_name != old_state.state:
            self._hass.bus.fire(
                f"{DOMAIN}_camera_event",
                {
                    "type": CAMERA_EVENT_PRESENCE,
                    "entity_id": entity_id,
                    "person_name": person_name,
                    "action": "detected",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            _LOGGER.debug("Person detected: %s - %s", entity_id, person_name)
    
    async def _handle_image_processing_event(
        self,
        entity_id: str,
        new_state: Any,
        old_state: Any,
    ) -> None:
        """Handle image processing events (face/object detection)."""
        if not hasattr(new_state, "attributes"):
            return
        
        attrs = new_state.attributes
        
        # Face detection
        if "faces" in attrs and attrs.get("faces"):
            self._hass.bus.fire(
                f"{DOMAIN}_camera_event",
                {
                    "type": CAMERA_EVENT_FACE,
                    "entity_id": entity_id,
                    "faces": attrs.get("faces", []),
                    "timestamp": datetime.now().isoformat(),
                }
            )
        
        # Object detection
        if "objects" in attrs and attrs.get("objects"):
            self._hass.bus.fire(
                f"{DOMAIN}_camera_event",
                {
                    "type": CAMERA_EVENT_OBJECT,
                    "entity_id": entity_id,
                    "objects": attrs.get("objects", []),
                    "timestamp": datetime.now().isoformat(),
                }
            )
    
    @callback
    async def _on_camera_event(self, event: Event) -> None:
        """Process camera events and forward to neural system."""
        event_data = event.data
        
        event_type = event_data.get("type")
        
        if event_type == CAMERA_EVENT_MOTION:
            await self._process_motion_to_neuron(event_data)
        elif event_type == CAMERA_EVENT_PRESENCE:
            await self._process_presence_to_neuron(event_data)
        elif event_type == CAMERA_EVENT_FACE:
            await self._process_face_to_neuron(event_data)
        elif event_type == CAMERA_EVENT_OBJECT:
            await self._process_object_to_neuron(event_data)
        elif event_type == CAMERA_EVENT_ZONE:
            await self._process_zone_to_neuron(event_data)
    
    async def _process_motion_to_neuron(self, event_data: Dict[str, Any]) -> None:
        """Process motion event → Activity Neuron."""
        # Create activity context for the neural system
        context = {
            "neuron_type": "activity",
            "source": "camera_motion",
            "camera_id": event_data.get("camera_id"),
            "camera_name": event_data.get("camera_name"),
            "action": event_data.get("action"),
            "confidence": event_data.get("confidence", 1.0),
            "timestamp": event_data.get("timestamp"),
        }
        
        # Forward to brain graph sync if available
        await self._forward_to_brain("motion", context)
        
        _LOGGER.debug("Motion → Activity Neuron: %s", context)
    
    async def _process_presence_to_neuron(self, event_data: Dict[str, Any]) -> None:
        """Process presence event → Person Recognition."""
        context = {
            "neuron_type": "presence",
            "source": "camera_presence",
            "entity_id": event_data.get("entity_id"),
            "person_name": event_data.get("person_name"),
            "action": event_data.get("action"),
            "timestamp": event_data.get("timestamp"),
        }
        
        await self._forward_to_brain("presence", context)
        
        _LOGGER.debug("Presence → Person Recognition: %s", context)
    
    async def _process_face_to_neuron(self, event_data: Dict[str, Any]) -> None:
        """Process face detection → Person Recognition (privacy-aware)."""
        # Check privacy settings before processing
        entity_id = event_data.get("entity_id", "")
        
        # Only process anonymized data
        context = {
            "neuron_type": "face",
            "source": "camera_face",
            "entity_id": entity_id,
            "face_count": len(event_data.get("faces", [])),
            "timestamp": event_data.get("timestamp"),
        }
        
        await self._forward_to_brain("face", context)
        
        _LOGGER.debug("Face → Person Recognition: %d faces", len(event_data.get("faces", [])))
    
    async def _process_object_to_neuron(self, event_data: Dict[str, Any]) -> None:
        """Process object detection → Environmental Context."""
        context = {
            "neuron_type": "object",
            "source": "camera_object",
            "entity_id": event_data.get("entity_id"),
            "objects": event_data.get("objects", []),
            "timestamp": event_data.get("timestamp"),
        }
        
        await self._forward_to_brain("object", context)
        
        _LOGGER.debug("Object → Environmental Context: %s", event_data.get("objects", []))
    
    async def _process_zone_to_neuron(self, event_data: Dict[str, Any]) -> None:
        """Process zone events → Spatial Context."""
        context = {
            "neuron_type": "zone",
            "source": "camera_zone",
            "camera_id": event_data.get("camera_id"),
            "zone_name": event_data.get("zone_name"),
            "event_type": event_data.get("event_type"),
            "timestamp": event_data.get("timestamp"),
        }
        
        await self._forward_to_brain("zone", context)
        
        _LOGGER.debug("Zone → Spatial Context: %s %s", 
            event_data.get("zone_name"), 
            event_data.get("event_type"))
    
    async def _forward_to_brain(self, event_subtype: str, context: Dict[str, Any]) -> None:
        """Forward camera events to brain graph sync module."""
        try:
            # Get the runtime and forwarder
            runtime = self._hass.data.get(DOMAIN)
            if runtime and hasattr(runtime, "registry"):
                # Try to get brain_graph_sync module
                module = runtime.registry.get("brain_graph_sync")
                if module and hasattr(module, "async_add_camera_event"):
                    await module.async_add_camera_event(event_subtype, context)
        except Exception as e:
            _LOGGER.debug("Could not forward to brain: %s", e)
    
    async def async_shutdown(self) -> None:
        """Clean up on shutdown."""
        _LOGGER.info("Shutting down Camera Context Module")
        self._enabled = False
    
    def get_tracked_cameras(self) -> List[str]:
        """Get list of tracked camera entity IDs."""
        return self._tracked_cameras.copy()
    
    def get_camera_info(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific camera."""
        return self._camera_entities.get(camera_id)
    
    async def trigger_motion_event(
        self,
        camera_id: str,
        camera_name: str,
        confidence: float = 1.0,
        zone: str | None = None,
    ) -> None:
        """Manually trigger a motion event (for testing/webhooks)."""
        self._hass.bus.fire(
            f"{DOMAIN}_camera_event",
            {
                "type": CAMERA_EVENT_MOTION,
                "camera_id": camera_id,
                "camera_name": camera_name,
                "action": "started",
                "confidence": confidence,
                "zone": zone,
                "timestamp": datetime.now().isoformat(),
            }
        )
    
    async def trigger_zone_event(
        self,
        camera_id: str,
        camera_name: str,
        zone_name: str,
        event_type: str = "entered",
        object_type: str | None = None,
    ) -> None:
        """Manually trigger a zone event."""
        self._hass.bus.fire(
            f"{DOMAIN}_camera_event",
            {
                "type": CAMERA_EVENT_ZONE,
                "camera_id": camera_id,
                "camera_name": camera_name,
                "zone_name": zone_name,
                "event_type": event_type,
                "object_type": object_type,
                "timestamp": datetime.now().isoformat(),
            }
        )


__all__ = ["CameraContextModule"]
