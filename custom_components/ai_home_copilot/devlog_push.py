from __future__ import annotations

from datetime import datetime, timezone, timedelta
import hashlib
import re
from collections import deque
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store

from .api import CopilotApiClient
from .const import (
    CONF_DEVLOG_PUSH_ENABLED,
    CONF_DEVLOG_PUSH_INTERVAL_SECONDS,
    CONF_DEVLOG_PUSH_MAX_CHARS,
    CONF_DEVLOG_PUSH_MAX_LINES,
    CONF_DEVLOG_PUSH_PATH,
    DEFAULT_DEVLOG_PUSH_ENABLED,
    DEFAULT_DEVLOG_PUSH_INTERVAL_SECONDS,
    DEFAULT_DEVLOG_PUSH_MAX_CHARS,
    DEFAULT_DEVLOG_PUSH_MAX_LINES,
    DEFAULT_DEVLOG_PUSH_PATH,
    DOMAIN,
)

_LOG_PATH = "/config/home-assistant.log"

_STORAGE_VERSION = 1
_STORAGE_KEY = f"{DOMAIN}.devlog_push"


_RE_TS = re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}")
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


def _extract_latest_block(lines: list[str]) -> str | None:
    """Extract the most recent traceback block that references ai_home_copilot."""

    if not lines:
        return None

    # Heuristic: find "Error handling request" blocks that include our integration path.
    starts = [
        i
        for i, line in enumerate(lines)
        if "Error handling request" in line and "Traceback" in line
    ]

    for start in reversed(starts):
        end = min(len(lines), start + 260)
        j = start + 1
        while j < end:
            # Stop at next "normal" log record (timestamp) after the traceback.
            if _RE_TS.match(lines[j]) and not lines[j].lstrip().startswith("File "):
                break
            j += 1

        block = "\n".join(lines[start:j]).strip()
        if not block:
            continue
        if "/config/custom_components/ai_home_copilot/" in block or "[ai_home_copilot]" in block:
            return block

    # Fallback: any block containing our integration path.
    for i in range(len(lines) - 1, -1, -1):
        if "/config/custom_components/ai_home_copilot/" in lines[i] or "[ai_home_copilot]" in lines[i]:
            start = max(0, i - 50)
            end = min(len(lines), i + 20)
            block = "\n".join(lines[start:end]).strip()
            return block

    return None


def _sanitize(text: str, *, max_chars: int) -> str:
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
    store = global_data.get("devlog_push_store")
    if store is None:
        store = Store(hass, _STORAGE_VERSION, _STORAGE_KEY)
        global_data["devlog_push_store"] = store
    return store


async def _load_state(hass: HomeAssistant) -> dict[str, Any]:
    store = _get_store(hass)
    return await store.async_load() or {}


async def _save_state(hass: HomeAssistant, data: dict[str, Any]) -> None:
    store = _get_store(hass)
    await store.async_save(data)


async def async_push_devlog_test(hass: HomeAssistant, entry: ConfigEntry, *, api: CopilotApiClient) -> None:
    """Manually push a short test message to the Copilot-Core devlog endpoint."""
    cfg = entry.data | entry.options
    path = str(cfg.get(CONF_DEVLOG_PUSH_PATH, DEFAULT_DEVLOG_PUSH_PATH) or DEFAULT_DEVLOG_PUSH_PATH)

    payload = {
        "kind": "devlog_test",
        "when": _now_iso(),
        "source": {"type": "homeassistant", "entry_id": entry.entry_id},
        "text": "AI Home CoPilot devlog test message (sanitized pipeline check).",
    }

    await api.async_post(path, payload)


async def async_push_latest_ai_copilot_error(hass: HomeAssistant, entry: ConfigEntry, *, api: CopilotApiClient) -> bool:
    """Push the latest ai_home_copilot-related traceback block, if any. Returns True if sent."""

    cfg = entry.data | entry.options
    max_lines = int(cfg.get(CONF_DEVLOG_PUSH_MAX_LINES, DEFAULT_DEVLOG_PUSH_MAX_LINES))
    max_chars = int(cfg.get(CONF_DEVLOG_PUSH_MAX_CHARS, DEFAULT_DEVLOG_PUSH_MAX_CHARS))
    path = str(cfg.get(CONF_DEVLOG_PUSH_PATH, DEFAULT_DEVLOG_PUSH_PATH) or DEFAULT_DEVLOG_PUSH_PATH)

    try:
        lines = await hass.async_add_executor_job(_tail_file_sync, _LOG_PATH, max_lines)
    except FileNotFoundError:
        return False

    block = _extract_latest_block(lines)
    if not block:
        return False

    sanitized = _sanitize(block, max_chars=max_chars)
    sig = _sha1(sanitized)

    state = await _load_state(hass)
    key = entry.entry_id
    last = state.get(key) if isinstance(state.get(key), dict) else {}
    last_sig = str(last.get("last_sig", ""))

    if sig == last_sig:
        return False

    payload = {
        "kind": "ha_log_snippet",
        "when": _now_iso(),
        "source": {"type": "homeassistant", "entry_id": entry.entry_id},
        "text": sanitized,
    }

    await api.async_post(path, payload)

    state[key] = {"last_sig": sig, "last_sent": payload["when"]}
    await _save_state(hass, state)
    return True


async def async_setup_devlog_push(
    hass: HomeAssistant, entry: ConfigEntry, *, coordinator_api: CopilotApiClient
) -> Callable[[], None]:
    """Set up periodic log-snippet push (opt-in). Returns an unsubscribe callable."""

    async def _tick(_now) -> None:
        cfg = entry.data | entry.options

        enabled = cfg.get(CONF_DEVLOG_PUSH_ENABLED, DEFAULT_DEVLOG_PUSH_ENABLED)
        if not enabled:
            return

        max_lines = int(cfg.get(CONF_DEVLOG_PUSH_MAX_LINES, DEFAULT_DEVLOG_PUSH_MAX_LINES))
        max_chars = int(cfg.get(CONF_DEVLOG_PUSH_MAX_CHARS, DEFAULT_DEVLOG_PUSH_MAX_CHARS))
        path = str(cfg.get(CONF_DEVLOG_PUSH_PATH, DEFAULT_DEVLOG_PUSH_PATH) or DEFAULT_DEVLOG_PUSH_PATH)

        try:
            lines = await hass.async_add_executor_job(_tail_file_sync, _LOG_PATH, max_lines)
        except FileNotFoundError:
            return
        except Exception:  # noqa: BLE001
            return

        block = _extract_latest_block(lines)
        if not block:
            return

        sanitized = _sanitize(block, max_chars=max_chars)
        sig = _sha1(sanitized)

        state = await _load_state(hass)
        key = entry.entry_id
        last = state.get(key) if isinstance(state.get(key), dict) else {}
        last_sig = str(last.get("last_sig", ""))

        # Deduplicate identical blocks.
        if sig == last_sig:
            return

        payload = {
            "kind": "ha_log_snippet",
            "when": _now_iso(),
            "source": {"type": "homeassistant", "entry_id": entry.entry_id},
            "text": sanitized,
        }

        try:
            await coordinator_api.async_post(path, payload)
        except Exception:  # noqa: BLE001
            # Best-effort only.
            return

        state[key] = {"last_sig": sig, "last_sent": payload["when"]}
        await _save_state(hass, state)

    interval = int(
        (entry.data | entry.options).get(
            CONF_DEVLOG_PUSH_INTERVAL_SECONDS, DEFAULT_DEVLOG_PUSH_INTERVAL_SECONDS
        )
    )
    interval = max(10, min(interval, 3600))

    return async_track_time_interval(hass, _tick, timedelta(seconds=interval))
