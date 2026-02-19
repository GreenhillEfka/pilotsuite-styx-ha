"""Frigate NVR Bridge Module for AI Home CoPilot.

Optional bridge that connects Frigate NVR events to the PilotSuite ecosystem.
Discovers Frigate-generated entities in Home Assistant and forwards person/motion
detection events to CameraContextModule and the neural system.

Frigate creates these HA entities:
- binary_sensor.<camera>_person  (on/off when person detected)
- binary_sensor.<camera>_motion  (on/off when motion detected)
- sensor.<camera>_person_count   (number of persons)
- camera.<camera>                (camera entity)

This module is gracefully disabled when Frigate is not installed.
"""
from __future__ import annotations

import logging
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.helpers import entity_registry

from ...const import DOMAIN
from .module import CopilotModule

_LOGGER = logging.getLogger(__name__)

# Patterns for Frigate entity discovery
_PERSON_ENTITY_RE = re.compile(r"^binary_sensor\.(.+)_person$")
_MOTION_ENTITY_RE = re.compile(r"^binary_sensor\.(.+)_motion$")
_PERSON_COUNT_RE = re.compile(r"^sensor\.(.+)_person_count$")


@dataclass
class FrigateCameraInfo:
    """Information about a discovered Frigate camera."""

    camera_name: str  # e.g. "front_door"
    camera_entity: str  # camera.front_door
    has_person_detection: bool
    has_motion_detection: bool
    person_entity: str | None  # binary_sensor.front_door_person
    motion_entity: str | None  # binary_sensor.front_door_motion
    person_count_entity: str | None  # sensor.front_door_person_count


@dataclass
class DetectionEvent:
    """A single detection event from Frigate."""

    camera_name: str
    detection_type: str  # "person" / "motion"
    state: str  # "on" / "off"
    person_count: int
    timestamp: datetime
    confidence: float


class FrigateBridgeModule(CopilotModule):
    """Optional Frigate NVR integration for person/motion detection.

    Discovers Frigate camera entities and processes person/motion detection events.
    Forwards detected persons to PersonTrackingModule and CameraContextModule.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        super().__init__(hass, entry_id)
        self._hass = hass
        self._entry_id = entry_id
        self._frigate_cameras: dict[str, FrigateCameraInfo] = {}
        self._recent_detections: deque[DetectionEvent] = deque(maxlen=200)
        self._listeners: list[Any] = []
        self._enabled = False  # Only enable if Frigate entities found

    @property
    def name(self) -> str:
        return "Frigate Bridge"

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_setup(self) -> bool:
        """Discover Frigate entities and start listening.

        Returns True if at least one Frigate camera was found.
        """
        _LOGGER.info("Setting up Frigate Bridge Module")

        await self._discover_frigate_cameras()

        if not self._frigate_cameras:
            _LOGGER.info(
                "No Frigate entities found - Frigate Bridge stays disabled"
            )
            self._store_module_reference()
            return False

        self._enabled = True

        # Listen for state changes on Frigate entities
        self._listeners.append(
            self._hass.bus.async_listen(
                EVENT_STATE_CHANGED, self._on_state_changed
            )
        )

        self._store_module_reference()

        camera_names = [c.camera_name for c in self._frigate_cameras.values()]
        _LOGGER.info(
            "Frigate Bridge Module initialized with %d camera(s): %s",
            len(self._frigate_cameras),
            ", ".join(camera_names),
        )
        return True

    def _store_module_reference(self) -> None:
        """Store this module instance in hass.data for cross-module access."""
        self._hass.data.setdefault(DOMAIN, {})
        self._hass.data[DOMAIN].setdefault(self._entry_id, {})
        self._hass.data[DOMAIN][self._entry_id]["frigate_bridge_module"] = self

    async def async_shutdown(self) -> None:
        """Cleanup listeners on shutdown."""
        _LOGGER.info("Shutting down Frigate Bridge Module")
        self._enabled = False

        for listener in self._listeners:
            if listener:
                listener()
        self._listeners.clear()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def _discover_frigate_cameras(self) -> None:
        """Scan the entity registry for Frigate-style entities.

        Strategy:
        1. Collect all binary_sensor.*_person entities.
        2. For each, derive the camera name and check that camera.<name> exists.
        3. Also look for binary_sensor.*_motion and sensor.*_person_count.
        """
        er = entity_registry.async_get(self._hass)

        # Build sets of known camera entity_ids for quick lookup
        camera_entity_ids: set[str] = set()
        person_entities: dict[str, str] = {}  # camera_name -> entity_id
        motion_entities: dict[str, str] = {}
        person_count_entities: dict[str, str] = {}

        for eid in er.entities:
            if eid.startswith("camera."):
                camera_entity_ids.add(eid)

        # Also consider states (entities not yet in registry but with state)
        for state in self._hass.states.async_all("camera"):
            camera_entity_ids.add(state.entity_id)

        # Scan for person binary sensors
        for eid in er.entities:
            match = _PERSON_ENTITY_RE.match(eid)
            if match:
                person_entities[match.group(1)] = eid
                continue
            match = _MOTION_ENTITY_RE.match(eid)
            if match:
                motion_entities[match.group(1)] = eid
                continue
            match = _PERSON_COUNT_RE.match(eid)
            if match:
                person_count_entities[match.group(1)] = eid

        # Also check states for entities that might not be in the registry yet
        for state in self._hass.states.async_all("binary_sensor"):
            eid = state.entity_id
            if eid not in er.entities:
                match = _PERSON_ENTITY_RE.match(eid)
                if match:
                    person_entities.setdefault(match.group(1), eid)
                    continue
                match = _MOTION_ENTITY_RE.match(eid)
                if match:
                    motion_entities.setdefault(match.group(1), eid)

        for state in self._hass.states.async_all("sensor"):
            eid = state.entity_id
            if eid not in er.entities:
                match = _PERSON_COUNT_RE.match(eid)
                if match:
                    person_count_entities.setdefault(match.group(1), eid)

        # Build FrigateCameraInfo for each camera that has person OR motion detection
        # AND a corresponding camera.* entity exists
        candidate_names = set(person_entities.keys()) | set(motion_entities.keys())

        for cam_name in sorted(candidate_names):
            camera_eid = f"camera.{cam_name}"
            if camera_eid not in camera_entity_ids:
                _LOGGER.debug(
                    "Skipping '%s': no matching camera entity %s",
                    cam_name,
                    camera_eid,
                )
                continue

            person_eid = person_entities.get(cam_name)
            motion_eid = motion_entities.get(cam_name)
            count_eid = person_count_entities.get(cam_name)

            info = FrigateCameraInfo(
                camera_name=cam_name,
                camera_entity=camera_eid,
                has_person_detection=person_eid is not None,
                has_motion_detection=motion_eid is not None,
                person_entity=person_eid,
                motion_entity=motion_eid,
                person_count_entity=count_eid,
            )
            self._frigate_cameras[cam_name] = info
            _LOGGER.debug("Discovered Frigate camera: %s", info)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    @callback
    def _on_state_changed(self, event: Event) -> None:
        """Handle Frigate entity state changes."""
        if not self._enabled:
            return

        entity_id: str = event.data.get("entity_id", "")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        if not new_state or not old_state:
            return

        # Check for person detection
        person_match = _PERSON_ENTITY_RE.match(entity_id)
        if person_match:
            cam_name = person_match.group(1)
            if cam_name in self._frigate_cameras:
                self._handle_person_event(cam_name, new_state, old_state)
            return

        # Check for motion detection
        motion_match = _MOTION_ENTITY_RE.match(entity_id)
        if motion_match:
            cam_name = motion_match.group(1)
            if cam_name in self._frigate_cameras:
                self._handle_motion_event(cam_name, new_state, old_state)
            return

        # Check for person count changes
        count_match = _PERSON_COUNT_RE.match(entity_id)
        if count_match:
            cam_name = count_match.group(1)
            if cam_name in self._frigate_cameras:
                self._handle_person_count_change(cam_name, new_state, old_state)

    def _handle_person_event(
        self, camera_name: str, new_state: Any, old_state: Any
    ) -> None:
        """Handle binary_sensor.*_person state changes."""
        if new_state.state == old_state.state:
            return

        confidence = float(
            new_state.attributes.get("score", new_state.attributes.get("confidence", 1.0))
        )
        person_count = self._get_current_person_count(camera_name)

        detection = DetectionEvent(
            camera_name=camera_name,
            detection_type="person",
            state=new_state.state,
            person_count=person_count,
            timestamp=datetime.now(),
            confidence=confidence,
        )
        self._recent_detections.append(detection)

        if new_state.state == "on":
            _LOGGER.info(
                "Frigate: Person erkannt auf %s (count=%d, confidence=%.2f)",
                camera_name,
                person_count,
                confidence,
            )
        else:
            _LOGGER.debug(
                "Frigate: Person-Erkennung beendet auf %s",
                camera_name,
            )

        # Fire bus event for CameraContextModule
        self._fire_camera_event(
            camera_name=camera_name,
            detection_type="person",
            action="started" if new_state.state == "on" else "ended",
            confidence=confidence,
            person_count=person_count,
        )

    def _handle_motion_event(
        self, camera_name: str, new_state: Any, old_state: Any
    ) -> None:
        """Handle binary_sensor.*_motion state changes."""
        if new_state.state == old_state.state:
            return

        confidence = float(
            new_state.attributes.get("score", new_state.attributes.get("confidence", 1.0))
        )

        detection = DetectionEvent(
            camera_name=camera_name,
            detection_type="motion",
            state=new_state.state,
            person_count=0,
            timestamp=datetime.now(),
            confidence=confidence,
        )
        self._recent_detections.append(detection)

        if new_state.state == "on":
            _LOGGER.debug(
                "Frigate: Bewegung erkannt auf %s (confidence=%.2f)",
                camera_name,
                confidence,
            )
        else:
            _LOGGER.debug(
                "Frigate: Bewegung beendet auf %s",
                camera_name,
            )

        # Fire bus event for CameraContextModule
        self._fire_camera_event(
            camera_name=camera_name,
            detection_type="motion",
            action="started" if new_state.state == "on" else "ended",
            confidence=confidence,
            person_count=0,
        )

    def _handle_person_count_change(
        self, camera_name: str, new_state: Any, old_state: Any
    ) -> None:
        """Handle sensor.*_person_count state changes."""
        try:
            new_count = int(float(new_state.state))
        except (ValueError, TypeError):
            return

        try:
            old_count = int(float(old_state.state))
        except (ValueError, TypeError):
            old_count = 0

        if new_count == old_count:
            return

        _LOGGER.debug(
            "Frigate: Personenanzahl auf %s: %d -> %d",
            camera_name,
            old_count,
            new_count,
        )

        # Record a detection event for count changes
        detection = DetectionEvent(
            camera_name=camera_name,
            detection_type="person",
            state="on" if new_count > 0 else "off",
            person_count=new_count,
            timestamp=datetime.now(),
            confidence=1.0,
        )
        self._recent_detections.append(detection)

    def _fire_camera_event(
        self,
        camera_name: str,
        detection_type: str,
        action: str,
        confidence: float,
        person_count: int,
    ) -> None:
        """Fire an ai_home_copilot_camera_event for CameraContextModule."""
        camera_info = self._frigate_cameras.get(camera_name)
        camera_entity = camera_info.camera_entity if camera_info else f"camera.{camera_name}"

        event_data: dict[str, Any] = {
            "type": detection_type,
            "source": "frigate",
            "camera_id": camera_entity,
            "camera_name": camera_name,
            "action": action,
            "confidence": confidence,
            "person_count": person_count,
            "timestamp": datetime.now().isoformat(),
        }

        self._hass.bus.fire(f"{DOMAIN}_camera_event", event_data)

    def _get_current_person_count(self, camera_name: str) -> int:
        """Read the current person count from the sensor entity."""
        camera_info = self._frigate_cameras.get(camera_name)
        if not camera_info or not camera_info.person_count_entity:
            return 0

        state = self._hass.states.get(camera_info.person_count_entity)
        if not state:
            return 0

        try:
            return int(float(state.state))
        except (ValueError, TypeError):
            return 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_recent_detections(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent detection events for the dashboard.

        Args:
            limit: Maximum number of detections to return.

        Returns:
            List of detection dicts, newest first.
        """
        detections: list[dict[str, Any]] = []
        items = list(self._recent_detections)
        items.reverse()  # newest first

        for det in items[:limit]:
            detections.append(
                {
                    "camera_name": det.camera_name,
                    "detection_type": det.detection_type,
                    "state": det.state,
                    "person_count": det.person_count,
                    "timestamp": det.timestamp.isoformat(),
                    "confidence": det.confidence,
                    "relative_time": _format_relative_time(det.timestamp),
                }
            )
        return detections

    def get_frigate_cameras(self) -> list[dict[str, Any]]:
        """Return discovered Frigate cameras with current status.

        Returns:
            List of camera info dicts including live state.
        """
        cameras: list[dict[str, Any]] = []

        for cam_name, info in sorted(self._frigate_cameras.items()):
            # Read current states
            person_state = None
            motion_state = None
            person_count = 0

            if info.person_entity:
                s = self._hass.states.get(info.person_entity)
                person_state = s.state if s else None

            if info.motion_entity:
                s = self._hass.states.get(info.motion_entity)
                motion_state = s.state if s else None

            if info.person_count_entity:
                s = self._hass.states.get(info.person_count_entity)
                if s:
                    try:
                        person_count = int(float(s.state))
                    except (ValueError, TypeError):
                        person_count = 0

            cameras.append(
                {
                    "camera_name": cam_name,
                    "camera_entity": info.camera_entity,
                    "has_person_detection": info.has_person_detection,
                    "has_motion_detection": info.has_motion_detection,
                    "person_entity": info.person_entity,
                    "motion_entity": info.motion_entity,
                    "person_count_entity": info.person_count_entity,
                    "person_detected": person_state == "on",
                    "motion_detected": motion_state == "on",
                    "person_count": person_count,
                }
            )
        return cameras

    def get_context_for_llm(self) -> str:
        """Return LLM context about recent camera detections.

        Generates a German-language summary of the most recent detection per
        camera, suitable for injection into the LLM system prompt.

        Example output:
            'Kamera Haustuer: Person erkannt (vor 5 Min). Kamera Garten: Bewegung (vor 12 Min).'
        """
        if not self._enabled or not self._frigate_cameras:
            return ""

        # Gather the most recent detection per camera
        latest_by_camera: dict[str, DetectionEvent] = {}
        for det in self._recent_detections:
            existing = latest_by_camera.get(det.camera_name)
            if existing is None or det.timestamp > existing.timestamp:
                latest_by_camera[det.camera_name] = det

        if not latest_by_camera:
            # No detections yet -- report camera count only
            return (
                f"Frigate NVR: {len(self._frigate_cameras)} Kamera(s) verbunden, "
                "keine aktuellen Erkennungen."
            )

        parts: list[str] = []
        for cam_name in sorted(latest_by_camera.keys()):
            det = latest_by_camera[cam_name]
            display_name = cam_name.replace("_", " ").title()
            rel_time = _format_relative_time(det.timestamp)

            if det.detection_type == "person" and det.state == "on":
                if det.person_count > 1:
                    label = f"{det.person_count} Personen erkannt"
                else:
                    label = "Person erkannt"
            elif det.detection_type == "person" and det.state == "off":
                label = "Person nicht mehr sichtbar"
            elif det.detection_type == "motion" and det.state == "on":
                label = "Bewegung"
            elif det.detection_type == "motion" and det.state == "off":
                label = "Bewegung beendet"
            else:
                label = f"{det.detection_type} ({det.state})"

            parts.append(f"Kamera {display_name}: {label} ({rel_time})")

        return "Frigate NVR: " + ". ".join(parts) + "."

    # ------------------------------------------------------------------
    # CopilotModule lifecycle bridge
    # ------------------------------------------------------------------

    async def async_setup_entry(self, ctx: Any) -> None:
        """CopilotModule interface: set up via ModuleContext."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry_id
        await self.async_setup()

    async def async_unload_entry(self, ctx: Any) -> bool:
        """CopilotModule interface: unload via ModuleContext."""
        await self.async_shutdown()
        return True


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _format_relative_time(timestamp: datetime) -> str:
    """Format a timestamp as a German relative time string.

    Examples:
        'gerade eben', 'vor 5 Min', 'vor 1 Std', 'vor 3 Std'
    """
    now = datetime.now()
    delta = now - timestamp

    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "gerade eben"

    if total_seconds < 60:
        return "gerade eben"

    minutes = total_seconds // 60
    if minutes < 60:
        return f"vor {minutes} Min"

    hours = minutes // 60
    if hours < 24:
        return f"vor {hours} Std"

    days = hours // 24
    if days == 1:
        return "vor 1 Tag"
    return f"vor {days} Tagen"


# ----------------------------------------------------------------------
# Module-level getter
# ----------------------------------------------------------------------


def get_frigate_bridge(
    hass: HomeAssistant, entry_id: str
) -> FrigateBridgeModule | None:
    """Get the FrigateBridgeModule instance for a config entry.

    Returns None if the module has not been set up or Frigate is not installed.
    """
    data = hass.data.get(DOMAIN, {}).get(entry_id, {})
    return data.get("frigate_bridge_module")


__all__ = [
    "FrigateBridgeModule",
    "FrigateCameraInfo",
    "DetectionEvent",
    "get_frigate_bridge",
]
