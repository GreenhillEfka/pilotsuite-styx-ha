from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.candidates"


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


async def _save(hass: HomeAssistant, data: dict[str, Any]) -> None:
    store = _get_store(hass)
    await store.async_save(data)


def _parse_record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        return {"state": value}
    return {}


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
