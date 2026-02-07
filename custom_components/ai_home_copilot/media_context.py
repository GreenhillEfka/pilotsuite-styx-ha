from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry, device_registry, entity_registry
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN


@dataclass(frozen=True, slots=True)
class MediaContextData:
    music_active: bool
    tv_active: bool
    music_primary_entity_id: str | None
    tv_primary_entity_id: str | None
    music_primary_area: str | None
    tv_primary_area: str | None
    music_now_playing: str | None
    tv_source: str | None
    music_active_count: int
    tv_active_count: int


def _parse_csv(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if not isinstance(value, str):
        return [str(value).strip()] if str(value).strip() else []
    parts = [p.strip() for p in value.replace("\n", ",").split(",")]
    return [p for p in parts if p]


def _area_name_for_entity(hass: HomeAssistant, entity_id: str) -> str | None:
    er = entity_registry.async_get(hass)
    dr = device_registry.async_get(hass)
    ar = area_registry.async_get(hass)

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


def _is_music_active_state(state: str | None) -> bool:
    # Conservative: only count actual playing.
    return state == "playing"


def _is_tv_active_state(state: str | None) -> bool:
    # Conservative but practical: treat anything other than clearly-off states as active.
    if not state:
        return False
    return state not in ("off", "standby", "unavailable", "unknown")


def _now_playing_from_attrs(attrs: dict[str, Any]) -> str | None:
    # Try to build a short, user-friendly string.
    artist = attrs.get("media_artist")
    title = attrs.get("media_title")
    if isinstance(artist, str) and isinstance(title, str) and artist and title:
        return f"{artist} – {title}"
    if isinstance(title, str) and title:
        return title
    return None


class MediaContextCoordinator(DataUpdateCoordinator[MediaContextData]):
    """Event-driven coordinator for media context signals."""

    def __init__(self, hass: HomeAssistant, *, music_players: list[str], tv_players: list[str]):
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=f"{DOMAIN}-media_context",
            update_interval=None,
        )
        self._music_players = music_players
        self._tv_players = tv_players
        self._unsub = None

    def set_players(self, *, music_players: list[str], tv_players: list[str]) -> None:
        self._music_players = music_players
        self._tv_players = tv_players

    async def async_start(self) -> None:
        if self._unsub is not None:
            return

        watched = sorted(set(self._music_players + self._tv_players))

        @callback
        def _on_change(event) -> None:
            # Only refresh if we watch this entity.
            entity_id = event.data.get("entity_id")
            if entity_id in watched:
                self.hass.async_create_task(self.async_refresh())

        if watched:
            self._unsub = async_track_state_change_event(self.hass, watched, _on_change)

        # Initial snapshot
        await self.async_refresh()

    async def async_stop(self) -> None:
        if callable(self._unsub):
            self._unsub()
        self._unsub = None

    async def _async_update_data(self) -> MediaContextData:
        music_active = False
        tv_active = False

        music_primary_entity_id = None
        tv_primary_entity_id = None

        music_now_playing = None
        tv_source = None

        music_active_count = 0
        tv_active_count = 0

        # MUSIC
        for entity_id in self._music_players:
            st = self.hass.states.get(entity_id)
            if not st:
                continue
            if _is_music_active_state(st.state):
                music_active = True
                music_active_count += 1
                if music_primary_entity_id is None:
                    music_primary_entity_id = entity_id
                    music_now_playing = _now_playing_from_attrs(dict(st.attributes))

        # TV/OTHER
        for entity_id in self._tv_players:
            st = self.hass.states.get(entity_id)
            if not st:
                continue
            if _is_tv_active_state(st.state):
                tv_active = True
                tv_active_count += 1
                if tv_primary_entity_id is None:
                    tv_primary_entity_id = entity_id
                    src = st.attributes.get("source")
                    if isinstance(src, str) and src:
                        tv_source = src

        music_primary_area = (
            _area_name_for_entity(self.hass, music_primary_entity_id)
            if music_primary_entity_id
            else None
        )
        tv_primary_area = (
            _area_name_for_entity(self.hass, tv_primary_entity_id) if tv_primary_entity_id else None
        )

        return MediaContextData(
            music_active=music_active,
            tv_active=tv_active,
            music_primary_entity_id=music_primary_entity_id,
            tv_primary_entity_id=tv_primary_entity_id,
            music_primary_area=music_primary_area,
            tv_primary_area=tv_primary_area,
            music_now_playing=music_now_playing,
            tv_source=tv_source,
            music_active_count=music_active_count,
            tv_active_count=tv_active_count,
        )
