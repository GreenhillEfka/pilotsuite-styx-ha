"""Debug mode sensor for HA Integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF

from .const import DOMAIN

DEBUG_MODE_ENTITY_ID = "sensor.ai_home_copilot_debug_mode_enabled"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up debug mode sensor."""
    async_add_entities([DebugModeSensor(hass)], update_before_add=True)


class DebugModeSensor(SensorEntity):
    """Debug mode sensor for AI Home CoPilot."""

    _attr_name = "AI Home CoPilot Debug Mode"
    _attr_unique_id = f"{DOMAIN}_debug_mode_sensor"
    _attr_icon = "mdi:bug"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "ai_home_copilot")},
            "name": "AI Home CoPilot",
            "manufacturer": "AI Home",
            "model": "Copilot Core",
        }

    @property
    def state(self) -> str:
        """Return the state."""
        debug_mode = self.hass.data.get(DOMAIN, {}).get("debug_mode", False)
        return STATE_ON if debug_mode else STATE_OFF

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        debug_mode = self.hass.data.get(DOMAIN, {}).get("debug_mode", False)
        return {"enabled": debug_mode}
