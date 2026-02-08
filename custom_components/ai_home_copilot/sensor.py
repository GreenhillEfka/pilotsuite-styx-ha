from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import CopilotBaseEntity
from .media_entities import (
    MusicActiveCountSensor,
    MusicNowPlayingSensor,
    MusicPrimaryAreaSensor,
    TvActiveCountSensor,
    TvPrimaryAreaSensor,
    TvSourceSensor,
)
from .habitus_zones_entities import HabitusZonesCountSensor
from .habitus_zones_store import async_get_zones
from .habitus_zone_aggregates import build_zone_average_sensors
from .core_v1_entities import CoreApiV1StatusSensor
from .systemhealth_entities import SystemHealthEntityCountSensor, SystemHealthSqliteDbSizeSensor


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = [
        CopilotVersionSensor(coordinator),
        CoreApiV1StatusSensor(coordinator, entry),
        HabitusZonesCountSensor(coordinator, entry),
        SystemHealthEntityCountSensor(coordinator),
        SystemHealthSqliteDbSizeSensor(coordinator),
    ]

    # Events Forwarder quality sensors (v0.1 kernel)
    if isinstance(data, dict) and data.get("events_forwarder_state") is not None:
        entities.extend(
            [
                EventsForwarderQueueDepthSensor(coordinator, entry),
                EventsForwarderDroppedTotalSensor(coordinator, entry),
                EventsForwarderErrorStreakSensor(coordinator, entry),
            ]
        )

    media_coordinator = data.get("media_coordinator") if isinstance(data, dict) else None
    if media_coordinator is not None:
        entities.extend(
            [
                MusicNowPlayingSensor(media_coordinator),
                MusicPrimaryAreaSensor(media_coordinator),
                TvPrimaryAreaSensor(media_coordinator),
                TvSourceSensor(media_coordinator),
                MusicActiveCountSensor(media_coordinator),
                TvActiveCountSensor(media_coordinator),
            ]
        )

    # Add optional Habitus zone aggregate sensors (e.g., Temperatur Ø / Luftfeuchte Ø).
    try:
        zones = await async_get_zones(hass, entry.entry_id)
        for z in zones:
            entities.extend(
                build_zone_average_sensors(
                    hass=hass,
                    coordinator=coordinator,
                    zone_id=z.zone_id,
                    zone_name=z.name,
                    entities_by_role=z.entities,
                )
            )
    except Exception:  # noqa: BLE001
        # Best-effort: never break setup because of aggregates.
        pass

    async_add_entities(entities, True)


class CopilotVersionSensor(CopilotBaseEntity, SensorEntity):
    _attr_name = "Version"
    _attr_unique_id = "version"
    _attr_icon = "mdi:tag"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.version
