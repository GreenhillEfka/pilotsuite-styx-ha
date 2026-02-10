from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any
import asyncio
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.storage import Store

from ...const import (
    DOMAIN,
    CONF_EVENTS_FORWARDER_ENABLED,
    CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
    CONF_EVENTS_FORWARDER_MAX_BATCH,
    CONF_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
    CONF_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
    CONF_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES,
    CONF_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS,
    CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES,
    DEFAULT_EVENTS_FORWARDER_ENABLED,
    DEFAULT_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
    DEFAULT_EVENTS_FORWARDER_MAX_BATCH,
    DEFAULT_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
    DEFAULT_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
    DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
    DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
    DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
    DEFAULT_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES,
    DEFAULT_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS,
    DEFAULT_EVENTS_FORWARDER_ADDITIONAL_ENTITIES,
    CONF_MEDIA_MUSIC_PLAYERS,
    CONF_MEDIA_TV_PLAYERS,
    DEFAULT_MEDIA_MUSIC_PLAYERS,
    DEFAULT_MEDIA_TV_PLAYERS,
)
from ...habitus_zones_store import SIGNAL_HABITUS_ZONES_UPDATED, async_get_zones
from ...core_v1 import async_fetch_core_capabilities
from ...media_context import _parse_csv
from ..module import ModuleContext


_LOGGER = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def _context_id(event: Event) -> str | None:
    # Home Assistant Event has a Context object with a stable UUID-like id.
    ctx = getattr(event, "context", None)
    ctx_id = getattr(ctx, "id", None)
    if isinstance(ctx_id, str) and ctx_id:
        return ctx_id
    return None


def _idempotency_key(event_type: str, event: Event) -> str:
    # Prefer event_type:context.id when present.
    ctx_id = _context_id(event)
    return f"{event_type}:{ctx_id}" if ctx_id else ""


def _ensure_list_entity_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for v in value:
            if isinstance(v, str) and v:
                out.append(v)
        return out
    return []


# `call_service` forwarding is **intent** forwarding, not payload forwarding.
# Keep it strict by default.
_ALLOWED_CALL_SERVICE_DOMAINS: set[str] = {
    "light",
    "media_player",
    "climate",
    "cover",
    "lock",
    "switch",
    "scene",
    "script",
}

_BLOCKED_CALL_SERVICE_DOMAINS: set[str] = {
    # Typical high-risk egress / payload carriers.
    "notify",
    "rest_command",
    "shell_command",
    "tts",
}


def _allowed_state_attrs(entity_id: str, state_obj: Any) -> dict[str, Any]:
    """Privacy-first allowlist of HA state attributes.

    We keep the overall event envelope stable and place allowlisted HA attributes
    under `attributes.state_attributes`.
    """

    dom = _domain(entity_id)
    attrs = getattr(state_obj, "attributes", None)
    if not isinstance(attrs, dict):
        return {}

    allow: set[str]
    if dom == "light":
        allow = {"brightness", "color_temp", "hs_color"}
    elif dom == "media_player":
        allow = {"volume_level"}
    else:
        allow = set()

    return {k: attrs.get(k) for k in allow if k in attrs}


def _store_key(entry_id: str) -> str:
    # Stored in .storage (local HA config directory).
    # Keep it stable + namespaced.
    return f"{DOMAIN}.events_forwarder.{entry_id}"


@dataclass(slots=True)
class _ForwarderState:
    unsub_state: Callable[[], None] | None = None
    unsub_zones: Callable[[], None] | None = None
    unsub_timer: Callable[[], None] | None = None
    unsub_call_service: Callable[[], None] | None = None

    # persistence timers
    unsub_persist_timer: Callable[[], None] | None = None

    entity_ids: list[str] | None = None
    entity_to_zone_ids: dict[str, list[str]] | None = None

    # bounded in-memory queue (drop-oldest policy enforced by our enqueue helpers)
    queue: list[dict[str, Any]] | None = None

    # best-effort idempotency (in-memory, optionally persisted)
    seen_until: dict[str, float] | None = None

    # persistent queue
    store: Store | None = None
    persistent_enabled: bool = False
    persistent_dirty: bool = False
    persistent_flush_interval: int = 5
    persistent_max_size: int = 500

    # stats / observability
    dropped_total: int = 0
    sent_total: int = 0
    error_total: int = 0
    error_streak: int = 0
    last_success_ts: float | None = None
    first_error_ts: float | None = None
    last_error_ts: float | None = None

    # concurrency guard (avoid overlapping flush tasks)
    flushing: bool = False


def _entry_data(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    dom = hass.data.setdefault(DOMAIN, {})
    ent = dom.setdefault(entry_id, {})
    if isinstance(ent, dict):
        return ent
    ent = {}
    dom[entry_id] = ent
    return ent


async def _build_forwarder_entity_allowlist(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> tuple[list[str], dict[str, list[str]]]:
    """Build entity allowlist based on config settings.
    
    Returns (entity_ids, entity_to_zone_ids_map)
    """
    cfg = entry.data | entry.options
    
    all_entities: list[str] = []
    entity_to_zone: dict[str, list[str]] = {}
    
    # 1. Include Habitus zone entities if enabled
    include_habitus = cfg.get(
        CONF_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES, 
        DEFAULT_EVENTS_FORWARDER_INCLUDE_HABITUS_ZONES
    )
    if include_habitus:
        zones = await async_get_zones(hass, entry.entry_id)
        for z in zones:
            for eid in z.entity_ids:
                entity_to_zone.setdefault(eid, []).append(z.zone_id)
    
    # 2. Include media players if enabled
    include_media = cfg.get(
        CONF_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS,
        DEFAULT_EVENTS_FORWARDER_INCLUDE_MEDIA_PLAYERS
    )
    if include_media:
        music_players = _parse_csv(cfg.get(CONF_MEDIA_MUSIC_PLAYERS, DEFAULT_MEDIA_MUSIC_PLAYERS))
        tv_players = _parse_csv(cfg.get(CONF_MEDIA_TV_PLAYERS, DEFAULT_MEDIA_TV_PLAYERS))
        
        for eid in music_players + tv_players:
            if eid and eid not in entity_to_zone:
                # Mark as media zone for better categorization
                entity_to_zone[eid] = ["media"]
    
    # 3. Include additional entities from config
    additional_entities = cfg.get(
        CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES,
        DEFAULT_EVENTS_FORWARDER_ADDITIONAL_ENTITIES
    )
    if isinstance(additional_entities, list):
        for eid in additional_entities:
            if isinstance(eid, str) and eid.strip():
                entity_id = eid.strip()
                if entity_id not in entity_to_zone:
                    entity_to_zone[entity_id] = ["additional"]
    
    # Build final sorted entity list
    for eid in sorted(entity_to_zone.keys()):
        all_entities.append(eid)
    
    return all_entities, entity_to_zone


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

        st = _ForwarderState(queue=[], seen_until={})
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

        forward_call_service = bool(
            cfg.get(
                CONF_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
                DEFAULT_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
            )
        )

        idempotency_ttl = int(
            cfg.get(
                CONF_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
                DEFAULT_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
            )
        )
        idempotency_ttl = max(0, min(idempotency_ttl, 86400))

        # Persistent queue options (store unsent events across HA restarts)
        persistent_enabled = bool(
            cfg.get(
                CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
                DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
            )
        )
        persistent_max_size = int(
            cfg.get(
                CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
                DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
            )
        )
        persistent_max_size = max(0, min(persistent_max_size, 50000))

        persistent_flush_interval = int(
            cfg.get(
                CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
                DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
            )
        )
        persistent_flush_interval = max(1, min(persistent_flush_interval, 60))

        st.persistent_enabled = persistent_enabled
        st.persistent_max_size = persistent_max_size
        st.persistent_flush_interval = persistent_flush_interval

        if persistent_enabled:
            st.store = Store(hass, version=1, key=_store_key(entry.entry_id))

        # Operator visibility / observability (read by sensors + diagnostics)
        data["events_forwarder_persistent_enabled"] = persistent_enabled
        data["events_forwarder_persistent_queue_len"] = 0
        data["events_forwarder_queue_len"] = 0
        data["events_forwarder_dropped_total"] = 0
        data["events_forwarder_sent_total"] = 0
        data["events_forwarder_error_total"] = 0
        data["events_forwarder_error_streak"] = 0
        data["events_forwarder_last_success_at"] = None
        data["events_forwarder_last_success_ts"] = None
        data["events_forwarder_last_error_at"] = None
        data["events_forwarder_last_error_ts"] = None

        def _schedule_task(coro_fn) -> None:
            """Schedule a coroutine function on the HA event loop.

            Avoid creating coroutine objects outside the loop thread.
            """

            def _run() -> None:
                hass.async_create_task(coro_fn())

            try:
                hass.loop.call_soon_threadsafe(_run)
            except Exception:  # noqa: BLE001
                _run()

        async def _persist_load() -> None:
            if not st.persistent_enabled or st.store is None:
                return

            try:
                loaded = await st.store.async_load()
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Events forwarder: failed to load persistent queue: %s", err)
                return

            if not isinstance(loaded, dict):
                return

            queue = loaded.get("queue")
            if isinstance(queue, list):
                st.queue = [q for q in queue if isinstance(q, dict)]
            if st.queue is None:
                st.queue = []

            seen_until = loaded.get("seen_until")
            if isinstance(seen_until, dict):
                # only keep numeric expiries
                st.seen_until = {
                    str(k): float(v)
                    for k, v in seen_until.items()
                    if isinstance(k, str) and k and isinstance(v, (int, float))
                }

            drops = loaded.get("dropped_total")
            if isinstance(drops, int):
                st.dropped_total = max(0, drops)

            # Enforce bounds on load as well.
            if st.persistent_max_size > 0 and len(st.queue) > st.persistent_max_size:
                overflow = len(st.queue) - st.persistent_max_size
                del st.queue[:overflow]
                st.dropped_total += overflow
                st.persistent_dirty = True

            data["events_forwarder_queue_len"] = len(st.queue)
            data["events_forwarder_persistent_queue_len"] = len(st.queue)
            data["events_forwarder_dropped_total"] = st.dropped_total

            # If we have pending items, schedule a send soon.
            if st.queue:
                st.unsub_timer = async_call_later(hass, 1, _flush_timer)

            if st.persistent_dirty:
                _schedule_task(_persist_save)

        async def _persist_save() -> None:
            if not st.persistent_enabled or st.store is None:
                return
            if not st.persistent_dirty:
                return

            payload = {
                "queue": st.queue or [],
                "seen_until": st.seen_until or {},
                "dropped_total": int(st.dropped_total or 0),
                "updated_at": _now_iso(),
            }
            try:
                await st.store.async_save(payload)
                st.persistent_dirty = False
                data["events_forwarder_persisted_at"] = payload["updated_at"]
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Events forwarder: failed to persist queue: %s", err)

        def _persist_timer(_now) -> None:
            # callback from async_call_later (sync context)
            # clear timer handle so future dirty writes can be scheduled
            st.unsub_persist_timer = None
            _schedule_task(_persist_save)

        def _persist_mark_dirty() -> None:
            if not st.persistent_enabled:
                return
            st.persistent_dirty = True
            if st.unsub_persist_timer is None:
                st.unsub_persist_timer = async_call_later(
                    hass, st.persistent_flush_interval, _persist_timer
                )

        def _seen_allow(id_key: str) -> bool:
            if not id_key or idempotency_ttl <= 0:
                return True

            if st.seen_until is None:
                st.seen_until = {}

            now = time.time()
            # opportunistic cleanup
            if len(st.seen_until) > 5000:
                st.seen_until = {k: v for k, v in st.seen_until.items() if v > now}
            else:
                for k, v in list(st.seen_until.items()):
                    if v <= now:
                        st.seen_until.pop(k, None)

            if st.seen_until.get(id_key, 0) > now:
                return False

            st.seen_until[id_key] = now + idempotency_ttl
            _persist_mark_dirty()
            return True

        def _enqueue(item: dict[str, Any]) -> None:
            if st.queue is None:
                st.queue = []
            st.queue.append(item)

            # Enforce bounded queue (drop-oldest). If max_size==0, treat as "no limit".
            # We apply this even when persistence is disabled to avoid unbounded RAM growth.
            if st.persistent_max_size > 0:
                overflow = len(st.queue) - st.persistent_max_size
                if overflow > 0:
                    del st.queue[:overflow]
                    st.dropped_total += overflow

            data["events_forwarder_queue_len"] = len(st.queue)
            data["events_forwarder_persistent_queue_len"] = len(st.queue)
            data["events_forwarder_dropped_total"] = st.dropped_total

            _persist_mark_dirty()

            # Schedule flush if this was the first in an empty queue.
            if st.unsub_timer is None:
                st.unsub_timer = async_call_later(hass, flush_interval, _flush_timer)

            # Flush immediately on size.
            if len(st.queue or []) >= max_batch:
                _schedule_task(_flush_now)

        async def _refresh_subscriptions() -> None:
            # Use configurable entity allowlist (Habitus zones + MediaContext + additional)
            all_entities, entity_to_zone = await _build_forwarder_entity_allowlist(hass, entry)

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

                    # Canonical event envelope (backwards compatible):
                    # keep core fields, store extra data in `attributes`.
                    id_key = _idempotency_key("state_changed", event)
                    if not _seen_allow(id_key):
                        return

                    item: dict[str, Any] = {
                        "id": id_key,
                        "ts": _now_iso(),
                        "type": "state_changed",
                        "source": "home_assistant",
                        "entity_id": eid,
                        "attributes": {
                            "domain": _domain(eid),
                            "zone_ids": zone_ids,
                            "old_state": old_state,
                            "new_state": new_state,
                            # Privacy-first: include a tiny allowlist of state attributes only.
                            "state_attributes": _allowed_state_attrs(eid, new),
                        },
                    }

                    _enqueue(item)

                    # Debug stats for operator UX
                    data["events_forwarder_seen"] = {
                        "time": _now_iso(),
                        "entity_id": eid,
                        "old_state": old_state,
                        "new_state": new_state,
                        "zones": zone_ids,
                    }

                except Exception as e:  # noqa: BLE001
                    _LOGGER.debug("Events forwarder state handler failed: %s", e)

            st.unsub_state = async_track_state_change_event(hass, all_entities, _handle_state)
            data["events_forwarder_subscribed"] = {
                "count": len(all_entities),
                "time": _now_iso(),
            }
            _LOGGER.info("Events forwarder subscribed to %d entities", len(all_entities))

        def _handle_call_service(event: Event) -> None:
            """Forward intent-like call_service events (privacy-first).

            Only forward if the call targets at least one entity that is part of a Habitus zone.
            Strip service_data except for a sanitized entity_id list.
            """

            try:
                dom = str(event.data.get("domain") or "")
                svc = str(event.data.get("service") or "")

                if dom in _BLOCKED_CALL_SERVICE_DOMAINS:
                    return

                # Strict allowlist: only forward safe-ish intent domains.
                if dom not in _ALLOWED_CALL_SERVICE_DOMAINS:
                    return
                svc_data = event.data.get("service_data")
                if not dom or not svc or not isinstance(svc_data, dict):
                    return

                entity_ids = _ensure_list_entity_ids(svc_data.get("entity_id"))
                if not entity_ids:
                    return

                entity_to_zone = st.entity_to_zone_ids or {}
                matched: list[str] = [eid for eid in entity_ids if eid in entity_to_zone]
                if not matched:
                    return

                zone_ids: list[str] = []
                for eid in matched:
                    zone_ids.extend(entity_to_zone.get(eid) or [])
                # stable + dedup
                zone_ids = sorted(set(zone_ids))

                id_key = _idempotency_key("call_service", event)
                if not _seen_allow(id_key):
                    return

                item: dict[str, Any] = {
                    "id": id_key,
                    "ts": _now_iso(),
                    "type": "call_service",
                    "source": "home_assistant",
                    # keep entity_id for envelope compatibility (first matched)
                    "entity_id": matched[0],
                    "attributes": {
                        "domain": dom,
                        "service": svc,
                        "entity_ids": matched,
                        "zone_ids": zone_ids,
                    },
                }

                _enqueue(item)

            except Exception as e:  # noqa: BLE001
                _LOGGER.debug("Events forwarder call_service handler failed: %s", e)

        async def _flush_now() -> None:
            # Avoid overlapping flush tasks; keep queue semantics predictable.
            if st.flushing:
                return
            st.flushing = True

            # Cancel pending timer if any
            if callable(st.unsub_timer):
                st.unsub_timer()
            st.unsub_timer = None

            if st.queue is None:
                st.queue = []

            if not st.queue:
                data["events_forwarder_queue_len"] = 0
                data["events_forwarder_persistent_queue_len"] = 0
                st.flushing = False
                return

            # Take up to max_batch items, keep remainder.
            items = list(st.queue[:max_batch])
            remain = list(st.queue[max_batch:])
            st.queue = remain

            data["events_forwarder_queue_len"] = len(st.queue)
            data["events_forwarder_persistent_queue_len"] = len(st.queue)

            _persist_mark_dirty()

            data["events_forwarder_last"] = {
                "sent": 0,
                "time": _now_iso(),
                "status": "sending",
            }

            payload = {"items": items}
            try:
                await api.async_post("/api/v1/events", payload)

                st.sent_total += len(items)
                st.error_streak = 0
                st.last_success_ts = time.time()
                st.first_error_ts = None

                # store last stats for diagnostics
                data["events_forwarder_last"] = {
                    "sent": len(items),
                    "time": _now_iso(),
                    "status": "sent",
                }
                data["events_forwarder_sent_total"] = st.sent_total
                data["events_forwarder_error_streak"] = st.error_streak
                data["events_forwarder_last_success_at"] = data["events_forwarder_last"]["time"]
                data["events_forwarder_last_success_ts"] = st.last_success_ts

                _persist_mark_dirty()
            except asyncio.CancelledError:
                # Cancellation should not happen during normal runtime; record it for debugging.
                data["events_forwarder_last"] = {
                    "sent": 0,
                    "time": _now_iso(),
                    "status": "cancelled",
                }
                # Re-queue: put items back at the front.
                st.queue = items + (st.queue or [])
                data["events_forwarder_queue_len"] = len(st.queue)
                data["events_forwarder_persistent_queue_len"] = len(st.queue)
                _persist_mark_dirty()
                st.flushing = False
                return
            except Exception as err:  # noqa: BLE001
                st.error_total += 1
                st.error_streak += 1
                now_ts = time.time()
                st.last_error_ts = now_ts
                if st.first_error_ts is None:
                    st.first_error_ts = now_ts

                data["events_forwarder_last"] = {
                    "sent": 0,
                    "time": _now_iso(),
                    "status": "error",
                    "error": str(err),
                }
                data["events_forwarder_error_total"] = st.error_total
                data["events_forwarder_error_streak"] = st.error_streak
                data["events_forwarder_last_error_at"] = data["events_forwarder_last"]["time"]
                data["events_forwarder_last_error_ts"] = st.last_error_ts

                _LOGGER.warning("Events forwarder failed to POST /api/v1/events: %s", err)

                # Re-queue items (front), keep order.
                st.queue = items + (st.queue or [])

                # Enforce bounds after re-queue.
                if st.persistent_max_size > 0:
                    overflow = len(st.queue) - st.persistent_max_size
                    if overflow > 0:
                        del st.queue[:overflow]
                        st.dropped_total += overflow
                        data["events_forwarder_dropped_total"] = st.dropped_total

                data["events_forwarder_queue_len"] = len(st.queue)
                data["events_forwarder_persistent_queue_len"] = len(st.queue)

                _persist_mark_dirty()

            st.flushing = False

        def _flush_timer(_now) -> None:
            # callback from async_call_later (sync context)
            _schedule_task(_flush_now)

        # Load persisted queue before subscriptions.
        await _persist_load()

        # initial subscriptions + listen for zone updates
        await _refresh_subscriptions()

        def _zones_updated(updated_entry_id: str) -> None:
            if updated_entry_id != entry.entry_id:
                return
            _schedule_task(_refresh_subscriptions)

        st.unsub_zones = async_dispatcher_connect(hass, SIGNAL_HABITUS_ZONES_UPDATED, _zones_updated)

        if forward_call_service:
            st.unsub_call_service = hass.bus.async_listen("call_service", _handle_call_service)

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
            if callable(st.unsub_call_service):
                st.unsub_call_service()
            if callable(st.unsub_persist_timer):
                st.unsub_persist_timer()

            if isinstance(data, dict):
                data.pop("events_forwarder_state", None)
                data.pop("unsub_events_forwarder", None)

        return _unsub

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        st = data.get("events_forwarder_state") if isinstance(data, dict) else None
        if isinstance(st, _ForwarderState) and st.persistent_enabled and st.store is not None:
            # Best-effort final persist.
            if st.persistent_dirty:
                try:
                    await st.store.async_save(
                        {
                            "queue": st.queue or [],
                            "seen_until": st.seen_until or {},
                            "dropped_total": int(st.dropped_total or 0),
                            "updated_at": _now_iso(),
                        }
                    )
                except Exception as err:  # noqa: BLE001
                    _LOGGER.warning("Events forwarder: failed to persist queue on unload: %s", err)

        unsub = data.get("unsub_events_forwarder") if isinstance(data, dict) else None
        if callable(unsub):
            unsub()
        return True
