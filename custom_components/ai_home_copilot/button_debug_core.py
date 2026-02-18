from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components import persistent_notification

from .core.modules.dev_surface import _async_ping
from .core_v1 import async_fetch_core_capabilities
from .entity import CopilotBaseEntity
from .suggest import Candidate, async_offer_candidate


class CopilotCoreCapabilitiesFetchButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot fetch core capabilities"
    _attr_unique_id = "ai_home_copilot_fetch_core_capabilities"
    _attr_icon = "mdi:api"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        try:
            cap = await async_fetch_core_capabilities(
                self.hass, self._entry, api=self.coordinator.api
            )
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

    def __init__(self, coordinator, entry):
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

    def __init__(self, coordinator, entry):
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

        lines: list[str] = []
        lines.append(f"nodes: {len(nodes)}")
        lines.append(f"edges: {len(edges)}")

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


class CopilotCoreGraphCandidatesPreviewButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = None
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot preview graph candidates"
    _attr_unique_id = "ai_home_copilot_preview_graph_candidates"
    _attr_icon = "mdi:graph-outline"

    def __init__(self, coordinator, entry):
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
    _attr_entity_category = None
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot offer graph candidates"
    _attr_unique_id = "ai_home_copilot_offer_graph_candidates"
    _attr_icon = "mdi:lightbulb-auto-outline"

    def __init__(self, coordinator, entry):
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
                seed_entities=[
                    str(x) for x in (it.get("seed_entities") or []) if isinstance(x, str)
                ],
                seed_text=str(it.get("seed_text") or ""),
                data=it.get("data") if isinstance(it.get("data"), dict) else None,
                translation_key="seed_suggestion",
                translation_placeholders={
                    "title": str(it.get("title") or "Graph candidate")
                },
            )

            await async_offer_candidate(self.hass, self._entry.entry_id, cand)
            offered += 1

        persistent_notification.async_create(
            self.hass,
            f"Offered {offered} graph candidates via Repairs.",
            title="AI Home CoPilot graph candidates",
            notification_id="ai_home_copilot_graph_candidates_offer",
        )


class CopilotPingCoreButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = None
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot ping core"
    _attr_unique_id = "ai_home_copilot_ping_core"
    _attr_icon = "mdi:access-point-network"

    def __init__(self, coordinator, entry):
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
