"""History Backfill Module — Bootstrap Brain Graph from HA Recorder.

On first setup (or on demand), fetches recent state history for allowlisted
entities and sends it to Core as events, so the Brain Graph can learn from
past behavior immediately instead of waiting for real-time events.

Privacy: Only entities in the Events Forwarder allowlist are fetched.
Persistence: Backfill completion is tracked via HA Storage so it only runs once.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from ...const import DOMAIN
from ..modules.module import ModuleContext
from .events_forwarder import (
    _build_forwarder_entity_allowlist,
    _domain,
    _entry_data,
    _now_iso,
)

_LOGGER = logging.getLogger(__name__)

_BACKFILL_HOURS = 24  # How far back to look
_BATCH_SIZE = 50  # Items per POST to Core
_STORAGE_VERSION = 1
_STORAGE_KEY_FMT = "{domain}.history_backfill.{entry_id}"


class HistoryBackfillModule:
    """One-time history backfill from HA Recorder to Core Brain Graph."""

    name = "history_backfill"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        data = _entry_data(hass, entry.entry_id)
        coordinator = data.get("coordinator")
        api = getattr(coordinator, "api", None)
        if api is None:
            _LOGGER.debug("History backfill: coordinator/api not ready, skipping")
            return

        # Check if backfill was already done
        store_key = _STORAGE_KEY_FMT.format(domain=DOMAIN, entry_id=entry.entry_id)
        store = Store(hass, version=_STORAGE_VERSION, key=store_key)

        stored = await store.async_load()
        if isinstance(stored, dict) and stored.get("completed"):
            _LOGGER.debug(
                "History backfill already completed at %s, skipping",
                stored.get("completed_at", "?"),
            )
            return

        # Build entity allowlist (same as events_forwarder)
        all_entities, entity_to_zone = await _build_forwarder_entity_allowlist(hass, entry)
        if not all_entities:
            _LOGGER.debug("History backfill: no entities in allowlist")
            return

        # Schedule backfill as a background task so it doesn't block setup
        hass.async_create_task(
            self._run_backfill(hass, api, store, all_entities, entity_to_zone, data)
        )

    async def _run_backfill(
        self,
        hass: HomeAssistant,
        api: Any,
        store: Store,
        entities: list[str],
        entity_to_zone: dict[str, list[str]],
        data: dict[str, Any],
    ) -> None:
        """Fetch history from Recorder and send to Core."""
        try:
            # Import recorder at runtime (only available in HA)
            from homeassistant.components.recorder import get_instance  # noqa: E402
            from homeassistant.components.recorder.history import state_changes_during_period  # noqa: E402
        except ImportError:
            _LOGGER.warning("History backfill: recorder component not available")
            return

        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=_BACKFILL_HOURS)

        _LOGGER.info(
            "History backfill: fetching last %dh for %d entities",
            _BACKFILL_HOURS,
            len(entities),
        )

        try:
            # Use Recorder API to get state changes
            recorder = get_instance(hass)
            history = await recorder.async_add_executor_job(
                state_changes_during_period,
                hass,
                start,
                now,
                ",".join(entities),
            )
        except Exception as exc:
            _LOGGER.warning("History backfill: failed to fetch history: %s", exc)
            return

        # Convert state changes to event items (same format as events_forwarder)
        items: list[dict[str, Any]] = []
        total_states = 0

        for entity_id, states in history.items():
            zone_ids = entity_to_zone.get(entity_id, [])
            prev_state = None

            for state in states:
                state_val = state.state if hasattr(state, "state") else str(state)
                ts = state.last_changed if hasattr(state, "last_changed") else now

                if prev_state is not None and prev_state != state_val:
                    items.append({
                        "id": f"backfill:{entity_id}:{ts.isoformat()}",
                        "ts": ts.isoformat(),
                        "type": "state_changed",
                        "source": "history_backfill",
                        "entity_id": entity_id,
                        "attributes": {
                            "domain": _domain(entity_id),
                            "zone_ids": zone_ids,
                            "old_state": prev_state,
                            "new_state": state_val,
                        },
                    })
                    total_states += 1

                prev_state = state_val

        _LOGGER.info(
            "History backfill: found %d state changes, sending in batches of %d",
            total_states,
            _BATCH_SIZE,
        )

        # Send in batches
        sent = 0
        errors = 0
        for i in range(0, len(items), _BATCH_SIZE):
            batch = items[i : i + _BATCH_SIZE]
            try:
                await api.async_post("/api/v1/events", {"items": batch})
                sent += len(batch)
            except Exception as exc:
                _LOGGER.warning("History backfill batch failed: %s", exc)
                errors += 1

        _LOGGER.info(
            "History backfill complete: %d events sent, %d batch errors",
            sent,
            errors,
        )

        # Mark as completed
        await store.async_save({
            "completed": True,
            "completed_at": _now_iso(),
            "entities_count": len(entities),
            "events_sent": sent,
            "batch_errors": errors,
            "backfill_hours": _BACKFILL_HOURS,
        })

        data["history_backfill_status"] = {
            "completed": True,
            "events_sent": sent,
            "time": _now_iso(),
        }

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        return True
