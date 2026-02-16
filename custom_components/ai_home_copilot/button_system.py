"""System control buttons for AI Home CoPilot."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN
from .entity import CopilotBaseEntity
from .inventory import async_generate_ha_overview
from .inventory_publish import async_publish_last_overview
from .inventory_kernel import async_generate_and_publish_inventory
from .systemhealth_report import async_generate_and_publish_systemhealth_report
from .config_snapshot import async_generate_config_snapshot, async_publish_last_config_snapshot
from .habitus_dashboard import async_generate_habitus_zones_dashboard, async_publish_last_habitus_dashboard
from .pilotsuite_dashboard import async_generate_pilotsuite_dashboard, async_publish_last_pilotsuite_dashboard

class CopilotGenerateOverviewButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot generate HA overview"
    _attr_unique_id = "ai_home_copilot_generate_ha_overview"
    _attr_icon = "mdi:map-search"

    async def async_press(self) -> None:
        await async_generate_ha_overview(self.hass)



class CopilotDownloadOverviewButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot download HA overview"
    _attr_unique_id = "ai_home_copilot_download_ha_overview"
    _attr_icon = "mdi:download"

    async def async_press(self) -> None:
        await async_publish_last_overview(self.hass)



class CopilotGenerateInventoryButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot generate inventory"
    _attr_unique_id = "ai_home_copilot_generate_inventory"
    _attr_icon = "mdi:clipboard-list"

    async def async_press(self) -> None:
        await async_generate_and_publish_inventory(self.hass)



class CopilotSystemHealthReportButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "SystemHealth report"
    _attr_unique_id = "ai_home_copilot_systemhealth_report"
    _attr_icon = "mdi:stethoscope"

    async def async_press(self) -> None:
        try:
            await async_generate_and_publish_systemhealth_report(self.hass)
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Failed to generate SystemHealth report: {err}",
                title="AI Home CoPilot SystemHealth",
                notification_id="ai_home_copilot_systemhealth",
            )



class CopilotGenerateConfigSnapshotButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot generate config snapshot"
    _attr_unique_id = "ai_home_copilot_generate_config_snapshot"
    _attr_icon = "mdi:content-save-cog"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_generate_config_snapshot(self.hass, self._entry)



class CopilotDownloadConfigSnapshotButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot download config snapshot"
    _attr_unique_id = "ai_home_copilot_download_config_snapshot"
    _attr_icon = "mdi:download"

    async def async_press(self) -> None:
        try:
            await async_publish_last_config_snapshot(self.hass)
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Failed to publish config snapshot: {err}",
                title="AI Home CoPilot config snapshot",
                notification_id="ai_home_copilot_config_snapshot",
            )



class CopilotReloadConfigEntryButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot reload"
    _attr_unique_id = "ai_home_copilot_reload_config_entry"
    _attr_icon = "mdi:reload"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    async def async_press(self) -> None:
        await self.hass.config_entries.async_reload(self._entry_id)



class CopilotGenerateHabitusDashboardButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot generate habitus dashboard"
    _attr_unique_id = "ai_home_copilot_generate_habitus_dashboard"
    _attr_icon = "mdi:view-dashboard-outline"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_generate_habitus_zones_dashboard(self.hass, self._entry.entry_id)



class CopilotDownloadHabitusDashboardButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot download habitus dashboard"
    _attr_unique_id = "ai_home_copilot_download_habitus_dashboard"
    _attr_icon = "mdi:download"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        try:
            await async_publish_last_habitus_dashboard(self.hass)
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Failed to publish habitus dashboard: {err}",
                title="AI Home CoPilot Habitus dashboard",
                notification_id="ai_home_copilot_habitus_dashboard_download",
            )



class CopilotGeneratePilotSuiteDashboardButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot generate PilotSuite dashboard"
    _attr_unique_id = "ai_home_copilot_generate_pilotsuite_dashboard"
    _attr_icon = "mdi:view-dashboard"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_generate_pilotsuite_dashboard(self.hass, self._entry)



class CopilotDownloadPilotSuiteDashboardButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot download PilotSuite dashboard"
    _attr_unique_id = "ai_home_copilot_download_pilotsuite_dashboard"
    _attr_icon = "mdi:download"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        try:
            await async_publish_last_pilotsuite_dashboard(self.hass)
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Failed to publish PilotSuite dashboard: {err}",
                title="AI Home CoPilot PilotSuite dashboard",
                notification_id="ai_home_copilot_pilotsuite_dashboard_download",
            )

