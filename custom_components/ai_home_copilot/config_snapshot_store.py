from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.config_snapshot"


@dataclass(frozen=True, slots=True)
class ConfigSnapshotState:
    last_generated_path: str | None = None
    last_published_path: str | None = None


def _store(hass: HomeAssistant) -> Store:
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    st = global_data.get("config_snapshot_store")
    if st is None:
        st = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        global_data["config_snapshot_store"] = st
    return st


async def async_get_state(hass: HomeAssistant) -> ConfigSnapshotState:
    data = await _store(hass).async_load() or {}
    if not isinstance(data, dict):
        data = {}
    return ConfigSnapshotState(
        last_generated_path=data.get("last_generated_path"),
        last_published_path=data.get("last_published_path"),
    )


async def async_set_last_generated(hass: HomeAssistant, path: str) -> None:
    st = _store(hass)
    data = await st.async_load() or {}
    if not isinstance(data, dict):
        data = {}
    data["last_generated_path"] = path
    await st.async_save(data)


async def async_set_last_published(hass: HomeAssistant, path: str) -> None:
    st = _store(hass)
    data = await st.async_load() or {}
    if not isinstance(data, dict):
        data = {}
    data["last_published_path"] = path
    await st.async_save(data)
