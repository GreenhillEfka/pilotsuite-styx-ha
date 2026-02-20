from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components import persistent_notification

from .entity import CopilotBaseEntity


class CopilotEnableDebug30mButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = None
    _attr_has_entity_name = False
    _attr_name = "PilotSuite enable debug for 30m"
    _attr_unique_id = "ai_home_copilot_enable_debug_30m"
    _attr_icon = "mdi:bug"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    async def async_press(self) -> None:
        await self.hass.services.async_call(
            "ai_home_copilot",
            "enable_debug_for",
            {"entry_id": self._entry_id, "minutes": 30},
            blocking=False,
        )
        persistent_notification.async_create(
            self.hass,
            "Debug enabled for 30 minutes (auto-disable).",
            title="PilotSuite debug",
            notification_id="ai_home_copilot_debug",
        )


class CopilotDisableDebugButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = None
    _attr_has_entity_name = False
    _attr_name = "PilotSuite disable debug"
    _attr_unique_id = "ai_home_copilot_disable_debug"
    _attr_icon = "mdi:bug-off"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    async def async_press(self) -> None:
        await self.hass.services.async_call(
            "ai_home_copilot",
            "disable_debug",
            {"entry_id": self._entry_id},
            blocking=False,
        )
        persistent_notification.async_create(
            self.hass,
            "Debug disabled.",
            title="PilotSuite debug",
            notification_id="ai_home_copilot_debug",
        )


class CopilotClearErrorDigestButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = None
    _attr_has_entity_name = False
    _attr_name = "PilotSuite clear error digest"
    _attr_unique_id = "ai_home_copilot_clear_error_digest"
    _attr_icon = "mdi:broom"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    async def async_press(self) -> None:
        await self.hass.services.async_call(
            "ai_home_copilot",
            "clear_error_digest",
            {"entry_id": self._entry_id},
            blocking=False,
        )
        persistent_notification.async_create(
            self.hass,
            "Error digest cleared.",
            title="PilotSuite dev surface",
            notification_id="ai_home_copilot_dev_surface",
        )


class CopilotClearAllLogsButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = None
    _attr_has_entity_name = False
    _attr_name = "PilotSuite clear all logs"
    _attr_unique_id = "ai_home_copilot_clear_all_logs"
    _attr_icon = "mdi:trash-can-outline"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    async def async_press(self) -> None:
        await self.hass.services.async_call(
            "ai_home_copilot",
            "clear_all_logs",
            {"entry_id": self._entry_id},
            blocking=False,
        )
        persistent_notification.async_create(
            self.hass,
            "All logs cleared (devlog + error digest).",
            title="PilotSuite dev surface",
            notification_id="ai_home_copilot_dev_surface",
        )
