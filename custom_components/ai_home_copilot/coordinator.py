"""PilotSuite — Coordinator with Neural System."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import json
import logging
from typing import Any
import re

import aiohttp

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_TOKEN, DEFAULT_PORT
from .api import (
    CopilotApiClient as SharedCopilotApiClient,
    CopilotApiError,
    CopilotStatus,
)
from .connection_config import resolve_core_connection_from_mapping
from .core_endpoint import build_base_url, build_candidate_hosts
from .camera_entities import (
    CameraState,
    CameraMotionEvent,
    CameraPresenceEvent,
    CameraActivityEvent,
    CameraZoneEvent,
    CameraPrivacySettings,
)

_LOGGER = logging.getLogger(__name__)
CHAT_COMPLETIONS_TIMEOUT_S = 90.0


def _extract_http_status(err: CopilotApiError) -> int | None:
    match = re.match(r"^HTTP\s+(\d+)\s+for\s+", str(err))
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _should_failover(err: CopilotApiError) -> bool:
    message = str(err)
    if message.startswith("Timeout calling ") or message.startswith("Client error calling "):
        return True
    if message.startswith("Unexpected content type ") or message.startswith("Invalid JSON from "):
        return True

    status = _extract_http_status(err)
    if status is None:
        return False

    # Wrong endpoint or transport issues should trigger fallback.
    # Do not fail over on auth failures: that usually indicates token issues,
    # and trying random hosts (e.g. host.docker.internal) only adds noise.
    return status in {404, 405, 408, 429} or status >= 500


class CopilotApiClient(SharedCopilotApiClient):
    """Coordinator-facing API client with endpoint failover + legacy helpers."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        base_urls: list[str],
        token: str,
    ) -> None:
        primary = (base_urls[0] if base_urls else "").rstrip("/")
        super().__init__(session, primary, token)
        self._base_urls = [u.rstrip("/") for u in base_urls if u]
        if not self._base_urls:
            self._base_urls = [primary]
        self._active_base_url = self._base_urls[0]

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict | None = None,
        params: dict | None = None,
        timeout_s: float = 10.0,
    ) -> dict:
        normalized_path = path if path.startswith("/") else f"/{path}"
        last_err: CopilotApiError | None = None

        for idx, base_url in enumerate(self._base_urls):
            url = f"{base_url}{normalized_path}"
            try:
                async with self._session.request(
                    method,
                    url,
                    json=payload,
                    params=params,
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=timeout_s),
                ) as resp:
                    if resp.status >= 400:
                        body = await resp.text()
                        raise CopilotApiError(f"HTTP {resp.status} for {url}: {body[:200]}")

                    ctype = (resp.headers.get("Content-Type", "") or "").lower()
                    if resp.status == 204:
                        data: dict = {}
                    else:
                        body = await resp.text()
                        if "json" not in ctype:
                            raise CopilotApiError(
                                f"Unexpected content type '{ctype or 'unknown'}' for {url}: {body[:200]}"
                            )
                        try:
                            parsed = json.loads(body) if body else {}
                        except json.JSONDecodeError as json_err:
                            raise CopilotApiError(
                                f"Invalid JSON from {url}: {body[:200]}"
                            ) from json_err
                        data = parsed if isinstance(parsed, dict) else {"data": parsed}

                    if base_url != self._active_base_url:
                        _LOGGER.warning(
                            "PilotSuite API failover: switched endpoint from %s to %s",
                            self._active_base_url,
                            base_url,
                        )
                    self._active_base_url = base_url
                    self._base_url = base_url
                    return data
            except asyncio.TimeoutError as err:
                last_err = CopilotApiError(f"Timeout calling {url}")
                if idx < len(self._base_urls) - 1:
                    continue
                raise last_err from err
            except aiohttp.ClientError as err:
                last_err = CopilotApiError(f"Client error calling {url}: {err}")
                if idx < len(self._base_urls) - 1:
                    continue
                raise last_err from err
            except CopilotApiError as err:
                last_err = err
                if idx < len(self._base_urls) - 1 and _should_failover(err):
                    continue
                raise

        raise last_err or CopilotApiError("No available Core API endpoint")

    async def async_get(self, path: str, params: dict | None = None) -> dict:
        return await self._request_json("GET", path, params=params, timeout_s=10.0)

    async def async_post(self, path: str, payload: dict) -> dict:
        return await self._request_json("POST", path, payload=payload, timeout_s=10.0)

    async def async_put(self, path: str, payload: dict) -> dict:
        return await self._request_json("PUT", path, payload=payload, timeout_s=10.0)

    async def async_get_status(self) -> CopilotStatus:
        health: dict | None = None
        version: dict | None = None

        ok: bool | None = None
        ver: str | None = None

        try:
            health = await self.async_get("/health")
            ok_val = health.get("ok")
            ok = bool(ok_val) if ok_val is not None else None
        except CopilotApiError:
            ok = None

        try:
            version = await self.async_get("/version")
            if isinstance(version.get("version"), str):
                ver = version["version"]
            elif isinstance(version.get("data"), dict) and isinstance(version["data"].get("version"), str):
                ver = version["data"]["version"]
        except CopilotApiError:
            ver = None

        return CopilotStatus(ok=ok, version=ver)

    async def async_get_mood(self) -> dict[str, Any]:
        """Get current mood from neural system."""
        try:
            data = await self.async_get("/api/v1/neurons/mood")
            return data.get("data", data)
        except CopilotApiError as e:
            _LOGGER.debug("Mood API not available: %s", e)
        return {"mood": "unknown", "confidence": 0.0}

    async def async_get_neurons(self) -> dict[str, Any]:
        """Get all neuron states."""
        try:
            data = await self.async_get("/api/v1/neurons")
            return data.get("data", data)
        except CopilotApiError as e:
            _LOGGER.debug("Neurons API not available: %s", e)
        return {"neurons": {}}

    async def async_chat_completions(
        self, messages: list[dict[str, str]], conversation_id: str | None = None
    ) -> dict[str, Any]:
        """Send a chat request to the Core Add-on via /v1/chat/completions."""
        payload: dict[str, Any] = {"model": "pilotsuite", "messages": messages}
        if conversation_id:
            payload["conversation_id"] = conversation_id

        data = await self._request_json(
            "POST",
            "/v1/chat/completions",
            payload=payload,
            # qwen3:4b on HA-class hardware often needs >20s for first tokens.
            timeout_s=CHAT_COMPLETIONS_TIMEOUT_S,
        )
        choices = data.get("choices", [])
        content = ""
        if choices:
            content = choices[0].get("message", {}).get("content", "")
        return {"content": content, "conversation_id": conversation_id}

    async def async_evaluate_neurons(self, context: dict[str, Any]) -> dict[str, Any]:
        """Evaluate neural pipeline with HA states."""
        try:
            data = await self.async_post("/api/v1/neurons/evaluate", context)
            return data.get("data", data)
        except CopilotApiError as e:
            _LOGGER.warning("Neural evaluation failed: %s", e)
        return {}

    @staticmethod
    def _normalize_v1_path(path: str) -> str:
        p = path.strip()
        if p.startswith("/"):
            return p
        if p.startswith("api/") or p.startswith("v1/"):
            return f"/{p}"
        return f"/api/v1/{p}"

    async def get_with_auth(self, path: str, params: dict | None = None) -> dict:
        return await self.async_get(self._normalize_v1_path(path), params=params)

    async def post_with_auth(self, path: str, data: dict | None = None) -> dict:
        return await self.async_post(self._normalize_v1_path(path), payload=data or {})

    async def put_with_auth(self, path: str, data: dict | None = None) -> dict:
        return await self.async_put(self._normalize_v1_path(path), payload=data or {})

    async def async_get_core_modules(self) -> dict[str, str]:
        """Return Core module states from /api/v1/modules/."""
        try:
            data = await self.async_get("/api/v1/modules/")
            return data.get("modules", {})
        except CopilotApiError as e:
            _LOGGER.debug("Core modules API not available: %s", e)
        return {}

    async def async_configure_core_module(self, module_id: str, state: str) -> dict:
        """Set the state of a Core module via /api/v1/modules/<id>/configure."""
        return await self.async_post(
            f"/api/v1/modules/{module_id}/configure",
            {"state": state},
        )

    async def async_get_brain_summary(self) -> dict:
        """Return Brain Graph summary from /api/v1/dashboard/brain-summary."""
        try:
            return await self.async_get("/api/v1/dashboard/brain-summary")
        except CopilotApiError as e:
            _LOGGER.debug("Brain summary not available: %s", e)
        return {}

    async def async_get_habitus_rules_summary(self) -> dict:
        """Return Habitus rules summary from /api/v1/habitus/rules/summary."""
        try:
            return await self.get_with_auth("habitus/rules/summary")
        except CopilotApiError as e:
            _LOGGER.debug("Habitus rules summary not available: %s", e)
        return {}

    async def async_get_automation_suggestions(self) -> dict:
        """Return automation suggestions from /api/v1/habitus/dashboard_cards/rules."""
        try:
            return await self.async_get("/api/v1/habitus/dashboard_cards/rules?min_confidence=0.7&limit=10")
        except CopilotApiError as e:
            _LOGGER.debug("Automation suggestions not available: %s", e)
        return {}

    async def async_get_rag_status(self) -> dict[str, Any]:
        """Return RAG status from Core API (best effort)."""
        try:
            data = await self.async_get("/api/v1/rag/status")
            if isinstance(data.get("rag"), dict):
                return data.get("rag", {})
            return data
        except CopilotApiError as e:
            _LOGGER.debug("RAG status API not available: %s", e)
        return {}


class CopilotDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator with neural system integration."""
    
    def __init__(self, hass: HomeAssistant, config: dict):
        self._config = config
        session = async_get_clientsession(hass)

        host, port, token = resolve_core_connection_from_mapping(config)
        self._config[CONF_HOST] = host
        self._config[CONF_PORT] = port
        self._config[CONF_TOKEN] = token

        candidate_hosts = build_candidate_hosts(
            host,
            internal_url=getattr(hass.config, "internal_url", None),
            external_url=getattr(hass.config, "external_url", None),
            include_docker_internal=host == "host.docker.internal",
        )
        port_candidates = [port]
        if DEFAULT_PORT not in port_candidates:
            port_candidates.append(DEFAULT_PORT)
        candidate_urls: list[str] = []
        for candidate_host in candidate_hosts:
            for candidate_port in port_candidates:
                url = build_base_url(candidate_host, candidate_port)
                if url not in candidate_urls:
                    candidate_urls.append(url)

        self.api = CopilotApiClient(
            session,
            base_urls=candidate_urls,
            token=token,
        )
        
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

                # Get Core module states (best-effort, non-blocking)
                core_modules = await self.api.async_get_core_modules()

                # Get Brain Graph summary (best-effort)
                brain_summary = await self.api.async_get_brain_summary()

                # Get Habitus rules summary (best-effort)
                habitus_rules = await self.api.async_get_habitus_rules_summary()

                # Get RAG status (best-effort)
                rag_status = await self.api.async_get_rag_status()

                # Get habit learning data from ML context if available
                habit_data = await self._get_habit_learning_data()

                return {
                    "ok": bool(status.ok) if status.ok is not None else True,
                    "version": status.version or "unknown",
                    "mood": mood_data,
                    "neurons": neurons_data.get("neurons", {}),
                    "dominant_mood": mood_data.get("mood", "unknown"),
                    "mood_confidence": mood_data.get("confidence", 0.0),
                    "habit_summary": habit_data.get("habit_summary", {}),
                    "predictions": habit_data.get("predictions", []),
                    "sequences": habit_data.get("sequences", []),
                    "core_modules": core_modules,
                    "brain_summary": brain_summary,
                    "habitus_rules": habitus_rules,
                    "rag_status": rag_status,
                }
            except CopilotApiError as err:
                last_err = err
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)  # 1s, 2s backoff
                    _LOGGER.debug("Retrying PilotSuite API (attempt %d): %s", attempt + 1, err)
                continue
                # fallthrough prevented by continue
            except Exception as err:  # noqa: BLE001
                last_err = err
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    _LOGGER.debug(
                        "Retrying PilotSuite API after unexpected error (attempt %d): %s",
                        attempt + 1,
                        err,
                    )
                    continue
                break

        if last_err is None:
            last_err = RuntimeError("unknown API error")
        _LOGGER.warning("PilotSuite API unreachable after 3 attempts: %s", last_err)
        raise UpdateFailed(f"API unavailable after retries: {last_err}") from last_err
    
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
