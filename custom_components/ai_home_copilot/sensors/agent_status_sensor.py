"""Agent Status Sensor for Home Assistant (v5.21.0).

Exposes Styx agent health, connectivity, and capabilities as an HA sensor.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class AgentStatusSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing Styx agent status and health."""

    _attr_name = "Styx Agent Status"
    _attr_unique_id = "copilot_agent_status"
    _attr_icon = "mdi:robot"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    @property
    def native_value(self) -> str | None:
        status = self._data.get("status", "offline")
        agent_name = self._data.get("agent_name", "Styx")
        return f"{agent_name}: {status}"

    @property
    def icon(self) -> str:
        status = self._data.get("status", "offline")
        if status == "ready":
            return "mdi:robot-happy"
        elif status == "degraded":
            return "mdi:robot-confused"
        return "mdi:robot-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "agent_name": self._data.get("agent_name", "Styx"),
            "agent_version": self._data.get("agent_version", ""),
            "status": self._data.get("status", "offline"),
            "uptime_seconds": self._data.get("uptime_seconds", 0),
            "conversation_ready": self._data.get("conversation_ready", False),
            "llm_available": self._data.get("llm_available", False),
            "llm_model": self._data.get("llm_model", ""),
            "llm_backend": self._data.get("llm_backend", ""),
            "character": self._data.get("character", ""),
            "features": self._data.get("features", []),
            "supported_languages": self._data.get("supported_languages", []),
            "last_health_check": self._data.get("last_health_check", ""),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"{self._core_base_url()}/api/v1/agent"
        headers = self._core_headers()

        try:
            async with session.get(
                f"{base}/status", headers=headers, timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._data = data
                else:
                    self._data["status"] = "offline"
        except Exception as exc:
            _LOGGER.debug("Failed to fetch agent status: %s", exc)
            self._data["status"] = "offline"
