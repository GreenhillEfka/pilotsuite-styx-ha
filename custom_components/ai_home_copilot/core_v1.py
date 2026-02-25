from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CopilotApiClient, CopilotApiError
from .connection_config import build_core_headers, resolve_core_connection
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


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
        # 404 means: Core without /api/v1/capabilities; try backward-compatible
        # readiness endpoints before marking as unsupported.
        if status == 404:
            for fallback in ("/api/v1/agent/status", "/chat/status"):
                try:
                    fallback_data = await api.async_get(fallback)
                    state.data = (
                        fallback_data
                        if isinstance(fallback_data, dict)
                        else {"raw": fallback_data}
                    )
                    state.http_status = 200
                    state.supported = True
                    state.error = None
                    break
                except CopilotApiError:
                    continue
                except Exception:  # noqa: BLE001
                    continue
            else:
                state.http_status = status
                state.supported = False
                state.error = "not_supported"
        elif status == 401:
            state.http_status = status
            state.supported = None
            state.error = "unauthorized"
        else:
            state.http_status = status
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


async def async_call_core_api(
    hass: HomeAssistant,
    entry: ConfigEntry,
    method: str,
    path: str,
    data: dict | None = None,
) -> dict | None:
    """Call Core Add-on API endpoint.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry with host, port, token
        method: HTTP method (GET, POST, PUT, DELETE)
        path: API path (e.g., /api/v1/status)
        data: Optional JSON payload for POST/PUT
        
    Returns:
        JSON response dict or None on error
    """
    session = async_get_clientsession(hass)
    host, port, token = resolve_core_connection(entry)
    
    url = f"http://{host}:{port}{path}"
    headers = build_core_headers(token)
    
    try:
        if method == "GET":
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        elif method == "POST":
            async with session.post(url, json=data, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        elif method == "PUT":
            async with session.put(url, json=data, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        elif method == "DELETE":
            async with session.delete(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        return None
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Core API call failed: %s", err)
        return None
