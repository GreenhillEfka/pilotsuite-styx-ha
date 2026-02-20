"""PilotSuite — Coordinator with Neural System."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any
from dataclasses import dataclass, field

import aiohttp

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
    """Client for PilotSuite Core API with neural system support."""
    
    def __init__(self, session, base_url: str, token: str):
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token = token
    
    async def async_get_status(self) -> dict[str, Any]:
        """Get basic status."""
        url = f"{self._base_url}/api/v1/status"
        headers = {"Authorization": f"Bearer {self._token}"}

        async with self._session.get(url, headers=headers, timeout=10) as resp:
            if resp.status != 200:
                raise CopilotApiError(f"API error: {resp.status}")
            return await resp.json()

    async def async_get_mood(self) -> dict[str, Any]:
        """Get current mood from neural system."""
        url = f"{self._base_url}/api/v1/neurons/mood"
        headers = {"Authorization": f"Bearer {self._token}"}

        try:
            async with self._session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", data)
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            _LOGGER.debug("Mood API not available: %s", e)
        return {"mood": "unknown", "confidence": 0.0}

    async def async_get_neurons(self) -> dict[str, Any]:
        """Get all neuron states."""
        url = f"{self._base_url}/api/v1/neurons"
        headers = {"Authorization": f"Bearer {self._token}"}

        try:
            async with self._session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", data)
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            _LOGGER.debug("Neurons API not available: %s", e)
        return {"neurons": {}}

    async def async_chat_completions(
        self, messages: list[dict[str, str]], conversation_id: str | None = None
    ) -> dict[str, Any]:
        """Send a chat request to the Core Add-on via /v1/chat/completions."""
        url = f"{self._base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self._token}"}
        payload: dict[str, Any] = {"model": "pilotsuite", "messages": messages}
        if conversation_id:
            payload["conversation_id"] = conversation_id

        async with self._session.post(
            url, json=payload, headers=headers, timeout=20
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise CopilotApiError(
                    f"Chat API error {resp.status}: {body[:200]}"
                )
            data = await resp.json()
            choices = data.get("choices", [])
            content = ""
            if choices:
                content = choices[0].get("message", {}).get("content", "")
            return {"content": content, "conversation_id": conversation_id}

    async def async_evaluate_neurons(self, context: dict[str, Any]) -> dict[str, Any]:
        """Evaluate neural pipeline with HA states."""
        url = f"{self._base_url}/api/v1/neurons/evaluate"
        headers = {"Authorization": f"Bearer {self._token}"}

        try:
            async with self._session.post(url, json=context, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", data)
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            _LOGGER.warning("Neural evaluation failed: %s", e)
        return {}


class CopilotApiError(Exception):
    """API error."""
    pass


class CopilotDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator with neural system integration."""
    
    def __init__(self, hass: HomeAssistant, config: dict):
        self._config = config
        session = async_get_clientsession(hass)
        
        host = str(config.get(CONF_HOST, ""))
        port = int(config.get(CONF_PORT, 0) or 0)
        base_url = f"http://{host}:{port}" if port else f"http://{host}"
        
        token = config.get(CONF_TOKEN, "")
        self.api = CopilotApiClient(session, base_url, token)
        
        # Camera state management
        self.camera_state: dict[str, CameraState] = {}
        self.camera_privacy: dict[str, CameraPrivacySettings] = {}
        
        # Hybrid mode: 120s fallback polling (real-time via webhook push)
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=120),
        )
    
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API with retry on transient failures."""
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                status = await self.api.async_get_status()

                # Get mood from neural system
                mood_data = await self.api.async_get_mood()

                # Get neuron states
                neurons_data = await self.api.async_get_neurons()

                # Get habit learning data from ML context if available
                habit_data = await self._get_habit_learning_data()

                return {
                    "ok": status.get("ok", True),
                    "version": status.get("version", "unknown"),
                    "mood": mood_data,
                    "neurons": neurons_data.get("neurons", {}),
                    "dominant_mood": mood_data.get("mood", "unknown"),
                    "mood_confidence": mood_data.get("confidence", 0.0),
                    "habit_summary": habit_data.get("habit_summary", {}),
                    "predictions": habit_data.get("predictions", []),
                    "sequences": habit_data.get("sequences", []),
                }
            except (asyncio.TimeoutError, aiohttp.ClientError) as err:
                last_err = err
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)  # 1s, 2s backoff
                    _LOGGER.debug("Retrying PilotSuite API (attempt %d): %s", attempt + 1, err)
            except CopilotApiError as err:
                _LOGGER.error("PilotSuite API error: %s", err)
                raise UpdateFailed(str(err)) from err

        _LOGGER.warning("PilotSuite API unreachable after 3 attempts: %s", last_err)
        raise UpdateFailed(f"API timeout after retries: {last_err}") from last_err
    
    async def _get_habit_learning_data(self) -> dict[str, Any]:
        """Get habit learning data from ML context."""
        try:
            # Try to get ML context from hass.data
            entry_data = self.hass.data.get("ai_home_copilot", {})
            
            for entry_id, data in entry_data.items():
                ml_context = data.get("ml_context")
                if ml_context and ml_context.habit_predictor:
                    # Get habit summary
                    summary = ml_context.habit_predictor.get_habit_summary(hours=24)
                    
                    # Build predictions
                    predictions = []
                    for device_id, device_info in summary.get("device_patterns", {}).items():
                        for event_type in device_info.get("event_types", []):
                            pred = ml_context.get_habit_prediction(device_id, event_type)
                            if pred.get("predicted"):
                                predictions.append({
                                    "pattern": f"{device_id}:{event_type}",
                                    "confidence": pred.get("confidence", 0),
                                    "predicted": True,
                                    "details": pred.get("details", {}),
                                })
                    
                    # Build sequences
                    sequences = []
                    for start_device, seq_list in ml_context.habit_predictor.sequence_patterns.items():
                        if seq_list:
                            seq_pred = ml_context.habit_predictor.predict_sequence(start_device)
                            if seq_pred.get("predicted"):
                                sequences.append({
                                    "sequence": seq_pred.get("sequence", []),
                                    "confidence": seq_pred.get("confidence", 0),
                                    "occurrences": seq_pred.get("occurrences", 0),
                                    "predicted": True,
                                })
                    
                    return {
                        "habit_summary": {
                            "total_patterns": summary.get("total_patterns", 0),
                            "time_patterns": summary.get("time_patterns", {}),
                            "sequences": summary.get("sequences", {}),
                            "device_patterns": summary.get("device_patterns", {}),
                            "last_update": summary.get("last_update"),
                        },
                        "predictions": predictions,
                        "sequences": sequences,
                    }
        except Exception as e:
            _LOGGER.debug("Could not get habit learning data: %s", e)
        
        return {
            "habit_summary": {},
            "predictions": [],
            "sequences": [],
        }
    
    @callback
    def async_get_mood(self) -> dict[str, Any]:
        """Get cached mood data."""
        return self.data.get("mood", {}) if self.data else {}
    
    @callback
    def async_get_neurons(self) -> dict[str, Any]:
        """Get cached neuron states."""
        return self.data.get("neurons", {}) if self.data else {}
    
    async def async_evaluate_with_states(self) -> dict[str, Any]:
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
        
        for entity_id in self.hass.states.async_entity_ids():
            for pattern in entity_patterns:
                if entity_id.startswith(pattern):
                    state = self.hass.states.get(entity_id)
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
            self.camera_privacy[camera_id] = CameraPrivacySettings(self.hass, camera_id)
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