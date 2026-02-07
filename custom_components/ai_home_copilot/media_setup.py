from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_MEDIA_MUSIC_PLAYERS,
    CONF_MEDIA_TV_PLAYERS,
    DEFAULT_MEDIA_MUSIC_PLAYERS,
    DEFAULT_MEDIA_TV_PLAYERS,
    DOMAIN,
)
from .media_context import MediaContextCoordinator, _parse_csv


async def async_setup_media_context(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up the MediaContext coordinator (read-only signals)."""

    cfg = entry.data | entry.options
    music_players = _parse_csv(cfg.get(CONF_MEDIA_MUSIC_PLAYERS, DEFAULT_MEDIA_MUSIC_PLAYERS))
    tv_players = _parse_csv(cfg.get(CONF_MEDIA_TV_PLAYERS, DEFAULT_MEDIA_TV_PLAYERS))

    coordinator = MediaContextCoordinator(
        hass,
        music_players=music_players,
        tv_players=tv_players,
    )

    await coordinator.async_start()

    data = hass.data[DOMAIN].get(entry.entry_id)
    if isinstance(data, dict):
        data["media_coordinator"] = coordinator


async def async_unload_media_context(hass: HomeAssistant, entry: ConfigEntry) -> None:
    data = hass.data[DOMAIN].get(entry.entry_id)
    coordinator = data.get("media_coordinator") if isinstance(data, dict) else None
    if coordinator is not None:
        try:
            await coordinator.async_stop()
        except Exception:  # noqa: BLE001
            pass
        if isinstance(data, dict):
            data.pop("media_coordinator", None)
