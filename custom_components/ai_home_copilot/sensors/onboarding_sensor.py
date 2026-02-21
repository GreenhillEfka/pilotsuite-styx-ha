"""Onboarding Status Sensor for Home Assistant (v5.22.0).

Exposes Styx onboarding progress as an HA sensor.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class OnboardingSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing Styx onboarding progress."""

    _attr_name = "Styx Onboarding"
    _attr_unique_id = "copilot_onboarding"
    _attr_icon = "mdi:school"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    @property
    def native_value(self) -> str | None:
        if self._data.get("is_complete"):
            return "Abgeschlossen"
        current = self._data.get("current_step", 0)
        total = self._data.get("total_steps", 0)
        if total > 0:
            return f"Schritt {current + 1}/{total}"
        return "Nicht gestartet"

    @property
    def icon(self) -> str:
        if self._data.get("is_complete"):
            return "mdi:check-decagram"
        return "mdi:school"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        steps = self._data.get("steps", [])
        completed = sum(1 for s in steps if s.get("completed"))
        skipped = sum(1 for s in steps if s.get("skipped"))

        return {
            "current_step": self._data.get("current_step", 0),
            "total_steps": self._data.get("total_steps", 0),
            "completed_steps": completed,
            "skipped_steps": skipped,
            "is_complete": self._data.get("is_complete", False),
            "agent_name": self._data.get("agent_name", "Styx"),
            "started_at": self._data.get("started_at", ""),
            "completed_at": self._data.get("completed_at", ""),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"http://{self._host}:{self._port}/api/v1/onboarding"
        headers = {}
        token = self.coordinator._config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with session.get(
                f"{base}/state", headers=headers, timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._data = data
        except Exception as exc:
            _LOGGER.debug("Failed to fetch onboarding state: %s", exc)
