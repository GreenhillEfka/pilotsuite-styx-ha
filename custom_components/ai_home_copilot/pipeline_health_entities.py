"""Pipeline Health sensor – single-entity overview of the full CoPilot pipeline.

Checks reachability of Core Add-on endpoints and exposes a consolidated
health state:
  - ``healthy``  – all components respond OK
  - ``degraded`` – some components unreachable
  - ``offline``  – Core not reachable at all

Attributes expose per-component status for debugging.
"""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity

from .entity import CopilotBaseEntity

if TYPE_CHECKING:
    from .coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class PipelineHealthSensor(CopilotBaseEntity, SensorEntity):
    """Consolidated pipeline health sensor."""

    _attr_name = "Pipeline Health"
    _attr_unique_id = "pipeline_health"
    _attr_icon = "mdi:heart-pulse"

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._components: dict[str, str] = {}
        self._last_check: str | None = None

    @property
    def native_value(self) -> str:
        """Return overall pipeline health state."""
        if not self.coordinator.data:
            return "offline"

        if self.coordinator.data.ok is not True:
            return "offline"

        # If we have component details, evaluate them.
        if self._components:
            statuses = list(self._components.values())
            if all(s == "ok" for s in statuses):
                return "healthy"
            if any(s == "ok" for s in statuses):
                return "degraded"
            return "offline"

        # Core is reachable but no component detail yet.
        return "healthy"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose per-component status as attributes."""
        attrs: dict[str, Any] = {}

        if self.coordinator.data:
            attrs["core_ok"] = self.coordinator.data.ok
            attrs["core_version"] = self.coordinator.data.version

        if self._components:
            attrs["components"] = dict(self._components)

        if self._last_check:
            attrs["last_deep_check"] = self._last_check

        return attrs

    async def async_update(self) -> None:
        """Run a deep health check against all Core API components."""
        await super().async_update()

        # Only deep-check if Core is reachable.
        if not self.coordinator.data or self.coordinator.data.ok is not True:
            self._components = {}
            return

        from datetime import datetime, timezone

        api = self.coordinator.api
        components: dict[str, str] = {}

        # 1) Candidates API
        try:
            resp = await api.async_get("/api/v1/candidates")
            components["candidates"] = "ok" if isinstance(resp, dict) and resp.get("ok") else "error"
        except Exception:  # noqa: BLE001
            components["candidates"] = "unreachable"

        # 2) Habitus Mining API
        try:
            resp = await api.async_get("/api/v1/habitus/status")
            components["habitus"] = "ok" if isinstance(resp, dict) else "error"
        except Exception:  # noqa: BLE001
            components["habitus"] = "unreachable"

        # 3) Brain Graph API
        try:
            resp = await api.async_get("/api/v1/graph/state")
            components["brain_graph"] = "ok" if isinstance(resp, dict) else "error"
        except Exception:  # noqa: BLE001
            components["brain_graph"] = "unreachable"

        # 4) Capabilities (general Core v1 readiness)
        try:
            resp = await api.async_get("/api/v1/capabilities")
            components["capabilities"] = "ok" if isinstance(resp, dict) else "error"
        except Exception:  # noqa: BLE001
            components["capabilities"] = "unreachable"

        self._components = components
        self._last_check = datetime.now(timezone.utc).isoformat()
