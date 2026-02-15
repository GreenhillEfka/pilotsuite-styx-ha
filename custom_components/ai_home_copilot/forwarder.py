"""Event Forwarder for AI Home CoPilot.

Forwards state_changed events to CoPilot Core with privacy-first envelope format.
Implements projection, redaction, and zone enrichment per N3 specification.
"""
import asyncio
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urlparse

import aiohttp
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.const import EVENT_STATE_CHANGED

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Schema version for envelope format
ENVELOPE_VERSION = 1

# Default attribute projections by domain
DEFAULT_PROJECTIONS = {
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

# Attributes that should always be redacted for privacy
REDACT_ATTRIBUTES = {
    "entity_picture", "media_image_url", "media_image_remotely_accessible",
    "latitude", "longitude", "gps_accuracy", "access_token", "friendly_name"
}

# Regex pattern for sensitive keys
SENSITIVE_KEY_PATTERN = re.compile(r'(token|key|secret|password)', re.IGNORECASE)

# Default debounce intervals by domain (seconds)
DEFAULT_DEBOUNCE = {
    "sensor": 1.0,
    "binary_sensor": 0.5,
}

class EventForwarder:
    """Forwards HA events to CoPilot Core with privacy-first envelope format."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        self.hass = hass
        self.config = config
        self._store = Store(hass, 1, f"{DOMAIN}_forwarder_queue")
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_sent: Dict[str, float] = {}  # entity_id -> timestamp for debounce
        self._pending_events: List[Dict[str, Any]] = []
        self._flush_task: Optional[asyncio.Task] = None
        self._zone_map: Dict[str, str] = {}  # entity_id -> zone_id
        self._unsub_state_listener = None
        
        # Configuration
        self._core_url = config.get("core_url", "http://localhost:8099")
        self._api_token = config.get("api_token", "")
        self._batch_size = config.get("batch_size", 50)
        self._flush_interval = config.get("flush_interval", 0.5)
        self._enabled_domains = set(config.get("enabled_domains", [
            "light", "climate", "media_player", "binary_sensor", "sensor", 
            "cover", "lock", "person", "device_tracker", "weather"
        ]))
        
        # Redaction settings
        redaction_config = config.get("redaction", {})
        self._keep_friendly_names = redaction_config.get("keep_friendly_names", False)
        self._keep_full_context_ids = redaction_config.get("keep_full_context_ids", False)
        self._extra_redact = set(redaction_config.get("extra_strip", []))
        
        # Attribute projections
        projections_config = config.get("projections", {})
        self._projections = DEFAULT_PROJECTIONS.copy()
        self._projections.update(projections_config)
        
        # Debounce settings
        debounce_config = config.get("debounce", {})
        self._debounce_intervals = DEFAULT_DEBOUNCE.copy()
        self._debounce_intervals.update(debounce_config)

    async def async_start(self):
        """Start the event forwarder."""
        _LOGGER.info("Starting AI Home CoPilot Event Forwarder")
        
        # Load persistent queue
        await self._load_persistent_queue()
        
        # Build zone map
        await self._build_zone_map()
        
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=10)
        self._session = aiohttp.ClientSession(timeout=timeout)
        
        # Start state change listener
        self._unsub_state_listener = async_track_state_change_event(
            self.hass, None, self._handle_state_change_event
        )
        
        # Start flush task
        self._flush_task = asyncio.create_task(self._flush_loop())
        
        _LOGGER.info("Event Forwarder started successfully")

    async def async_stop(self):
        """Stop the event forwarder."""
        _LOGGER.info("Stopping AI Home CoPilot Event Forwarder")
        
        # Stop state listener
        if self._unsub_state_listener:
            self._unsub_state_listener()
            self._unsub_state_listener = None
        
        # Cancel flush task
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush any pending events
        if self._pending_events:
            await self._flush_events()
        
        # Close HTTP session
        if self._session:
            await self._session.close()
            self._session = None
            
        _LOGGER.info("Event Forwarder stopped")

    async def _handle_state_change_event(self, event: Event):
        """Handle HA state_changed event."""
        if event.event_type != EVENT_STATE_CHANGED:
            return
            
        event_data = event.data
        entity_id = event_data.get("entity_id")
        if not entity_id:
            return
            
        domain = entity_id.split(".", 1)[0]
        if domain not in self._enabled_domains:
            return
            
        # Apply debounce
        now = time.time()
        debounce_interval = self._debounce_intervals.get(domain, 0)
        if debounce_interval > 0:
            last_sent = self._last_sent.get(entity_id, 0)
            if now - last_sent < debounce_interval:
                return
            self._last_sent[entity_id] = now
        
        # Create envelope
        envelope = await self._create_envelope(event_data)
        if envelope:
            self._pending_events.append(envelope)
            
            # Trigger flush if batch is full
            if len(self._pending_events) >= self._batch_size:
                await self._flush_events()

    async def _create_envelope(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create privacy-first envelope from HA state_changed event."""
        entity_id = event_data.get("entity_id")
        old_state = event_data.get("old_state")
        new_state = event_data.get("new_state")
        
        if not entity_id or not new_state:
            return None
            
        domain = entity_id.split(".", 1)[0]
        
        # Extract basic envelope data
        envelope = {
            "v": ENVELOPE_VERSION,
            "ts": datetime.utcnow().isoformat() + "Z",
            "src": "ha",
            "kind": "state_changed",
            "entity_id": entity_id,
            "domain": domain,
            "zone_id": self._zone_map.get(entity_id),
        }
        
        # Add timing from new_state
        if hasattr(new_state, 'last_changed') and new_state.last_changed:
            envelope["last_changed"] = new_state.last_changed.isoformat() + "Z"
        if hasattr(new_state, 'last_updated') and new_state.last_updated:
            envelope["last_updated"] = new_state.last_updated.isoformat() + "Z"
            
        # Add context with privacy redaction
        context = getattr(new_state, 'context', None)
        if context:
            context_id = getattr(context, 'id', None)
            if context_id:
                if self._keep_full_context_ids:
                    envelope["context_id"] = context_id
                else:
                    envelope["context_id"] = context_id[:12]  # Truncate for privacy
                    
            parent_id = getattr(context, 'parent_id', None)
            if parent_id:
                if self._keep_full_context_ids:
                    envelope["parent_id"] = parent_id
                else:
                    envelope["parent_id"] = parent_id[:12]
            
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

    def _project_attributes(self, domain: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Project and redact attributes according to privacy policy."""
        projected = {}
        allowed_attrs = self._projections.get(domain, set())
        
        for key, value in attributes.items():
            # Skip if not in projection list for this domain
            if allowed_attrs and key not in allowed_attrs:
                continue
                
            # Skip if in redaction list
            if key in REDACT_ATTRIBUTES:
                continue
            if not self._keep_friendly_names and key == "friendly_name":
                continue
            if key in self._extra_redact:
                continue
                
            # Skip if sensitive key pattern
            if SENSITIVE_KEY_PATTERN.search(key):
                continue
                
            projected[key] = value
            
        return projected

    async def _build_zone_map(self):
        """Build entity_id -> zone_id mapping from area/device registry."""
        # TODO: Implement zone mapping from HA area/device registry
        # For now, use a simple heuristic based on entity naming
        self._zone_map = {}
        
        # Get all entities and try to infer zones
        entity_registry = self.hass.helpers.entity_registry.async_get(self.hass)
        area_registry = self.hass.helpers.area_registry.async_get(self.hass)
        device_registry = self.hass.helpers.device_registry.async_get(self.hass)
        
        for entity in entity_registry.entities.values():
            zone_id = None
            
            # Try entity area first
            if entity.area_id:
                area = area_registry.async_get(entity.area_id)
                if area:
                    zone_id = area.normalized_name
            
            # Try device area if no entity area
            elif entity.device_id:
                device = device_registry.async_get(entity.device_id)
                if device and device.area_id:
                    area = area_registry.async_get(device.area_id)
                    if area:
                        zone_id = area.normalized_name
            
            if zone_id:
                self._zone_map[entity.entity_id] = zone_id

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

    async def _flush_events(self):
        """Send pending events to CoPilot Core."""
        if not self._pending_events or not self._session:
            return
            
        events_to_send = self._pending_events.copy()
        self._pending_events.clear()
        
        try:
            url = f"{self._core_url}/api/v1/events"
            headers = {
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json"
            }
            
            # Send as batch
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
                    # Re-queue failed events for retry
                    self._pending_events.extend(events_to_send)
                    
        except Exception as e:
            _LOGGER.exception("Exception sending events to Core: %s", e)
            # Re-queue failed events for retry
            self._pending_events.extend(events_to_send)
            
        # Persist queue state
        await self._save_persistent_queue()

    async def _load_persistent_queue(self):
        """Load persistent event queue from storage."""
        try:
            data = await self._store.async_load()
            if data and "pending_events" in data:
                self._pending_events = data["pending_events"]
                _LOGGER.info("Loaded %d events from persistent queue", len(self._pending_events))
        except Exception as e:
            _LOGGER.exception("Failed to load persistent queue: %s", e)
            self._pending_events = []

    async def _save_persistent_queue(self):
        """Save persistent event queue to storage."""
        try:
            # Only keep the most recent events to prevent unbounded growth
            max_queue_size = 1000
            if len(self._pending_events) > max_queue_size:
                self._pending_events = self._pending_events[-max_queue_size:]
                
            data = {"pending_events": self._pending_events}
            await self._store.async_save(data)
        except Exception as e:
            _LOGGER.exception("Failed to save persistent queue: %s", e)

    async def async_get_stats(self) -> Dict[str, Any]:
        """Get forwarder statistics."""
        return {
            "pending_events": len(self._pending_events),
            "enabled_domains": list(self._enabled_domains),
            "zone_mappings": len(self._zone_map),
            "debounce_active": len(self._last_sent),
            "core_url": self._core_url,
            "batch_size": self._batch_size,
            "flush_interval": self._flush_interval,
        }