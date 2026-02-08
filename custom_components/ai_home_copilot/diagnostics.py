from __future__ import annotations

import dataclasses
import hashlib
import hmac
import re
import time
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DEVLOG_PUSH_ENABLED,
    CONF_DEVLOG_PUSH_INTERVAL_SECONDS,
    CONF_DEVLOG_PUSH_MAX_CHARS,
    CONF_DEVLOG_PUSH_MAX_LINES,
    CONF_HOST,
    CONF_MEDIA_MUSIC_PLAYERS,
    CONF_MEDIA_TV_PLAYERS,
    CONF_PORT,
    CONF_TOKEN,
    CONF_WATCHDOG_ENABLED,
    CONF_WATCHDOG_INTERVAL_SECONDS,
    DOMAIN,
)

TO_REDACT = {
    CONF_TOKEN,
    "token",
    "access_token",
    "refresh_token",
    "password",
    "api_key",
}

CONTRACT = "diagnostics_contract"
CONTRACT_VERSION = "0.1"

_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_RE_JWT = re.compile(
    r"(?<![A-Za-z0-9_-])(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})"
)
_RE_BEARER = re.compile(r"(?i)(bearer\s+)(\S+)")
_RE_URL = re.compile(r"https?://[^\s]+")
_RE_SECRETISH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9_\-]{32,}(?![A-Za-z0-9])")


@dataclasses.dataclass
class RedactionStats:
    redacted_email: int = 0
    redacted_secret: int = 0


def _now_ms() -> int:
    return int(time.time() * 1000)


def _sanitize_text(text: str, *, stats: RedactionStats | None = None, max_chars: int = 2000) -> str:
    if not text:
        return ""

    def _count_sub(regex: re.Pattern[str], repl: str, s: str, field: str) -> str:
        nonlocal stats
        if stats is None:
            return regex.sub(repl, s)
        new_s, n = regex.subn(repl, s)
        if n:
            setattr(stats, field, getattr(stats, field) + n)
        return new_s

    def _url_repl(m: re.Match[str]) -> str:
        url = m.group(0)
        return url.split("?", 1)[0].split("#", 1)[0]

    text = _RE_URL.sub(_url_repl, text)
    text = _count_sub(_RE_BEARER, r"\1[REDACTED_SECRET]", text, "redacted_secret")
    text = _count_sub(_RE_JWT, "[REDACTED_SECRET]", text, "redacted_secret")
    text = _count_sub(_RE_SECRETISH, "[REDACTED_SECRET]", text, "redacted_secret")
    text = _count_sub(_RE_EMAIL, "[REDACTED_EMAIL]", text, "redacted_email")

    if len(text) > max_chars:
        text = text[: max_chars - 20] + "…(truncated)…"
    return text


def _pseudonymize(*, salt: bytes, prefix: str, value: str) -> str:
    digest = hmac.new(salt, value.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"{prefix}_{digest}"


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Privacy-first:
    - best-effort redaction
    - bounded sizes

    Docs: https://developers.home-assistant.io/docs/core/diagnostics/
    """

    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator") if isinstance(data, dict) else None
    media_coordinator = data.get("media_coordinator") if isinstance(data, dict) else None

    cfg = entry.data | entry.options

    core_status: dict[str, Any] | None = None
    core_devlogs: Any = None

    if coordinator is not None:
        try:
            st = await coordinator.api.async_get_status()
            core_status = {"ok": st.ok, "version": st.version}
        except Exception as err:  # noqa: BLE001
            core_status = {"error": str(err)}

        # Best-effort: may require token and endpoint support.
        try:
            core_devlogs = await coordinator.api.async_get("/api/v1/dev/logs?limit=10")
        except Exception as err:  # noqa: BLE001
            core_devlogs = {"error": str(err)}

    media_state: dict[str, Any] | None = None
    if media_coordinator is not None and getattr(media_coordinator, "data", None) is not None:
        d = media_coordinator.data
        media_state = {
            "music_active": d.music_active,
            "tv_active": d.tv_active,
            "music_primary_area": d.music_primary_area,
            "tv_primary_area": d.tv_primary_area,
            "music_now_playing": d.music_now_playing,
            "tv_source": d.tv_source,
            "music_active_count": d.music_active_count,
            "tv_active_count": d.tv_active_count,
        }

    red_stats = RedactionStats()
    # Stable per-entry salt (salt itself is not secret; do not include derived bytes).
    salt_id = entry.entry_id
    salt = hashlib.sha256(("diag:" + salt_id).encode("utf-8")).digest()

    def pseudo_ent(v: str) -> str:
        return _pseudonymize(salt=salt, prefix="ent", value=v)

    # Only include a curated subset of config (privacy-first, no raw entity_ids/paths).
    host = str(cfg.get(CONF_HOST) or "")
    cfg_public = {
        CONF_HOST: (_pseudonymize(salt=salt, prefix="host", value=host) if host else None),
        CONF_PORT: cfg.get(CONF_PORT),
        CONF_WATCHDOG_ENABLED: cfg.get(CONF_WATCHDOG_ENABLED),
        CONF_WATCHDOG_INTERVAL_SECONDS: cfg.get(CONF_WATCHDOG_INTERVAL_SECONDS),
        CONF_MEDIA_MUSIC_PLAYERS: [pseudo_ent(x) for x in (cfg.get(CONF_MEDIA_MUSIC_PLAYERS) or [])][:50],
        CONF_MEDIA_TV_PLAYERS: [pseudo_ent(x) for x in (cfg.get(CONF_MEDIA_TV_PLAYERS) or [])][:50],
        CONF_DEVLOG_PUSH_ENABLED: cfg.get(CONF_DEVLOG_PUSH_ENABLED),
        CONF_DEVLOG_PUSH_INTERVAL_SECONDS: cfg.get(CONF_DEVLOG_PUSH_INTERVAL_SECONDS),
        # omit CONF_DEVLOG_PUSH_PATH (may leak filesystem layout)
        CONF_DEVLOG_PUSH_MAX_LINES: cfg.get(CONF_DEVLOG_PUSH_MAX_LINES),
        CONF_DEVLOG_PUSH_MAX_CHARS: cfg.get(CONF_DEVLOG_PUSH_MAX_CHARS),
        CONF_TOKEN: cfg.get(CONF_TOKEN),
    }

    # v0.1 dev_surface kernel (optional).
    dev_surface = None
    k = data.get("dev_surface") if isinstance(data, dict) else None
    if isinstance(k, dict):
        devlog = k.get("devlog")
        errors = k.get("errors")

        dev_surface = {
            "debug": bool(k.get("debug")),
            "debug_until": k.get("debug_until"),
            "last_success": k.get("last_success"),
            "devlogs_excerpt": devlog.tail(200) if hasattr(devlog, "tail") else [],
            "error_digest": errors.as_dict() if hasattr(errors, "as_dict") else None,
        }

    # Sanitize potentially free text coming from errors or remote API.
    if isinstance(core_status, dict):
        for k, v in list(core_status.items()):
            if isinstance(v, str):
                core_status[k] = _sanitize_text(v, stats=red_stats)
    if isinstance(core_devlogs, dict):
        for k, v in list(core_devlogs.items()):
            if isinstance(v, str):
                core_devlogs[k] = _sanitize_text(v, stats=red_stats)

    events_forwarder = None
    if isinstance(data, dict):
        # bounded, privacy-first counters only (no payload)
        events_forwarder = {
            "enabled": bool(data.get("events_forwarder_state")),
            "persistent_enabled": bool(data.get("events_forwarder_persistent_enabled")),
            "queue_len": int(data.get("events_forwarder_queue_len") or 0),
            "dropped_total": int(data.get("events_forwarder_dropped_total") or 0),
            "sent_total": int(data.get("events_forwarder_sent_total") or 0),
            "error_total": int(data.get("events_forwarder_error_total") or 0),
            "error_streak": int(data.get("events_forwarder_error_streak") or 0),
            "last": data.get("events_forwarder_last"),
            "last_success_at": data.get("events_forwarder_last_success_at"),
            "last_error_at": data.get("events_forwarder_last_error_at"),
            "health": data.get("events_forwarder_health"),
        }

    return {
        "contract": CONTRACT,
        "contract_version": CONTRACT_VERSION,
        "created_ts_ms": _now_ms(),
        "level": "standard",
        "window": {"from_ts_ms": None, "to_ts_ms": None},
        "focus": {"incident_id": None, "module": DOMAIN},
        "redaction": {
            "enabled": True,
            "mode": "strict",
            "pseudonymization": {"enabled": True, "method": "hmac-sha256", "salt_id": salt_id},
            "stats": dataclasses.asdict(red_stats),
        },
        "contributors": [
            {
                "module": DOMAIN,
                "version": entry.version,
                "paths": ["(home-assistant-diagnostics-json)"],
                "notes": "Integration diagnostics (sanitized, bounded)",
            }
        ],
        "entry": {
            "entry_id": _pseudonymize(salt=salt, prefix="entry", value=entry.entry_id),
            "title": _sanitize_text(str(entry.title), stats=red_stats),
        },
        "config": async_redact_data(cfg_public, TO_REDACT),
        "core": {
            "status": core_status,
            "devlogs": core_devlogs,
        },
        "media_context": media_state,
        "events_forwarder": events_forwarder,
        "dev_surface": dev_surface,
    }
