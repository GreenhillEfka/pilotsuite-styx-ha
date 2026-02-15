"""HA Integration for AI Home CoPilot - Coordinator with Neural System."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_TOKEN
from .camera_entities import (
    CameraState,
    CameraMotionEvent,
    CameraPresenceEvent,
    CameraActivityEvent,
    CameraZoneEvent,
    CameraPrivacySettings,
)

_LOGGER = logging.getLogger(__name__)


class CopilotApiClient:
    """Client for Copilot Core API with neural system support."""
    
    def __init__(self, session, base_url: str, token: str):
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token = token
    
    async def async_get_status(self) -> Dict[str, Any]:
        """Get basic status."""
        url = f"{self._base_url}/api/v1/status"
        headers = {"Authorization": f"Bearer {self._token}"}
        
        async with self._session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise CopilotApiError(f"API error: {resp.status}")
            return await resp.json()
    
    async def async_get_mood(self) -> Dict[str, Any]:
        """Get current mood from neural system."""
        url = f"{self._base_url}/api/v1/neurons/mood"
        headers = {"Authorization": f"Bearer {self._token}"}
        
        try:
            async with self._session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # API returns {success: true, data: {...}}
                    # Extract the data part
                    return data.get("data", data)
        except Exception as e:
            _LOGGER.debug("Mood API not available: %s", e)
        return {"mood": "unknown", "confidence": 0.0}
    
    async def async_get_neurons(self) -> Dict[str, Any]:
        """Get all neuron states."""
        url = f"{self._base_url}/api/v1/neurons"
        headers = {"Authorization": f"Bearer {self._token}"}
        
        try:
            async with self._session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # API returns {success: true, data: {...}}
                    return data.get("data", data)
        except Exception as e:
            _LOGGER.debug("Neurons API not available: %s", e)
        return {"neurons": {}}
    
    async def async_evaluate_neurons(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate neural pipeline with HA states."""
        url = f"{self._base_url}/api/v1/neurons/evaluate"
        headers = {"Authorization": f"Bearer {self._token}"}
        
        try:
            async with self._session.post(url, json=context, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", data)
        except Exception as e:
            _LOGGER.warning("Neural evaluation failed: %s", e)
        return {}


class CopilotApiError(Exception):
    """API error."""
    pass


class CopilotDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator with neural system integration."""
    
    def __init__(self, hass: HomeAssistant, config: dict):
        self._hass = hass
        self._config = config
        session = async_get_clientsession(hass)
        
        host = str(config.get(CONF_HOST, ""))
        port = int(config.get(CONF_PORT, 0) or 0)
        base_url = f"http://{host}:{port}" if port else f"http://{host}"
        
        token = config.get(CONF_TOKEN, "")
        self.api = CopilotApiClient(session, base_url, token)
        
        # Camera state management
        self.camera_state: Dict[str, CameraState] = {}
        self.camera_privacy: Dict[str, CameraPrivacySettings] = {}
        
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=30),
        )
    
    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API."""
        try:
            # Get basic status
            status = await self.api.async_get_status()
            
            # Get mood from neural system
            mood_data = await self.api.async_get_mood()
            
            # Get neuron states
            neurons_data = await self.api.async_get_neurons()
            
            # Combine all data
            return {
                "ok": status.get("ok", True),
                "version": status.get("version", "unknown"),
                "mood": mood_data,
                "neurons": neurons_data.get("neurons", {}),
                "dominant_mood": mood_data.get("mood", "unknown"),
                "mood_confidence": mood_data.get("confidence", 0.0),
            }
        except Exception as err:
            _LOGGER.error("Error fetching Copilot data: %s", err)
            raise UpdateFailed(str(err)) from err
    
    @callback
    def async_get_mood(self) -> Dict[str, Any]:
        """Get cached mood data."""
        return self.data.get("mood", {}) if self.data else {}
    
    @callback
    def async_get_neurons(self) -> Dict[str, Any]:
        """Get cached neuron states."""
        return self.data.get("neurons", {}) if self.data else {}
    
    async def async_evaluate_with_states(self) -> Dict[str, Any]:
        """Evaluate neural pipeline with current HA states."""
        # Build context from HA states
        context = {
            "states": {},
            "time": {},
            "weather": {},
            "presence": {},
        }
        
        # Get relevant states
        entity_patterns = [
            "person.", "binary_sensor.", "sensor.temperature", 
            "sensor.humidity", "sensor.light", "sensor.illuminance",
            "weather.", "light.", "media_player."
        ]
        
        for entity_id in self._hass.states.async_entity_ids():
            for pattern in entity_patterns:
                if entity_id.startswith(pattern):
                    state = self._hass.states.get(entity_id)
                    if state:
                        context["states"][entity_id] = {
                            "state": state.state,
                            "attributes": dict(state.attributes)
                        }
                    break
        
        # Evaluate
        return await self.api.async_evaluate_neurons(context)
    
    # ========== Camera State Management ==========
    
    def register_camera(
        self,
        camera_id: str,
        camera_name: str,
        zones: list[str] | None = None,
        retention_hours: int = 24,
    ) -> CameraState:
        """Register a camera and return its state."""
        if camera_id not in self.camera_state:
            self.camera_state[camera_id] = CameraState(retention_hours=retention_hours)
            self.camera_privacy[camera_id] = CameraPrivacySettings(self._hass, camera_id)
            _LOGGER.info("Registered camera: %s (%s)", camera_name, camera_id)
        else:
            # Update retention
            self.camera_state[camera_id].retention_hours = retention_hours
        return self.camera_state[camera_id]
    
    def unregister_camera(self, camera_id: str) -> None:
        """Unregister a camera."""
        if camera_id in self.camera_state:
            del self.camera_state[camera_id]
            del self.camera_privacy[camera_id]
            _LOGGER.info("Unregistered camera: %s", camera_id)
    
    @callback
    def async_add_motion_event(
        self,
        camera_id: str,
        camera_name: str,
        confidence: float = 1.0,
        zone: str | None = None,
        thumbnail: str | None = None,
    ) -> None:
        """Add a motion event to a camera."""
        if camera_id not in self.camera_state:
            self.register_camera(camera_id, camera_name)
        
        state = self.camera_state[camera_id]
        event = CameraMotionEvent(
            camera_id=camera_id,
            camera_name=camera_name,
            timestamp=dt_util.now(),
            confidence=confidence,
            zone=zone,
            thumbnail=thumbnail,
        )
        state.motion_events.append(event)
        state.last_motion = event.timestamp
        state.is_motion_detected = True
        
        # Clean old events
        self._clean_old_events(camera_id)
        
        _LOGGER.debug("Motion detected: %s at %s", camera_id, event.timestamp)
    
    @callback
    def async_clear_motion(self, camera_id: str) -> None:
        """Clear motion detection for a camera."""
        if camera_id in self.camera_state:
            self.camera_state[camera_id].is_motion_detected = False
    
    @callback
    def async_add_presence_event(
        self,
        camera_id: str,
        camera_name: str,
        presence_type: str = "person",
        person_name: str | None = None,
        confidence: float = 1.0,
    ) -> None:
        """Add a presence event to a camera."""
        if camera_id not in self.camera_state:
            self.register_camera(camera_id, camera_name)
        
        state = self.camera_state[camera_id]
        event = CameraPresenceEvent(
            camera_id=camera_id,
            camera_name=camera_name,
            timestamp=dt_util.now(),
            presence_type=presence_type,
            person_name=person_name,
            confidence=confidence,
        )
        state.presence_events.append(event)
        state.last_presence = event.timestamp
        state.current_presence = presence_type
        
        # Clean old events
        self._clean_old_events(camera_id)
        
        _LOGGER.debug("Presence detected: %s - %s at %s", camera_id, presence_type, event.timestamp)
    
    @callback
    def async_add_activity_event(
        self,
        camera_id: str,
        camera_name: str,
        activity_type: str,
        duration_seconds: int = 0,
        confidence: float = 1.0,
    ) -> None:
        """Add an activity event to a camera."""
        if camera_id not in self.camera_state:
            self.register_camera(camera_id, camera_name)
        
        state = self.camera_state[camera_id]
        event = CameraActivityEvent(
            camera_id=camera_id,
            camera_name=camera_name,
            timestamp=dt_util.now(),
            activity_type=activity_type,
            duration_seconds=duration_seconds,
            confidence=confidence,
        )
        state.activity_events.append(event)
        
        # Clean old events
        self._clean_old_events(camera_id)
        
        _LOGGER.debug("Activity detected: %s - %s at %s", camera_id, activity_type, event.timestamp)
    
    @callback
    def async_add_zone_event(
        self,
        camera_id: str,
        camera_name: str,
        zone_name: str,
        event_type: str = "entered",
        object_type: str | None = None,
    ) -> None:
        """Add a zone event to a camera."""
        if camera_id not in self.camera_state:
            self.register_camera(camera_id, camera_name)
        
        state = self.camera_state[camera_id]
        event = CameraZoneEvent(
            camera_id=camera_id,
            camera_name=camera_name,
            timestamp=dt_util.now(),
            zone_name=zone_name,
            event_type=event_type,
            object_type=object_type,
        )
        state.zone_events.append(event)
        
        # Clean old events
        self._clean_old_events(camera_id)
        
        _LOGGER.debug("Zone event: %s - %s %s at %s", camera_id, zone_name, event_type, event.timestamp)
    
    def _clean_old_events(self, camera_id: str) -> None:
        """Clean old events based on retention policy."""
        if camera_id not in self.camera_state:
            return
        
        state = self.camera_state[camera_id]
        retention = timedelta(hours=state.retention_hours)
        now = dt_util.now()
        
        # Clean motion events
        state.motion_events = [
            e for e in state.motion_events
            if now - e.timestamp < retention
        ]
        
        # Clean presence events
        state.presence_events = [
            e for e in state.presence_events
            if now - e.timestamp < retention
        ]
        
        # Clean activity events
        state.activity_events = [
            e for e in state.activity_events
            if now - e.timestamp < retention
        ]
        
        # Clean zone events
        state.zone_events = [
            e for e in state.zone_events
            if now - e.timestamp < retention
        ]
        
        # Update 24h motion count
        state.motion_count_24h = sum(
            1 for e in state.motion_events
            if now - e.timestamp < timedelta(hours=24)
        )
    
    def get_camera_privacy(self, camera_id: str) -> CameraPrivacySettings | None:
        """Get privacy settings for a camera."""
        return self.camera_privacy.get(camera_id)
    
    def set_camera_face_blur(self, camera_id: str, enabled: bool) -> None:
        """Enable/disable face blur for a camera."""
        if camera_id in self.camera_privacy:
            self.camera_privacy[camera_id].face_blur_enabled = enabled
    
    def set_camera_retention(self, camera_id: str, hours: int) -> None:
        """Set retention hours for a camera."""
        if camera_id in self.camera_state:
            self.camera_state[camera_id].retention_hours = hours
            self._clean_old_events(camera_id)