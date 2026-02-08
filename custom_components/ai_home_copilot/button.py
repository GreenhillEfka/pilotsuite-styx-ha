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
from .config_snapshot import async_generate_config_snapshot, async_publish_last_config_snapshot
from .log_fixer import async_analyze_logs, async_rollback_last_fix
from .suggest import async_offer_demo_candidate
from .devlog_push import async_push_devlog_test, async_push_latest_ai_copilot_error
from .habitus_zones_entities import HabitusZonesValidateButton
from .habitus_dashboard import async_generate_habitus_zones_dashboard, async_publish_last_habitus_dashboard
from .pilotsuite_dashboard import (
    async_generate_pilotsuite_dashboard,
    async_publish_last_pilotsuite_dashboard,
)
from .core_v1 import async_fetch_core_capabilities


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
            CopilotGenerateConfigSnapshotButton(coordinator, entry),
            CopilotDownloadConfigSnapshotButton(coordinator),
            CopilotReloadConfigEntryButton(coordinator, entry.entry_id),
            CopilotDevLogTestPushButton(coordinator, entry),
            CopilotDevLogPushLatestButton(coordinator, entry),
            CopilotDevLogsFetchButton(coordinator, entry),
            CopilotCoreCapabilitiesFetchButton(coordinator, entry),
            CopilotCoreEventsFetchButton(coordinator, entry),
            HabitusZonesValidateButton(coordinator, entry),
            CopilotGenerateHabitusDashboardButton(coordinator, entry),
            CopilotDownloadHabitusDashboardButton(coordinator, entry),
            CopilotGeneratePilotSuiteDashboardButton(coordinator, entry),
            CopilotDownloadPilotSuiteDashboardButton(coordinator, entry),
        ],
        True,
    )


class CopilotToggleLightButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
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
    _attr_entity_registry_enabled_default = False
    _attr_name = "Create demo suggestion"
    _attr_unique_id = "create_demo_suggestion"
    _attr_icon = "mdi:lightbulb-on-outline"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    async def async_press(self) -> None:
        await async_offer_demo_candidate(self.hass, self._entry_id)


class CopilotAnalyzeLogsButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot analyze logs"
    _attr_unique_id = "ai_home_copilot_analyze_logs"
    _attr_icon = "mdi:file-search"

    async def async_press(self) -> None:
        # Governance-first: this only creates Repairs issues; it does not apply fixes.
        await async_analyze_logs(self.hass)


class CopilotRollbackLastFixButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot rollback last fix"
    _attr_unique_id = "ai_home_copilot_rollback_last_fix"
    _attr_icon = "mdi:undo-variant"

    async def async_press(self) -> None:
        await async_rollback_last_fix(self.hass)


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


class CopilotDevLogTestPushButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
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
    _attr_entity_registry_enabled_default = False
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


class CopilotCoreCapabilitiesFetchButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot fetch core capabilities"
    _attr_unique_id = "ai_home_copilot_fetch_core_capabilities"
    _attr_icon = "mdi:api"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        try:
            cap = await async_fetch_core_capabilities(self.hass, self._entry, api=self.coordinator.api)
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Failed to fetch capabilities: {err}",
                title="AI Home CoPilot Core capabilities",
                notification_id="ai_home_copilot_core_capabilities",
            )
            return

        msg = [f"fetched: {cap.fetched}", f"supported: {cap.supported}"]
        if cap.http_status is not None:
            msg.append(f"http_status: {cap.http_status}")
        if cap.error:
            msg.append(f"error: {cap.error}")

        modules = None
        if isinstance(cap.data, dict):
            modules = cap.data.get("modules")
        if isinstance(modules, dict):
            msg.append("")
            msg.append("modules:")
            for k, v in modules.items():
                msg.append(f"- {k}: {v}")

        persistent_notification.async_create(
            self.hass,
            "\n".join(msg),
            title="AI Home CoPilot Core capabilities",
            notification_id="ai_home_copilot_core_capabilities",
        )


class CopilotCoreEventsFetchButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot fetch core events"
    _attr_unique_id = "ai_home_copilot_fetch_core_events"
    _attr_icon = "mdi:clipboard-list-outline"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        url = "/api/v1/events?limit=20"
        try:
            data = await self.coordinator.api.async_get(url)
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Failed to fetch core events: {err}",
                title="AI Home CoPilot Core events",
                notification_id="ai_home_copilot_core_events",
            )
            return

        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            items = []

        lines: list[str] = []
        for it in items[-20:]:
            if not isinstance(it, dict):
                continue

            received = str(it.get("received") or it.get("ts") or "")
            entity_id = it.get("entity_id")
            typ = it.get("type")
            attrs = it.get("attributes") if isinstance(it.get("attributes"), dict) else {}

            header = f"- {received}".strip()

            meta: list[str] = []
            if typ:
                meta.append(str(typ))
            if entity_id:
                meta.append(f"entity={entity_id}")

            zone_ids = attrs.get("zone_ids")
            if isinstance(zone_ids, list) and zone_ids:
                meta.append("zones=" + ",".join([str(z) for z in zone_ids][:5]))

            new_state = attrs.get("new_state")
            old_state = attrs.get("old_state")
            if new_state is not None:
                meta.append(f"new={new_state}")
            if old_state is not None:
                meta.append(f"old={old_state}")

            if meta:
                header += " (" + ", ".join(meta) + ")"

            lines.append(header)

        msg = "\n".join(lines) if lines else "No core events returned."

        persistent_notification.async_create(
            self.hass,
            msg,
            title="AI Home CoPilot Core events (last 20)",
            notification_id="ai_home_copilot_core_events",
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
