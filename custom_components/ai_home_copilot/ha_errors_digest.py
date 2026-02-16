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
    return hashlib.blake2b(text.encode("utf-8", errors="ignore")).hexdigest()[:32]


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


def _parse_traceback_signature(entry: list[str]) -> str:
    """Extract a signature for grouping similar tracebacks."""
    text = "\n".join(entry)
    
    # Extract error type and location
    error_type = "Unknown"
    location = "unknown"
    
    # Handle simple format: "ValueError@api.py error 1"
    if len(entry) == 1 and "@" in entry[0]:
        first_line = entry[0]
        # Look for pattern: ErrorType@file.extension
        import re
        match = re.match(r'^(\w+Error|\w+Exception|\w+Warning)@(\S+)', first_line)
        if match:
            error_type = match.group(1)
            location = match.group(2).split()[0]  # Get filename, ignore rest
            return f"{error_type}@{location}"
    
    # Look for Python exception patterns
    for line in entry:
        # Exception type at end of traceback
        if ": " in line and any(exc in line for exc in ["Error", "Exception", "Warning"]):
            parts = line.split(": ", 1)
            if parts[0].strip():
                error_type = parts[0].strip().split(".")[-1]  # Get last part of module.Error
                break
    
    # Look for file location (most specific stack frame in our code)
    for line in entry:
        if "custom_components/ai_home_copilot" in line and "line " in line:
            # Extract filename and line
            if 'File "' in line:
                try:
                    file_part = line.split('File "')[1].split('"')[0]
                    filename = file_part.split("/")[-1]  # Just the filename
                    location = filename
                    break
                except (IndexError, AttributeError):
                    pass
    
    return f"{error_type}@{location}"


def _group_entries(entries: list[str]) -> list[tuple[str, list[str]]]:
    """Group similar error entries by signature."""
    groups: dict[str, list[str]] = {}
    
    for entry_text in entries:
        entry_lines = entry_text.split("\n")
        signature = _parse_traceback_signature(entry_lines)
        
        if signature not in groups:
            groups[signature] = []
        groups[signature].append(entry_text)
    
    # Sort by frequency (most common errors first)
    sorted_groups = sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)
    
    return sorted_groups


def _format_grouped_entries(grouped: list[tuple[str, list[str]]]) -> str:
    """Format grouped entries with counts and latest example."""
    sections = []
    
    for signature, entries in grouped:
        count = len(entries)
        latest = entries[-1]  # Most recent occurrence
        
        if count == 1:
            header = f"🔸 **{signature}**"
        else:
            header = f"🔸 **{signature}** ({count}x)"
        
        # For repeated errors, show just the latest occurrence
        sections.append(f"{header}\n```\n{latest}\n```")
    
    return "\n\n".join(sections)


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
    tail = hits[-20:]  # Increased from 12 to allow better grouping

    # Group similar errors for better readability
    grouped = _group_entries(tail)
    
    # Format with grouping and counts
    text = _format_grouped_entries(grouped)
    
    # Add summary header
    total_errors = len(tail)
    unique_types = len(grouped)
    summary = f"**Fehler-Digest** ({total_errors} Einträge, {unique_types} Typen)\n\n"
    text = summary + text
    
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
