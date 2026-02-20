from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import CopilotBaseEntity
from .update_rollback import async_show_update_rollback_report


class CopilotUpdateRollbackReportButton(CopilotBaseEntity, ButtonEntity):
    """Governance-first update overview button (v0.1).

    Pressing the button is the explicit user action; it only generates a report.
    """

    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "PilotSuite update/rollback report"
    _attr_unique_id = "ai_home_copilot_update_rollback_report"
    _attr_icon = "mdi:update"

    async def async_press(self) -> None:
        await async_show_update_rollback_report(self.hass)
