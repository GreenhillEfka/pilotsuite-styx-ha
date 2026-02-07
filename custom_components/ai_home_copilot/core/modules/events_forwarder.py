from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from ...const import (
    DOMAIN,
    CONF_EVENTS_FORWARDER_ENABLED,
    CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
    CONF_EVENTS_FORWARDER_MAX_BATCH,
    DEFAULT_EVENTS_FORWARDER_ENABLED,
    DEFAULT_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
    DEFAULT_EVENTS_FORWARDER_MAX_BATCH,
)
from ...habitus_zones_store import SIGNAL_HABITUS_ZONES_UPDATED, async_get_zones
from ...core_v1 import async_fetch_core_capabilities
from ..module import ModuleContext


_LOGGER = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


@dataclass(slots=True)
class _ForwarderState:
    unsub_state: Callable[[], None] | None = None
    unsub_zones: Callable[[], None] | None = None
    unsub_timer: Callable[[], None] | None = None

    entity_ids: list[str] | None = None
    entity_to_zone_ids: dict[str, list[str]] | None = None

    queue: list[dict[str, Any]] | None = None


def _entry_data(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    dom = hass.data.setdefault(DOMAIN, {})
    ent = dom.setdefault(entry_id, {})
    if isinstance(ent, dict):
        return ent
    ent = {}
    dom[entry_id] = ent
    return ent


class EventsForwarderModule:
    """Opt-in HA->Core event forwarder (privacy-first allowlist)."""

    name = "events_forwarder"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry
        cfg = entry.data | entry.options

        enabled = bool(cfg.get(CONF_EVENTS_FORWARDER_ENABLED, DEFAULT_EVENTS_FORWARDER_ENABLED))
        if not enabled:
            _LOGGER.debug("Events forwarder disabled")
            return

        data = _entry_data(hass, entry.entry_id)
        coordinator = data.get("coordinator")
        api = getattr(coordinator, "api", None)
        if api is None:
            _LOGGER.warning("Events forwarder: coordinator/api not ready")
            return

        # Check Core API v1 capabilities once. If unsupported, do not start forwarding.
        cap = await async_fetch_core_capabilities(hass, entry, api=api)
        if cap.supported is False:
            _LOGGER.warning(
                "Events forwarder enabled, but Core does not support /api/v1 yet (HTTP 404). "
                "Upgrade copilot_core to >= v0.2.0 to use forwarding."
            )
            return

        st = _ForwarderState(queue=[])
        data["events_forwarder_state"] = st

        flush_interval = int(
            cfg.get(
                CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
                DEFAULT_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
            )
        )
        flush_interval = max(1, min(flush_interval, 60))

        max_batch = int(cfg.get(CONF_EVENTS_FORWARDER_MAX_BATCH, DEFAULT_EVENTS_FORWARDER_MAX_BATCH))
        max_batch = max(1, min(max_batch, 500))

        async def _refresh_subscriptions() -> None:
            zones = await async_get_zones(hass, entry.entry_id)
            entity_to_zone: dict[str, list[str]] = {}
            all_entities: list[str] = []

            for z in zones:
                for eid in z.entity_ids:
                    entity_to_zone.setdefault(eid, []).append(z.zone_id)

            # stable order
            for eid in sorted(entity_to_zone.keys()):
                all_entities.append(eid)

            st.entity_ids = all_entities
            st.entity_to_zone_ids = entity_to_zone

            # Re-subscribe
            if callable(st.unsub_state):
                st.unsub_state()
                st.unsub_state = None

            if not all_entities:
                _LOGGER.warning("Events forwarder: no Habitus zone entities found; nothing to forward")
                return

            def _handle_state(event: Event) -> None:
                try:
                    eid = str(event.data.get("entity_id") or "")
                    if not eid:
                        return

                    old = event.data.get("old_state")
                    new = event.data.get("new_state")
                    if new is None:
                        return

                    old_state = getattr(old, "state", None)
                    new_state = getattr(new, "state", None)
                    if old_state == new_state:
                        return

                    zone_ids = (st.entity_to_zone_ids or {}).get(eid) or []

                    item: dict[str, Any] = {
                        "id": "",
                        "ts": _now_iso(),
                        "type": "state_changed",
                        "source": "home_assistant",
                        "entity_id": eid,
                        "domain": _domain(eid),
                        "zone_ids": zone_ids,
                        "old_state": old_state,
                        "new_state": new_state,
                        # Keep attributes minimal (privacy/perf). Add more later behind opt-in.
                        "attributes": {
                            "device_class": getattr(new, "attributes", {}).get("device_class")
                            if hasattr(new, "attributes")
                            else None
                        },
                    }

                    (st.queue or []).append(item)

                    # Schedule flush if this was the first in an empty queue.
                    if st.unsub_timer is None:
                        st.unsub_timer = async_call_later(hass, flush_interval, _flush_timer)

                    # Flush immediately on size.
                    if len(st.queue or []) >= max_batch:
                        hass.async_create_task(_flush_now())

                except Exception as e:  # noqa: BLE001
                    _LOGGER.debug("Events forwarder state handler failed: %s", e)

            st.unsub_state = async_track_state_change_event(hass, all_entities, _handle_state)
            _LOGGER.info("Events forwarder subscribed to %d entities", len(all_entities))

        async def _flush_now() -> None:
            # Cancel pending timer if any
            if callable(st.unsub_timer):
                st.unsub_timer()
            st.unsub_timer = None

            items = list(st.queue or [])
            st.queue = []
            if not items:
                return

            payload = {"items": items}
            try:
                await api.async_post("/api/v1/events", payload)
                # store last stats for diagnostics
                data["events_forwarder_last"] = {
                    "sent": len(items),
                    "time": _now_iso(),
                }
            except Exception as err:  # noqa: BLE001
                data["events_forwarder_last"] = {
                    "sent": 0,
                    "time": _now_iso(),
                    "error": str(err),
                }
                _LOGGER.warning("Events forwarder failed to POST /api/v1/events: %s", err)

        def _flush_timer(_now) -> None:
            # callback from async_call_later (sync context)
            hass.async_create_task(_flush_now())

        # initial subscriptions + listen for zone updates
        await _refresh_subscriptions()

        async def _zones_updated(updated_entry_id: str) -> None:
            if updated_entry_id != entry.entry_id:
                return
            await _refresh_subscriptions()

        st.unsub_zones = async_dispatcher_connect(hass, SIGNAL_HABITUS_ZONES_UPDATED, _zones_updated)
        data["unsub_events_forwarder"] = self._unsub_factory(hass, entry.entry_id)

    def _unsub_factory(self, hass: HomeAssistant, entry_id: str) -> Callable[[], None]:
        def _unsub() -> None:
            data = hass.data.get(DOMAIN, {}).get(entry_id)
            st = data.get("events_forwarder_state") if isinstance(data, dict) else None
            if not isinstance(st, _ForwarderState):
                return

            if callable(st.unsub_state):
                st.unsub_state()
            if callable(st.unsub_zones):
                st.unsub_zones()
            if callable(st.unsub_timer):
                st.unsub_timer()

            if isinstance(data, dict):
                data.pop("events_forwarder_state", None)
                data.pop("unsub_events_forwarder", None)

        return _unsub

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        unsub = data.get("unsub_events_forwarder") if isinstance(data, dict) else None
        if callable(unsub):
            unsub()
        return True
