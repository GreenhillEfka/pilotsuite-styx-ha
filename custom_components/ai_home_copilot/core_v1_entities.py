from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .core_v1 import (
    SIGNAL_CORE_CAPABILITIES_UPDATED,
    get_cached_core_capabilities,
)
from .entity import CopilotBaseEntity


class CoreApiV1StatusSensor(CopilotBaseEntity, SensorEntity):
    """Shows whether Core supports /api/v1 and exposes capabilities as attributes."""

    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot core API v1"
    _attr_unique_id = "ai_home_copilot_core_api_v1"
    _attr_icon = "mdi:api"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._unsub = None
        self._state: str | None = None
        self._attrs: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = async_dispatcher_connect(
            self.hass, SIGNAL_CORE_CAPABILITIES_UPDATED, self._on_update
        )
        self._refresh_from_cache()

    async def async_will_remove_from_hass(self) -> None:
        if callable(self._unsub):
            self._unsub()
        self._unsub = None
        await super().async_will_remove_from_hass()

    def _on_update(self, entry_id: str) -> None:
        if entry_id != self._entry.entry_id:
            return
        # Dispatcher callbacks may be invoked from non-eventloop threads.
        self.hass.loop.call_soon_threadsafe(self._refresh_from_cache)

    def _refresh_from_cache(self) -> None:
        cap = get_cached_core_capabilities(self.hass, self._entry.entry_id) or {}
        supported = cap.get("supported")
        http_status = cap.get("http_status")
        error = cap.get("error")
        fetched = cap.get("fetched")
        data = cap.get("data") if isinstance(cap.get("data"), dict) else None

        if supported is True:
            self._state = "supported"
        elif supported is False:
            self._state = "not_supported"
        else:
            # unknown / network / unauthorized
            if http_status == 401 or error == "unauthorized":
                self._state = "unauthorized"
            else:
                self._state = "unknown"

        self._attrs = {
            "fetched": fetched,
            "http_status": http_status,
            "error": error,
        }
        if data is not None:
            modules = data.get("modules") if isinstance(data.get("modules"), dict) else None
            if modules is not None:
                self._attrs["modules"] = modules

        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        return self._attrs
