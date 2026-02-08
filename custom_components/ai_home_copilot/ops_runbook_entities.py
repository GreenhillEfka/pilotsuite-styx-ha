"""Ops Runbook sensor entity (v0.1 kernel).

Shows the last preflight-check result as a diagnostic sensor.
Privacy-first: only exposes ok/fail status + check count.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import CopilotBaseEntity


class OpsRunbookPreflightSensor(CopilotBaseEntity, SensorEntity):
    """Sensor that shows the latest preflight check status."""

    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot ops preflight"
    _attr_unique_id = "ai_home_copilot_ops_runbook_preflight"
    _attr_icon = "mdi:clipboard-check-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._last_result: dict | None = None

    def set_preflight_result(self, result: dict) -> None:
        """Called after a preflight check to update state."""
        self._last_result = result
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        if self._last_result is None:
            return "unknown"
        return "ok" if self._last_result.get("ok") else "issues"

    @property
    def extra_state_attributes(self) -> dict:
        if self._last_result is None:
            return {}
        checks = self._last_result.get("checks", [])
        return {
            "checks_total": len(checks),
            "checks_ok": sum(1 for c in checks if isinstance(c, dict) and c.get("ok")),
            "last_check_time": self._last_result.get("time", ""),
        }
