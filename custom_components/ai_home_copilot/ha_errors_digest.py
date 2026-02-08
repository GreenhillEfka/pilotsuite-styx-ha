from __future__ import annotations

from datetime import datetime, timezone, timedelta
import hashlib
from collections import deque
import re
from typing import Any, Callable

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store

from .const import (
    CONF_HA_ERRORS_DIGEST_ENABLED,
    CONF_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
    CONF_HA_ERRORS_DIGEST_MAX_LINES,
    DEFAULT_HA_ERRORS_DIGEST_ENABLED,
    DEFAULT_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
    DEFAULT_HA_ERRORS_DIGEST_MAX_LINES,
    DOMAIN,
)

_LOG_PATH = "/config/home-assistant.log"

_STORAGE_VERSION = 1
_STORAGE_KEY = f"{DOMAIN}.ha_errors_digest"

_RE_REDACT_KV = re.compile(r"(?i)(x-auth-token\s*[:=]\s*)(\S+)")
_RE_REDACT_BEARER = re.compile(r"(?i)(authorization\s*:\s*bearer\s+)(\S+)")
_RE_REDACT_ACCESS_TOKEN = re.compile(r"(?i)(access_token=)([^&\s]+)")
_RE_REDACT_JWT = re.compile(r"(?<![A-Za-z0-9_-])(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tail_file_sync(path: str, max_lines: int) -> list[str]:
    dq: deque[str] = deque(maxlen=max_lines)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            dq.append(line.rstrip("\n"))
    return list(dq)


def _sanitize(text: str, *, max_chars: int = 6000) -> str:
    text = _RE_REDACT_KV.sub(r"\1**REDACTED**", text)
    text = _RE_REDACT_BEARER.sub(r"\1**REDACTED**", text)
    text = _RE_REDACT_ACCESS_TOKEN.sub(r"\1**REDACTED**", text)
    text = _RE_REDACT_JWT.sub("**REDACTED_JWT**", text)

    if len(text) > max_chars:
        text = text[: max_chars - 50] + "\n...(truncated)..."
    return text


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def _get_store(hass: HomeAssistant) -> Store:
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    store = global_data.get("ha_errors_digest_store")
    if store is None:
        store = Store(hass, _STORAGE_VERSION, _STORAGE_KEY)
        global_data["ha_errors_digest_store"] = store
    return store


async def _load_state(hass: HomeAssistant) -> dict[str, Any]:
    return await _get_store(hass).async_load() or {}


async def _save_state(hass: HomeAssistant, data: dict[str, Any]) -> None:
    await _get_store(hass).async_save(data)


_MATCH_SUBSTRINGS = [
    "ai_home_copilot",
    "RuntimeError",
    "UpdateFailed",
    "Detected that custom integration",
    "calls hass.async_create_task",
    "Task exception was never retrieved",
    "Error doing job",
    "Traceback (most recent call last)",
]


def _filter_relevant(lines: list[str]) -> list[str]:
    out: list[str] = []
    for ln in lines:
        if any(s in ln for s in _MATCH_SUBSTRINGS):
            out.append(ln)
    return out


async def async_fetch_ha_errors_digest(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    max_lines: int | None = None,
) -> tuple[str, str]:
    """Return (title, message) for a relevant HA error/warn digest."""

    cfg = entry.data | entry.options
    if max_lines is None:
        max_lines = int(cfg.get(CONF_HA_ERRORS_DIGEST_MAX_LINES, DEFAULT_HA_ERRORS_DIGEST_MAX_LINES))

    max_lines = max(50, min(int(max_lines), 5000))

    try:
        lines = await hass.async_add_executor_job(_tail_file_sync, _LOG_PATH, max_lines)
    except FileNotFoundError:
        return ("AI Home CoPilot HA errors", f"Log file not found: {_LOG_PATH}")
    except Exception as err:  # noqa: BLE001
        return ("AI Home CoPilot HA errors", f"Failed to read HA log: {err}")

    hits = _filter_relevant(lines)
    if not hits:
        return (
            "AI Home CoPilot HA errors",
            f"No matching errors/warnings found in the last {max_lines} log lines.",
        )

    # Keep the tail of the hits to focus on latest problems.
    tail = hits[-80:]
    text = "\n".join(tail)
    text = _sanitize(text, max_chars=8000)
    return ("AI Home CoPilot HA errors (digest)", text)


async def async_show_ha_errors_digest(hass: HomeAssistant, entry: ConfigEntry) -> None:
    title, msg = await async_fetch_ha_errors_digest(hass, entry)
    persistent_notification.async_create(
        hass,
        msg,
        title=title,
        notification_id="ai_home_copilot_ha_errors_digest",
    )


async def async_setup_ha_errors_digest(hass: HomeAssistant, entry: ConfigEntry) -> Callable[[], None]:
    """Set up periodic HA error digest notifications (opt-in)."""

    async def _tick(_now) -> None:
        cfg = entry.data | entry.options
        if not bool(cfg.get(CONF_HA_ERRORS_DIGEST_ENABLED, DEFAULT_HA_ERRORS_DIGEST_ENABLED)):
            return

        title, msg = await async_fetch_ha_errors_digest(hass, entry)

        sig = _sha1(msg)
        state = await _load_state(hass)
        key = entry.entry_id
        last = state.get(key) if isinstance(state.get(key), dict) else {}
        last_sig = str(last.get("last_sig", ""))
        if sig == last_sig:
            return

        persistent_notification.async_create(
            hass,
            msg,
            title=title,
            notification_id="ai_home_copilot_ha_errors_digest",
        )

        state[key] = {"last_sig": sig, "last_sent": _now_iso()}
        await _save_state(hass, state)

    interval = int(
        (entry.data | entry.options).get(
            CONF_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
            DEFAULT_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
        )
    )
    interval = max(60, min(interval, 3600))

    return async_track_time_interval(hass, _tick, timedelta(seconds=interval))
