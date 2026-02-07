from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import CopilotBaseEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([CopilotVersionSensor(coordinator)], True)


class CopilotVersionSensor(CopilotBaseEntity, SensorEntity):
    _attr_name = "Version"
    _attr_unique_id = "version"
    _attr_icon = "mdi:tag"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.version
