"""N0 MediaContext v0.1 – Read-only media player state module.

Provides a lightweight, read-only snapshot of configured media players
(Spotify, Sonos, TV, etc.) for consumption by Mood, Habitus, and Entertain
modules. No actions, no volume control – pure signal.

Privacy-first: only entity_id, state, media_type, media_title, area are exposed.
No album art URLs, no playback positions, no user account info.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import area_registry, device_registry, entity_registry
from homeassistant.helpers.event import async_track_state_change_event

from ...const import (
    CONF_MEDIA_MUSIC_PLAYERS,
    CONF_MEDIA_TV_PLAYERS,
    DEFAULT_MEDIA_MUSIC_PLAYERS,
    DEFAULT_MEDIA_TV_PLAYERS,
    DOMAIN,
)
from ..module import ModuleContext

_LOGGER = logging.getLogger(__name__)

# States that indicate active playback
_MUSIC_ACTIVE_STATES = {"playing"}
_TV_ACTIVE_STATES = {"on", "idle", "playing", "paused"}


def _parse_csv(value: Any) -> list[str]:
    """Parse comma-separated string or list into list[str]."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if not isinstance(value, str):
        return [str(value).strip()] if str(value).strip() else []
    parts = [p.strip() for p in value.replace("\n", ",").split(",")]
    return [p for p in parts if p]


@dataclass(slots=True)
class MediaPlayerSnapshot:
    """Read-only snapshot of a single media player."""

    entity_id: str
    role: str  # "music" or "tv"
    state: str  # HA state (playing, paused, idle, off, unavailable)
    is_active: bool
    media_content_type: str | None = None
    media_title: str | None = None
    media_artist: str | None = None
    app_name: str | None = None
    source: str | None = None
    area_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Privacy-safe dict representation."""
        d: dict[str, Any] = {
            "entity_id": self.entity_id,
            "role": self.role,
            "state": self.state,
            "is_active": self.is_active,
        }
        if self.media_content_type:
            d["media_content_type"] = self.media_content_type
        if self.media_title:
            d["media_title"] = self.media_title
        if self.media_artist:
            d["media_artist"] = self.media_artist
        if self.app_name:
            d["app_name"] = self.app_name
        if self.source:
            d["source"] = self.source
        if self.area_name:
            d["area_name"] = self.area_name
        return d


@dataclass(slots=True)
class MediaContextSnapshot:
    """Aggregated read-only snapshot of all configured media players."""

    timestamp: str  # ISO 8601
    music_active: bool = False
    tv_active: bool = False
    music_active_count: int = 0
    tv_active_count: int = 0
    primary_music_entity: str | None = None
    primary_tv_entity: str | None = None
    primary_music_area: str | None = None
    primary_tv_area: str | None = None
    primary_music_title: str | None = None
    players: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "music_active": self.music_active,
            "tv_active": self.tv_active,
            "music_active_count": self.music_active_count,
            "tv_active_count": self.tv_active_count,
            "primary_music_entity": self.primary_music_entity,
            "primary_tv_entity": self.primary_tv_entity,
            "primary_music_area": self.primary_music_area,
            "primary_tv_area": self.primary_tv_area,
            "primary_music_title": self.primary_music_title,
            "players": self.players,
        }


class MediaContextModule:
    """Read-only media context provider for other CoPilot modules.

    Listens to state changes of configured media players and maintains
    a current snapshot accessible via hass.data or the provided API.
    """

    name = "media_zones"

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._entry: ConfigEntry | None = None
        self._music_entities: list[str] = []
        self._tv_entities: list[str] = []
        self._unsub_listeners: list[CALLBACK_TYPE] = []
        self._snapshot: MediaContextSnapshot = MediaContextSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    @property
    def snapshot(self) -> MediaContextSnapshot:
        """Current media context snapshot (read-only)."""
        return self._snapshot

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up media context tracking."""
        self._hass = ctx.hass
        self._entry = ctx.entry

        data = {**ctx.entry.data, **ctx.entry.options}
        self._music_entities = _parse_csv(
            data.get(CONF_MEDIA_MUSIC_PLAYERS, DEFAULT_MEDIA_MUSIC_PLAYERS)
        )
        self._tv_entities = _parse_csv(
            data.get(CONF_MEDIA_TV_PLAYERS, DEFAULT_MEDIA_TV_PLAYERS)
        )

        all_entities = self._music_entities + self._tv_entities
        if not all_entities:
            _LOGGER.info(
                "MediaContext: no media players configured — module idle. "
                "Configure media_music_players / media_tv_players in Options."
            )
            return

        _LOGGER.info(
            "MediaContext v0.1: tracking %d music + %d TV players",
            len(self._music_entities),
            len(self._tv_entities),
        )

        # Track state changes
        unsub = async_track_state_change_event(
            ctx.hass, all_entities, self._handle_state_change
        )
        self._unsub_listeners.append(unsub)

        # Initial snapshot
        self._refresh_snapshot()

        # Store reference for other modules
        domain_data = ctx.hass.data.setdefault(DOMAIN, {})
        entry_data = domain_data.setdefault(ctx.entry.entry_id, {})
        entry_data["media_zones_module"] = self

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload media context tracking."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

        domain_data = ctx.hass.data.get(DOMAIN, {})
        entry_data = domain_data.get(ctx.entry.entry_id, {})
        entry_data.pop("media_zones_module", None)

        _LOGGER.debug("MediaContext: unloaded")
        return True

    @callback
    def _handle_state_change(self, event: Event) -> None:
        """React to media player state changes."""
        self._refresh_snapshot()

    def _refresh_snapshot(self) -> None:
        """Rebuild the current media context snapshot from HA states."""
        if not self._hass:
            return

        players: list[MediaPlayerSnapshot] = []

        for entity_id in self._music_entities:
            snap = self._build_player_snapshot(entity_id, "music")
            if snap:
                players.append(snap)

        for entity_id in self._tv_entities:
            snap = self._build_player_snapshot(entity_id, "tv")
            if snap:
                players.append(snap)

        active_music = [p for p in players if p.role == "music" and p.is_active]
        active_tv = [p for p in players if p.role == "tv" and p.is_active]

        primary_music = active_music[0] if active_music else None
        primary_tv = active_tv[0] if active_tv else None

        now_playing = None
        if primary_music:
            parts = []
            if primary_music.media_artist:
                parts.append(primary_music.media_artist)
            if primary_music.media_title:
                parts.append(primary_music.media_title)
            now_playing = " – ".join(parts) if parts else None

        self._snapshot = MediaContextSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            music_active=bool(active_music),
            tv_active=bool(active_tv),
            music_active_count=len(active_music),
            tv_active_count=len(active_tv),
            primary_music_entity=primary_music.entity_id if primary_music else None,
            primary_tv_entity=primary_tv.entity_id if primary_tv else None,
            primary_music_area=primary_music.area_name if primary_music else None,
            primary_tv_area=primary_tv.area_name if primary_tv else None,
            primary_music_title=now_playing,
            players=[p.to_dict() for p in players],
        )

    def _build_player_snapshot(
        self, entity_id: str, role: str
    ) -> MediaPlayerSnapshot | None:
        """Build a snapshot for a single media player entity."""
        if not self._hass:
            return None

        state_obj = self._hass.states.get(entity_id)
        if state_obj is None:
            return MediaPlayerSnapshot(
                entity_id=entity_id,
                role=role,
                state="unavailable",
                is_active=False,
            )

        state_val = state_obj.state or "unknown"
        attrs = state_obj.attributes or {}

        if role == "music":
            is_active = state_val in _MUSIC_ACTIVE_STATES
        else:
            is_active = state_val in _TV_ACTIVE_STATES

        area = self._resolve_area(entity_id)

        return MediaPlayerSnapshot(
            entity_id=entity_id,
            role=role,
            state=state_val,
            is_active=is_active,
            media_content_type=attrs.get("media_content_type"),
            media_title=attrs.get("media_title"),
            media_artist=attrs.get("media_artist"),
            app_name=attrs.get("app_name"),
            source=attrs.get("source"),
            area_name=area,
        )

    def _resolve_area(self, entity_id: str) -> str | None:
        """Resolve area name for a media player entity."""
        if not self._hass:
            return None

        try:
            er = entity_registry.async_get(self._hass)
            dr = device_registry.async_get(self._hass)
            ar = area_registry.async_get(self._hass)

            ent = er.async_get(entity_id)
            if not ent:
                return None

            area_id = ent.area_id
            if not area_id and ent.device_id:
                dev = dr.async_get(ent.device_id)
                area_id = dev.area_id if dev else None

            if not area_id:
                return None

            area = ar.async_get_area(area_id)
            return area.name if area else None
        except Exception:  # noqa: BLE001
            return None
