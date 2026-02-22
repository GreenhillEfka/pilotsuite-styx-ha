"""Media Follow / Musikwolke Sensor for PilotSuite HA Integration (v6.7.0).

Displays active media playback with follow mode overview.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)

_MEDIA_ICONS = {
    "music": "mdi:music",
    "tv": "mdi:television",
    "radio": "mdi:radio",
    "podcast": "mdi:podcast",
    "video": "mdi:video",
}


class MediaFollowSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing media follow / Musikwolke overview."""

    _attr_name = "Media Follow"
    _attr_icon = "mdi:music-circle"
    _attr_unique_id = "pilotsuite_media_follow"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}

    async def _fetch(self) -> dict | None:
        import aiohttp
        try:
            url = f"{self._core_base_url()}/api/v1/hub/media"
            headers = self._core_headers()
            session = async_get_clientsession(self.hass)
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception:
            logger.debug("Failed to fetch media follow data")
        return None

    async def async_update(self) -> None:
        data = await self._fetch()
        if data and data.get("ok"):
            self._data = data

    @property
    def native_value(self) -> str:
        active = self._data.get("active_sessions", 0)
        if active == 0:
            return "Keine Wiedergabe"
        sessions = self._data.get("sessions", [])
        playing = [s for s in sessions if s.get("state") == "playing"]
        if len(playing) == 1:
            title = playing[0].get("title", "")
            artist = playing[0].get("artist", "")
            if artist:
                return f"{artist} — {title}"
            return title or "Wiedergabe"
        return f"{len(playing)} Wiedergaben"

    @property
    def icon(self) -> str:
        sessions = self._data.get("sessions", [])
        playing = [s for s in sessions if s.get("state") == "playing"]
        if not playing:
            return "mdi:music-off"
        if len(playing) == 1:
            mt = playing[0].get("media_type", "music")
            return _MEDIA_ICONS.get(mt, "mdi:music")
        return "mdi:music-circle-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "total_sources": self._data.get("total_sources", 0),
            "active_sessions": self._data.get("active_sessions", 0),
            "zones_with_playback": self._data.get("zones_with_playback", 0),
            "follow_enabled_zones": self._data.get("follow_enabled_zones", 0),
        }

        sessions = self._data.get("sessions", [])
        if sessions:
            attrs["sessions"] = [
                {
                    "zone": s.get("zone_id"),
                    "title": s.get("title"),
                    "artist": s.get("artist"),
                    "state": s.get("state"),
                    "media_type": s.get("media_type"),
                    "follow": s.get("follow_enabled"),
                }
                for s in sessions
            ]

        zones = self._data.get("zone_states", [])
        if zones:
            attrs["zone_states"] = [
                {
                    "zone": z.get("zone_id"),
                    "title": z.get("primary_title"),
                    "artist": z.get("primary_artist"),
                    "state": z.get("primary_state"),
                    "follow": z.get("follow_enabled"),
                }
                for z in zones
            ]

        transfers = self._data.get("recent_transfers", [])
        if transfers:
            attrs["recent_transfers"] = transfers[:5]

        return attrs
