"""Mood State Persistence — HA Storage API.

Caches zone mood snapshots locally so HA can survive Core restarts
without losing mood context. Uses HA's built-in Store API.

Privacy: All data stays local in HA's .storage directory.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.mood_cache"
_CACHE_TTL_SECONDS = 86400  # 24h — stale cache invalidated


async def _get_store(hass: HomeAssistant) -> Store:
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    store = global_data.get("_mood_store")
    if store is None:
        store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        global_data["_mood_store"] = store
    return store


async def async_save_moods(hass: HomeAssistant, moods: Dict[str, Dict[str, Any]]) -> None:
    """Persist all zone moods at once."""
    store = await _get_store(hass)
    await store.async_save({
        "ts": time.time(),
        "zones": moods,
    })


async def async_load_moods(hass: HomeAssistant) -> Dict[str, Dict[str, Any]]:
    """Load cached moods. Returns empty dict if cache is stale or missing."""
    store = await _get_store(hass)
    data = await store.async_load()
    if not isinstance(data, dict):
        return {}
    ts = data.get("ts", 0)
    if time.time() - ts > _CACHE_TTL_SECONDS:
        _LOGGER.debug("Mood cache expired (age %.0fs), ignoring", time.time() - ts)
        return {}
    return data.get("zones", {})
