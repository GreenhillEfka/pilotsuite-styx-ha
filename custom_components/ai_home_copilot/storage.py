from __future__ import annotations

from enum import StrEnum
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.candidates"

# Privacy/governance-first: keep the persisted store bounded.
# These values are intentionally conservative for v0.1.
MAX_CANDIDATES_PER_ENTRY = 300


class CandidateState(StrEnum):
    NEW = "new"
    OFFERED = "offered"
    DEFERRED = "deferred"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"


def _get_store(hass: HomeAssistant) -> Store:
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    store = global_data.get("store")
    if store is None:
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        global_data["store"] = store
    return store


async def _load(hass: HomeAssistant) -> dict[str, Any]:
    store = _get_store(hass)
    data = await store.async_load() or {}
    data.setdefault("entries", {})
    return data


def _parse_record(value: Any) -> dict[str, Any]:
    """Be liberal in what we accept (migration-friendly)."""
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        return {"state": value}
    return {}


def _candidate_to_snapshot(candidate: Any) -> dict[str, Any]:
    """Create a small, UI-friendly snapshot from a Candidate-like object.

    The snapshot is deliberately compact and must not contain raw event payloads.
    """

    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    title = _get(candidate, "title")
    kind = _get(candidate, "kind")
    blueprint_url = _get(candidate, "blueprint_url")
    if blueprint_url is None:
        blueprint = _get(candidate, "blueprint")
        if isinstance(blueprint, dict):
            blueprint_url = blueprint.get("url")

    score = None
    ranking = _get(candidate, "ranking")
    if isinstance(ranking, dict):
        score = ranking.get("score")

    explanation_summary = None
    evidence_small = None
    explanation = _get(candidate, "explanation")
    if isinstance(explanation, dict):
        explanation_summary = explanation.get("summary")
        ev = explanation.get("evidence")
        if isinstance(ev, dict):
            evidence_small = {
                k: ev.get(k)
                for k in ("support", "confidence", "median_dt_seconds", "lift")
                if k in ev
            }

    snap: dict[str, Any] = {
        "title": str(title) if title is not None else "",
        "kind": str(kind) if kind is not None else "",
    }
    if score is not None:
        try:
            snap["score"] = float(score)
        except Exception:  # noqa: BLE001
            pass
    if blueprint_url:
        snap["blueprint_url"] = str(blueprint_url)
    if explanation_summary:
        snap["explanation_summary"] = str(explanation_summary)
    if evidence_small:
        snap["evidence"] = evidence_small

    return snap


def _prune_entry_records(entry_records: dict[str, Any]) -> None:
    """Bound per-entry growth (LRU-ish by last_seen_ts, then first_seen_ts)."""
    if len(entry_records) <= MAX_CANDIDATES_PER_ENTRY:
        return

    sortable: list[tuple[float, float, str]] = []
    for cid, raw in list(entry_records.items()):
        rec = _parse_record(raw)
        try:
            last_seen = float(rec.get("last_seen_ts") or 0.0)
        except Exception:  # noqa: BLE001
            last_seen = 0.0
        try:
            first_seen = float(rec.get("first_seen_ts") or 0.0)
        except Exception:  # noqa: BLE001
            first_seen = 0.0
        sortable.append((last_seen, first_seen, cid))

    # Keep most-recent, drop the rest.
    sortable.sort(reverse=True)
    keep = {cid for _ls, _fs, cid in sortable[:MAX_CANDIDATES_PER_ENTRY]}
    for cid in list(entry_records.keys()):
        if cid not in keep:
            entry_records.pop(cid, None)


async def _save(hass: HomeAssistant, data: dict[str, Any]) -> None:
    # Opportunistic pruning before persisting.
    entries = data.get("entries")
    if isinstance(entries, dict):
        for _entry_id, entry_records in entries.items():
            if isinstance(entry_records, dict):
                _prune_entry_records(entry_records)

    store = _get_store(hass)
    await store.async_save(data)


async def async_get_candidate_record(
    hass: HomeAssistant, entry_id: str, candidate_id: str
) -> dict[str, Any]:
    data = await _load(hass)
    entry = data["entries"].get(entry_id, {})
    rec = _parse_record(entry.get(candidate_id))
    return rec


async def async_get_candidate_state(
    hass: HomeAssistant, entry_id: str, candidate_id: str
) -> CandidateState:
    rec = await async_get_candidate_record(hass, entry_id, candidate_id)
    state = rec.get("state", CandidateState.NEW)
    try:
        return CandidateState(state)
    except Exception:  # noqa: BLE001
        return CandidateState.NEW


async def async_set_candidate_state(
    hass: HomeAssistant, entry_id: str, candidate_id: str, state: CandidateState
) -> None:
    data = await _load(hass)
    entries = data["entries"].setdefault(entry_id, {})
    cur = _parse_record(entries.get(candidate_id))
    cur["state"] = state.value
    entries[candidate_id] = cur
    await _save(hass, data)


async def async_mark_seen(
    hass: HomeAssistant,
    entry_id: str,
    candidate_id: str,
    *,
    ts: float,
) -> None:
    """Mark candidate as seen/refreshed.

    This is used to support pruning and UI/debug info.
    """
    data = await _load(hass)
    entries = data["entries"].setdefault(entry_id, {})
    cur = _parse_record(entries.get(candidate_id))

    if not cur.get("first_seen_ts"):
        cur["first_seen_ts"] = float(ts)
    cur["last_seen_ts"] = float(ts)

    # Default state if missing.
    cur.setdefault("state", CandidateState.NEW.value)

    entries[candidate_id] = cur
    await _save(hass, data)


async def async_upsert_candidate_snapshot(
    hass: HomeAssistant,
    entry_id: str,
    candidate: Any,
) -> None:
    """Persist a compact candidate snapshot (so Repairs still works if Core is offline)."""

    def _get(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    candidate_id = _get(candidate, "candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id:
        return

    snapshot = _candidate_to_snapshot(candidate)

    data = await _load(hass)
    entries = data["entries"].setdefault(entry_id, {})
    cur = _parse_record(entries.get(candidate_id))
    cur["snapshot"] = snapshot
    entries[candidate_id] = cur
    await _save(hass, data)


async def async_defer_candidate(
    hass: HomeAssistant,
    entry_id: str,
    candidate_id: str,
    *,
    until_ts: float,
) -> None:
    data = await _load(hass)
    entries = data["entries"].setdefault(entry_id, {})
    cur = _parse_record(entries.get(candidate_id))
    cur["state"] = CandidateState.DEFERRED.value
    cur["defer_until_ts"] = float(until_ts)
    entries[candidate_id] = cur
    await _save(hass, data)


async def async_should_offer(
    hass: HomeAssistant,
    entry_id: str,
    candidate_id: str,
    *,
    now_ts: float,
) -> bool:
    """Offer-guard (anti-nagging)."""
    state = await async_get_candidate_state(hass, entry_id, candidate_id)
    if state in (CandidateState.ACCEPTED, CandidateState.DISMISSED):
        return False

    if state == CandidateState.DEFERRED:
        rec = await async_get_candidate_record(hass, entry_id, candidate_id)
        until_ts = rec.get("defer_until_ts")
        try:
            until_ts_f = float(until_ts)
        except Exception:  # noqa: BLE001
            until_ts_f = 0.0

        if until_ts_f and now_ts < until_ts_f:
            return False

    return True


async def async_record_offer(
    hass: HomeAssistant,
    entry_id: str,
    candidate_id: str,
    *,
    now_ts: float,
    issue_id: str | None = None,
) -> None:
    """Persist side-effects of an offer (state, counters, timestamps)."""
    data = await _load(hass)
    entries = data["entries"].setdefault(entry_id, {})
    cur = _parse_record(entries.get(candidate_id))

    cur["state"] = CandidateState.OFFERED.value
    cur["last_offered_ts"] = float(now_ts)
    cur["offer_count"] = int(cur.get("offer_count") or 0) + 1
    if issue_id:
        cur["last_issue_id"] = issue_id

    entries[candidate_id] = cur
    await _save(hass, data)
