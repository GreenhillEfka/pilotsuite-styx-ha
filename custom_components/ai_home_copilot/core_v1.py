from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .api import CopilotApiClient, CopilotApiError
from .const import DOMAIN


SIGNAL_CORE_CAPABILITIES_UPDATED = f"{DOMAIN}_core_capabilities_updated"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_http_status(err: Exception) -> int | None:
    # CopilotApiError text: "HTTP {status} for {url}: ..."
    m = re.match(r"^HTTP\s+(\d+)\s+for\s+", str(err))
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:  # noqa: BLE001
        return None


@dataclass(slots=True)
class CoreCapabilitiesState:
    fetched: str | None = None
    supported: bool | None = None
    http_status: int | None = None
    error: str | None = None
    data: dict[str, Any] | None = None


def _entry_data(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    dom = hass.data.setdefault(DOMAIN, {})
    ent = dom.setdefault(entry_id, {})
    if isinstance(ent, dict):
        return ent
    # should not happen, but keep safe
    ent = {}
    dom[entry_id] = ent
    return ent


async def async_fetch_core_capabilities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    api: CopilotApiClient,
) -> CoreCapabilitiesState:
    state = CoreCapabilitiesState(fetched=_now_iso())

    try:
        data = await api.async_get("/api/v1/capabilities")
        state.data = data if isinstance(data, dict) else {"raw": data}
        state.http_status = 200
        state.supported = True
        state.error = None
    except CopilotApiError as err:
        status = _parse_http_status(err)
        state.http_status = status
        # 404 means: old core without API v1
        if status == 404:
            state.supported = False
            state.error = "not_supported"
        elif status == 401:
            state.supported = None
            state.error = "unauthorized"
        else:
            state.supported = None
            state.error = str(err)

    data = _entry_data(hass, entry.entry_id)
    data["core_capabilities"] = {
        "fetched": state.fetched,
        "supported": state.supported,
        "http_status": state.http_status,
        "error": state.error,
        "data": state.data,
    }

    # Thread-safe dispatch: ensure callbacks run on the event loop.
    hass.loop.call_soon_threadsafe(async_dispatcher_send, hass, SIGNAL_CORE_CAPABILITIES_UPDATED, entry.entry_id)
    return state


def get_cached_core_capabilities(hass: HomeAssistant, entry_id: str) -> dict[str, Any] | None:
    ent = hass.data.get(DOMAIN, {}).get(entry_id)
    if not isinstance(ent, dict):
        return None
    cap = ent.get("core_capabilities")
    return cap if isinstance(cap, dict) else None
