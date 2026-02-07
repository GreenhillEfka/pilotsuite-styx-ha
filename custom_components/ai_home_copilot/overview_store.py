from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

DOMAIN = "ai_home_copilot"
STORE_KEY = f"{DOMAIN}.overview"
STORE_VERSION = 1


@dataclass
class OverviewState:
    last_path: str | None = None
    last_shared_path: str | None = None
    last_published_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "last_path": self.last_path,
            "last_shared_path": self.last_shared_path,
            "last_published_path": self.last_published_path,
        }


async def async_get_overview_state(hass: HomeAssistant) -> OverviewState:
    store: Store = Store(hass, STORE_VERSION, STORE_KEY)
    data = await store.async_load() or {}
    return OverviewState(
        last_path=data.get("last_path"),
        last_shared_path=data.get("last_shared_path"),
        last_published_path=data.get("last_published_path"),
    )


async def async_set_overview_state(hass: HomeAssistant, state: OverviewState) -> None:
    store: Store = Store(hass, STORE_VERSION, STORE_KEY)
    await store.async_save(state.as_dict())
