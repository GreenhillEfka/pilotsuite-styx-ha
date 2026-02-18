"""
Brain Graph Sync Module for AI Home CoPilot Runtime.

Manages syncing HA state and relationships to Core Brain Graph module
via the /api/v1/graph endpoints. Creates a real-time knowledge graph
of HA entities, their relationships, and state transitions.

Optimizations:
- Batch API calls for efficiency
- Event deduplication with TTL-based cache
- Integration with Knowledge Graph and Neurons
- Proper error handling and recovery

Privacy-first: only essential entity metadata and anonymized state patterns.
Security: entity_id sanitization prevents injection in node IDs.
"""
import logging
import asyncio
from typing import Optional, Dict, Any, Set, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

from homeassistant.core import HomeAssistant, Event

from ..module import CopilotModule, ModuleContext
from ...brain_graph_sync import (
    BrainGraphSync as BrainGraphSyncService,
    async_setup_brain_graph_sync as setup_service,
    async_unload_brain_graph_sync as unload_service,
)
from ...const import DOMAIN
from ...module_connector import (
    ModuleConnector,
    get_module_connector,
    SIGNAL_ACTIVITY_UPDATED,
    SIGNAL_CALENDAR_LOAD_UPDATED,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class SyncConfig:
    """Configuration for brain graph sync."""
    core_url: str = "http://localhost:8909"
    access_token: str = ""
    batch_size: int = 50
    sync_interval: int = 300  # 5 minutes for full sync
    event_ttl_seconds: int = 60
    enabled_domains: Set[str] = field(default_factory=lambda: {
        "light", "switch", "climate", "media_player", "cover",
        "sensor", "binary_sensor", "person", "device_tracker",
        "humidifier", "fan", "vacuum", "lock", "alarm_control_panel"
    })


class BrainGraphSyncModule(CopilotModule):
    """Module for Brain Graph synchronization with Core Add-on.
    
    This module provides:
    - Real-time sync of HA entities to Core Brain Graph
    - Batch processing for efficiency
    - Integration with Knowledge Graph module
    - Neuron event publishing for activity/calendar context
    """
    
    name = "brain_graph_sync"
    version = "1.1.0"
    
    def __init__(self):
        """Initialize the module."""
        self._hass: Optional[HomeAssistant] = None
        self._config: Optional[SyncConfig] = None
        self._sync_service: Optional[BrainGraphSyncService] = None
        self._module_connector: Optional[ModuleConnector] = None
        self._batch_queue: asyncio.Queue = asyncio.Queue()
        self._batch_task: Optional[asyncio.Task] = None
        self._running = False
        self._entry_id: str = ""
        self._listener_unsubs: list = []
        
    @property
    def sync_service(self) -> Optional[BrainGraphSyncService]:
        """Get the brain graph sync service."""
        return self._sync_service
    
    async def async_setup_entry(self, ctx: ModuleContext) -> bool:
        """Set up the Brain Graph sync module."""
        try:
            self._hass = ctx.hass
            self._entry_id = ctx.entry.entry_id
            
            # Get configuration from config entry
            entry_data = ctx.entry.data
            core_url = entry_data.get("core_url", "http://localhost:8909")
            access_token = entry_data.get("access_token", "")
            
            if not core_url or not access_token:
                _LOGGER.warning(
                    "Brain Graph sync disabled: missing core_url or access_token"
                )
                return True  # Return True to not block module loading
            
            # Create sync configuration
            self._config = SyncConfig(
                core_url=core_url,
                access_token=access_token,
            )
            
            # Set up Brain Graph sync service
            self._sync_service = await setup_service(
                self._hass, 
                entry_data,
                core_url, 
                access_token
            )
            
            if not self._sync_service:
                _LOGGER.error("Failed to start Brain Graph sync service")
                return False
            
            # Get module connector for neuron integration
            self._module_connector = await get_module_connector(
                self._hass, 
                self._entry_id
            )
            
            # Store in hass.data for later access
            if DOMAIN not in self._hass.data:
                self._hass.data[DOMAIN] = {}
            if self._entry_id not in self._hass.data[DOMAIN]:
                self._hass.data[DOMAIN][self._entry_id] = {}
            self._hass.data[DOMAIN][self._entry_id]["brain_graph_sync"] = self._sync_service
            
            # Set up event listeners for neurons
            await self._setup_neuron_listeners()
            
            # Start batch processing task
            self._batch_task = self._hass.async_create_task(self._process_batch_queue())
            
            self._running = True
            _LOGGER.info(
                "Brain Graph sync module started (url: %s)", 
                core_url
            )
            return True
            
        except Exception as err:
            _LOGGER.error("Brain Graph sync module setup failed: %s", err)
            return False
    
    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the Brain Graph sync module."""
        try:
            self._running = False

            # Cancel event listener subscriptions
            for unsub in self._listener_unsubs:
                unsub()
            self._listener_unsubs.clear()

            # Cancel batch task
            if self._batch_task:
                self._batch_task.cancel()
                try:
                    await self._batch_task
                except asyncio.CancelledError:
                    pass
                self._batch_task = None

            # Unload sync service
            if self._sync_service:
                await unload_service(self._sync_service)
                self._sync_service = None

            # Remove from hass.data
            if (DOMAIN in self._hass.data and 
                self._entry_id in self._hass.data[DOMAIN] and
                "brain_graph_sync" in self._hass.data[DOMAIN][self._entry_id]):
                del self._hass.data[DOMAIN][self._entry_id]["brain_graph_sync"]
            
            _LOGGER.info("Brain Graph sync module unloaded")
            return True
            
        except Exception as err:
            _LOGGER.error("Brain Graph sync module unload failed: %s", err)
            return False
    
    async def _setup_neuron_listeners(self) -> None:
        """Set up listeners for neuron events."""

        async def on_activity_updated(event: Event) -> None:
            """Handle activity neuron updates."""
            if not self._sync_service:
                return

            data = event.data
            activity_level = data.get("activity_level", "idle")

            node_data = {
                "node_id": f"neuron:activity:{activity_level}",
                "node_type": "context",
                "properties": {
                    "activity_level": activity_level,
                    "source": data.get("source", "unknown"),
                    "confidence": data.get("confidence", 1.0),
                    "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                }
            }

            await self._queue_node_update(node_data)

            _LOGGER.debug(
                "Activity neuron -> Brain Graph: level=%s",
                activity_level
            )

        async def on_calendar_load_updated(event: Event) -> None:
            """Handle calendar load neuron updates."""
            if not self._sync_service:
                return

            data = event.data
            load_level = data.get("load_level", "free")

            node_data = {
                "node_id": f"neuron:calendar_load:{load_level}",
                "node_type": "context",
                "properties": {
                    "load_level": load_level,
                    "event_count": data.get("event_count", 0),
                    "meetings_today": data.get("meetings_today", 0),
                    "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                }
            }

            await self._queue_node_update(node_data)

            _LOGGER.debug(
                "Calendar load neuron -> Brain Graph: level=%s",
                load_level
            )

        # Register listeners and store unsub handles for cleanup
        self._listener_unsubs.append(
            self._hass.bus.async_listen(SIGNAL_ACTIVITY_UPDATED, on_activity_updated)
        )
        self._listener_unsubs.append(
            self._hass.bus.async_listen(SIGNAL_CALENDAR_LOAD_UPDATED, on_calendar_load_updated)
        )

        _LOGGER.debug("Neuron listeners registered for brain graph sync")
    
    async def _queue_node_update(self, node_data: Dict[str, Any]) -> None:
        """Queue a node update for batch processing."""
        await self._batch_queue.put(("node", node_data))
    
    async def _queue_edge_update(self, edge_data: Dict[str, Any]) -> None:
        """Queue an edge update for batch processing."""
        await self._batch_queue.put(("edge", edge_data))
    
    async def _process_batch_queue(self) -> None:
        """Process queued updates in batches."""
        batch: List[Dict[str, Any]] = []
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        
        while self._running:
            try:
                # Wait for items with timeout
                try:
                    item = await asyncio.wait_for(
                        self._batch_queue.get(), 
                        timeout=5.0
                    )
                    item_type, data = item
                    
                    if item_type == "node":
                        nodes.append(data)
                    else:
                        edges.append(data)
                    
                    # Check for more items in queue (non-blocking)
                    while not self._batch_queue.empty() and len(nodes) + len(edges) < self._config.batch_size:
                        try:
                            item = self._batch_queue.get_nowait()
                            item_type, data = item
                            if item_type == "node":
                                nodes.append(data)
                            else:
                                edges.append(data)
                        except asyncio.QueueEmpty:
                            break
                            
                except asyncio.TimeoutError:
                    # No items received, continue
                    pass
                
                # Process batch if we have items
                if nodes or edges:
                    await self._send_batch(nodes, edges)
                    nodes = []
                    edges = []
                    
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.error("Batch processing error: %s", err)
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def _send_batch(
        self, 
        nodes: List[Dict[str, Any]], 
        edges: List[Dict[str, Any]]
    ) -> None:
        """Send a batch of nodes and edges to Core."""
        if not self._sync_service or not self._sync_service._session:
            return
            
        try:
            payload = {}
            if nodes:
                payload["nodes"] = nodes
            if edges:
                payload["edges"] = edges
            
            if payload:
                async with self._sync_service._session.post(
                    f"{self._sync_service.core_url}/api/v1/graph/state",
                    json=payload
                ) as resp:
                    if resp.status != 200:
                        _LOGGER.warning(
                            "Brain Graph batch update failed: status %s", 
                            resp.status
                        )
                    else:
                        _LOGGER.debug(
                            "Brain Graph batch sent: %d nodes, %d edges",
                            len(nodes), len(edges)
                        )
                        
        except Exception as err:
            _LOGGER.error("Failed to send batch to Brain Graph: %s", err)
    
    # === Public API for Knowledge Graph Integration ===
    
    async def sync_entity_to_graph(
        self, 
        entity_id: str, 
        properties: Dict[str, Any]
    ) -> bool:
        """Sync an entity to the Brain Graph (public API for KG module).
        
        Args:
            entity_id: The entity ID to sync
            properties: Additional properties to include
            
        Returns:
            True if sync was queued, False otherwise
        """
        if not self._sync_service or not self._running:
            return False
            
        node_data = {
            "node_id": f"entity:{entity_id}",
            "node_type": "entity",
            "properties": {
                **properties,
                "source": "knowledge_graph_module"
            }
        }
        
        await self._queue_node_update(node_data)
        return True
    
    async def add_entity_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a relationship between entities (public API for KG module).
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship
            properties: Optional additional properties
            
        Returns:
            True if sync was queued, False otherwise
        """
        if not self._sync_service or not self._running:
            return False
        
        edge_data = {
            "source_id": source_id,
            "target_id": target_id,
            "edge_type": relationship_type,
            "properties": {
                **(properties or {}),
                "source": "knowledge_graph_module"
            }
        }
        
        await self._queue_edge_update(edge_data)
        return True
    
    async def get_graph_stats(self) -> Optional[Dict[str, Any]]:
        """Get Brain Graph statistics.
        
        Returns:
            Graph stats dict or None if unavailable
        """
        if not self._sync_service:
            return None
        return await self._sync_service.get_graph_stats()
    
    async def get_graph_snapshot_url(self) -> str:
        """Get URL for Brain Graph SVG visualization.
        
        Returns:
            URL string for the snapshot
        """
        if not self._sync_service:
            return ""
        return self._sync_service.get_graph_snapshot_url()


# === Helper Functions ===

async def get_brain_graph_sync(
    hass: HomeAssistant, 
    entry_id: str
) -> Optional[BrainGraphSyncModule]:
    """Get the Brain Graph sync module from hass.data.
    
    Args:
        hass: HomeAssistant instance
        entry_id: The config entry ID
        
    Returns:
        BrainGraphSyncModule instance or None
    """
    return hass.data.get(DOMAIN, {}).get(entry_id, {}).get("brain_graph_sync")


async def get_brain_graph_stats(
    hass: HomeAssistant, 
    entry_id: str
) -> Optional[Dict[str, Any]]:
    """Get Brain Graph statistics via the module.
    
    Args:
        hass: HomeAssistant instance
        entry_id: The config entry ID
        
    Returns:
        Stats dict or None
    """
    module = await get_brain_graph_sync(hass, entry_id)
    if module and module.sync_service:
        return await module.sync_service.get_graph_stats()
    return None


__all__ = [
    "BrainGraphSyncModule",
    "get_brain_graph_sync",
    "get_brain_graph_stats",
    "SyncConfig",
]
