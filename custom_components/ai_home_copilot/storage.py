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


async def async_get_candidate_state(
    hass: HomeAssistant, entry_id: str, candidate_id: str
) -> CandidateState:
    data = await _load(hass)
    entry = data["entries"].get(entry_id, {})
    state = entry.get(candidate_id, CandidateState.NEW)
    try:
        return CandidateState(state)
    except Exception:  # noqa: BLE001
        return CandidateState.NEW


async def async_set_candidate_state(
    hass: HomeAssistant, entry_id: str, candidate_id: str, state: CandidateState
) -> None:
    data = await _load(hass)
    entries = data["entries"].setdefault(entry_id, {})
    entries[candidate_id] = state.value
    await _save(hass, data)
