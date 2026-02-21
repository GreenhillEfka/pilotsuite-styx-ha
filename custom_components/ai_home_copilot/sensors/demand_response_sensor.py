"""Demand Response Sensor for Home Assistant (v5.14.0).

Exposes demand response status as an HA sensor.
State shows current grid signal level.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)

SIGNAL_LABELS = {0: "Normal", 1: "Advisory", 2: "Moderate", 3: "Critical"}
SIGNAL_ICONS = {
    0: "mdi:transmission-tower",
    1: "mdi:alert-circle-outline",
    2: "mdi:alert",
    3: "mdi:alert-octagon",
}


class DemandResponseSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing demand response status."""

    _attr_name = "Demand Response"
    _attr_unique_id = "copilot_demand_response"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}
        self._signal_level = 0

    @property
    def native_value(self) -> str:
        return SIGNAL_LABELS.get(self._signal_level, "Unknown")

    @property
    def icon(self) -> str:
        return SIGNAL_ICONS.get(self._signal_level, "mdi:transmission-tower")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "signal_level": self._signal_level,
            "active_signals": self._data.get("active_signals", 0),
            "managed_devices": self._data.get("managed_devices", 0),
            "curtailed_devices": self._data.get("curtailed_devices", 0),
            "total_reduction_watts": self._data.get("total_reduction_watts", 0),
            "response_active": self._data.get("response_active", False),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        url = f"http://{self._host}:{self._port}/api/v1/energy/demand-response/status"
        headers = {}
        token = self.coordinator._config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._data = data
                        self._signal_level = data.get("current_signal", 0)
                else:
                    _LOGGER.warning("Demand response API returned %s", resp.status)
        except Exception as exc:
            _LOGGER.error("Failed to fetch demand response status: %s", exc)
