"""Ops Runbook button – run preflight check (v0.1 kernel)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .entity import CopilotBaseEntity
from .ops_runbook import async_show_preflight_notification


class CopilotOpsRunbookPreflightButton(CopilotBaseEntity, ButtonEntity):
    """Button to trigger an ops preflight check."""

    _attr_entity_registry_enabled_default = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot ops preflight check"
    _attr_unique_id = "ai_home_copilot_ops_runbook_preflight_btn"
    _attr_icon = "mdi:clipboard-check-outline"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_show_preflight_notification(self.hass, self._entry)

        # Update sensor if available
        data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
        if isinstance(data, dict):
            sensor = data.get("ops_runbook_sensor")
            if sensor is not None:
                from .ops_runbook import async_run_preflight

                coord = data.get("coordinator")
                api = getattr(coord, "api", None) if coord else None
                result = await async_run_preflight(self.hass, self._entry, api=api)
                sensor.set_preflight_result(result)
