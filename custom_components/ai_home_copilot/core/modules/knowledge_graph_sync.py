"""Knowledge Graph Sync Module for AI Home CoPilot.

Synchronizes Home Assistant entities to the Core Add-on Knowledge Graph.
Creates nodes for entities and relationships for:
- Entity → Area (BELONGS_TO)
- Entity → Zone (BELONGS_TO via Habitus Zones)
- Entity → Tags (HAS_TAG)
- Entity → Capabilities (HAS_CAPABILITY)
- Pattern → Mood (RELATES_TO_MOOD)

This module runs as a background sync that keeps the Knowledge Graph
in sync with HA state changes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.event import async_track_state_change

from ..module import CopilotModule
from ...api.knowledge_graph import (
    KnowledgeGraphClient,
    KnowledgeGraphError,
    NodeType,
    EdgeType,
    KGNode,
    KGEdge,
)

_LOGGER = logging.getLogger(__name__)

# Sync interval for full sync (seconds)
FULL_SYNC_INTERVAL = 3600  # 1 hour

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

    def __init__(self, hass: HomeAssistant, config: dict):
        super().__init__(hass, config)
        self._client: Optional[KnowledgeGraphClient] = None
        self._entity_registry: Optional[er.EntityRegistry] = None
        self._area_registry: Optional[ar.AreaRegistry] = None
        self._sync_task: Optional[asyncio.Task] = None
        self._unsub_state_change: Optional[callable] = None
        self._synced_entities: set[str] = set()
        self._synced_areas: set[str] = set()
        self._enabled: bool = config.get("knowledge_graph_enabled", True)
        self._full_sync_interval: int = config.get("knowledge_graph_sync_interval", FULL_SYNC_INTERVAL)

    @property
    def client(self) -> KnowledgeGraphClient:
        """Get the Knowledge Graph client."""
        if self._client is None:
            raise RuntimeError("Knowledge Graph client not initialized")
        return self._client

    async def async_setup(self) -> None:
        """Set up the module."""
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
            base_url = runtime.config.get("core_addon_url", "http://localhost:8099")
            token = runtime.config.get("token")
            self._client = KnowledgeGraphClient(session, base_url, token)
        else:
            _LOGGER.warning("Knowledge Graph sync: No API client available")
            return

        # Initial sync
        await self._async_initial_sync()

        # Set up state change tracking
        self._setup_state_change_tracking()

        # Schedule periodic full sync
        self._sync_task = asyncio.create_task(self._async_periodic_sync())

        _LOGGER.info("Knowledge Graph sync module started")

    async def async_unload(self) -> None:
        """Unload the module."""
        if self._unsub_state_change:
            self._unsub_state_change()
            self._unsub_state_change = None

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        _LOGGER.info("Knowledge Graph sync module unloaded")

    def _setup_state_change_tracking(self) -> None:
        """Set up tracking for entity state changes."""

        @callback
        def _state_changed(entity_id: str, old_state, new_state) -> None:
            """Handle entity state change."""
            if entity_id not in self._synced_entities:
                # New entity, sync it
                self._hass.async_create_task(self._async_sync_entity(entity_id))
            else:
                # Check for capability changes
                self._hass.async_create_task(self._async_update_entity_capabilities(entity_id, new_state))

        # Track state changes for all relevant domains
        entity_ids = []
        for state in self._hass.states.async_all():
            domain = state.entity_id.split(".")[0]
            if domain in SYNC_DOMAINS:
                entity_ids.append(state.entity_id)

        if entity_ids:
            self._unsub_state_change = async_track_state_change(
                self._hass, entity_ids, _state_changed
            )

    async def _async_initial_sync(self) -> None:
        """Perform initial sync of all entities."""
        _LOGGER.info("Starting initial Knowledge Graph sync...")

        try:
            # Sync all areas first
            await self._async_sync_areas()

            # Sync all entities
            entity_count = 0
            for state in self._hass.states.async_all():
                domain = state.entity_id.split(".")[0]
                if domain in SYNC_DOMAINS:
                    await self._async_sync_entity(state.entity_id)
                    entity_count += 1

            _LOGGER.info("Initial sync complete: %d entities, %d areas",
                        entity_count, len(self._synced_areas))

        except KnowledgeGraphError as err:
            _LOGGER.error("Knowledge Graph sync failed: %s", err)

    async def _async_periodic_sync(self) -> None:
        """Periodic full sync task."""
        while True:
            try:
                await asyncio.sleep(self._full_sync_interval)
                _LOGGER.info("Starting periodic Knowledge Graph sync...")
                await self._async_initial_sync()
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.error("Periodic sync failed: %s", err)
                await asyncio.sleep(60)  # Retry after 1 minute on error

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
                self._synced_areas.add(area_id)
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
            self._synced_entities.add(entity_id)

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

    async def _async_sync_entity_capabilities(self, entity_id: str, state) -> None:
        """Sync entity capabilities as nodes and edges."""
        capabilities = []

        # Check for capability attributes
        for attr, cap_name in CAPABILITY_ATTRS.items():
            if state.attributes.get(attr) is not None:
                capabilities.append(cap_name)

        # Check supported_features for lights
        if entity_id.startswith("light."):
            supported = state.attributes.get("supported_features", 0)
            if supported & 1:  # SUPPORT_BRIGHTNESS
                capabilities.append("dimmable")
            if supported & 4:  # SUPPORT_COLOR_TEMP
                capabilities.append("color_temp")
            if supported & 16:  # SUPPORT_COLOR
                capabilities.append("color")

        # Create capability nodes and edges
        for cap in set(capabilities):
            try:
                # Create capability node (idempotent)
                cap_node = KGNode(
                    id=f"cap.{cap}",
                    type=NodeType.CAPABILITY,
                    label=cap.replace("_", " ").title(),
                )
                await self.client.create_node(cap_node)

                # Create edge
                await self.client.add_relationship(
                    entity_id,
                    f"cap.{cap}",
                    EdgeType.HAS_CAPABILITY,
                )
            except KnowledgeGraphError:
                pass  # Ignore errors for capabilities

    async def _async_update_entity_capabilities(self, entity_id: str, new_state) -> None:
        """Update entity capabilities when state changes."""
        if new_state is None:
            return

        await self._async_sync_entity_capabilities(entity_id, new_state)

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


async def async_get_knowledge_graph_sync(hass: HomeAssistant) -> Optional[KnowledgeGraphSyncModule]:
    """Get the Knowledge Graph sync module from runtime."""
    runtime = hass.data.get("ai_home_copilot", {}).get("runtime")
    if runtime and hasattr(runtime, "registry"):
        return runtime.registry.get("knowledge_graph_sync")
    return None


__all__ = [
    "KnowledgeGraphSyncModule",
    "async_get_knowledge_graph_sync",
]