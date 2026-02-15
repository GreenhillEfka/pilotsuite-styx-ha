"""Other buttons for AI Home CoPilot."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry

from .entity import CopilotBaseEntity
from .log_fixer import async_analyze_logs
from .ha_errors_digest import async_show_ha_errors_digest


class CopilotAnalyzeLogsButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot analyze logs"
    _attr_unique_id = "ai_home_copilot_analyze_logs"
    _attr_icon = "mdi:file-search"

    async def async_press(self) -> None:
        # Governance-first: this only creates Repairs issues; it does not apply fixes.
        await async_analyze_logs(self.hass)



class CopilotHaErrorsFetchButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot fetch HA errors"
    _attr_unique_id = "ai_home_copilot_fetch_ha_errors"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_show_ha_errors_digest(self.hass, self._entry)

