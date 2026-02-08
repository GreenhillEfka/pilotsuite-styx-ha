from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry

from .entity import CopilotBaseEntity
from .safety_backup import async_create_safety_backup, async_show_safety_backup_status


class CopilotSafetyBackupCreateButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot Safety-Backup erstellen"
    _attr_unique_id = "ai_home_copilot_safety_backup_create"
    _attr_icon = "mdi:shield-check"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        # Ensure stable entity_id (PilotSuite dashboard references this).
        self.entity_id = "button.ai_home_copilot_safety_backup_create"

    async def async_press(self) -> None:
        await async_create_safety_backup(self.hass)


class CopilotSafetyBackupStatusButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot Safety-Backup Status"
    _attr_unique_id = "ai_home_copilot_safety_backup_status"
    _attr_icon = "mdi:shield-search"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        # Ensure stable entity_id (PilotSuite dashboard references this).
        self.entity_id = "button.ai_home_copilot_safety_backup_status"

    async def async_press(self) -> None:
        await async_show_safety_backup_status(self.hass)
