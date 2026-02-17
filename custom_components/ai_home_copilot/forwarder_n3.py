"""N3 Specification Event Forwarder for AI Home CoPilot.

Implements the privacy-first envelope format per N3 Worker specification:
- Stable schema with version field for Core evolution
- Minimal attribute projections by domain
- Privacy redaction (GPS, tokens, context IDs)
- Zone enrichment from HA area registry
- Batching and persistence for reliability
"""
import asyncio
import hashlib
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set

import aiohttp
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.const import EVENT_STATE_CHANGED, EVENT_CALL_SERVICE

from .const import DOMAIN
from .core.performance import get_entity_cache, DomainFilter, TTLCache

_LOGGER = logging.getLogger(__name__)

# Schema version for N3 envelope format
ENVELOPE_VERSION = 1

# Attribute projections by domain (N3 specification)
DOMAIN_PROJECTIONS = {
    "light": {"brightness", "color_temp", "rgb_color", "hs_color", "color_mode"},
    "climate": {"temperature", "current_temperature", "hvac_action", "humidity"},
    "media_player": {"media_content_type", "media_title", "media_artist", "source", "volume_level"},
    "binary_sensor": {"device_class"},
    "sensor": {"unit_of_measurement", "device_class", "state_class"},
    "cover": {"current_position", "current_tilt_position"},
    "lock": {"device_class"},
    "person": {"source_type"},
    "device_tracker": {"source_type"},
    "weather": {"temperature", "humidity", "pressure", "wind_speed", "condition"},
}

# Attributes that should always be redacted for privacy (N3 specification)
REDACTED_ATTRIBUTES = {
    "entity_picture", "media_image_url", "media_image_remotely_accessible",
    "latitude", "longitude", "gps_accuracy", "access_token", "token"
}

# Regex pattern for sensitive keys (tokens, secrets, etc.)
SENSITIVE_KEY_PATTERN = re.compile(r'(token|key|secret|password)', re.IGNORECASE)

# Allowed call_service domains for intent forwarding
ALLOWED_CALL_SERVICE_DOMAINS = {
    "light", "media_player", "climate", "cover", "lock", "switch", "scene", "script"
}

# Blocked domains that should never be forwarded
BLOCKED_CALL_SERVICE_DOMAINS = {
    "notify", "rest_command", "shell_command", "tts"
}

# Default debounce intervals by domain (seconds)
DEFAULT_DEBOUNCE_INTERVALS = {
    "sensor": 1.0,
    "binary_sensor": 0.5,
}


class N3EventForwarder:
    """N3 specification-compliant event forwarder."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        self.hass = hass
        self.config = config
        self._store = Store(hass, 1, f"{DOMAIN}_n3_forwarder")
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Event queue and processing
        self._pending_events: List[Dict[str, Any]] = []
        self._flush_task: Optional[asyncio.Task] = None
        self._debounce_cache: Dict[str, float] = {}  # entity_id -> last_sent_time
        self._seen_events: Dict[str, float] = {}  # context_id -> expires_at
        
        # Zone mapping
        self._entity_to_zone: Dict[str, str] = {}
        
        # Performance: Entity state cache
        self._entity_cache = get_entity_cache()

        # User context tracking (local-only; never forwarded to Core)
        self._last_user_actions_by_zone: Dict[str, Dict[str, Any]] = {}
        self._user_presence_by_zone: Dict[str, Dict[str, float]] = {}
        self._user_last_zone_by_user: Dict[str, str] = {}
        
        # State listeners
        self._unsub_state_listener = None
        self._unsub_call_service_listener = None
        
        # Configuration
        self._core_url = config.get("core_url", "http://localhost:8909")
        self._api_token = config.get("api_token", "")
        self._batch_size = config.get("batch_size", 50)
        self._flush_interval = config.get("flush_interval", 0.5)
        self._max_queue_size = config.get("max_queue_size", 1000)
        
        # Heartbeat configuration
        self._heartbeat_interval = config.get("heartbeat_interval", 60)  # seconds
        self._heartbeat_enabled = config.get("heartbeat_enabled", True)
        
        # Enabled domains
        self._enabled_domains = set(config.get("enabled_domains", list(DOMAIN_PROJECTIONS.keys())))
        
        # Forward call_service events
        self._forward_call_service = config.get("forward_call_service", True)
        
        # Redaction settings
        redaction_config = config.get("redaction", {})
        self._keep_friendly_names = redaction_config.get("keep_friendly_names", False)
        self._keep_full_context_ids = redaction_config.get("keep_full_context_ids", False)
        self._extra_redact_attrs = set(redaction_config.get("extra_strip", []))
        
        # Debounce settings
        debounce_config = config.get("debounce", {})
        self._debounce_intervals = DEFAULT_DEBOUNCE_INTERVALS.copy()
        self._debounce_intervals.update(debounce_config)
        
        # Idempotency TTL (seconds)
        self._idempotency_ttl = config.get("idempotency_ttl", 120)

    async def async_start(self):
        """Start the N3 event forwarder."""
        _LOGGER.info("Starting AI Home CoPilot N3 Event Forwarder")
        
        # Load persistent queue
        await self._load_persistent_state()
        
        # Build zone mapping from HA registries
        await self._build_zone_mapping()
        
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=10)
        self._session = aiohttp.ClientSession(timeout=timeout)
        
        # Start event listeners
        self._start_event_listeners()
        
        # Start flush task
        self._flush_task = asyncio.create_task(self._flush_loop())
        
        # Start heartbeat task if enabled
        self._heartbeat_task = None
        if self._heartbeat_enabled and self._heartbeat_interval > 0:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        _LOGGER.info("N3 Event Forwarder started successfully")

    async def async_stop(self):
        """Stop the N3 event forwarder."""
        _LOGGER.info("Stopping AI Home CoPilot N3 Event Forwarder")
        
        # Stop event listeners
        if self._unsub_state_listener:
            self._unsub_state_listener()
            self._unsub_state_listener = None
            
        if self._unsub_call_service_listener:
            self._unsub_call_service_listener()
            self._unsub_call_service_listener = None
        
        # Cancel background tasks
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
                
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Flush any pending events
        if self._pending_events:
            await self._flush_events()
        
        # Save state
        await self._save_persistent_state()
        
        # Close HTTP session
        if self._session:
            await self._session.close()
            self._session = None
            
        _LOGGER.info("N3 Event Forwarder stopped")

    def _start_event_listeners(self):
        """Start HA event listeners."""
        # Listen for state changes on all entities
        self._unsub_state_listener = async_track_state_change_event(
            self.hass, None, self._handle_state_change_event
        )
        
        # Listen for call_service events if enabled
        if self._forward_call_service:
            self._unsub_call_service_listener = self.hass.bus.async_listen(
                EVENT_CALL_SERVICE, self._handle_call_service_event
            )

    async def _handle_state_change_event(self, event: Event):
        """Handle HA state_changed event and create N3 envelope."""
        if event.event_type != EVENT_STATE_CHANGED:
            return
            
        event_data = event.data
        entity_id = event_data.get("entity_id")
        if not entity_id:
            return
            
        # Extract domain
        domain = entity_id.split(".", 1)[0]
        if domain not in self._enabled_domains:
            return
        
        old_state = event_data.get("old_state")
        new_state = event_data.get("new_state")
        if not new_state:
            return
            
        # Skip if state didn't actually change
        old_state_value = old_state.state if old_state else None
        new_state_value = new_state.state
        if old_state_value == new_state_value:
            return
        
        # Apply debounce
        if not self._should_forward_entity(entity_id, domain):
            return
        
        # Check idempotency
        context_id = self._extract_context_id(event)
        if context_id and not self._is_event_new(f"state_changed:{context_id}"):
            return
        
        # Create N3 envelope
        envelope = self._create_state_change_envelope(
            entity_id, domain, old_state, new_state, event
        )
        
        if envelope:
            self._track_user_action_from_event(
                event=event,
                zone_ids=[envelope.get("zone_id")],
                entity_id=entity_id,
                kind="state_changed",
            )
            await self._enqueue_event(envelope)

    async def _handle_call_service_event(self, event: Event):
        """Handle HA call_service event for intent forwarding."""
        if event.event_type != EVENT_CALL_SERVICE:
            return
            
        event_data = event.data
        domain = event_data.get("domain", "")
        service = event_data.get("service", "")
        service_data = event_data.get("service_data", {})
        
        # Security checks
        if domain in BLOCKED_CALL_SERVICE_DOMAINS:
            return
            
        if domain not in ALLOWED_CALL_SERVICE_DOMAINS:
            return
        
        # Extract target entity IDs
        entity_ids = self._extract_entity_ids_from_service_data(service_data)
        if not entity_ids:
            return
        
        # Filter to entities we're tracking
        tracked_entities = [eid for eid in entity_ids if eid.split(".", 1)[0] in self._enabled_domains]
        if not tracked_entities:
            return
        
        # Check idempotency
        context_id = self._extract_context_id(event)
        if context_id and not self._is_event_new(f"call_service:{context_id}"):
            return
        
        # Create N3 envelope for call_service
        envelope = self._create_call_service_envelope(
            domain, service, tracked_entities, event
        )
        
        if envelope:
            self._track_user_action_from_event(
                event=event,
                zone_ids=envelope.get("zone_ids") or [],
                entity_id=entity_ids[0] if entity_ids else None,
                kind="call_service",
            )
            await self._enqueue_event(envelope)

    def _create_state_change_envelope(
        self, entity_id: str, domain: str, old_state, new_state, event: Event
    ) -> Dict[str, Any]:
        """Create N3 specification envelope for state_changed event."""
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        envelope = {
            "v": ENVELOPE_VERSION,
            "ts": now_utc,
            "src": "ha",
            "kind": "state_changed",
            "entity_id": entity_id,
            "domain": domain,
            "zone_id": self._get_zone_for_entity(entity_id, domain, new_state),
        }
        
        # Add timing from HA state object
        if hasattr(new_state, 'last_changed') and new_state.last_changed:
            envelope["last_changed"] = new_state.last_changed.isoformat().replace("+00:00", "Z")
        if hasattr(new_state, 'last_updated') and new_state.last_updated:
            envelope["last_updated"] = new_state.last_updated.isoformat().replace("+00:00", "Z")
        
        # Add context with privacy redaction
        context = getattr(event, 'context', None) or getattr(new_state, 'context', None)
        if context:
            context_id = getattr(context, 'id', None)
            if context_id:
                envelope["context_id"] = self._redact_context_id(context_id)
                
            parent_id = getattr(context, 'parent_id', None)
            if parent_id:
                envelope["parent_id"] = self._redact_context_id(parent_id)
            
            # Infer trigger type
            user_id = getattr(context, 'user_id', None)
            if user_id:
                envelope["trigger"] = "user"
            elif parent_id:
                envelope["trigger"] = "automation"
            else:
                envelope["trigger"] = "unknown"
        
        # Project old state
        old_attrs = {}
        if old_state and hasattr(old_state, 'attributes'):
            old_attrs = self._project_attributes(domain, old_state.attributes)
        
        envelope["old"] = {
            "state": old_state.state if old_state else None,
            "attrs": old_attrs
        }
        
        # Project new state
        new_attrs = {}
        if hasattr(new_state, 'attributes'):
            new_attrs = self._project_attributes(domain, new_state.attributes)
        
        envelope["new"] = {
            "state": new_state.state,
            "attrs": new_attrs
        }
        
        return envelope

    def _create_call_service_envelope(
        self, domain: str, service: str, entity_ids: List[str], event: Event
    ) -> Dict[str, Any]:
        """Create N3 specification envelope for call_service event."""
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        # Get zones for all target entities
        zone_ids = []
        for entity_id in entity_ids:
            zone_id = self._entity_to_zone.get(entity_id)
            if zone_id and zone_id not in zone_ids:
                zone_ids.append(zone_id)
        
        envelope = {
            "v": ENVELOPE_VERSION,
            "ts": now_utc,
            "src": "ha",
            "kind": "call_service",
            "entity_id": entity_ids[0],  # Primary entity for compatibility
            "domain": domain,
            "zone_id": zone_ids[0] if zone_ids else None,
        }
        
        # Add context with privacy redaction
        context = getattr(event, 'context', None)
        if context:
            context_id = getattr(context, 'id', None)
            if context_id:
                envelope["context_id"] = self._redact_context_id(context_id)
                
            parent_id = getattr(context, 'parent_id', None)
            if parent_id:
                envelope["parent_id"] = self._redact_context_id(parent_id)
            
            # Infer trigger type
            user_id = getattr(context, 'user_id', None)
            if user_id:
                envelope["trigger"] = "user"
            elif parent_id:
                envelope["trigger"] = "automation"
            else:
                envelope["trigger"] = "unknown"
        
        # Add call_service specific fields
        envelope["service"] = service
        envelope["entity_ids"] = entity_ids
        envelope["zone_ids"] = zone_ids
        
        return envelope

    def _project_attributes(self, domain: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Project attributes according to N3 specification privacy policy."""
        projected = {}
        allowed_attrs = DOMAIN_PROJECTIONS.get(domain, set())
        
        for key, value in attributes.items():
            # Skip if not in projection allowlist for this domain
            if allowed_attrs and key not in allowed_attrs:
                continue
                
            # Skip if in global redaction list
            if key in REDACTED_ATTRIBUTES:
                continue
                
            # Skip friendly_name unless explicitly allowed
            if key == "friendly_name" and not self._keep_friendly_names:
                continue
                
            # Skip extra redacted attributes
            if key in self._extra_redact_attrs:
                continue
                
            # Skip sensitive keys (tokens, secrets, etc.)
            if SENSITIVE_KEY_PATTERN.search(key):
                continue
                
            projected[key] = value
            
        return projected

    def _redact_context_id(self, context_id: str) -> str:
        """Redact context ID for privacy (N3 specification)."""
        if self._keep_full_context_ids:
            return context_id
        
        # Truncate to first 12 characters for correlation without full reversibility
        return context_id[:12]

    def _extract_context_id(self, event: Event) -> Optional[str]:
        """Extract context ID from HA event."""
        context = getattr(event, 'context', None)
        if context:
            return getattr(context, 'id', None)
        return None

    def _extract_entity_ids_from_service_data(self, service_data: Dict[str, Any]) -> List[str]:
        """Extract entity IDs from service call data."""
        entity_id_value = service_data.get("entity_id")
        if not entity_id_value:
            return []
        
        if isinstance(entity_id_value, str):
            return [entity_id_value]
        elif isinstance(entity_id_value, list):
            return [str(eid) for eid in entity_id_value if isinstance(eid, str)]
        
        return []

    def _track_user_action_from_event(
        self,
        *,
        event: Event,
        zone_ids: List[Optional[str]],
        entity_id: Optional[str],
        kind: str,
    ) -> None:
        """Track last user actions per zone and store user presence mapping (local-only)."""
        context = getattr(event, "context", None)
        user_id = getattr(context, "user_id", None) if context else None
        if not user_id:
            return

        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        now_ts = time.time()

        for zone_id in zone_ids:
            if not zone_id:
                continue

            self._last_user_actions_by_zone[zone_id] = {
                "user_id": user_id,
                "ts": now_iso,
                "kind": kind,
                "entity_id": entity_id,
            }

            zone_presence = self._user_presence_by_zone.setdefault(zone_id, {})
            zone_presence[user_id] = now_ts
            self._user_last_zone_by_user[user_id] = zone_id

    def _should_forward_entity(self, entity_id: str, domain: str) -> bool:
        """Check if entity should be forwarded based on debounce rules."""
        debounce_interval = self._debounce_intervals.get(domain, 0)
        if debounce_interval <= 0:
            return True
        
        now = time.time()
        last_sent = self._debounce_cache.get(entity_id, 0)
        if now - last_sent < debounce_interval:
            return False
        
        self._debounce_cache[entity_id] = now
        return True

    def _is_event_new(self, event_key: str) -> bool:
        """Check if event is new for idempotency (N3 specification)."""
        if self._idempotency_ttl <= 0:
            return True
        
        now = time.time()
        
        # Clean expired entries periodically
        if len(self._seen_events) > 1000:
            self._seen_events = {k: v for k, v in self._seen_events.items() if v > now}
        
        # Check if already seen
        expires_at = self._seen_events.get(event_key, 0)
        if expires_at > now:
            return False
        
        # Mark as seen
        self._seen_events[event_key] = now + self._idempotency_ttl
        return True

    async def _build_zone_mapping(self):
        """Build entity_id -> zone_id mapping from HA area registry."""
        entity_registry = self.hass.helpers.entity_registry.async_get(self.hass)
        area_registry = self.hass.helpers.area_registry.async_get(self.hass)
        device_registry = self.hass.helpers.device_registry.async_get(self.hass)
        
        self._entity_to_zone = {}
        
        for entity in entity_registry.entities.values():
            zone_id = None
            
            # Try entity area first
            if entity.area_id:
                area = area_registry.async_get(entity.area_id)
                if area:
                    zone_id = area.normalized_name or area.name
            
            # Try device area if no entity area
            elif entity.device_id:
                device = device_registry.async_get(entity.device_id)
                if device and device.area_id:
                    area = area_registry.async_get(device.area_id)
                    if area:
                        zone_id = area.normalized_name or area.name
            
            if zone_id:
                self._entity_to_zone[entity.entity_id] = zone_id

        _LOGGER.info("Built zone mapping for %d entities", len(self._entity_to_zone))

    def _get_zone_for_entity(self, entity_id: str, domain: str, state_obj) -> Optional[str]:
        """Get zone for entity, with special handling for person/device_tracker state-based zones."""
        # First try static mapping
        static_zone = self._entity_to_zone.get(entity_id)
        
        # For person/device_tracker, state value may indicate zone
        if domain in ("person", "device_tracker") and state_obj and hasattr(state_obj, 'state'):
            state_value = state_obj.state
            # Common zone states that HA uses
            if state_value and state_value not in ("unknown", "unavailable", "not_home"):
                # If state looks like a zone name, use it (with fallback to static)
                if state_value != "home" and len(state_value) > 1:
                    return state_value
                elif state_value == "home" and not static_zone:
                    return "home"
        
        return static_zone

    async def _enqueue_event(self, envelope: Dict[str, Any]):
        """Add event to pending queue."""
        self._pending_events.append(envelope)
        
        # Enforce max queue size (drop oldest)
        if len(self._pending_events) > self._max_queue_size:
            dropped = len(self._pending_events) - self._max_queue_size
            self._pending_events = self._pending_events[-self._max_queue_size:]
            _LOGGER.warning("Dropped %d old events due to queue size limit", dropped)
        
        # Trigger immediate flush if batch is full
        if len(self._pending_events) >= self._batch_size:
            await self._flush_events()

    async def _flush_loop(self):
        """Background task to flush events periodically."""
        try:
            while True:
                await asyncio.sleep(self._flush_interval)
                if self._pending_events:
                    await self._flush_events()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            _LOGGER.exception("Error in flush loop: %s", e)

    async def _heartbeat_loop(self):
        """Background task to send heartbeat envelopes periodically."""
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval)
                await self._send_heartbeat()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            _LOGGER.exception("Error in heartbeat loop: %s", e)

    async def _send_heartbeat(self):
        """Send heartbeat envelope to Core for health monitoring."""
        if not self._session:
            return
            
        try:
            now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            
            # Count entities by domain in our zone mapping
            domain_counts = defaultdict(int)
            for entity_id in self._entity_to_zone.keys():
                domain = entity_id.split(".", 1)[0]
                if domain in self._enabled_domains:
                    domain_counts[domain] += 1
            
            heartbeat_envelope = {
                "v": ENVELOPE_VERSION,
                "ts": now_utc,
                "src": "ha",
                "kind": "heartbeat",
                "entity_count": sum(domain_counts.values()),
                "domain_counts": dict(domain_counts),
                "pending_events": len(self._pending_events),
                "enabled_domains": list(self._enabled_domains),
            }
            
            url = f"{self._core_url}/api/v1/events"
            headers = {
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json"
            }
            
            payload = {"events": [heartbeat_envelope]}
            
            async with self._session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    _LOGGER.debug("Sent heartbeat to Core successfully")
                else:
                    _LOGGER.warning(
                        "Failed to send heartbeat to Core: %s %s", 
                        response.status, response.reason
                    )
                    
        except Exception as e:
            _LOGGER.exception("Exception sending heartbeat to Core: %s", e)

    async def _flush_events(self):
        """Send pending events to CoPilot Core."""
        if not self._pending_events or not self._session:
            return
        
        # Take events to send and clear queue
        events_to_send = self._pending_events.copy()
        self._pending_events.clear()
        
        try:
            url = f"{self._core_url}/api/v1/events"
            headers = {
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json"
            }
            
            # Send as batch per Core API
            payload = {"events": events_to_send}
            
            async with self._session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    _LOGGER.debug("Sent %d events to Core successfully", len(events_to_send))
                else:
                    error_text = await response.text()
                    _LOGGER.error(
                        "Failed to send events to Core: %s %s - %s", 
                        response.status, response.reason, error_text
                    )
                    # Re-queue failed events (at front to preserve order)
                    self._pending_events = events_to_send + self._pending_events
                    
        except Exception as e:
            _LOGGER.exception("Exception sending events to Core: %s", e)
            # Re-queue failed events
            self._pending_events = events_to_send + self._pending_events

    async def _load_persistent_state(self):
        """Load persistent state from storage."""
        try:
            data = await self._store.async_load()
            if data:
                if "pending_events" in data:
                    self._pending_events = data["pending_events"]
                if "debounce_cache" in data:
                    self._debounce_cache = data["debounce_cache"]
                if "seen_events" in data:
                    self._seen_events = data["seen_events"]
                
                _LOGGER.info("Loaded persistent state: %d pending events", len(self._pending_events))
        except Exception as e:
            _LOGGER.exception("Failed to load persistent state: %s", e)

    async def _save_persistent_state(self):
        """Save persistent state to storage."""
        try:
            # Clean up old debounce and seen events before saving
            now = time.time()
            self._debounce_cache = {
                k: v for k, v in self._debounce_cache.items() 
                if now - v < 3600  # Keep last hour
            }
            self._seen_events = {
                k: v for k, v in self._seen_events.items() 
                if v > now  # Keep non-expired
            }
            
            data = {
                "pending_events": self._pending_events,
                "debounce_cache": self._debounce_cache,
                "seen_events": self._seen_events,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            await self._store.async_save(data)
        except Exception as e:
            _LOGGER.exception("Failed to save persistent state: %s", e)

    async def async_get_stats(self) -> Dict[str, Any]:
        """Get forwarder statistics."""
        return {
            "pending_events": len(self._pending_events),
            "enabled_domains": list(self._enabled_domains),
            "zone_mappings": len(self._entity_to_zone),
            "debounce_cache_size": len(self._debounce_cache),
            "seen_events_cache_size": len(self._seen_events),
            "core_url": self._core_url,
            "batch_size": self._batch_size,
            "flush_interval": self._flush_interval,
            "forward_call_service": self._forward_call_service,
            "idempotency_ttl": self._idempotency_ttl,
            "heartbeat_enabled": self._heartbeat_enabled,
            "heartbeat_interval": self._heartbeat_interval,
        }
