from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

DOMAIN = "ai_home_copilot"
STORE_KEY = f"{DOMAIN}.seed_limiter"
STORE_VERSION = 1


@dataclass
class SeedLimiterState:
    window_start_ts: float | None = None
    count_in_window: int = 0
    last_offer_ts: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "window_start_ts": self.window_start_ts,
            "count_in_window": self.count_in_window,
            "last_offer_ts": self.last_offer_ts,
        }


async def async_get_seed_limiter_state(hass: HomeAssistant) -> SeedLimiterState:
    store: Store = Store(hass, STORE_VERSION, STORE_KEY)
    data = await store.async_load() or {}
    return SeedLimiterState(
        window_start_ts=data.get("window_start_ts"),
        count_in_window=int(data.get("count_in_window") or 0),
        last_offer_ts=data.get("last_offer_ts"),
    )


async def async_set_seed_limiter_state(hass: HomeAssistant, state: SeedLimiterState) -> None:
    store: Store = Store(hass, STORE_VERSION, STORE_KEY)
    await store.async_save(state.as_dict())
