from __future__ import annotations

from typing import Any

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


def _redact_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    out = dict(cfg)
    if CONF_TOKEN in out:
        out[CONF_TOKEN] = "**REDACTED**" if out.get(CONF_TOKEN) else ""
    return out


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Keep this privacy-first. Do not include tokens. Keep payload small.

    Docs: https://developers.home-assistant.io/docs/core/diagnostics/
    """

    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator") if isinstance(data, dict) else None
    media_coordinator = data.get("media_coordinator") if isinstance(data, dict) else None

    cfg = entry.data | entry.options

    core_status = None
    core_devlogs = None

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

    media_state = None
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

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
        },
        "config": _redact_cfg(cfg_public),
        "core": {
            "status": core_status,
            "devlogs": core_devlogs,
        },
        "media_context": media_state,
    }
