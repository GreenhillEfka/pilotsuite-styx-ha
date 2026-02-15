"""
Brain Graph Sync Service for AI Home CoPilot.

Synchronizes Home Assistant entities/state with the Core Brain Graph module
via the /api/v1/graph endpoints. This creates a real-time knowledge graph
of HA entities, their relationships, and state transitions.

Privacy-first: only essential entity metadata and anonymized state patterns.

Security: entity_id sanitization prevents injection in node IDs.
"""
import logging
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
import asyncio

import aiohttp
from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import area_registry, device_registry, entity_registry
from homeassistant.const import (
    EVENT_STATE_CHANGED,
    EVENT_CALL_SERVICE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from .const import DOMAIN
from .core.error_helpers import log_error_with_context
from .core.performance import get_entity_cache, DomainFilter

_LOGGER = logging.getLogger(__name__)


def sanitize_entity_id(entity_id: str) -> str:
    """Sanitize entity_id for use in node IDs.
    
    Removes/replaces characters that could cause issues in node IDs:
    - Non-alphanumeric characters (except underscore, dot, hyphen)
    - Unicode characters
    
    Args:
        entity_id: The entity_id to sanitize (e.g., "light.kitchen_lamp")
    
    Returns:
        Sanitized entity_id safe for use in node IDs
    """
    if not entity_id:
        return "unknown"
    
    # Keep only alphanumeric, underscore, dot, and hyphen
    # Handle unicode by converting to ASCII-compatible representation
    try:
        # Try to encode to ASCII, replacing non-ASCII chars
        ascii_id = entity_id.encode('ascii', errors='replace').decode('ascii')
    except Exception:
        ascii_id = entity_id
    
    sanitized = re.sub(r'[^a-zA-Z0-9_.\-]', '_', ascii_id)
    
    # Collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    # Collapse multiple dots
    sanitized = re.sub(r'\.+', '.', sanitized)
    
    # Fallback if empty after sanitization
    if not sanitized:
        return "unknown"
    
    return sanitized


def safe_sanitize_entity_id(entity_id: str | None) -> str:
    """Safely sanitize entity_id, handling None values."""
    if entity_id is None:
        return "unknown"
    return sanitize_entity_id(entity_id)


def sanitize_node_id(node_type: str, identifier: str) -> str:
    """Create a sanitized node ID from type and identifier.
    
    Args:
        node_type: The node type (e.g., "entity", "area", "device")
        identifier: The identifier (e.g., entity_id, area_id)
    
    Returns:
        Sanitized node ID (e.g., "entity:light_kitchen_lamp")
    """
    safe_type = re.sub(r'[^a-z0-9_]', '_', node_type.lower())
    safe_id = sanitize_entity_id(identifier)
    return f"{safe_type}:{safe_id}"


class BrainGraphSync:
    """Manages syncing HA state and relationships to Core Brain Graph."""

    def __init__(self, hass: HomeAssistant, core_url: str, access_token: str):
        """Initialize the Brain Graph sync service."""
        self.hass = hass
        self.core_url = core_url.rstrip('/')
        self.access_token = access_token
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
        
        # Registries for relationships
        self._area_reg: Optional[area_registry.AreaRegistry] = None
        self._device_reg: Optional[device_registry.DeviceRegistry] = None
        self._entity_reg: Optional[entity_registry.EntityRegistry] = None
        
        # Track processed events to avoid cycles
        self._processed_events: Set[str] = set()
        self._max_processed_events = 1000
        
    async def async_start(self) -> bool:
        """Start the Brain Graph sync service."""
        try:
            if self._running:
                return True
                
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            # Initialize registries
            self._area_reg = area_registry.async_get(self.hass)
            self._device_reg = device_registry.async_get(self.hass)  
            self._entity_reg = entity_registry.async_get(self.hass)
            
            # Test connectivity
            if not await self._test_brain_graph_connection():
                _LOGGER.error("Failed to connect to Core Brain Graph")
                await self._session.close()
                return False
                
            # Initial sync of entities and relationships
            await self._sync_initial_graph()
            
            # Start listening to HA events
            self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_state_changed)
            self.hass.bus.async_listen(EVENT_CALL_SERVICE, self._handle_service_call)
            
            self._running = True
            _LOGGER.info("Brain Graph sync service started")
            return True
            
        except Exception as err:
            log_error_with_context(
                _LOGGER, err, "Brain Graph sync startup",
                {"core_url": self.core_url}
            )
            if self._session:
                await self._session.close()
            return False
    
    async def async_stop(self):
        """Stop the Brain Graph sync service."""
        if not self._running:
            return
            
        self._running = False
        if self._session:
            await self._session.close()
            self._session = None
            
        _LOGGER.info("Brain Graph sync service stopped")
    
    async def _test_brain_graph_connection(self) -> bool:
        """Test if Core Brain Graph endpoints are accessible."""
        try:
            async with self._session.get(f"{self.core_url}/api/v1/graph/stats") as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    _LOGGER.info("Connected to Brain Graph (nodes: %s, edges: %s)", 
                               stats.get('nodes', 0), stats.get('edges', 0))
                    return True
                else:
                    _LOGGER.error("Brain Graph stats returned status %s", resp.status)
                    return False
        except Exception as err:
            log_error_with_context(
                _LOGGER, err, "Brain Graph connection test",
                {"endpoint": f"{self.core_url}/api/v1/graph/stats"}
            )
            return False
    
    async def _sync_initial_graph(self):
        """Perform initial sync of HA entities and relationships to Brain Graph."""
        try:
            _LOGGER.info("Starting initial Brain Graph sync")
            
            # Sync areas first (zones)
            await self._sync_areas()
            
            # Sync devices and their area relationships
            await self._sync_devices()
            
            # Sync entities and their device/area relationships
            await self._sync_entities()
            
            # Sync current entity states
            await self._sync_entity_states()
            
            _LOGGER.info("Initial Brain Graph sync completed")
            
        except Exception as err:
            log_error_with_context(
                _LOGGER, err, "Initial Brain Graph sync",
                {"num_areas": len(self._area_reg.areas), "num_entities": len(self._entity_reg.entities)}
            )
    
    async def _sync_areas(self):
        """Sync HA areas as zone nodes in Brain Graph."""
        areas = self._area_reg.areas
        
        for area in areas.values():
            node_data = {
                "node_id": f"area:{area.id}",
                "node_type": "zone",
                "properties": {
                    "name": area.name,
                    "area_id": area.id,
                    "source": "ha_area_registry"
                }
            }
            
            await self._send_node_update(node_data)
    
    async def _sync_devices(self):
        """Sync HA devices as device nodes with area relationships."""
        devices = self._device_reg.devices
        
        for device in devices.values():
            # Create device node
            node_data = {
                "node_id": f"device:{device.id}",
                "node_type": "device", 
                "properties": {
                    "name": device.name or "Unnamed Device",
                    "device_id": device.id,
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "source": "ha_device_registry"
                }
            }
            
            await self._send_node_update(node_data)
            
            # Create area relationship if device has area
            if device.area_id:
                edge_data = {
                    "source_id": f"device:{device.id}",
                    "target_id": f"area:{device.area_id}",
                    "edge_type": "located_in",
                    "properties": {
                        "source": "ha_device_area_assignment"
                    }
                }
                
                await self._send_edge_update(edge_data)
    
    async def _sync_entities(self):
        """Sync HA entities as entity nodes with device/area relationships."""
        entities = self._entity_reg.entities
        
        for entity in entities.values():
            # Skip disabled entities
            if entity.disabled:
                continue
            
            # Sanitize entity_id for safe node ID construction
            safe_entity_id = sanitize_entity_id(entity.entity_id)
                
            # Create entity node
            node_data = {
                "node_id": f"entity:{safe_entity_id}",
                "node_type": "entity",
                "properties": {
                    "name": entity.original_name or entity.entity_id.split('.')[-1],
                    "entity_id": entity.entity_id,
                    "domain": entity.entity_id.split('.')[0],
                    "platform": entity.platform,
                    "source": "ha_entity_registry"
                }
            }
            
            await self._send_node_update(node_data)
            
            # Create device relationship if entity has device
            if entity.device_id:
                edge_data = {
                    "source_id": f"entity:{safe_entity_id}",
                    "target_id": f"device:{entity.device_id}",
                    "edge_type": "belongs_to",
                    "properties": {
                        "source": "ha_entity_device_assignment"
                    }
                }
                
                await self._send_edge_update(edge_data)
            
            # Create area relationship if entity has area (direct or via device)
            area_id = entity.area_id
            if not area_id and entity.device_id:
                device = self._device_reg.async_get(entity.device_id)
                if device:
                    area_id = device.area_id
                    
            if area_id:
                edge_data = {
                    "source_id": f"entity:{safe_entity_id}",
                    "target_id": f"area:{area_id}",
                    "edge_type": "located_in",
                    "properties": {
                        "source": "ha_entity_area_assignment"
                    }
                }
                
                await self._send_edge_update(edge_data)
    
    async def _sync_entity_states(self, domains: Optional[List[str]] = None):
        """Sync current entity states as state nodes with domain filtering.
        
        Args:
            domains: Optional list of domains to sync. If None, uses optimized default set.
        """
        # Default domains for smart home graph (extended coverage)
        if domains is None:
            domains = [
                "light", "switch", "climate", "media_player", "cover",
                "sensor", "binary_sensor", "person", "device_tracker",
                "humidifier", "fan", "vacuum", "lock", "alarm_control_panel"
            ]
        
        # Use domain filter for performance optimization
        states = DomainFilter.get_entities_by_domain(self.hass, set(domains))
        
        for entity_id, state in states.items():
            # Skip unavailable/unknown states and internal entities
            if (state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN] or 
                entity_id.startswith(('input_', 'group.', 'zone.'))):
                continue
                
            await self._sync_entity_state(entity_id, state)
    
    async def _sync_entity_state(self, entity_id: str, state):
        """Sync a single entity state to Brain Graph."""
        try:
            # Sanitize entity_id for safe node ID construction
            safe_entity_id = sanitize_entity_id(entity_id)
            safe_state = sanitize_entity_id(str(state.state)) if state.state else "unknown"
            
            # Create state node
            state_node_id = f"state:{safe_entity_id}:{safe_state}"
            node_data = {
                "node_id": state_node_id,
                "node_type": "state",
                "properties": {
                    "entity_id": entity_id,
                    "state_value": str(state.state),
                    "domain": entity_id.split('.')[0],
                    "last_changed": state.last_changed.isoformat(),
                    "source": "ha_entity_state"
                }
            }
            
            await self._send_node_update(node_data)
            
            # Create relationship from entity to current state
            edge_data = {
                "source_id": f"entity:{safe_entity_id}",
                "target_id": state_node_id,
                "edge_type": "has_state",
                "properties": {
                    "timestamp": state.last_changed.isoformat(),
                    "source": "ha_state_transition"
                }
            }
            
            await self._send_edge_update(edge_data)
            
        except Exception as err:
            log_error_with_context(
                _LOGGER, err, f"Brain Graph state sync for {entity_id}",
                {"entity_id": entity_id, "state": str(state.state) if state else None},
                level=logging.DEBUG
            )
    
    async def _handle_state_changed(self, event: Event):
        """Handle HA state change events."""
        if not self._running:
            return
            
        event_id = f"state_changed_{event.time_fired.timestamp()}_{event.data.get('entity_id', '')}"
        if event_id in self._processed_events:
            return
            
        # Add to processed events (with size limit)
        self._processed_events.add(event_id)
        if len(self._processed_events) > self._max_processed_events:
            # Remove oldest 100 events
            for _ in range(100):
                self._processed_events.pop()
        
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        
        if entity_id and new_state:
            await self._sync_entity_state(entity_id, new_state)
    
    async def _handle_service_call(self, event: Event):
        """Handle HA service call events."""
        if not self._running:
            return
            
        event_id = f"service_call_{event.time_fired.timestamp()}_{event.data.get('domain', '')}_{event.data.get('service', '')}"
        if event_id in self._processed_events:
            return
            
        self._processed_events.add(event_id)
        if len(self._processed_events) > self._max_processed_events:
            for _ in range(100):
                self._processed_events.pop()
        
        domain = event.data.get("domain")
        service = event.data.get("service")
        service_data = event.data.get("service_data", {})
        
        # Create service call node for significant actions
        if domain in ["light", "switch", "climate", "media_player", "cover"]:
            node_data = {
                "node_id": f"service:{domain}.{service}:{event.time_fired.timestamp()}",
                "node_type": "action",
                "properties": {
                    "domain": domain,
                    "service": service,
                    "timestamp": event.time_fired.isoformat(),
                    "source": "ha_service_call"
                }
            }
            
            await self._send_node_update(node_data)
            
            # Link to affected entities
            target_entities = service_data.get("entity_id", [])
            if isinstance(target_entities, str):
                target_entities = [target_entities]
                
            for entity_id in target_entities:
                # Sanitize entity_id for safe edge construction
                safe_entity_id = sanitize_entity_id(entity_id)
                edge_data = {
                    "source_id": f"service:{domain}.{service}:{event.time_fired.timestamp()}",
                    "target_id": f"entity:{safe_entity_id}",
                    "edge_type": "targets",
                    "properties": {
                        "timestamp": event.time_fired.isoformat(),
                        "source": "ha_service_call_target"
                    }
                }
                
                await self._send_edge_update(edge_data)
    
    async def _send_node_update(self, node_data: Dict[str, Any]):
        """Send a node update to Core Brain Graph."""
        try:
            async with self._session.post(
                f"{self.core_url}/api/v1/graph/state",
                json={"nodes": [node_data]}
            ) as resp:
                if resp.status != 200:
                    _LOGGER.debug("Brain Graph node update failed: status %s", resp.status)
        except Exception as err:
            log_error_with_context(
                _LOGGER, err, "Brain Graph node update",
                {"node_type": node_data.get("type"), "node_id": node_data.get("id", "unknown")},
                level=logging.DEBUG
            )
    
    async def _send_edge_update(self, edge_data: Dict[str, Any]):
        """Send an edge update to Core Brain Graph."""
        try:
            async with self._session.post(
                f"{self.core_url}/api/v1/graph/state",
                json={"edges": [edge_data]}
            ) as resp:
                if resp.status != 200:
                    _LOGGER.debug("Brain Graph edge update failed: status %s", resp.status)
        except Exception as err:
            log_error_with_context(
                _LOGGER, err, "Brain Graph edge update",
                {"edge_type": edge_data.get("type"), "from": edge_data.get("from"), "to": edge_data.get("to")},
                level=logging.DEBUG
            )
    
    async def get_graph_stats(self) -> Optional[Dict[str, Any]]:
        """Get Brain Graph statistics."""
        try:
            async with self._session.get(f"{self.core_url}/api/v1/graph/stats") as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as err:
            log_error_with_context(
                _LOGGER, err, "Brain Graph stats retrieval",
                {"endpoint": f"{self.core_url}/api/v1/graph/stats"},
                level=logging.DEBUG
            )
        return None
    
    async def get_graph_snapshot_url(self) -> str:
        """Get URL for Brain Graph SVG visualization."""
        return f"{self.core_url}/api/v1/graph/snapshot.svg"


async def async_setup_brain_graph_sync(
    hass: HomeAssistant, 
    config: ConfigType, 
    core_url: str, 
    access_token: str
) -> Optional[BrainGraphSync]:
    """Set up Brain Graph sync service."""
    
    brain_graph_sync = BrainGraphSync(hass, core_url, access_token)
    
    if await brain_graph_sync.async_start():
        return brain_graph_sync
    else:
        _LOGGER.error("Failed to start Brain Graph sync")
        return None


async def async_unload_brain_graph_sync(brain_graph_sync: Optional[BrainGraphSync]):
    """Unload Brain Graph sync service."""
    if brain_graph_sync:
        await brain_graph_sync.async_stop()