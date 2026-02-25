"""
Camera Context Module for PilotSuite.

Integrates camera events with the Habitus neural system:
- Camera Motion → Activity Neuron
- Face Detection → Person Recognition  
- Object Detection → Environmental Context

Privacy-first: local processing only, face blurring, configurable retention.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypedDict

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers import entity_registry
from homeassistant.const import EVENT_STATE_CHANGED

from ...const import DOMAIN
from ...module_connector import SIGNAL_ACTIVITY_UPDATED
from .module import CopilotModule

_LOGGER = logging.getLogger(__name__)


class CameraEventType(str, Enum):
    """Camera event types."""
    MOTION = "motion"
    PRESENCE = "presence"
    FACE = "face"
    OBJECT = "object"
    ZONE = "zone"


class MotionAction(str, Enum):
    """Motion detection actions."""
    STARTED = "started"
    ENDED = "ended"


class ZoneEventType(str, Enum):
    """Zone event types."""
    ENTERED = "entered"
    EXITED = "exited"


# Camera domains to monitor
CAMERA_DOMAINS = frozenset({"camera", "binary_sensor"})

# Entity prefixes to monitor
MOTION_SENSOR_PREFIXES = ("binary_sensor.",)
PERSON_SENSOR_PREFIXES = ("person",)
IMAGE_PROCESSING_PREFIXES = ("image_processing",)


class CameraCapabilities(TypedDict, total=False):
    """Camera capabilities."""
    motion: bool
    person: bool
    face: bool
    object: bool
    zone: bool


@dataclass(frozen=True)
class CameraInfo:
    """Camera information container."""
    entity_id: str
    name: str
    platform: str
    capabilities: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MotionEventData:
    """Motion event data."""
    camera_id: str
    camera_name: str
    action: MotionAction
    confidence: float = 1.0
    zone: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class PresenceEventData:
    """Presence event data."""
    entity_id: str
    person_name: str
    action: str = "detected"
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class ImageProcessingEventData:
    """Image processing event data."""
    entity_id: str
    faces: list[dict[str, Any]] = field(default_factory=list)
    objects: list[dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class CameraContextModule(CopilotModule):
    """Module for camera event processing and Habitus integration."""
    
    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._entry_id: str | None = None
        self._camera_entities: dict[str, CameraInfo] = {}
        self._tracked_cameras: list[str] = []
        self._enabled = True
        self._listeners: list[Any] = []
        self._forward_tasks: set[asyncio.Task] = set()

    @property
    def name(self) -> str:
        return "Camera Context"

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def async_setup_entry(self, ctx) -> None:
        """Set up the module for a config entry."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry_id
        await self._async_setup()

    async def async_unload_entry(self, ctx) -> bool:
        """Unload listeners."""
        for unsub in self._listeners:
            unsub()
        self._listeners.clear()

        if self._forward_tasks:
            for task in list(self._forward_tasks):
                task.cancel()
            await asyncio.gather(*list(self._forward_tasks), return_exceptions=True)
            self._forward_tasks.clear()
        return True

    async def _async_setup(self) -> bool:
        """Set up camera event listeners."""
        _LOGGER.info("Setting up Camera Context Module")
        
        # Get all camera entities
        await self._discover_cameras()
        
        # Listen for camera state changes
        self._listeners.append(
            self._hass.bus.async_listen(EVENT_STATE_CHANGED, self._on_state_changed)
        )
        
        # Listen for camera-specific events
        self._listeners.append(
            self._hass.bus.async_listen(
                f"{DOMAIN}_camera_event",
                self._on_camera_event
            )
        )
        
        _LOGGER.info(
            "Camera Context Module initialized with %d cameras",
            len(self._tracked_cameras)
        )
        return True
    
    async def _discover_cameras(self) -> None:
        """Discover camera entities in Home Assistant."""
        er = entity_registry.async_get(self._hass)
        
        # Find all camera entities
        for entity_id, entry in er.entities.items():
            if entry.domain != "camera":
                continue
                
            capabilities: list[str] = []
            
            # Check for motion detection capability (binary_sensor)
            motion_entity = f"binary_sensor.{entity_id.split('.', 1)[1]}"
            if self._hass.states.get(motion_entity):
                capabilities.append("motion")
            
            # Check for person detection
            person_entity = f"person.{entity_id.split('.', 1)[1]}"
            if self._hass.states.get(person_entity):
                capabilities.append("person")
            
            self._camera_entities[entity_id] = CameraInfo(
                entity_id=entity_id,
                name=entry.name or entry.original_name or entity_id,
                platform=entry.platform,
                capabilities=tuple(capabilities),
            )
        
        self._tracked_cameras = list(self._camera_entities.keys())
        _LOGGER.debug("Discovered cameras: %s", self._tracked_cameras)
    
    @callback
    def _on_state_changed(self, event: Event) -> None:
        """Handle state changes for camera-related entities."""
        entity_id = event.data.get("entity_id", "")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        
        if not new_state or not old_state:
            return
        
        # Check for motion binary sensors
        if entity_id.startswith(MOTION_SENSOR_PREFIXES) and "motion" in entity_id.lower():
            self._handle_motion_event(entity_id, new_state, old_state)
        
        # Check for person sensors
        elif entity_id.startswith(PERSON_SENSOR_PREFIXES):
            self._handle_presence_event(entity_id, new_state, old_state)
        
        # Check for image_processing entities
        elif entity_id.startswith(IMAGE_PROCESSING_PREFIXES):
            self._handle_image_processing_event(entity_id, new_state, old_state)
    
    def _handle_motion_event(
        self,
        entity_id: str,
        new_state: Any,
        old_state: Any,
    ) -> None:
        """Handle motion detection events."""
        camera_id = entity_id.replace("binary_sensor.", "camera.")
        camera_name = camera_id.split(".")[-1]
        
        # Get confidence from attributes
        confidence: float = 1.0
        if hasattr(new_state, "attributes"):
            confidence = new_state.attributes.get("confidence", 1.0)
        
        # Determine action based on state change
        if new_state.state == "on" and old_state.state == "off":
            action = MotionAction.STARTED
        elif new_state.state == "off" and old_state.state == "on":
            action = MotionAction.ENDED
        else:
            return
        
        self._hass.bus.fire(
            f"{DOMAIN}_camera_event",
            {
                "type": CameraEventType.MOTION,
                "camera_id": camera_id,
                "camera_name": camera_name,
                "action": action.value,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
            }
        )
        _LOGGER.debug("Motion %s: %s", action.value, camera_id)
    
    def _handle_presence_event(
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
                    "type": CameraEventType.PRESENCE,
                    "entity_id": entity_id,
                    "person_name": person_name,
                    "action": "detected",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            _LOGGER.debug("Person detected: %s - %s", entity_id, person_name)
    
    def _handle_image_processing_event(
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
        faces = attrs.get("faces", [])
        if faces:
            self._hass.bus.fire(
                f"{DOMAIN}_camera_event",
                {
                    "type": CameraEventType.FACE,
                    "entity_id": entity_id,
                    "faces": faces,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        
        # Object detection
        objects = attrs.get("objects", [])
        if objects:
            self._hass.bus.fire(
                f"{DOMAIN}_camera_event",
                {
                    "type": CameraEventType.OBJECT,
                    "entity_id": entity_id,
                    "objects": objects,
                    "timestamp": datetime.now().isoformat(),
                }
            )
    
    @callback
    def _on_camera_event(self, event: Event) -> None:
        """Process camera events and forward to neural system."""
        event_data: dict[str, Any] = event.data
        event_type = event_data.get("type")
        
        # Use match-case for cleaner event routing
        match event_type:
            case CameraEventType.MOTION:
                self._process_motion_to_neuron(event_data)
            case CameraEventType.PRESENCE:
                self._process_presence_to_neuron(event_data)
            case CameraEventType.FACE:
                self._process_face_to_neuron(event_data)
            case CameraEventType.OBJECT:
                self._process_object_to_neuron(event_data)
            case CameraEventType.ZONE:
                self._process_zone_to_neuron(event_data)
            case _:
                _LOGGER.warning("Unknown camera event type: %s", event_type)
    
    def _process_motion_to_neuron(self, event_data: dict[str, Any]) -> None:
        """Process motion event → Activity Neuron."""
        context: dict[str, Any] = {
            "neuron_type": "activity",
            "source": "camera_motion",
            "camera_id": event_data.get("camera_id"),
            "camera_name": event_data.get("camera_name"),
            "action": event_data.get("action"),
            "confidence": event_data.get("confidence", 1.0),
            "timestamp": event_data.get("timestamp"),
        }
        
        self._schedule_forward_to_brain("motion", context)
        _LOGGER.debug("Motion → Activity Neuron: %s", context)
    
    def _process_presence_to_neuron(self, event_data: dict[str, Any]) -> None:
        """Process presence event → Person Recognition."""
        context: dict[str, Any] = {
            "neuron_type": "presence",
            "source": "camera_presence",
            "entity_id": event_data.get("entity_id"),
            "person_name": event_data.get("person_name"),
            "action": event_data.get("action"),
            "timestamp": event_data.get("timestamp"),
        }
        
        self._schedule_forward_to_brain("presence", context)
        _LOGGER.debug("Presence → Person Recognition: %s", context)
    
    def _process_face_to_neuron(self, event_data: dict[str, Any]) -> None:
        """Process face detection → Person Recognition (privacy-aware)."""
        # Only process anonymized data
        context: dict[str, Any] = {
            "neuron_type": "face",
            "source": "camera_face",
            "entity_id": event_data.get("entity_id", ""),
            "face_count": len(event_data.get("faces", [])),
            "timestamp": event_data.get("timestamp"),
        }
        
        self._schedule_forward_to_brain("face", context)
        _LOGGER.debug(
            "Face → Person Recognition: %d faces",
            len(event_data.get("faces", []))
        )
    
    def _process_object_to_neuron(self, event_data: dict[str, Any]) -> None:
        """Process object detection → Environmental Context."""
        context: dict[str, Any] = {
            "neuron_type": "object",
            "source": "camera_object",
            "entity_id": event_data.get("entity_id"),
            "objects": event_data.get("objects", []),
            "timestamp": event_data.get("timestamp"),
        }
        
        self._schedule_forward_to_brain("object", context)
        _LOGGER.debug("Object → Environmental Context: %s", event_data.get("objects", []))
    
    def _process_zone_to_neuron(self, event_data: dict[str, Any]) -> None:
        """Process zone events → Spatial Context."""
        context: dict[str, Any] = {
            "neuron_type": "zone",
            "source": "camera_zone",
            "camera_id": event_data.get("camera_id"),
            "zone_name": event_data.get("zone_name"),
            "event_type": event_data.get("event_type"),
            "timestamp": event_data.get("timestamp"),
        }
        
        self._schedule_forward_to_brain("zone", context)
        _LOGGER.debug(
            "Zone → Spatial Context: %s %s",
            event_data.get("zone_name"),
            event_data.get("event_type")
        )

    def _schedule_forward_to_brain(
        self,
        event_subtype: str,
        context: dict[str, Any],
    ) -> None:
        """Run async forwarding without dropping coroutine execution."""
        if not self._hass:
            return
        task = self._hass.async_create_task(self._forward_to_brain(event_subtype, context))
        self._forward_tasks.add(task)

        def _on_done(done_task: asyncio.Task) -> None:
            self._forward_tasks.discard(done_task)
            try:
                done_task.result()
            except asyncio.CancelledError:
                return
            except Exception:
                _LOGGER.debug("Camera event forwarding task failed", exc_info=True)

        task.add_done_callback(_on_done)
    
    async def _forward_to_brain(
        self,
        event_subtype: str,
        context: dict[str, Any],
    ) -> None:
        """Forward camera events to brain graph sync module and neurons.

        Implements Camera → Activity Neuron connection:
        - Motion events → activity.level Neuron
        - Presence events → presence.room Neuron
        - Zone events → spatial context
        """
        # Forward to brain graph sync module (if available)
        await self._forward_to_brain_graph(event_subtype, context)
        
        # Forward to Module Connector for Activity/Presence Neuron update
        await self._forward_to_module_connector(event_subtype, context)
        
        # Fire activity update signal for direct neuron updates
        self._hass.bus.async_fire(
            SIGNAL_ACTIVITY_UPDATED,
            {
                "source": "camera",
                "event_subtype": event_subtype,
                "context": context,
            }
        )
    
    async def _forward_to_brain_graph(
        self,
        event_subtype: str,
        context: dict[str, Any],
    ) -> None:
        """Forward to brain graph sync module if available."""
        try:
            runtime = self._hass.data.get(DOMAIN)
            if runtime and hasattr(runtime, "registry"):
                module = runtime.registry.get("brain_graph_sync")
                if module and hasattr(module, "async_add_camera_event"):
                    await module.async_add_camera_event(event_subtype, context)
        except Exception as e:
            _LOGGER.debug("Could not forward to brain: %s", e)
    
    async def _forward_to_module_connector(
        self,
        event_subtype: str,
        context: dict[str, Any],
    ) -> None:
        """Forward events to module connector for Activity/Presence neurons."""
        try:
            from ...module_connector import get_module_connector
            
            connector = await get_module_connector(self._hass, self._entry_id)
            
            match event_subtype:
                case "motion":
                    await connector.async_handle_camera_motion({
                        "type": "motion",
                        "camera_id": context.get("camera_id"),
                        "camera_name": context.get("camera_name"),
                        "action": context.get("action"),
                        "confidence": context.get("confidence", 1.0),
                        "timestamp": context.get("timestamp"),
                    })
                case "presence":
                    await connector.async_handle_presence({
                        "type": "presence",
                        "entity_id": context.get("entity_id"),
                        "person_name": context.get("person_name"),
                        "action": context.get("action"),
                        "timestamp": context.get("timestamp"),
                    })
                case "zone":
                    await connector.async_handle_zone_event({
                        "type": "zone",
                        "camera_id": context.get("camera_id"),
                        "zone_name": context.get("zone_name"),
                        "event_type": context.get("event_type"),
                        "timestamp": context.get("timestamp"),
                    })
                    
        except ImportError as e:
            _LOGGER.debug("Module connector not available: %s", e)
        except AttributeError as e:
            _LOGGER.debug("Method not found on connector: %s", e)
        except Exception as e:
            _LOGGER.debug("Could not forward to module connector: %s", e)
    
    async def async_shutdown(self) -> None:
        """Clean up on shutdown."""
        _LOGGER.info("Shutting down Camera Context Module")
        self._enabled = False

        if self._forward_tasks:
            for task in list(self._forward_tasks):
                task.cancel()
            await asyncio.gather(*list(self._forward_tasks), return_exceptions=True)
            self._forward_tasks.clear()

        # Clean up listeners
        for listener in self._listeners:
            if listener:
                listener()
        self._listeners.clear()
    
    def get_tracked_cameras(self) -> list[str]:
        """Get list of tracked camera entity IDs."""
        return self._tracked_cameras.copy()
    
    def get_camera_info(self, camera_id: str) -> CameraInfo | None:
        """Get information about a specific camera."""
        return self._camera_entities.get(camera_id)
    
    def get_cameras_by_capability(self, capability: str) -> list[CameraInfo]:
        """Get all cameras with a specific capability."""
        return [
            cam for cam in self._camera_entities.values()
            if capability in cam.capabilities
        ]
    
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
                "type": CameraEventType.MOTION,
                "camera_id": camera_id,
                "camera_name": camera_name,
                "action": MotionAction.STARTED.value,
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
        event_type: str = ZoneEventType.ENTERED.value,
        object_type: str | None = None,
    ) -> None:
        """Manually trigger a zone event."""
        self._hass.bus.fire(
            f"{DOMAIN}_camera_event",
            {
                "type": CameraEventType.ZONE,
                "camera_id": camera_id,
                "camera_name": camera_name,
                "zone_name": zone_name,
                "event_type": event_type,
                "object_type": object_type,
                "timestamp": datetime.now().isoformat(),
            }
        )
    
    async def trigger_presence_event(
        self,
        person_entity_id: str,
        person_name: str,
    ) -> None:
        """Manually trigger a presence event."""
        self._hass.bus.fire(
            f"{DOMAIN}_camera_event",
            {
                "type": CameraEventType.PRESENCE,
                "entity_id": person_entity_id,
                "person_name": person_name,
                "action": "detected",
                "timestamp": datetime.now().isoformat(),
            }
        )


__all__ = [
    "CameraContextModule",
    "CameraEventType",
    "MotionAction",
    "ZoneEventType",
    "CameraInfo",
    "MotionEventData",
    "PresenceEventData",
]
