from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .entity import CopilotBaseEntity
from .ha_errors_digest import async_show_ha_errors_digest


class CopilotHaErrorsFetchButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "PilotSuite fetch HA errors"
    _attr_unique_id = "ai_home_copilot_fetch_ha_errors"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_show_ha_errors_digest(self.hass, self._entry)
