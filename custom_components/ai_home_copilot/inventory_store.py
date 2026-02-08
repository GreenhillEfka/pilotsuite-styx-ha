from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

DOMAIN = "ai_home_copilot"
STORE_KEY = f"{DOMAIN}.inventory"
STORE_VERSION = 1


@dataclass
class InventoryState:
    last_generated_at: str | None = None  # ISO string
    last_generated_json: str | None = None
    last_generated_md: str | None = None
    last_published_json: str | None = None
    last_published_md: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "last_generated_at": self.last_generated_at,
            "last_generated_json": self.last_generated_json,
            "last_generated_md": self.last_generated_md,
            "last_published_json": self.last_published_json,
            "last_published_md": self.last_published_md,
        }


async def async_get_inventory_state(hass: HomeAssistant) -> InventoryState:
    store: Store = Store(hass, STORE_VERSION, STORE_KEY)
    data = await store.async_load() or {}
    return InventoryState(
        last_generated_at=data.get("last_generated_at"),
        last_generated_json=data.get("last_generated_json"),
        last_generated_md=data.get("last_generated_md"),
        last_published_json=data.get("last_published_json"),
        last_published_md=data.get("last_published_md"),
    )


async def async_set_inventory_state(hass: HomeAssistant, state: InventoryState) -> None:
    store: Store = Store(hass, STORE_VERSION, STORE_KEY)
    await store.async_save(state.as_dict())
