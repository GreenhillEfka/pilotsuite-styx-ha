from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import CopilotBaseEntity
from .media_entities import MusicActiveBinarySensor, TvActiveBinarySensor


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = [CopilotOnlineBinarySensor(coordinator)]

    media_coordinator = data.get("media_coordinator") if isinstance(data, dict) else None
    if media_coordinator is not None:
        entities.extend(
            [
                MusicActiveBinarySensor(media_coordinator),
                TvActiveBinarySensor(media_coordinator),
            ]
        )

    async_add_entities(entities, True)


class CopilotOnlineBinarySensor(CopilotBaseEntity, BinarySensorEntity):
    _attr_name = "Online"
    _attr_unique_id = "online"
    _attr_icon = "mdi:robot"

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.ok
