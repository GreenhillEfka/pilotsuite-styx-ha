from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_TEST_LIGHT, DEFAULT_TEST_LIGHT, DOMAIN
from .entity import CopilotBaseEntity
from .inventory import async_generate_ha_overview
from .inventory_publish import async_publish_last_overview
from .log_fixer import async_analyze_logs, async_rollback_last_fix
from .suggest import async_offer_demo_candidate
from .devlog_push import async_push_devlog_test, async_push_latest_ai_copilot_error


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    cfg = entry.data | entry.options
    async_add_entities(
        [
            CopilotToggleLightButton(
                coordinator, cfg.get(CONF_TEST_LIGHT, DEFAULT_TEST_LIGHT)
            ),
            CopilotCreateDemoSuggestionButton(coordinator, entry.entry_id),
            CopilotAnalyzeLogsButton(coordinator),
            CopilotRollbackLastFixButton(coordinator),
            CopilotGenerateOverviewButton(coordinator),
            CopilotDownloadOverviewButton(coordinator),
            CopilotReloadConfigEntryButton(coordinator, entry.entry_id),
            CopilotDevLogTestPushButton(coordinator, entry),
            CopilotDevLogPushLatestButton(coordinator, entry),
        ],
        True,
    )


class CopilotToggleLightButton(CopilotBaseEntity, ButtonEntity):
    _attr_name = "Toggle test light"
    _attr_unique_id = "toggle_test_light"
    _attr_icon = "mdi:light-switch"

    def __init__(self, coordinator, entity_id: str):
        super().__init__(coordinator)
        self._light_entity_id = entity_id

    async def async_press(self) -> None:
        if not self._light_entity_id:
            return
        await self.hass.services.async_call(
            "light",
            "toggle",
            {"entity_id": self._light_entity_id},
            blocking=False,
        )


class CopilotCreateDemoSuggestionButton(CopilotBaseEntity, ButtonEntity):
    _attr_name = "Create demo suggestion"
    _attr_unique_id = "create_demo_suggestion"
    _attr_icon = "mdi:lightbulb-on-outline"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    async def async_press(self) -> None:
        await async_offer_demo_candidate(self.hass, self._entry_id)


class CopilotAnalyzeLogsButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot analyze logs"
    _attr_unique_id = "ai_home_copilot_analyze_logs"
    _attr_icon = "mdi:file-search"

    async def async_press(self) -> None:
        # Governance-first: this only creates Repairs issues; it does not apply fixes.
        await async_analyze_logs(self.hass)


class CopilotRollbackLastFixButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot rollback last fix"
    _attr_unique_id = "ai_home_copilot_rollback_last_fix"
    _attr_icon = "mdi:undo-variant"

    async def async_press(self) -> None:
        await async_rollback_last_fix(self.hass)


class CopilotGenerateOverviewButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot generate HA overview"
    _attr_unique_id = "ai_home_copilot_generate_ha_overview"
    _attr_icon = "mdi:map-search"

    async def async_press(self) -> None:
        await async_generate_ha_overview(self.hass)


class CopilotDownloadOverviewButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot download HA overview"
    _attr_unique_id = "ai_home_copilot_download_ha_overview"
    _attr_icon = "mdi:download"

    async def async_press(self) -> None:
        await async_publish_last_overview(self.hass)


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


class CopilotDevLogTestPushButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot devlog push test"
    _attr_unique_id = "ai_home_copilot_devlog_push_test"
    _attr_icon = "mdi:bug-play"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_push_devlog_test(self.hass, self._entry, api=self.coordinator.api)


class CopilotDevLogPushLatestButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot devlog push latest"
    _attr_unique_id = "ai_home_copilot_devlog_push_latest"
    _attr_icon = "mdi:bug-outline"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_push_latest_ai_copilot_error(self.hass, self._entry, api=self.coordinator.api)
