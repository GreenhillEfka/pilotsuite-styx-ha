"""Automation Templates Sensor for PilotSuite HA Integration (v6.9.0).

Displays automation template overview and generation status.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)


class AutomationTemplateSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing automation templates overview."""

    _attr_name = "Automation Templates"
    _attr_icon = "mdi:robot"
    _attr_unique_id = "pilotsuite_automation_templates"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    async def _fetch(self) -> dict | None:
        import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
        try:
            url = f"{self._core_base_url()}/api/v1/hub/templates/summary"
            session = async_get_clientsession(self.hass)
            session = async_get_clientsession(self.hass)
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception:
            logger.debug("Failed to fetch automation templates data")
        return None

    async def async_update(self) -> None:
        data = await self._fetch()
        if data and data.get("ok"):
            self._data = data

    @property
    def native_value(self) -> str:
        total = self._data.get("total_templates", 0)
        generated = self._data.get("generated_count", 0)
        if total == 0:
            return "Nicht verfügbar"
        return f"{total} Templates, {generated} generiert"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "total_templates": self._data.get("total_templates", 0),
            "generated_count": self._data.get("generated_count", 0),
        }

        categories = self._data.get("categories", {})
        if categories:
            attrs["categories"] = categories

        popular = self._data.get("popular", [])
        if popular:
            attrs["popular"] = [
                {
                    "name": p.get("name_de"),
                    "icon": p.get("icon"),
                    "usage": p.get("usage_count"),
                    "rating": p.get("rating"),
                }
                for p in popular[:5]
            ]

        return attrs
