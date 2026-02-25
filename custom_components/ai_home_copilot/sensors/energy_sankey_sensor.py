"""Energy Sankey Flow Sensor for PilotSuite.

Exposes energy flow data and Sankey SVG URL as a Home Assistant sensor.
Fetches flow data from Core API and makes it available for dashboards.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator
from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class EnergySankeySensor(CopilotBaseEntity):
    """Sensor exposing energy Sankey flow data from Core."""

    _attr_name = "Energy Sankey Flow"
    _attr_icon = "mdi:chart-sankey"

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "copilot_energy_sankey_flow"
        self._flow_data: dict[str, Any] | None = None

    @property
    def native_value(self) -> str | None:
        """Return flow summary as state."""
        if self._flow_data and self._flow_data.get("ok"):
            nodes = len(self._flow_data.get("nodes", []))
            flows = len(self._flow_data.get("flows", []))
            return f"{nodes} nodes, {flows} flows"
        return "unavailable"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return Sankey flow details."""
        attrs: dict[str, Any] = {
            "sankey_svg_url": f"{self._core_base_url()}/api/v1/energy/sankey.svg",
            "sankey_json_url": f"{self._core_base_url()}/api/v1/energy/sankey",
        }

        if self._flow_data and self._flow_data.get("ok"):
            summary = self._flow_data.get("summary", {})
            attrs["total_consumption_kwh"] = summary.get("total_consumption_kwh", 0)
            attrs["total_production_kwh"] = summary.get("total_production_kwh", 0)
            attrs["grid_kwh"] = summary.get("grid_kwh", 0)
            attrs["node_count"] = len(self._flow_data.get("nodes", []))
            attrs["flow_count"] = len(self._flow_data.get("flows", []))

            # Node labels for quick overview
            attrs["sources"] = [
                n["label"] for n in self._flow_data.get("nodes", [])
                if n.get("category") == "source"
            ]
            attrs["consumers"] = [
                n["label"] for n in self._flow_data.get("nodes", [])
                if n.get("category") in ("device", "zone")
            ]

        return attrs

    async def async_update(self) -> None:
        """Fetch Sankey data from Core API."""
        try:
            session = self.coordinator._session
            if session is None:
                return

            url = f"{self._core_base_url()}/api/v1/energy/sankey"
            headers = self._core_headers()

            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    self._flow_data = await resp.json()
                else:
                    _LOGGER.debug("Sankey API returned %s", resp.status)
        except Exception as e:
            _LOGGER.debug("Failed to fetch Sankey data: %s", e)
