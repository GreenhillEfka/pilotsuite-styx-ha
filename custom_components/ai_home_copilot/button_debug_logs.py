from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components import persistent_notification

from .const import CONF_DEVLOG_PUSH_PATH, DEFAULT_DEVLOG_PUSH_PATH
from .devlog_push import async_push_devlog_test, async_push_latest_ai_copilot_error
from .entity import CopilotBaseEntity
from .log_fixer import async_analyze_logs, async_rollback_last_fix


class CopilotAnalyzeLogsButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot analyze logs"
    _attr_unique_id = "ai_home_copilot_analyze_logs"
    _attr_icon = "mdi:file-search"

    async def async_press(self) -> None:
        await async_analyze_logs(self.hass)


class CopilotRollbackLastFixButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot rollback last fix"
    _attr_unique_id = "ai_home_copilot_rollback_last_fix"
    _attr_icon = "mdi:undo-variant"

    async def async_press(self) -> None:
        await async_rollback_last_fix(self.hass)


class CopilotDevLogTestPushButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot devlog push test"
    _attr_unique_id = "ai_home_copilot_devlog_push_test"
    _attr_icon = "mdi:bug-play"

    def __init__(self, coordinator, entry):
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

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_push_latest_ai_copilot_error(
            self.hass, self._entry, api=self.coordinator.api
        )


class CopilotDevLogsFetchButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot devlogs fetch"
    _attr_unique_id = "ai_home_copilot_devlogs_fetch"
    _attr_icon = "mdi:clipboard-text-search"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        cfg = self._entry.data | self._entry.options
        path = str(
            cfg.get(CONF_DEVLOG_PUSH_PATH, DEFAULT_DEVLOG_PUSH_PATH)
            or DEFAULT_DEVLOG_PUSH_PATH
        )
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
