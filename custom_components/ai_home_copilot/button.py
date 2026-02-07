from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DEVLOG_PUSH_PATH,
    CONF_TEST_LIGHT,
    DEFAULT_DEVLOG_PUSH_PATH,
    DEFAULT_TEST_LIGHT,
    DOMAIN,
)
from .entity import CopilotBaseEntity
from .inventory import async_generate_ha_overview
from .inventory_publish import async_publish_last_overview
from .log_fixer import async_analyze_logs, async_rollback_last_fix
from .suggest import async_offer_demo_candidate
from .devlog_push import async_push_devlog_test, async_push_latest_ai_copilot_error
from .habitus_zones_entities import HabitusZonesValidateButton
from .habitus_dashboard import async_generate_habitus_zones_dashboard, async_publish_last_habitus_dashboard


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
            CopilotDevLogsFetchButton(coordinator, entry),
            HabitusZonesValidateButton(coordinator, entry),
            CopilotGenerateHabitusDashboardButton(coordinator, entry),
            CopilotDownloadHabitusDashboardButton(coordinator, entry),
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


class CopilotDevLogsFetchButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot devlogs fetch"
    _attr_unique_id = "ai_home_copilot_devlogs_fetch"
    _attr_icon = "mdi:clipboard-text-search"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        cfg = self._entry.data | self._entry.options
        path = str(cfg.get(CONF_DEVLOG_PUSH_PATH, DEFAULT_DEVLOG_PUSH_PATH) or DEFAULT_DEVLOG_PUSH_PATH)
        if not path.startswith("/"):
            path = "/" + path

        url = f"{path}?limit=10" if "?" not in path else path

        try:
            data = await self.coordinator.api.async_get(url)
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Failed to fetch devlogs: {err}",
                title="AI Home CoPilot DevLogs",
                notification_id="ai_home_copilot_devlogs",
            )
            return

        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            items = []

        lines: list[str] = []
        for it in items[-10:]:
            if not isinstance(it, dict):
                continue
            received = str(it.get("received", ""))
            payload = it.get("payload") if isinstance(it.get("payload"), dict) else {}
            kind = str(payload.get("kind", ""))
            text = payload.get("text")
            if not isinstance(text, str):
                text = ""
            text = text.strip()
            if len(text) > 500:
                text = text[:500] + "\n...(truncated)..."

            header = f"- {received} ({kind})".strip()
            lines.append(header)
            if text:
                snippet = "\n".join("  " + ln for ln in text.splitlines()[:20])
                lines.append(snippet)

        msg = "\n".join(lines) if lines else "No devlogs returned."

        persistent_notification.async_create(
            self.hass,
            msg,
            title="AI Home CoPilot DevLogs (last 10)",
            notification_id="ai_home_copilot_devlogs",
        )


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
