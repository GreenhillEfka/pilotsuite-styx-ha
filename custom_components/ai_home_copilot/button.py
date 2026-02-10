from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

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
from .inventory_kernel import async_generate_and_publish_inventory
from .config_snapshot import async_generate_config_snapshot, async_publish_last_config_snapshot
from .systemhealth_report import async_generate_and_publish_systemhealth_report
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
from .ha_errors_digest import async_show_ha_errors_digest
from .core.modules.dev_surface import _async_ping
from .suggest import Candidate, async_offer_candidate
from .button_safety_backup import (
    CopilotSafetyBackupCreateButton,
    CopilotSafetyBackupStatusButton,
)
from .button_tag_registry import CopilotTagRegistrySyncLabelsNowButton
from .button_update_rollback import CopilotUpdateRollbackReportButton
from .brain_graph_viz import async_publish_brain_graph_viz
from .media_context_v2_entities import (
    VolumeUpButton,
    VolumeDownButton,
    VolumeMuteButton,
    ClearOverridesButton,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    cfg = entry.data | entry.options
    
    entities = [
        CopilotToggleLightButton(
            coordinator, cfg.get(CONF_TEST_LIGHT, DEFAULT_TEST_LIGHT)
        ),
        CopilotCreateDemoSuggestionButton(coordinator, entry.entry_id),
        CopilotAnalyzeLogsButton(coordinator),
        CopilotRollbackLastFixButton(coordinator),
        CopilotGenerateOverviewButton(coordinator),
        CopilotDownloadOverviewButton(coordinator),
        CopilotGenerateInventoryButton(coordinator),
        CopilotSystemHealthReportButton(coordinator),
        CopilotGenerateConfigSnapshotButton(coordinator, entry),
        CopilotDownloadConfigSnapshotButton(coordinator),
        CopilotReloadConfigEntryButton(coordinator, entry.entry_id),
        CopilotDevLogTestPushButton(coordinator, entry),
        CopilotDevLogPushLatestButton(coordinator, entry),
        CopilotDevLogsFetchButton(coordinator, entry),
        CopilotCoreCapabilitiesFetchButton(coordinator, entry),
        CopilotCoreEventsFetchButton(coordinator, entry),
        CopilotCoreGraphStateFetchButton(coordinator, entry),
        CopilotCoreGraphCandidatesPreviewButton(coordinator, entry),
        CopilotCoreGraphCandidatesOfferButton(coordinator, entry),
        CopilotPublishBrainGraphVizButton(coordinator, entry),
        CopilotBrainDashboardSummaryButton(coordinator, entry),
        CopilotForwarderStatusButton(coordinator, entry),
        CopilotHaErrorsFetchButton(coordinator, entry),
        CopilotPingCoreButton(coordinator, entry),
        CopilotEnableDebug30mButton(coordinator, entry.entry_id),
        CopilotDisableDebugButton(coordinator, entry.entry_id),
        CopilotClearErrorDigestButton(coordinator, entry.entry_id),
        CopilotSafetyBackupCreateButton(coordinator, entry),
        CopilotSafetyBackupStatusButton(coordinator, entry),
        HabitusZonesValidateButton(coordinator, entry),
        CopilotGenerateHabitusDashboardButton(coordinator, entry),
        CopilotDownloadHabitusDashboardButton(coordinator, entry),
        CopilotGeneratePilotSuiteDashboardButton(coordinator, entry),
        CopilotDownloadPilotSuiteDashboardButton(coordinator, entry),
        CopilotTagRegistrySyncLabelsNowButton(coordinator),
        CopilotUpdateRollbackReportButton(coordinator),
    ]
    
    # Media Context v2 button entities
    media_coordinator_v2 = data.get("media_coordinator_v2") if isinstance(data, dict) else None
    if media_coordinator_v2 is not None:
        entities.extend([
            VolumeUpButton(media_coordinator_v2),
            VolumeDownButton(media_coordinator_v2),
            VolumeMuteButton(media_coordinator_v2),
            ClearOverridesButton(media_coordinator_v2),
        ])

    async_add_entities(entities, True)


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


class CopilotCoreGraphStateFetchButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot fetch core graph state"
    _attr_unique_id = "ai_home_copilot_fetch_core_graph_state"
    _attr_icon = "mdi:graph"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        url = "/api/v1/graph/state?limitNodes=120&limitEdges=240"
        try:
            data = await self.coordinator.api.async_get(url)
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Failed to fetch core graph state: {err}",
                title="AI Home CoPilot Core graph",
                notification_id="ai_home_copilot_core_graph_state",
            )
            return

        nodes = data.get("nodes") if isinstance(data, dict) else None
        edges = data.get("edges") if isinstance(data, dict) else None
        if not isinstance(nodes, list):
            nodes = []
        if not isinstance(edges, list):
            edges = []

        # Compact summary
        lines: list[str] = []
        lines.append(f"nodes: {len(nodes)}")
        lines.append(f"edges: {len(edges)}")

        # Show a few interesting nodes
        sample_nodes: list[str] = []
        for n in nodes[:12]:
            if not isinstance(n, dict):
                continue
            nid = n.get("id")
            if isinstance(nid, str) and nid:
                sample_nodes.append(nid)
        if sample_nodes:
            lines.append("")
            lines.append("sample nodes:")
            lines.extend([f"- {x}" for x in sample_nodes])

        # Show a few edges
        sample_edges: list[str] = []
        for e in edges[:12]:
            if not isinstance(e, dict):
                continue
            t = e.get("type")
            frm = e.get("from")
            to = e.get("to")
            if isinstance(frm, str) and isinstance(to, str) and frm and to:
                if isinstance(t, str) and t:
                    sample_edges.append(f"{frm} -[{t}]-> {to}")
                else:
                    sample_edges.append(f"{frm} -> {to}")
        if sample_edges:
            lines.append("")
            lines.append("sample edges:")
            lines.extend([f"- {x}" for x in sample_edges])

        msg = "\n".join(lines)
        if len(msg) > 8000:
            msg = msg[:7950] + "\n...(truncated)..."

        persistent_notification.async_create(
            self.hass,
            msg,
            title="AI Home CoPilot Core graph (state)",
            notification_id="ai_home_copilot_core_graph_state",
        )


class CopilotPublishBrainGraphVizButton(CopilotBaseEntity, ButtonEntity):
    """Publish a minimal local HTML/SVG brain-graph preview."""

    _attr_entity_registry_enabled_default = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot publish brain graph viz"
    _attr_unique_id = "ai_home_copilot_publish_brain_graph_viz"
    _attr_icon = "mdi:graph"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_publish_brain_graph_viz(self.hass, self.coordinator)


class CopilotCoreGraphCandidatesPreviewButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot preview graph candidates"
    _attr_unique_id = "ai_home_copilot_preview_graph_candidates"
    _attr_icon = "mdi:graph-outline"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        url = "/api/v1/candidates/graph_candidates?limit=10"
        try:
            data = await self.coordinator.api.async_get(url)
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Failed to fetch graph candidates: {err}",
                title="AI Home CoPilot graph candidates",
                notification_id="ai_home_copilot_graph_candidates",
            )
            return

        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            items = []

        lines: list[str] = [f"count: {len(items)}"]
        for it in items[:10]:
            if not isinstance(it, dict):
                continue
            title = str(it.get("title") or "")
            text = str(it.get("seed_text") or "")
            cid = str(it.get("candidate_id") or "")
            lines.append("")
            lines.append(f"- {title} ({cid})")
            if text:
                lines.append(f"  {text}")

        msg = "\n".join(lines) if lines else "No items."
        if len(msg) > 8000:
            msg = msg[:7950] + "\n...(truncated)..."

        persistent_notification.async_create(
            self.hass,
            msg,
            title="AI Home CoPilot graph candidates (preview)",
            notification_id="ai_home_copilot_graph_candidates",
        )


class CopilotCoreGraphCandidatesOfferButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot offer graph candidates"
    _attr_unique_id = "ai_home_copilot_offer_graph_candidates"
    _attr_icon = "mdi:lightbulb-auto-outline"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        url = "/api/v1/candidates/graph_candidates?limit=5"
        try:
            data = await self.coordinator.api.async_get(url)
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Failed to fetch graph candidates: {err}",
                title="AI Home CoPilot graph candidates",
                notification_id="ai_home_copilot_graph_candidates_offer",
            )
            return

        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            items = []

        offered = 0
        for it in items[:5]:
            if not isinstance(it, dict):
                continue

            cid = str(it.get("candidate_id") or "")
            if not cid:
                continue

            cand = Candidate(
                candidate_id=cid,
                kind="seed",
                title=str(it.get("title") or "Graph candidate"),
                seed_source=str(it.get("seed_source") or "brain_graph"),
                seed_entities=[str(x) for x in (it.get("seed_entities") or []) if isinstance(x, str)],
                seed_text=str(it.get("seed_text") or ""),
                data=it.get("data") if isinstance(it.get("data"), dict) else None,
                translation_key="seed_suggestion",
                translation_placeholders={"title": str(it.get("title") or "Graph candidate")},
            )

            await async_offer_candidate(self.hass, self._entry.entry_id, cand)
            offered += 1

        persistent_notification.async_create(
            self.hass,
            f"Offered {offered} graph candidates via Repairs.",
            title="AI Home CoPilot graph candidates",
            notification_id="ai_home_copilot_graph_candidates_offer",
        )


class CopilotForwarderStatusButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot forwarder status"
    _attr_unique_id = "ai_home_copilot_forwarder_status"
    _attr_icon = "mdi:transit-connection-variant"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
        if not isinstance(data, dict):
            msg = "No entry data found."
        else:
            sub = data.get("events_forwarder_subscribed")
            last = data.get("events_forwarder_last")
            seen = data.get("events_forwarder_seen")
            qlen = data.get("events_forwarder_queue_len")

            persisted_enabled = data.get("events_forwarder_persistent_enabled")
            persisted_qlen = data.get("events_forwarder_persistent_queue_len")
            drops = data.get("events_forwarder_dropped_total")
            persisted_at = data.get("events_forwarder_persisted_at")

            msg_lines = []
            if isinstance(sub, dict):
                msg_lines.append(f"subscribed: {sub.get('count')} entities @ {sub.get('time')}")
            else:
                msg_lines.append("subscribed: (unknown)")

            if isinstance(seen, dict):
                msg_lines.append(
                    "last seen: "
                    + f"{seen.get('time')} entity={seen.get('entity_id')} old={seen.get('old_state')} new={seen.get('new_state')} zones={seen.get('zones')}"
                )
            else:
                msg_lines.append("last seen: (none)")

            if qlen is not None:
                msg_lines.append(f"queue_len: {qlen}")

            if persisted_enabled is not None:
                msg_lines.append(f"persistent_queue: {bool(persisted_enabled)}")
            if persisted_qlen is not None:
                msg_lines.append(f"persisted_queue_len: {persisted_qlen}")
            if drops is not None:
                msg_lines.append(f"drops_total: {drops}")
            if persisted_at:
                msg_lines.append(f"persisted_at: {persisted_at}")

            if isinstance(last, dict):
                msg_lines.append(f"last send: sent={last.get('sent')} @ {last.get('time')}")
                if last.get("error"):
                    msg_lines.append(f"error: {last.get('error')}")
            else:
                msg_lines.append("last send: (none)")

            msg = "\n".join(msg_lines)

        persistent_notification.async_create(
            self.hass,
            msg,
            title="AI Home CoPilot forwarder status",
            notification_id="ai_home_copilot_forwarder_status",
        )


class CopilotHaErrorsFetchButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot fetch HA errors"
    _attr_unique_id = "ai_home_copilot_fetch_ha_errors"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_show_ha_errors_digest(self.hass, self._entry)


class CopilotPingCoreButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot ping core"
    _attr_unique_id = "ai_home_copilot_ping_core"
    _attr_icon = "mdi:access-point-network"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        try:
            res = await _async_ping(self.hass, self._entry)
            dt = res.get("duration_ms")
            persistent_notification.async_create(
                self.hass,
                f"Core ping ok (duration_ms={dt}).",
                title="AI Home CoPilot core ping",
                notification_id="ai_home_copilot_core_ping",
            )
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Core ping failed: {err}",
                title="AI Home CoPilot core ping",
                notification_id="ai_home_copilot_core_ping",
            )


class CopilotEnableDebug30mButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot enable debug for 30m"
    _attr_unique_id = "ai_home_copilot_enable_debug_30m"
    _attr_icon = "mdi:bug"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    async def async_press(self) -> None:
        await self.hass.services.async_call(
            DOMAIN,
            "enable_debug_for",
            {"entry_id": self._entry_id, "minutes": 30},
            blocking=False,
        )
        persistent_notification.async_create(
            self.hass,
            "Debug enabled for 30 minutes (auto-disable).",
            title="AI Home CoPilot debug",
            notification_id="ai_home_copilot_debug",
        )


class CopilotDisableDebugButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot disable debug"
    _attr_unique_id = "ai_home_copilot_disable_debug"
    _attr_icon = "mdi:bug-off"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    async def async_press(self) -> None:
        await self.hass.services.async_call(
            DOMAIN,
            "disable_debug",
            {"entry_id": self._entry_id},
            blocking=False,
        )
        persistent_notification.async_create(
            self.hass,
            "Debug disabled.",
            title="AI Home CoPilot debug",
            notification_id="ai_home_copilot_debug",
        )


class CopilotClearErrorDigestButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot clear error digest"
    _attr_unique_id = "ai_home_copilot_clear_error_digest"
    _attr_icon = "mdi:broom"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    async def async_press(self) -> None:
        await self.hass.services.async_call(
            DOMAIN,
            "clear_error_digest",
            {"entry_id": self._entry_id},
            blocking=False,
        )
        persistent_notification.async_create(
            self.hass,
            "Error digest cleared.",
            title="AI Home CoPilot dev surface",
            notification_id="ai_home_copilot_dev_surface",
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


class CopilotBrainDashboardSummaryButton(CopilotBaseEntity, ButtonEntity):
    """Fetch brain graph dashboard summary from Core Add-on."""

    _attr_entity_registry_enabled_default = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot brain dashboard summary"
    _attr_unique_id = "ai_home_copilot_brain_dashboard_summary"
    _attr_icon = "mdi:brain"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        """Fetch brain dashboard summary and display it."""
        from .core_v1 import async_call_core_api

        try:
            # Fetch dashboard summary
            dashboard_data = await async_call_core_api(
                self.hass, 
                self._entry, 
                "GET", 
                "/api/v1/dashboard/brain-summary"
            )
            
            if not dashboard_data:
                raise Exception("No response from Core Add-on")

            # Format summary for notification
            brain_stats = dashboard_data.get("brain_graph", {})
            activity = dashboard_data.get("activity", {})
            health = dashboard_data.get("health", {})
            recommendations = dashboard_data.get("recommendations", [])
            
            nodes = brain_stats.get("nodes", 0)
            edges = brain_stats.get("edges", 0)
            events_24h = activity.get("events_24h", 0)
            active_entities = activity.get("active_entities", 0)
            health_score = health.get("score", 0)
            status = health.get("status", "Unknown")
            
            # Build summary message
            summary_lines = [
                f"**Brain Graph Status: {status} ({health_score}/100)**",
                f"📊 Nodes: {nodes}, Edges: {edges}",
                f"⚡ Activity: {events_24h} events, {active_entities} entities (24h)",
            ]
            
            if recommendations:
                summary_lines.append("**Recommendations:**")
                for rec in recommendations[:3]:  # Show top 3
                    summary_lines.append(f"• {rec}")
            
            summary_text = "\n".join(summary_lines)
            
            # Show notification
            persistent_notification.async_create(
                self.hass,
                summary_text,
                title=f"🧠 Brain Dashboard Summary",
                notification_id="ai_home_copilot_brain_dashboard_summary",
            )
            
        except Exception as err:
            persistent_notification.async_create(
                self.hass,
                f"Failed to fetch brain dashboard summary: {str(err)}",
                title="AI Home CoPilot Brain Dashboard",
                notification_id="ai_home_copilot_brain_dashboard_error",
            )
