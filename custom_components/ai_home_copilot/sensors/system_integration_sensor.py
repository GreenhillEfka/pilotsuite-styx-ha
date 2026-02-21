"""System Integration Sensor for PilotSuite HA Integration (v7.3.0).

Displays cross-engine integration status, wiring diagram, and event flow.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)


class SystemIntegrationSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing system integration hub status."""

    _attr_name = "System Integration"
    _attr_icon = "mdi:hub"
    _attr_unique_id = "pilotsuite_system_integration"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    async def _fetch(self) -> dict | None:
        import aiohttp
        try:
            url = f"http://{self._host}:{self._port}/api/v1/hub/integration"
            headers = {"Authorization": f"Bearer {self.coordinator._config.get('token', '')}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception:
            logger.debug("Failed to fetch system integration data")
        return None

    async def async_update(self) -> None:
        data = await self._fetch()
        if data and data.get("ok"):
            self._data = data

    @property
    def native_value(self) -> str:
        engines = self._data.get("engines_connected", 0)
        subs = self._data.get("active_subscriptions", 0)
        if engines == 0:
            return "Nicht verbunden"
        return f"{engines} Engines / {subs} Verknüpfungen"

    @property
    def icon(self) -> str:
        engines = self._data.get("engines_connected", 0)
        events = self._data.get("events_processed", 0)
        if engines == 0:
            return "mdi:hub-outline"
        if events > 0:
            return "mdi:hub"
        return "mdi:hub-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "engines_connected": self._data.get("engines_connected", 0),
            "events_processed": self._data.get("events_processed", 0),
            "active_subscriptions": self._data.get("active_subscriptions", 0),
            "last_event": self._data.get("last_event", ""),
            "last_event_time": self._data.get("last_event_time", ""),
            "engine_names": self._data.get("engine_names", []),
        }

        wiring = self._data.get("wiring_diagram", {})
        if wiring:
            attrs["wiring_diagram"] = wiring
            attrs["event_types"] = list(wiring.keys())

        event_log = self._data.get("event_log", [])
        if event_log:
            attrs["recent_events"] = [
                {
                    "event_type": e.get("event_type"),
                    "source": e.get("source"),
                    "handled_by": e.get("handled_by"),
                    "timestamp": e.get("timestamp"),
                }
                for e in event_log[:5]
            ]

        return attrs
