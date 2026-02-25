"""Hub Dashboard Sensor for Home Assistant (v6.0.0).

Exposes PilotSuite Hub dashboard overview as an HA sensor.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class HubDashboardSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing PilotSuite Hub dashboard overview."""

    _attr_name = "Hub Dashboard"
    _attr_unique_id = "copilot_hub_dashboard"
    _attr_icon = "mdi:view-dashboard"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._overview: dict[str, Any] = {}

    @property
    def native_value(self) -> int | None:
        return self._overview.get("active_devices", 0)

    @property
    def icon(self) -> str:
        alerts = self._overview.get("alerts_count", 0)
        if alerts > 0:
            return "mdi:view-dashboard-alert"
        return "mdi:view-dashboard"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        summary = self._overview.get("summary", {})
        return {
            "active_devices": self._overview.get("active_devices", 0),
            "alerts_count": self._overview.get("alerts_count", 0),
            "savings_today_eur": self._overview.get("savings_today_eur", 0),
            "total_widgets": summary.get("total_widgets", 0),
            "layout_name": summary.get("layout_name", "default"),
            "theme": summary.get("theme", "auto"),
            "language": summary.get("language", "de"),
            "data_sources": summary.get("data_sources", []),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"{self._core_base_url()}/api/v1/hub"
        headers = self._core_headers()

        try:
            async with session.get(
                f"{base}/dashboard", headers=headers, timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._overview = data
        except Exception as exc:
            _LOGGER.debug("Failed to fetch hub dashboard data: %s", exc)


class HubPluginsSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing PilotSuite Hub plugin status."""

    _attr_name = "Hub Plugins"
    _attr_unique_id = "copilot_hub_plugins"
    _attr_icon = "mdi:puzzle"
    _attr_native_unit_of_measurement = "plugins"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._plugins: dict[str, Any] = {}

    @property
    def native_value(self) -> int | None:
        return self._plugins.get("active", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "total": self._plugins.get("total", 0),
            "active": self._plugins.get("active", 0),
            "disabled": self._plugins.get("disabled", 0),
            "error": self._plugins.get("error", 0),
            "categories": self._plugins.get("categories", {}),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"{self._core_base_url()}/api/v1/hub"
        headers = self._core_headers()

        try:
            async with session.get(
                f"{base}/plugins", headers=headers, timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._plugins = data
        except Exception as exc:
            _LOGGER.debug("Failed to fetch hub plugins data: %s", exc)


class HubMultiHomeSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing PilotSuite multi-home status."""

    _attr_name = "Hub Homes"
    _attr_unique_id = "copilot_hub_homes"
    _attr_icon = "mdi:home-group"
    _attr_native_unit_of_measurement = "homes"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._homes: dict[str, Any] = {}

    @property
    def native_value(self) -> int | None:
        return self._homes.get("total_homes", 0)

    @property
    def icon(self) -> str:
        count = self._homes.get("total_homes", 0)
        if count > 1:
            return "mdi:home-group"
        return "mdi:home"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "total_homes": self._homes.get("total_homes", 0),
            "online_homes": self._homes.get("online_homes", 0),
            "total_devices": self._homes.get("total_devices", 0),
            "total_energy_kwh": self._homes.get("total_energy_kwh", 0),
            "total_cost_eur": self._homes.get("total_cost_eur", 0),
            "active_home_id": self._homes.get("active_home_id", ""),
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"{self._core_base_url()}/api/v1/hub"
        headers = self._core_headers()

        try:
            async with session.get(
                f"{base}/homes", headers=headers, timeout=10
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._homes = data
        except Exception as exc:
            _LOGGER.debug("Failed to fetch hub homes data: %s", exc)
