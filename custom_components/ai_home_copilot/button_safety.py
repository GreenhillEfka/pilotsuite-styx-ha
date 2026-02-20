"""Safety-related buttons for AI Home CoPilot."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .entity import CopilotBaseEntity
from .log_fixer import async_rollback_last_fix


class CopilotRollbackLastFixButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot rollback last fix"
    _attr_unique_id = "ai_home_copilot_rollback_last_fix"
    _attr_icon = "mdi:undo-variant"

    async def async_press(self) -> None:
        await async_rollback_last_fix(self.hass)

