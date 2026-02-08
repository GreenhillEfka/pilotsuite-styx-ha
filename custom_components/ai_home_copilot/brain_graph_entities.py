"""Brain Graph sensor entities (v0.1 kernel).

Exposes brain graph node/edge counts as HA sensors for operator visibility.
Privacy-first: only aggregate counts, no raw data.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass

from .entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class BrainGraphNodeCountSensor(CopilotBaseEntity, SensorEntity):
    """Number of nodes currently in the Brain Graph."""

    _attr_name = "AI Home CoPilot brain graph nodes"
    _attr_unique_id = "ai_home_copilot_brain_graph_node_count"
    _attr_icon = "mdi:graph"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "nodes"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._cached: int | None = None

    @property
    def native_value(self) -> int | None:
        return self._cached

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"source": "brain_graph", "version": "0.1"}

    async def async_update(self) -> None:
        """Fetch brain graph state and extract node count."""
        try:
            data = await self.coordinator.api.async_get(
                "/api/v1/graph/state?limitNodes=500&limitEdges=1"
            )
            if isinstance(data, dict):
                nodes = data.get("nodes")
                self._cached = len(nodes) if isinstance(nodes, list) else 0
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Failed to fetch brain graph node count", exc_info=True)


class BrainGraphEdgeCountSensor(CopilotBaseEntity, SensorEntity):
    """Number of edges currently in the Brain Graph."""

    _attr_name = "AI Home CoPilot brain graph edges"
    _attr_unique_id = "ai_home_copilot_brain_graph_edge_count"
    _attr_icon = "mdi:graph-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "edges"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._cached: int | None = None

    @property
    def native_value(self) -> int | None:
        return self._cached

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"source": "brain_graph", "version": "0.1"}

    async def async_update(self) -> None:
        """Fetch brain graph state and extract edge count."""
        try:
            data = await self.coordinator.api.async_get(
                "/api/v1/graph/state?limitNodes=1&limitEdges=1500"
            )
            if isinstance(data, dict):
                edges = data.get("edges")
                self._cached = len(edges) if isinstance(edges, list) else 0
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Failed to fetch brain graph edge count", exc_info=True)
