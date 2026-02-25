"""Regional Context Sensor for Home Assistant (v5.15.0).

Exposes regional context as an HA sensor and auto-syncs
location from HA's zone.home entity for zero-config.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class RegionalContextSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing regional context and solar position."""

    _attr_name = "Regional Context"
    _attr_unique_id = "copilot_regional_context"
    _attr_icon = "mdi:map-marker-radius"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._data: dict[str, Any] = {}
        self._location_synced = False

    @property
    def native_value(self) -> str:
        loc = self._data.get("location", {})
        return f"{loc.get('country_code', '??')} — {loc.get('region', 'Unknown')}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        loc = self._data.get("location", {})
        solar = self._data.get("solar", {})
        defaults = self._data.get("defaults", {})
        return {
            "latitude": loc.get("latitude"),
            "longitude": loc.get("longitude"),
            "country": loc.get("country_code"),
            "region": loc.get("region"),
            "timezone": loc.get("timezone"),
            "sunrise": solar.get("sunrise"),
            "sunset": solar.get("sunset"),
            "day_length_hours": solar.get("day_length_hours"),
            "solar_elevation_deg": solar.get("elevation_deg"),
            "is_daylight": solar.get("is_daylight"),
            "grid_price_eur_kwh": defaults.get("grid_price_eur_kwh"),
            "feed_in_tariff_eur_kwh": defaults.get("feed_in_tariff_eur_kwh"),
            "weather_service": defaults.get("weather_service"),
            "language": defaults.get("language"),
            "location_synced": self._location_synced,
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self.hass)
        base = f"{self._core_base_url()}/api/v1/regional"
        headers = self._core_headers()

        # Auto-sync location from HA zone.home (zero-config)
        if not self._location_synced:
            await self._sync_location(session, base, headers)

        try:
            async with session.get(
                f"{base}/context", headers=headers, timeout=15
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        self._data = data
        except Exception as exc:
            _LOGGER.error("Failed to fetch regional context: %s", exc)

    async def _sync_location(self, session, base: str, headers: dict) -> None:
        """Push HA zone.home location to Core for auto-configuration."""
        try:
            zone_home = self.hass.states.get("zone.home")
            if zone_home:
                lat = zone_home.attributes.get("latitude")
                lon = zone_home.attributes.get("longitude")
                if lat and lon:
                    import json
                    tz = str(self.hass.config.time_zone) if hasattr(self.hass.config, "time_zone") else "Europe/Berlin"
                    elev = self.hass.config.elevation if hasattr(self.hass.config, "elevation") else 200
                    headers_post = {**headers, "Content-Type": "application/json"}
                    async with session.post(
                        f"{base}/location",
                        headers=headers_post,
                        data=json.dumps({
                            "latitude": lat,
                            "longitude": lon,
                            "elevation_m": elev,
                            "timezone": tz,
                        }),
                        timeout=10,
                    ) as resp:
                        if resp.status == 200:
                            self._location_synced = True
                            _LOGGER.info(
                                "Location synced from HA: %.4f, %.4f", lat, lon
                            )
        except Exception as exc:
            _LOGGER.debug("Could not sync location: %s", exc)
