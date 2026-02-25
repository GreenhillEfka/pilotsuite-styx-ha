"""Proactive Alert Sensor for Home Assistant (v5.19.0).

Exposes combined weather+price+grid proactive alerts as an HA sensor
with priority levels and actionable recommendations.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)

_PRIORITY_ICONS = {
    0: "mdi:check-circle",
    1: "mdi:information",
    2: "mdi:alert-outline",
    3: "mdi:alert",
    4: "mdi:alert-octagon",
}


class ProactiveAlertSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing proactive energy alerts."""

    _attr_name = "Proactive Alerts"
    _attr_unique_id = "copilot_proactive_alerts"
    _attr_icon = "mdi:bell-alert"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    @property
    def native_value(self) -> str:
        total = self._data.get("total", 0)
        if total == 0:
            return "Keine Alerts"
        highest = self._data.get("highest_priority_label", "Info")
        return f"{total}x {highest}"

    @property
    def icon(self) -> str:
        priority = self._data.get("highest_priority", 0)
        return _PRIORITY_ICONS.get(priority, "mdi:bell-alert")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        by_priority = self._data.get("by_priority", {})
        by_category = self._data.get("by_category", {})
        alerts = self._data.get("alerts", [])

        # Compact alert list
        alert_list = []
        for a in alerts[:10]:
            alert_list.append({
                "title": a.get("title_de", ""),
                "priority": a.get("priority_label", ""),
                "category": a.get("category", ""),
                "action": a.get("action", ""),
                "message": a.get("message_de", ""),
                "icon": a.get("icon", ""),
            })

        return {
            "total_alerts": self._data.get("total", 0),
            "highest_priority": self._data.get("highest_priority", 0),
            "highest_priority_label": self._data.get("highest_priority_label", ""),
            "info_count": by_priority.get("info", 0),
            "advisory_count": by_priority.get("advisory", 0),
            "warning_count": by_priority.get("warning", 0),
            "critical_count": by_priority.get("critical", 0),
            "categories": by_category,
            "alerts": alert_list,
            "last_evaluated": self._data.get("last_evaluated", ""),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"{self._core_base_url()}/api/v1/regional"
        headers = self._core_headers()

        try:
            async with session.get(
                f"{base}/alerts", headers=headers, timeout=15
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._data = data
        except Exception as exc:
            _LOGGER.error("Failed to fetch proactive alerts: %s", exc)
