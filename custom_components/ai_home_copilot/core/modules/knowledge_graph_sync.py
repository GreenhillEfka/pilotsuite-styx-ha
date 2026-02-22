"""Knowledge Graph Sync Module for PilotSuite.

Synchronizes Home Assistant entities to the Core Add-on Knowledge Graph.
Creates nodes for entities and relationships for:
- Entity → Area (BELONGS_TO)
- Entity → Zone (BELONGS_TO via Habitus Zones)
- Entity → Tags (HAS_TAG)
- Entity → Capabilities (HAS_CAPABILITY)
- Pattern → Mood (RELATES_TO_MOOD)

This module runs as a background sync that keeps the Knowledge Graph
in sync with HA state changes.

OPTIMIZATIONS:
- Batch node/edge creation for efficiency
- Dynamic entity discovery for state tracking
- Incremental sync (only changed entities)
- Brain Graph integration with graph state API
- Proper error handling and retry logic
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.area_registry import AreaEntry

from ..module import CopilotModule, ModuleContext
from ...connection_config import merged_entry_config
from ...api.knowledge_graph import (
    KnowledgeGraphClient,
    KnowledgeGraphError,
    NodeType,
    EdgeType,
    KGNode,
    KGEdge,
)

_LOGGER = logging.getLogger(__name__)

# Sync configuration
FULL_SYNC_INTERVAL = 3600  # 1 hour
BATCH_SIZE = 50  # Nodes/edges per batch request
RETRY_DELAY = 5  # Seconds between retries on failure
MAX_RETRIES = 3  # Max retries for failed operations

# Entity domains to sync (exclude transient/noise)
SYNC_DOMAINS = {
    "light", "switch", "binary_sensor", "sensor", "climate",
    "media_player", "cover", "fan", "humidifier", "vacuum",
    "lock", "alarm_control_panel", "camera", "input_boolean",
    "input_select", "input_number", "scene", "script",
}

# Capability mapping from entity attributes
CAPABILITY_ATTRS = {
    "brightness": "dimmable",
    "color_temp": "color_temp",
    "rgb_color": "color",
    "hs_color": "color",
    "xy_color": "color",
    "temperature": "temperature_sensor",
    "humidity": "humidity_sensor",
    "power": "power_metering",
    "battery": "battery_powered",
}


class KnowledgeGraphSyncModule(CopilotModule):
    """Module to sync Home Assistant entities to Knowledge Graph."""

    NAME = "knowledge_graph_sync"

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._entry_id: str | None = None
        self._client: Optional[KnowledgeGraphClient] = None
        self._entity_registry: Optional[er.EntityRegistry] = None
        self._area_registry: Optional[ar.AreaRegistry] = None
        self._sync_task: Optional[asyncio.Task] = None
        self._unsub_state_change: Optional[callable] = None
        self._unsub_area_change: Optional[callable] = None
        self._synced_entities: dict[str, int] = {}  # entity_id -> last_sync_time
        self._synced_areas: dict[str, int] = {}
        self._known_capabilities: set[str] = set()
        self._enabled: bool = True
        self._full_sync_interval: int = FULL_SYNC_INTERVAL
        self._last_full_sync: float = 0
        self._sync_lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return self.NAME

    async def async_setup_entry(self, ctx: ModuleContext) -> bool:
        """Runtime-compatible setup entry."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry.entry_id
        cfg = merged_entry_config(ctx.entry)
        self._enabled = bool(cfg.get("knowledge_graph_enabled", True))
        self._full_sync_interval = int(cfg.get("knowledge_graph_sync_interval", FULL_SYNC_INTERVAL))
        await self.async_setup()
        return True

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Runtime-compatible unload entry."""
        await self.async_unload()
        return True

    @property
    def client(self) -> KnowledgeGraphClient:
        """Get the Knowledge Graph client."""
        if self._client is None:
            raise RuntimeError("Knowledge Graph client not initialized")
        return self._client

    @property
    def graph_state(self) -> dict[str, Any]:
        """Get current graph state for Brain Graph panel."""
        nodes = []
        edges = []

        # Add entities as nodes
        for entity_id, last_sync in self._synced_entities.items():
            state = self._hass.states.get(entity_id)
            if state:
                nodes.append({
                    "id": entity_id,
                    "label": state.name or entity_id,
                    "kind": entity_id.split(".")[0],
                    "domain": entity_id.split(".")[0],
                    "zone": self._get_entity_zone(entity_id),
                    "score": 0.5,
                })

        # Add areas as nodes
        if self._area_registry:
            for area_id in self._synced_areas:
                area = self._area_registry.areas.get(area_id)
                if area:
                    nodes.append({
                        "id": f"area.{area_id}",
                        "label": area.name,
                        "kind": "area",
                        "domain": None,
                        "zone": None,
                        "score": 0.3,
                    })

        # Add entity → area edges
        if self._entity_registry:
            for entity_id in self._synced_entities:
                entry = self._entity_registry.async_get(entity_id)
                if entry and entry.area_id:
                    edges.append({
                        "from": entity_id,
                        "to": f"area.{entry.area_id}",
                        "type": "belongs_to",
                        "weight": 0.8,
                    })

        return {"nodes": nodes, "edges": edges}

    def _get_entity_zone(self, entity_id: str) -> Optional[str]:
        """Get the zone for an entity."""
        entry = self._entity_registry.async_get(entity_id) if self._entity_registry else None
        if entry and entry.area_id:
            area = self._area_registry.areas.get(entry.area_id) if self._area_registry else None
            return area.name if area else None
        return None

    async def async_setup(self) -> None:
        """Set up the module."""
        if self._hass is None:
            _LOGGER.warning("Knowledge Graph sync: no hass context")
            return
        if not self._enabled:
            _LOGGER.info("Knowledge Graph sync disabled")
            return

        # Get registries
        self._entity_registry = er.async_get(self._hass)
        self._area_registry = ar.async_get(self._hass)

        # Get API client from runtime
        runtime = self._hass.data.get("ai_home_copilot", {}).get("runtime")
        if runtime and hasattr(runtime, "api_client"):
            session = self._hass.helpers.aiohttp_client.async_get_clientsession()
            base_url = runtime.config.get("core_addon_url", "http://localhost:8909")
            token = runtime.config.get("token")
            self._client = KnowledgeGraphClient(session, base_url, token)
        else:
            _LOGGER.warning("Knowledge Graph sync: No API client available")
            return

        # Register for Brain Graph access
        if runtime and hasattr(runtime, "registry"):
            runtime.registry["knowledge_graph_sync"] = self

        # Initial sync with retry logic
        await self._async_initial_sync_with_retry()

        # Set up state change tracking
        self._setup_state_change_tracking()
        self._setup_area_registry_listeners()

        # Schedule periodic full sync
        self._sync_task = asyncio.create_task(self._async_periodic_sync())

        _LOGGER.info("Knowledge Graph sync module started (entities: %d, areas: %d)",
                    len(self._synced_entities), len(self._synced_areas))

    async def _async_initial_sync_with_retry(self) -> None:
        """Perform initial sync with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                await self._async_initial_sync()
                return
            except KnowledgeGraphError as err:
                _LOGGER.warning("Initial sync attempt %d failed: %s", attempt + 1, err)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        _LOGGER.error("Initial sync failed after %d attempts", MAX_RETRIES)

    def _setup_area_registry_listeners(self) -> None:
        """Set up listeners for area registry changes."""

        @callback
        def _area_added(event: Any) -> None:
            """Handle area added."""
            area: AreaEntry = event.data.get("area")
            if area:
                self._hass.async_create_task(self._async_sync_area(area))

        @callback
        def _area_updated(event: Any) -> None:
            """Handle area updated."""
            area: AreaEntry = event.data.get("area")
            if area:
                self._hass.async_create_task(self._async_sync_area(area))

        # Register listeners
        self._hass.bus.async_listen("area_registry_updated", _area_added)
        # Note: HA doesn't have specific add/update events, using updated trigger

    async def _async_sync_area(self, area: AreaEntry) -> None:
        """Sync a single area to Knowledge Graph."""
        try:
            node = KGNode(
                id=f"area.{area.area_id}",
                type=NodeType.AREA,
                label=area.name,
                properties={
                    "area_id": area.area_id,
                    "icon": area.icon,
                }
            )
            await self.client.create_node(node)
            self._synced_areas[area.area_id] = int(time.time())
            _LOGGER.debug("Synced area: %s", area.name)
        except KnowledgeGraphError as err:
            if "already exists" not in str(err).lower():
                _LOGGER.warning("Failed to sync area %s: %s", area.area_id, err)

    async def async_unload(self) -> None:
        """Unload the module."""
        if self._unsub_state_change:
            self._unsub_state_change()
            self._unsub_state_change = None

        if self._unsub_area_change:
            self._unsub_area_change()
            self._unsub_area_change = None

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        _LOGGER.info("Knowledge Graph sync module unloaded")

    def _setup_state_change_tracking(self) -> None:
        """Set up tracking for entity state changes using wildcard."""

        @callback
        def _state_changed(entity_id: str, old_state, new_state) -> None:
            """Handle entity state change."""
            domain = entity_id.split(".")[0]
            if domain not in SYNC_DOMAINS:
                return

            # Schedule async update
            self._hass.async_create_task(
                self._async_handle_entity_change(entity_id, old_state, new_state)
            )

        # Track all state changes - more efficient than tracking specific entities
        self._unsub_state_change = async_track_state_change(
            self._hass, None, _state_changed  # None = all entities
        )

    async def _async_handle_entity_change(
        self,
        entity_id: str,
        old_state,
        new_state,
    ) -> None:
        """Handle entity state change with proper error handling."""
        async with self._sync_lock:
            try:
                if entity_id not in self._synced_entities:
                    # New entity - full sync
                    await self._async_sync_entity(entity_id)
                else:
                    # Existing entity - update state and capabilities
                    await self._async_update_entity_state(entity_id, new_state)

                # Update sync timestamp
                self._synced_entities[entity_id] = int(time.time())

            except KnowledgeGraphError as err:
                _LOGGER.warning("Failed to sync entity %s: %s", entity_id, err)
            except Exception as err:
                _LOGGER.error("Unexpected error syncing entity %s: %s", entity_id, err)

    async def _async_initial_sync(self) -> None:
        """Perform initial sync of all entities."""
        _LOGGER.info("Starting initial Knowledge Graph sync...")

        # Sync all areas first
        await self._async_sync_areas()

        # Collect all entities to sync
        entities_to_sync = []
        for state in self._hass.states.async_all():
            domain = state.entity_id.split(".")[0]
            if domain in SYNC_DOMAINS:
                entities_to_sync.append(state.entity_id)

        # Sync in batches
        for i in range(0, len(entities_to_sync), BATCH_SIZE):
            batch = entities_to_sync[i:i + BATCH_SIZE]
            await self._async_batch_sync_entities(batch)
            _LOGGER.debug("Synced batch %d/%d", i // BATCH_SIZE + 1,
                         (len(entities_to_sync) + BATCH_SIZE - 1) // BATCH_SIZE)

        _LOGGER.info("Initial sync complete: %d entities, %d areas",
                    len(self._synced_entities), len(self._synced_areas))

    async def _async_batch_sync_entities(self, entity_ids: list[str]) -> None:
        """Sync a batch of entities efficiently."""
        nodes_to_create = []
        edges_to_create = []
        capabilities_by_entity: dict[str, set[str]] = {}

        for entity_id in entity_ids:
            state = self._hass.states.get(entity_id)
            if not state:
                continue

            entity_entry = self._entity_registry.async_get(entity_id)
            domain = entity_id.split(".")[0]

            # Build node
            node = KGNode(
                id=entity_id,
                type=NodeType.ENTITY,
                label=entity_entry.name if entity_entry and entity_entry.name else state.name,
                properties={
                    "domain": domain,
                    "state": state.state,
                    "device_class": state.attributes.get("device_class"),
                    "unit_of_measurement": state.attributes.get("unit_of_measurement"),
                    "last_changed": state.last_changed.isoformat() if state.last_changed else None,
                }
            )
            nodes_to_create.append(node)

            # Collect capabilities
            capabilities = self._extract_capabilities(entity_id, state)
            capabilities_by_entity[entity_id] = capabilities

            # Area relationship
            area_id = entity_entry.area_id if entity_entry else None
            if area_id:
                edges_to_create.append(KGEdge(
                    source=entity_id,
                    target=f"area.{area_id}",
                    type=EdgeType.BELONGS_TO,
                ))

        # Create capability nodes (once per unique capability)
        for cap in set().union(*capabilities_by_entity.values()):
            if cap not in self._known_capabilities:
                nodes_to_create.append(KGNode(
                    id=f"cap.{cap}",
                    type=NodeType.CAPABILITY,
                    label=cap.replace("_", " ").title(),
                ))
                self._known_capabilities.add(cap)

        # Create capability edges
        for entity_id, caps in capabilities_by_entity.items():
            for cap in caps:
                edges_to_create.append(KGEdge(
                    source=entity_id,
                    target=f"cap.{cap}",
                    type=EdgeType.HAS_CAPABILITY,
                ))

        # Batch create nodes (if API supports it, otherwise sequential)
        try:
            for node in nodes_to_create:
                try:
                    await self.client.create_node(node)
                    self._synced_entities[node.id] = int(time.time())
                except KnowledgeGraphError as err:
                    if "already exists" not in str(err).lower():
                        _LOGGER.debug("Node create error (may be OK): %s", err)
        except Exception as err:
            _LOGGER.warning("Batch node sync failed, falling back: %s", err)

        # Batch create edges
        try:
            for edge in edges_to_create:
                try:
                    await self.client.create_edge(edge)
                except KnowledgeGraphError as err:
                    if "already exists" not in str(err).lower():
                        _LOGGER.debug("Edge create error (may be OK): %s", err)
        except Exception as err:
            _LOGGER.warning("Batch edge sync failed: %s", err)

    async def _async_periodic_sync(self) -> None:
        """Periodic incremental sync task."""
        while True:
            try:
                await asyncio.sleep(self._full_sync_interval)

                # Check if we need a full sync or incremental
                now = time.time()
                if now - self._last_full_sync >= self._full_sync_interval:
                    _LOGGER.info("Starting periodic full Knowledge Graph sync...")
                    await self._async_initial_sync_with_retry()
                    self._last_full_sync = now
                else:
                    # Incremental sync - only sync entities changed since last sync
                    _LOGGER.info("Starting incremental Knowledge Graph sync...")
                    await self._async_incremental_sync()

            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.error("Periodic sync failed: %s", err)
                await asyncio.sleep(60)

    async def _async_incremental_sync(self) -> None:
        """Sync only entities that have changed since last full sync."""
        entities_to_sync = []

        for state in self._hass.states.async_all():
            domain = state.entity_id.split(".")[0]
            if domain not in SYNC_DOMAINS:
                continue

            last_sync = self._synced_entities.get(state.entity_id, 0)
            last_changed = state.last_changed.timestamp() if state.last_changed else 0

            if last_changed > last_sync:
                entities_to_sync.append(state.entity_id)

        if entities_to_sync:
            _LOGGER.info("Incremental sync: %d changed entities", len(entities_to_sync))
            for i in range(0, len(entities_to_sync), BATCH_SIZE):
                batch = entities_to_sync[i:i + BATCH_SIZE]
                await self._async_batch_sync_entities(batch)

    async def _async_sync_areas(self) -> None:
        """Sync all areas to Knowledge Graph."""
        if not self._area_registry:
            return

        for area_id, area in self._area_registry.areas.items():
            try:
                node = KGNode(
                    id=f"area.{area_id}",
                    type=NodeType.AREA,
                    label=area.name,
                    properties={
                        "area_id": area_id,
                        "icon": area.icon,
                    }
                )
                await self.client.create_node(node)
                self._synced_areas[area_id] = int(time.time())
                _LOGGER.debug("Synced area: %s", area.name)
            except KnowledgeGraphError as err:
                if "already exists" not in str(err).lower():
                    _LOGGER.warning("Failed to sync area %s: %s", area_id, err)

    async def _async_sync_entity(self, entity_id: str) -> bool:
        """Sync a single entity to Knowledge Graph."""
        if not self._entity_registry:
            return False

        state = self._hass.states.get(entity_id)
        if not state:
            return False

        domain = entity_id.split(".")[0]

        try:
            # Get entity from registry
            entity_entry = self._entity_registry.async_get(entity_id)

            # Create entity node
            node = KGNode(
                id=entity_id,
                type=NodeType.ENTITY,
                label=entity_entry.name if entity_entry and entity_entry.name else state.name,
                properties={
                    "domain": domain,
                    "state": state.state,
                    "device_class": state.attributes.get("device_class"),
                    "unit_of_measurement": state.attributes.get("unit_of_measurement"),
                }
            )
            await self.client.create_node(node)
            self._synced_entities[entity_id] = int(time.time())

            # Create area relationship
            area_id = entity_entry.area_id if entity_entry else None
            if area_id:
                await self.client.add_relationship(
                    entity_id,
                    f"area.{area_id}",
                    EdgeType.BELONGS_TO,
                )

            # Sync capabilities
            await self._async_sync_entity_capabilities(entity_id, state)

            _LOGGER.debug("Synced entity: %s", entity_id)
            return True

        except KnowledgeGraphError as err:
            if "already exists" not in str(err).lower():
                _LOGGER.warning("Failed to sync entity %s: %s", entity_id, err)
            return False

    async def _async_update_entity_state(self, entity_id: str, new_state) -> None:
        """Update entity state in Knowledge Graph."""
        if new_state is None:
            return

        # Get existing node and update properties
        try:
            existing = await self.client.get_node(entity_id)
            if existing:
                # Update node with new state
                updated = KGNode(
                    id=entity_id,
                    type=existing.type,
                    label=existing.label,
                    properties={
                        **existing.properties,
                        "state": new_state.state,
                        "last_changed": new_state.last_changed.isoformat() if new_state.last_changed else None,
                    }
                )
                await self.client.create_node(updated)  # Upsert

            # Update capabilities if they might have changed
            await self._async_sync_entity_capabilities(entity_id, new_state)

        except KnowledgeGraphError as err:
            _LOGGER.debug("Failed to update entity state %s: %s", entity_id, err)

    def _extract_capabilities(self, entity_id: str, state) -> set[str]:
        """Extract capabilities from entity state."""
        capabilities = set()

        # Check for capability attributes
        for attr, cap_name in CAPABILITY_ATTRS.items():
            if state.attributes.get(attr) is not None:
                capabilities.add(cap_name)

        # Check supported_features for lights
        if entity_id.startswith("light."):
            supported = state.attributes.get("supported_features", 0)
            if supported & 1:  # SUPPORT_BRIGHTNESS
                capabilities.add("dimmable")
            if supported & 4:  # SUPPORT_COLOR_TEMP
                capabilities.add("color_temp")
            if supported & 16:  # SUPPORT_COLOR
                capabilities.add("color")

        return capabilities

    async def _async_sync_entity_capabilities(self, entity_id: str, state) -> None:
        """Sync entity capabilities as nodes and edges."""
        capabilities = self._extract_capabilities(entity_id, state)

        # Create capability nodes and edges
        for cap in capabilities:
            try:
                # Create capability node (idempotent)
                if cap not in self._known_capabilities:
                    cap_node = KGNode(
                        id=f"cap.{cap}",
                        type=NodeType.CAPABILITY,
                        label=cap.replace("_", " ").title(),
                    )
                    await self.client.create_node(cap_node)
                    self._known_capabilities.add(cap)

                # Create edge
                await self.client.add_relationship(
                    entity_id,
                    f"cap.{cap}",
                    EdgeType.HAS_CAPABILITY,
                )
            except KnowledgeGraphError:
                pass  # Ignore errors for capabilities

    async def async_sync_zone(self, zone_id: str, zone_name: str, entities: list[str]) -> None:
        """Sync a Habitus zone to the Knowledge Graph."""
        try:
            # Create zone node
            zone_node = KGNode(
                id=f"zone.{zone_id}",
                type=NodeType.ZONE,
                label=zone_name,
                properties={"entity_count": len(entities)},
            )
            await self.client.create_node(zone_node)

            # Create edges from entities to zone
            for entity_id in entities:
                await self.client.add_relationship(
                    entity_id,
                    f"zone.{zone_id}",
                    EdgeType.BELONGS_TO,
                )

            _LOGGER.info("Synced zone %s with %d entities", zone_name, len(entities))

        except KnowledgeGraphError as err:
            _LOGGER.error("Failed to sync zone %s: %s", zone_id, err)

    async def async_sync_tag(self, entity_id: str, tag: str) -> None:
        """Sync an entity tag to the Knowledge Graph."""
        try:
            # Create tag node
            tag_node = KGNode(
                id=f"tag.{tag}",
                type=NodeType.TAG,
                label=tag,
            )
            await self.client.create_node(tag_node)

            # Create edge
            await self.client.add_relationship(
                entity_id,
                f"tag.{tag}",
                EdgeType.HAS_TAG,
            )

        except KnowledgeGraphError as err:
            if "already exists" not in str(err).lower():
                _LOGGER.warning("Failed to sync tag %s: %s", tag, err)

    async def async_sync_mood_relation(
        self,
        entity_id: str,
        mood: str,
        weight: float = 1.0,
        confidence: float = 0.5,
    ) -> None:
        """Sync an entity-mood relationship to the Knowledge Graph."""
        try:
            # Create mood node
            mood_node = KGNode(
                id=f"mood.{mood}",
                type=NodeType.MOOD,
                label=mood.capitalize(),
            )
            await self.client.create_node(mood_node)

            # Create edge with weight and confidence
            await self.client.add_relationship(
                entity_id,
                f"mood.{mood}",
                EdgeType.RELATES_TO_MOOD,
                weight=weight,
                confidence=confidence,
            )

        except KnowledgeGraphError as err:
            _LOGGER.warning("Failed to sync mood relation %s→%s: %s", entity_id, mood, err)

    async def async_get_related_entities(
        self,
        entity_id: str,
        max_results: int = 10,
    ) -> list[dict]:
        """Get entities related to a given entity from the Knowledge Graph."""
        try:
            result = await self.client.find_related(entity_id, max_results=max_results)
            return [
                {
                    "entity_id": node.id,
                    "label": node.label,
                    "type": node.type.value,
                    "confidence": result.confidence,
                }
                for node in result.nodes
                if node.type == NodeType.ENTITY and node.id != entity_id
            ]
        except KnowledgeGraphError as err:
            _LOGGER.warning("Failed to get related entities for %s: %s", entity_id, err)
            return []

    async def async_get_mood_entities(
        self,
        mood: str,
        max_results: int = 20,
    ) -> list[dict]:
        """Get entities related to a mood from the Knowledge Graph."""
        try:
            result = await self.client.find_by_mood(mood, max_results=max_results)
            return [
                {
                    "entity_id": node.id,
                    "label": node.label,
                    "confidence": edge.confidence,
                }
                for node, edge in zip(result.nodes, result.edges)
                if node.type == NodeType.ENTITY
            ]
        except KnowledgeGraphError as err:
            _LOGGER.warning("Failed to get mood entities for %s: %s", mood, err)
            return []

    async def async_get_graph_stats(self) -> dict[str, Any]:
        """Get sync statistics."""
        try:
            stats = await self.client.get_stats()
            return {
                "kg_stats": {
                    "node_count": stats.node_count,
                    "edge_count": stats.edge_count,
                    "nodes_by_type": stats.nodes_by_type,
                    "edges_by_type": stats.edges_by_type,
                },
                "sync_status": {
                    "synced_entities": len(self._synced_entities),
                    "synced_areas": len(self._synced_areas),
                    "known_capabilities": len(self._known_capabilities),
                    "last_full_sync": self._last_full_sync,
                }
            }
        except KnowledgeGraphError as err:
            _LOGGER.warning("Failed to get graph stats: %s", err)
            return {
                "sync_status": {
                    "synced_entities": len(self._synced_entities),
                    "synced_areas": len(self._synced_areas),
                    "known_capabilities": len(self._known_capabilities),
                    "last_full_sync": self._last_full_sync,
                }
            }


async def async_get_knowledge_graph_sync(hass: HomeAssistant) -> Optional[KnowledgeGraphSyncModule]:
    """Get the Knowledge Graph sync module from runtime."""
    runtime = hass.data.get("ai_home_copilot", {}).get("runtime")
    if runtime and hasattr(runtime, "registry"):
        return runtime.registry.get("knowledge_graph_sync")
    return None


async def async_get_brain_graph_data(hass: HomeAssistant) -> dict[str, Any]:
    """Get Brain Graph data from the sync module."""
    module = await async_get_knowledge_graph_sync(hass)
    if module:
        return module.graph_state
    return {"nodes": [], "edges": []}


__all__ = [
    "KnowledgeGraphSyncModule",
    "async_get_knowledge_graph_sync",
    "async_get_brain_graph_data",
]
