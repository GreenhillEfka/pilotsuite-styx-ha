from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DEVLOG_PUSH_ENABLED,
    CONF_DEVLOG_PUSH_INTERVAL_SECONDS,
    CONF_DEVLOG_PUSH_MAX_CHARS,
    CONF_DEVLOG_PUSH_MAX_LINES,
    CONF_DEVLOG_PUSH_PATH,
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

    # Only include a curated subset of config.
    cfg_public = {
        CONF_HOST: cfg.get(CONF_HOST),
        CONF_PORT: cfg.get(CONF_PORT),
        CONF_WATCHDOG_ENABLED: cfg.get(CONF_WATCHDOG_ENABLED),
        CONF_WATCHDOG_INTERVAL_SECONDS: cfg.get(CONF_WATCHDOG_INTERVAL_SECONDS),
        CONF_MEDIA_MUSIC_PLAYERS: cfg.get(CONF_MEDIA_MUSIC_PLAYERS),
        CONF_MEDIA_TV_PLAYERS: cfg.get(CONF_MEDIA_TV_PLAYERS),
        CONF_DEVLOG_PUSH_ENABLED: cfg.get(CONF_DEVLOG_PUSH_ENABLED),
        CONF_DEVLOG_PUSH_INTERVAL_SECONDS: cfg.get(CONF_DEVLOG_PUSH_INTERVAL_SECONDS),
        CONF_DEVLOG_PUSH_PATH: cfg.get(CONF_DEVLOG_PUSH_PATH),
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

    return {
        "privacy": {
            "redaction": "best_effort",
            "notes": [
                "Tokens/credentials are redacted by key and by best-effort pattern matching.",
                "DevLogs are bounded (ring buffer) and may be truncated.",
            ],
        },
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
        },
        "config": async_redact_data(cfg_public, TO_REDACT),
        "core": {
            "status": core_status,
            "devlogs": core_devlogs,
        },
        "media_context": media_state,
        "dev_surface": dev_surface,
    }
