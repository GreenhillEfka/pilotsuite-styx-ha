"""Appliance Fingerprint Sensor for Home Assistant (v5.12.0).

Exposes appliance fingerprinting data as an HA sensor.
State shows the count of known device fingerprints.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class ApplianceFingerprintSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing known appliance fingerprints and usage stats."""

    _attr_name = "Appliance Fingerprints"
    _attr_unique_id = "copilot_appliance_fingerprints"
    _attr_icon = "mdi:chart-timeline-variant-shimmer"
    _attr_native_unit_of_measurement = "devices"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    @property
    def native_value(self) -> int:
        return self._data.get("fingerprint_count", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "fingerprints": self._data.get("fingerprints", [])[:5],
            "usage_stats": self._data.get("usage_stats", [])[:5],
            "total_devices": self._data.get("fingerprint_count", 0),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"http://{self._host}:{self._port}/api/v1/energy"
        headers = {}
        token = self.coordinator._config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with session.get(
                f"{base}/fingerprints", headers=headers, timeout=15
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._data["fingerprints"] = [
                            {"id": fp["device_id"], "name": fp["device_name"],
                             "type": fp["device_type"], "avg_watts": fp["avg_power_watts"]}
                            for fp in data.get("fingerprints", [])
                        ]
                        self._data["fingerprint_count"] = data.get("count", 0)

            async with session.get(
                f"{base}/fingerprints/usage", headers=headers, timeout=15
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._data["usage_stats"] = [
                            {"id": s["device_id"], "name": s["device_name"],
                             "runs": s["total_runs"], "kwh": s["total_kwh"]}
                            for s in data.get("devices", [])
                        ]
        except Exception as exc:
            _LOGGER.error("Failed to fetch fingerprint data: %s", exc)
