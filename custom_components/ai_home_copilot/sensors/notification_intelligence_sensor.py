"""Notification Intelligence Sensor for PilotSuite HA Integration (v7.2.0).

Displays notification overview, unread count, DND status, and delivery stats.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)


class NotificationIntelligenceSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing notification intelligence overview."""

    _attr_name = "Notification Intelligence"
    _attr_icon = "mdi:bell-ring"
    _attr_unique_id = "pilotsuite_notification_intelligence"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    async def _fetch(self) -> dict | None:
        import aiohttp
        try:
            url = f"{self._core_base_url()}/api/v1/hub/notifications"
            headers = self._core_headers()
            session = async_get_clientsession(self.hass)
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            logger.debug("Failed to fetch notification intelligence data")
        return None

    async def async_update(self) -> None:
        data = await self._fetch()
        if data and data.get("ok"):
            self._data = data

    @property
    def native_value(self) -> str:
        total = self._data.get("total_notifications", 0)
        unread = self._data.get("unread_count", 0)
        if total == 0:
            return "Keine Benachrichtigungen"
        if unread == 0:
            return "Alle gelesen"
        return f"{unread} ungelesen"

    @property
    def icon(self) -> str:
        dnd = self._data.get("dnd_active", False)
        if dnd:
            return "mdi:bell-off"
        unread = self._data.get("unread_count", 0)
        if unread > 0:
            return "mdi:bell-badge"
        return "mdi:bell-check"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "total_notifications": self._data.get("total_notifications", 0),
            "unread_count": self._data.get("unread_count", 0),
            "dnd_active": self._data.get("dnd_active", False),
            "batch_pending": self._data.get("batch_pending", 0),
            "rules_count": self._data.get("rules_count", 0),
            "channels_active": self._data.get("channels_active", []),
        }

        stats = self._data.get("stats", {})
        if stats:
            attrs["total_sent"] = stats.get("total_sent", 0)
            attrs["total_suppressed"] = stats.get("total_suppressed", 0)
            attrs["by_priority"] = stats.get("by_priority", {})

        recent = self._data.get("recent", [])
        if recent:
            attrs["recent"] = [
                {
                    "title": n.get("title"),
                    "priority": n.get("priority"),
                    "channel": n.get("channel"),
                    "read": n.get("read"),
                }
                for n in recent[:5]
            ]

        return attrs
