"""Knowledge Graph sensors for PilotSuite.

Provides sensors to monitor Knowledge Graph state:
- Node count
- Edge count
- Sync status
- Last sync time
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class KnowledgeGraphStatsSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing Knowledge Graph statistics."""

    _attr_icon = "mdi:graph"
    _attr_native_unit_of_measurement = None

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_kg_stats"
        self._attr_name = "Knowledge Graph Stats"

    @property
    def native_value(self) -> str | None:
        """Return the sensor value."""
        data = self.coordinator.data or {}
        kg_data = data.get("knowledge_graph", {})
        if kg_data.get("ok"):
            return "connected"
        return "disconnected"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self.coordinator.data or {}
        kg_data = data.get("knowledge_graph", {})
        stats = kg_data.get("stats", {})

        return {
            "node_count": stats.get("node_count", 0),
            "edge_count": stats.get("edge_count", 0),
            "nodes_by_type": stats.get("nodes_by_type", {}),
            "edges_by_type": stats.get("edges_by_type", {}),
            "last_updated": stats.get("last_updated"),
            "last_sync": kg_data.get("last_sync"),
            "sync_status": kg_data.get("sync_status", "unknown"),
        }


class KnowledgeGraphNodeCountSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing total node count in Knowledge Graph."""

    _attr_icon = "mdi:graph-node"
    _attr_native_unit_of_measurement = "nodes"

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_kg_nodes"
        self._attr_name = "Knowledge Graph Nodes"

    @property
    def native_value(self) -> int:
        """Return the sensor value."""
        data = self.coordinator.data or {}
        kg_data = data.get("knowledge_graph", {})
        stats = kg_data.get("stats", {})
        return stats.get("node_count", 0)


class KnowledgeGraphEdgeCountSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing total edge count in Knowledge Graph."""

    _attr_icon = "mdi:graph-edge"
    _attr_native_unit_of_measurement = "edges"

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_kg_edges"
        self._attr_name = "Knowledge Graph Edges"

    @property
    def native_value(self) -> int:
        """Return the sensor value."""
        data = self.coordinator.data or {}
        kg_data = data.get("knowledge_graph", {})
        stats = kg_data.get("stats", {})
        return stats.get("edge_count", 0)


class KnowledgeGraphSyncStatusSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing Knowledge Graph sync status."""

    _attr_icon = "mdi:sync"

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_kg_sync_status"
        self._attr_name = "Knowledge Graph Sync Status"

    @property
    def native_value(self) -> str:
        """Return the sensor value."""
        data = self.coordinator.data or {}
        kg_data = data.get("knowledge_graph", {})
        return kg_data.get("sync_status", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self.coordinator.data or {}
        kg_data = data.get("knowledge_graph", {})

        return {
            "last_sync": kg_data.get("last_sync"),
            "synced_entities": kg_data.get("synced_entities", 0),
            "synced_areas": kg_data.get("synced_areas", 0),
            "error": kg_data.get("error"),
        }


class KnowledgeGraphLastSyncSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing when Knowledge Graph was last synced."""

    _attr_icon = "mdi:clock-outline"
    _attr_device_class = "timestamp"

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_kg_last_sync"
        self._attr_name = "Knowledge Graph Last Sync"

    @property
    def native_value(self) -> str | None:
        """Return the sensor value."""
        data = self.coordinator.data or {}
        kg_data = data.get("knowledge_graph", {})
        return kg_data.get("last_sync")


async def async_setup_knowledge_graph_sensors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Knowledge Graph sensors."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator") if isinstance(data, dict) else None
    if coordinator is None:
        _LOGGER.error("Coordinator not available for %s, skipping knowledge_graph setup", entry.entry_id)
        return

    entities = [
        KnowledgeGraphStatsSensor(coordinator, entry),
        KnowledgeGraphNodeCountSensor(coordinator, entry),
        KnowledgeGraphEdgeCountSensor(coordinator, entry),
        KnowledgeGraphSyncStatusSensor(coordinator, entry),
        KnowledgeGraphLastSyncSensor(coordinator, entry),
    ]

    async_add_entities(entities)


__all__ = [
    "KnowledgeGraphStatsSensor",
    "KnowledgeGraphNodeCountSensor",
    "KnowledgeGraphEdgeCountSensor",
    "KnowledgeGraphSyncStatusSensor",
    "KnowledgeGraphLastSyncSensor",
    "async_setup_knowledge_graph_sensors",
]