"""Predictive Maintenance Sensor for Home Assistant (v6.1.0).

Exposes device health monitoring as an HA sensor.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class PredictiveMaintenanceSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing predictive maintenance summary."""

    _attr_name = "Device Health"
    _attr_unique_id = "copilot_device_health"
    _attr_icon = "mdi:wrench-cog"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._summary: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        return self._summary.get("avg_health_score")

    @property
    def icon(self) -> str:
        critical = self._summary.get("critical", 0)
        warning = self._summary.get("warning", 0)
        if critical > 0:
            return "mdi:wrench-clock"
        elif warning > 0:
            return "mdi:wrench-cog"
        return "mdi:check-decagram"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "total_devices": self._summary.get("total_devices", 0),
            "healthy": self._summary.get("healthy", 0),
            "degraded": self._summary.get("degraded", 0),
            "warning": self._summary.get("warning", 0),
            "critical": self._summary.get("critical", 0),
            "avg_health_score": self._summary.get("avg_health_score", 100),
            "devices_needing_attention": self._summary.get("devices_needing_attention", []),
            "upcoming_maintenance": self._summary.get("upcoming_maintenance", []),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"http://{self._host}:{self._port}/api/v1/hub"
        headers = {}
        token = self.coordinator._config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with session.get(
                f"{base}/maintenance", headers=headers, timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._summary = data
        except Exception as exc:
            _LOGGER.debug("Failed to fetch maintenance data: %s", exc)
