"""Notification Sensor for PilotSuite (v5.8.0).

Exposes notification count and latest alerts as a HA sensor.
Polls Core notification engine for pending/digest data.
"""
from __future__ import annotations

import logging
from typing import Any

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class NotificationSensor(CopilotBaseEntity):
    """Sensor exposing notification engine state."""

    _attr_name = "PilotSuite Notifications"
    _attr_icon = "mdi:bell-badge"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "copilot_notifications"
        self._notif_data: dict[str, Any] | None = None
        self._digest_data: dict[str, Any] | None = None

    @property
    def native_value(self) -> str | None:
        """Return unread notification count as state."""
        if self._notif_data and self._notif_data.get("ok"):
            count = self._notif_data.get("count", 0)
            return f"{count} pending" if count > 0 else "no alerts"
        return "unavailable"

    @property
    def icon(self) -> str:
        """Dynamic icon based on pending count."""
        if self._notif_data and self._notif_data.get("ok"):
            count = self._notif_data.get("count", 0)
            if count > 0:
                return "mdi:bell-alert"
        return "mdi:bell-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return notification details."""
        attrs: dict[str, Any] = {
            "notifications_url": (
                f"{self._core_base_url()}/api/v1/notifications"
            ),
            "digest_url": (
                f"{self._core_base_url()}/api/v1/notifications/digest"
            ),
        }

        if self._notif_data and self._notif_data.get("ok"):
            notifications = self._notif_data.get("notifications", [])
            attrs["pending_count"] = self._notif_data.get("count", 0)
            attrs["latest"] = notifications[:5]

        if self._digest_data and self._digest_data.get("ok"):
            attrs["digest_count"] = self._digest_data.get("count", 0)
            attrs["by_source"] = self._digest_data.get("by_source", {})
            attrs["by_priority"] = self._digest_data.get("by_priority", {})

        return attrs

    async def async_update(self) -> None:
        """Fetch notification data from Core API."""
        try:
            session = self.coordinator._session
            if session is None:
                return

            headers = self._core_headers()

            base = f"{self._core_base_url()}"

            async with session.get(
                f"{base}/api/v1/notifications?limit=10",
                headers=headers, timeout=10,
            ) as resp:
                if resp.status == 200:
                    self._notif_data = await resp.json()

            async with session.get(
                f"{base}/api/v1/notifications/digest?hours=24",
                headers=headers, timeout=10,
            ) as resp:
                if resp.status == 200:
                    self._digest_data = await resp.json()

        except Exception as e:
            _LOGGER.debug("Failed to fetch notification data: %s", e)
