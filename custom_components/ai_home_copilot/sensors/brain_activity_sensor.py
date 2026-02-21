"""Brain Activity Sensor for PilotSuite HA Integration (v7.5.0).

Displays brain state (active/idle/sleeping), pulse count, and chat activity.
Frontend uses this to animate the brain visualization.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)

_STATE_LABELS = {
    "active": "Aktiv — pulsierend",
    "idle": "Wach — bereit",
    "sleeping": "Schlafend",
}

_STATE_ICONS = {
    "active": "mdi:head-lightbulb",
    "idle": "mdi:brain",
    "sleeping": "mdi:power-sleep",
}


class BrainActivitySensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing brain activity state for dashboard animation."""

    _attr_name = "Brain Activity"
    _attr_icon = "mdi:brain"
    _attr_unique_id = "pilotsuite_brain_activity"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    async def _fetch(self) -> dict | None:
        import aiohttp
        try:
            url = f"http://{self._host}:{self._port}/api/v1/hub/brain/activity"
            headers = {"Authorization": f"Bearer {self.coordinator._config.get('token', '')}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception:
            logger.debug("Failed to fetch brain activity data")
        return None

    async def async_update(self) -> None:
        data = await self._fetch()
        if data and data.get("ok"):
            self._data = data

    @property
    def native_value(self) -> str:
        state = self._data.get("state", "idle")
        return _STATE_LABELS.get(state, state)

    @property
    def icon(self) -> str:
        state = self._data.get("state", "idle")
        return _STATE_ICONS.get(state, "mdi:brain")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "state": self._data.get("state", "idle"),
            "total_pulses": self._data.get("total_pulses", 0),
            "total_chat_messages": self._data.get("total_chat_messages", 0),
            "uptime_seconds": self._data.get("uptime_seconds", 0),
            "sleep_seconds": self._data.get("sleep_seconds", 0),
            "idle_timeout_seconds": self._data.get("idle_timeout_seconds", 300),
            "sleep_timeout_seconds": self._data.get("sleep_timeout_seconds", 1800),
            "last_active": self._data.get("last_active", ""),
        }

        recent_pulses = self._data.get("recent_pulses", [])
        if recent_pulses:
            attrs["recent_pulses"] = [
                {"reason": p.get("reason"), "duration_ms": p.get("duration_ms")}
                for p in recent_pulses[:3]
            ]

        recent_chat = self._data.get("recent_chat", [])
        if recent_chat:
            attrs["recent_chat"] = [
                {"role": m.get("role"), "content": m.get("content", "")[:100]}
                for m in recent_chat[:3]
            ]

        return attrs
