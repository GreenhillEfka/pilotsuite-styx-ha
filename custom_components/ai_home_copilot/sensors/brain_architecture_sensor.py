"""Brain Architecture Sensor for PilotSuite HA Integration (v7.4.0).

Displays brain health, region status, synapse connectivity, and neuron state.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)


class BrainArchitectureSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing brain architecture status."""

    _attr_name = "Brain Architecture"
    _attr_icon = "mdi:brain"
    _attr_unique_id = "pilotsuite_brain_architecture"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    async def _fetch(self) -> dict | None:
        import aiohttp
        try:
            url = f"{self._core_base_url()}/api/v1/hub/brain"
            headers = self._core_headers()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception:
            logger.debug("Failed to fetch brain architecture data")
        return None

    async def async_update(self) -> None:
        data = await self._fetch()
        if data and data.get("ok"):
            self._data = data

    @property
    def native_value(self) -> str:
        total = self._data.get("total_regions", 0)
        active = self._data.get("active_regions", 0)
        health = self._data.get("health_score", 0)
        if total == 0:
            return "Nicht initialisiert"
        if health >= 100:
            return f"{active}/{total} Regionen aktiv"
        return f"{active}/{total} Regionen — {health:.0f}% Gesundheit"

    @property
    def icon(self) -> str:
        health = self._data.get("health_score", 0)
        if health >= 80:
            return "mdi:brain"
        if health >= 50:
            return "mdi:head-alert"
        return "mdi:head-remove"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "total_regions": self._data.get("total_regions", 0),
            "active_regions": self._data.get("active_regions", 0),
            "total_neurons": self._data.get("total_neurons", 0),
            "total_synapses": self._data.get("total_synapses", 0),
            "active_synapses": self._data.get("active_synapses", 0),
            "connectivity_score": self._data.get("connectivity_score", 0),
            "health_score": self._data.get("health_score", 0),
        }

        regions = self._data.get("regions", [])
        if regions:
            attrs["regions"] = [
                {
                    "name": r.get("name_de"),
                    "color": r.get("color"),
                    "role": r.get("role"),
                    "active": r.get("active"),
                    "health": r.get("health"),
                }
                for r in regions
            ]

        synapses = self._data.get("synapses", [])
        if synapses:
            attrs["synapse_summary"] = {
                "active": sum(1 for s in synapses if s.get("state") == "active"),
                "dormant": sum(1 for s in synapses if s.get("state") == "dormant"),
                "total_fires": sum(s.get("fire_count", 0) for s in synapses),
            }

        graph = self._data.get("graph", {})
        if graph:
            attrs["graph_nodes"] = len(graph.get("nodes", []))
            attrs["graph_edges"] = len(graph.get("edges", []))

        return attrs
