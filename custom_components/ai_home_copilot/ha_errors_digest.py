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
    # direct signal
    "ai_home_copilot",
    "custom_components.ai_home_copilot",
    "custom integration 'ai_home_copilot'",
    # generic HA issues we care about (only when our stack/lines are involved)
    "Detected that custom integration",
    "calls hass.async_create_task",
    "calls async_write_ha_state",
    "Detected blocking call",
    "UpdateFailed",
    "RuntimeError",
    "Task exception was never retrieved",
    "Error doing job",
]

_RE_ENTRY_START = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} ")


def _split_log_entries(lines: list[str]) -> list[list[str]]:
    """Split raw log lines into entries (timestamp line + continuation).

    Home Assistant writes multiline tracebacks without timestamps on continuation lines.
    """

    entries: list[list[str]] = []
    cur: list[str] = []

    for ln in lines:
        if _RE_ENTRY_START.match(ln):
            if cur:
                entries.append(cur)
            cur = [ln]
        else:
            if not cur:
                # Skip preamble/noise.
                continue
            cur.append(ln)

    if cur:
        entries.append(cur)

    return entries


def _is_relevant_entry(entry: list[str]) -> bool:
    text = "\n".join(entry)

    # Prefer entries clearly tied to our integration.
    if any(s in text for s in ("ai_home_copilot", "custom_components.ai_home_copilot")):
        return True

    # Allow some generic HA problems *only* if the stack points to our files.
    if "custom_components/ai_home_copilot" in text:
        return True

    return False


def _format_entry(entry: list[str]) -> str:
    # Keep tracebacks intact but bounded.
    # Strip trailing empty lines.
    while entry and not entry[-1].strip():
        entry.pop()
    return "\n".join(entry)


def _filter_relevant(lines: list[str]) -> list[str]:
    """Return a list of formatted, relevant log entries."""

    entries = _split_log_entries(lines)
    hits: list[str] = []

    for e in entries:
        text = "\n".join(e)
        if not any(s in text for s in _MATCH_SUBSTRINGS):
            continue
        if not _is_relevant_entry(e):
            continue
        hits.append(_format_entry(list(e)))

    return hits


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
            f"Keine passenden Fehler/Warnungen in den letzten {max_lines} Log-Zeilen gefunden.",
        )

    # Keep the tail of the hits to focus on latest problems.
    tail = hits[-12:]

    text = "\n\n---\n\n".join(tail)
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
