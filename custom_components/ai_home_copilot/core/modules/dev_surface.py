from __future__ import annotations

import asyncio
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import logging
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.event import async_call_later

from ...const import (
    DEBUG_LEVEL_FULL,
    DEBUG_LEVEL_LIGHT,
    DEBUG_LEVEL_OFF,
    DEBUG_LEVELS,
    DOMAIN,
)
from ..module import CopilotModule, ModuleContext
from ..error_helpers import format_error_context

_LOGGER = logging.getLogger(__name__)

# --- Minimal error code registry (v0.1) ---
# Keep stable keys; values are human hints shown in diagnostics.
ERROR_REGISTRY: dict[str, dict[str, str]] = {
    "auth_failed": {
        "title": "Authentication failed",
        "hint": "Check the configured token and restart the integration.",
    },
    "network": {
        "title": "Network error",
        "hint": "Check host/port reachability and DNS; then retry ping.",
    },
    "rate_limited": {
        "title": "Rate limited",
        "hint": "Retry later; reduce polling frequency if applicable.",
    },
    "parse_error": {
        "title": "Response parse error",
        "hint": "Capture diagnostics and attach to an issue (redacted).",
    },
    "unknown": {
        "title": "Unknown error",
        "hint": "Capture diagnostics; include steps to reproduce.",
    },
}

# --- Redaction helpers (best-effort, privacy-first) ---
_RE_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_RE_JWT = re.compile(r"(?<![A-Za-z0-9_-])(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})")
_RE_BEARER = re.compile(r"(?i)(bearer\s+)(\S+)")
_RE_URL_CREDS = re.compile(r"(?i)(https?://)([^\s:/]+):([^\s@/]+)@")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_value(val: Any, *, max_str: int = 2048) -> Any:
    """Best-effort redaction for strings; otherwise returns as-is.

    Keep small and safe; do not try to be perfect.
    """

    if isinstance(val, str):
        s = val
        s = _RE_URL_CREDS.sub(r"\1**REDACTED**:**REDACTED**@", s)
        s = _RE_BEARER.sub(r"\1**REDACTED**", s)
        s = _RE_JWT.sub("**REDACTED_JWT**", s)
        s = _RE_EMAIL.sub("**REDACTED_EMAIL**", s)
        if len(s) > max_str:
            s = s[: max_str - 50] + "...(truncated)..."
        return s

    if isinstance(val, dict):
        return {str(k): _sanitize_value(v, max_str=max_str) for k, v in list(val.items())[:100]}

    if isinstance(val, list):
        return [_sanitize_value(v, max_str=max_str) for v in val[:100]]

    return val


@dataclass
class DevLogEvent:
    ts: str
    level: str
    typ: str
    msg: str
    data: dict[str, Any]


class DevLogBuffer:
    def __init__(self, *, max_events: int = 800) -> None:
        self._dq: deque[DevLogEvent] = deque(maxlen=max_events)

    def add(self, *, level: str, typ: str, msg: str, data: dict[str, Any] | None = None) -> None:
        self._dq.append(
            DevLogEvent(
                ts=_now_iso(),
                level=str(level),
                typ=str(typ),
                msg=_sanitize_value(str(msg), max_str=512),
                data=_sanitize_value(data or {}, max_str=1024),
            )
        )

    def tail(self, n: int) -> list[dict[str, Any]]:
        n = max(0, min(int(n), len(self._dq)))
        return [e.__dict__ for e in list(self._dq)[-n:]]

    def __len__(self) -> int:
        return len(self._dq)


class ErrorDigest:
    def __init__(self, *, max_recent: int = 50) -> None:
        self._max_recent = max_recent
        self.last_error: dict[str, Any] | None = None
        self.counters: Counter[str] = Counter()
        self.recent: deque[dict[str, Any]] = deque(maxlen=max_recent)
        self._error_groups: dict[str, dict[str, Any]] = {}  # group_key -> {count, first_seen, last_seen, sample_error}

    def clear(self) -> None:
        self.last_error = None
        self.counters.clear()
        self.recent.clear()
        self._error_groups.clear()
        self._error_groups.clear()

    def record(self, *, error_key: str, message: str, where: str, hint: str | None = None) -> None:
        key = error_key if error_key in ERROR_REGISTRY else "unknown"
        rec = {
            "time": _now_iso(),
            "error_key": key,
            "message": _sanitize_value(message, max_str=512),
            "where": _sanitize_value(where, max_str=256),
            "hint": hint or ERROR_REGISTRY.get(key, {}).get("hint"),
        }
        self.last_error = rec
        self.counters[key] += 1
        self.recent.append(rec)

    def record_exception(self, error: Exception, operation: str, context: dict[str, Any] | None = None) -> None:
        """Record an exception with enhanced context and traceback info."""
        error_data = format_error_context(error, operation, context, include_traceback=True, max_frames=5)
        
        # Classify the exception type
        error_key = _classify_exception(error)
        
        # Create enhanced record with traceback summary
        rec = {
            "time": error_data["timestamp"],
            "error_key": error_key,
            "message": error_data["error_message"],
            "where": operation,
            "hint": ERROR_REGISTRY.get(error_key, {}).get("hint"),
            "error_type": error_data["error_type"],
            "context": error_data.get("context", {}),
            "traceback_summary": error_data.get("traceback_summary"),
        }
        
        # Track error grouping
        group_key = _get_error_group_key(error, operation)
        rec["group_key"] = group_key
        
        if group_key not in self._error_groups:
            self._error_groups[group_key] = {
                "count": 0,
                "first_seen": rec["time"],
                "last_seen": rec["time"],
                "sample_error": {
                    "error_key": error_key,
                    "message": rec["message"],
                    "where": rec["where"],
                },
            }
        
        self._error_groups[group_key]["count"] += 1
        self._error_groups[group_key]["last_seen"] = rec["time"]
        
        self.last_error = rec
        self.counters[error_key] += 1
        self.recent.append(rec)

    def get_error_groups(self, min_count: int = 2) -> list[dict[str, Any]]:
        """Return grouped errors with occurrence count >= min_count."""
        return [
            {
                "group_key": k,
                "count": v["count"],
                "first_seen": v["first_seen"],
                "last_seen": v["last_seen"],
                "sample_error": v["sample_error"],
            }
            for k, v in self._error_groups.items()
            if v["count"] >= min_count
        ]

    def as_dict(self) -> dict[str, Any]:
        # Keep stable output.
        return {
            "last_error": self.last_error,
            "counters": dict(self.counters),
            "recent": list(self.recent),
            "error_groups": self.get_error_groups(),
            "registry": ERROR_REGISTRY,
            "max_recent": self._max_recent,
        }


def _classify_exception(err: Exception) -> str:
    # Minimal mapping. Avoid importing aiohttp in this module.
    msg = str(err).lower()
    if "http 401" in msg or "http 403" in msg or "unauthorized" in msg:
        return "auth_failed"
    if "http 429" in msg or ("rate" in msg and "limit" in msg):
        return "rate_limited"
    if "timeout" in msg:
        return "network"
    if "json" in msg and "decode" in msg:
        return "parse_error"
    if "client error" in msg or "cannot connect" in msg or "name or service not known" in msg:
        return "network"
    return "unknown"


def _get_error_group_key(error: Exception, operation: str) -> str:
    """Create a stable group key for similar errors based on exception type + operation."""
    # Use exception class name + operation as group key
    exc_class = type(error).__name__
    return f"{exc_class}:{operation}"


def _entry_state(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    return hass.data.setdefault(DOMAIN, {}).setdefault(entry_id, {})


def _get_kernel(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    data = _entry_state(hass, entry_id)
    kernel = data.get("dev_surface")
    if isinstance(kernel, dict):
        return kernel

    kernel = {
        "devlog": DevLogBuffer(max_events=800),
        "errors": ErrorDigest(max_recent=50),
        "debug": False,
        "debug_until": None,
        "unsub_debug_timer": None,
        "last_success": None,
    }
    data["dev_surface"] = kernel
    return kernel


async def _async_ping(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    data = _entry_state(hass, entry.entry_id)
    coordinator = data.get("coordinator") if isinstance(data, dict) else None
    kernel = _get_kernel(hass, entry.entry_id)

    if coordinator is None:
        raise RuntimeError("No coordinator available")

    t0 = asyncio.get_running_loop().time()
    try:
        payload = await coordinator.api.async_get("/health")
        dt_ms = int((asyncio.get_running_loop().time() - t0) * 1000)
        kernel["last_success"] = _now_iso()
        kernel["devlog"].add(level="info", typ="ping", msg="Ping ok", data={"duration_ms": dt_ms})
        return {"ok": True, "duration_ms": dt_ms, "payload": _sanitize_value(payload)}
    except Exception as err:  # noqa: BLE001
        key = _classify_exception(err)
        kernel["errors"].record(error_key=key, message=str(err), where="ping")
        kernel["devlog"].add(level="error", typ="ping", msg="Ping failed", data={"error_key": key})
        raise


class DevSurfaceModule(CopilotModule):
    @property
    def name(self) -> str:
        return "dev_surface"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        hass = ctx.hass
        entry = ctx.entry
        kernel = _get_kernel(hass, entry.entry_id)
        kernel["devlog"].add(level="info", typ="init", msg="dev_surface module setup")

        # Register services once (global). They are entry-scoped by entry_id field.
        global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
        if global_data.get("dev_surface_services_registered"):
            return

        async def _svc_enable_debug(call: ServiceCall) -> None:
            entry_id = str(call.data.get("entry_id", ""))
            minutes = int(call.data.get("minutes", 30))
            k = _get_kernel(hass, entry_id)

            # Cancel existing timer.
            unsub = k.get("unsub_debug_timer")
            if callable(unsub):
                try:
                    unsub()
                except Exception:  # noqa: BLE001
                    pass

            k["debug"] = True

            # Auto-disable after timeout.
            def _disable_later(_now) -> None:
                kk = _get_kernel(hass, entry_id)
                kk["debug"] = False
                kk["debug_until"] = None
                kk["unsub_debug_timer"] = None
                kk["devlog"].add(level="info", typ="debug", msg="Debug auto-disabled")

            seconds = max(60, min(minutes * 60, 24 * 60 * 60))
            k["unsub_debug_timer"] = async_call_later(hass, seconds, _disable_later)
            k["debug_until"] = (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()
            k["devlog"].add(level="info", typ="debug", msg=f"Debug enabled for {minutes} min")

        async def _svc_disable_debug(call: ServiceCall) -> None:
            entry_id = str(call.data.get("entry_id", ""))
            k = _get_kernel(hass, entry_id)
            unsub = k.get("unsub_debug_timer")
            if callable(unsub):
                try:
                    unsub()
                except Exception:  # noqa: BLE001
                    pass
            k["unsub_debug_timer"] = None
            k["debug"] = False
            k["debug_until"] = None
            k["devlog"].add(level="info", typ="debug", msg="Debug disabled")

        async def _svc_clear_errors(call: ServiceCall) -> None:
            entry_id = str(call.data.get("entry_id", ""))
            k = _get_kernel(hass, entry_id)
            k["errors"].clear()
            k["devlog"].add(level="info", typ="errors", msg="Error digest cleared")

        async def _svc_set_debug_level(call: ServiceCall) -> None:
            entry_id = str(call.data.get("entry_id", ""))
            level = str(call.data.get("level", DEBUG_LEVEL_OFF))
            k = _get_kernel(hass, entry_id)

            if level == DEBUG_LEVEL_FULL:
                k["debug"] = True
            elif level == DEBUG_LEVEL_LIGHT:
                k["debug"] = True  # Light still enables debug, but filters in UI
            else:  # off
                k["debug"] = False

            k["debug_level"] = level
            k["devlog"].add(level="info", typ="debug_level", msg=f"Debug level set to {level}", data={"level": level})

        async def _svc_clear_all_logs(call: ServiceCall) -> None:
            """Clear all log buffers (devlog and errors)."""
            entry_id = str(call.data.get("entry_id", ""))
            k = _get_kernel(hass, entry_id)

            # Clear devlog buffer
            if "devlog" in k:
                k["devlog"]._dq.clear()

            # Clear error digest
            if "errors" in k:
                k["errors"].clear()

            k["devlog"].add(level="info", typ="logs", msg="All logs cleared")

        async def _svc_ping(call: ServiceCall) -> None:
            entry_id = str(call.data.get("entry_id", ""))
            ent = hass.config_entries.async_get_entry(entry_id)
            if ent is None:
                raise ValueError("Unknown entry_id")
            try:
                await _async_ping(hass, ent)
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Ping failed (entry_id=%s): %s", entry_id, err)

        hass.services.async_register(DOMAIN, "enable_debug_for", _svc_enable_debug)
        hass.services.async_register(DOMAIN, "disable_debug", _svc_disable_debug)
        hass.services.async_register(DOMAIN, "clear_error_digest", _svc_clear_errors)
        hass.services.async_register(DOMAIN, "set_debug_level", _svc_set_debug_level)
        hass.services.async_register(DOMAIN, "clear_all_logs", _svc_clear_all_logs)
        hass.services.async_register(DOMAIN, "ping", _svc_ping)

        global_data["dev_surface_services_registered"] = True

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        # Keep global services; entry-specific state is allowed to linger until HA restart.
        return True
