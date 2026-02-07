from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORE_KEY = f"{DOMAIN}.habitus_dashboard"
STORE_VERSION = 1


@dataclass
class HabitusDashboardState:
    last_path: str | None = None
    last_published_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "last_path": self.last_path,
            "last_published_path": self.last_published_path,
        }


def _store(hass: HomeAssistant) -> Store:
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    st = global_data.get("habitus_dashboard_store")
    if st is None:
        st = Store(hass, STORE_VERSION, STORE_KEY)
        global_data["habitus_dashboard_store"] = st
    return st


async def async_get_state(hass: HomeAssistant) -> HabitusDashboardState:
    data = await _store(hass).async_load() or {}
    return HabitusDashboardState(
        last_path=data.get("last_path"),
        last_published_path=data.get("last_published_path"),
    )


async def async_set_state(hass: HomeAssistant, st: HabitusDashboardState) -> None:
    await _store(hass).async_save(st.as_dict())
