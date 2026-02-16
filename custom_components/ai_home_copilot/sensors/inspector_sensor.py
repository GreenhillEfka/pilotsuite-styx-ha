"""Inspector Sensor - Shows AI CoPilot internal state"""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CopilotDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up inspector sensor."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    
    entities = [
        InspectorSensor(coordinator, "zones", "Habitus Zones", "mdi:floor-plan"),
        InspectorSensor(coordinator, "tags", "Active Tags", "mdi:tag-multiple"),
        InspectorSensor(coordinator, "character", "Character Profile", "mdi:account-cog"),
        InspectorSensor(coordinator, "mood", "Current Mood", "mdi:emoticon"),
    ]
    
    async_add_entities(entities)


class InspectorSensor(SensorEntity):
    """Inspector sensor showing CoPilot state."""
    
    def __init__(self, coordinator, sensor_type: str, name: str, icon: str):
        self._coordinator = coordinator
        self._sensor_type = sensor_type
        self._attr_name = f"AI CoPilot {name}"
        self._attr_unique_id = f"ai_copilot_inspector_{sensor_type}"
        self._attr_icon = icon
        self._attr_should_poll = False
    
    @property
    def state(self):
        """Return current state."""
        if not self._coordinator.data:
            return "unknown"
        
        data = self._coordinator.data
        
        if self._sensor_type == "zones":
            zones = data.get("zones", {})
            return len(zones.get("zones", []))
        
        elif self._sensor_type == "tags":
            tags = data.get("tags", {})
            return len(tags.get("tags", []))
        
        elif self._sensor_type == "character":
            return data.get("character", {}).get("preset", "not set")
        
        elif self._sensor_type == "mood":
            return data.get("mood", {}).get("current", "unknown")
        
        return "unknown"
    
    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        if not self._coordinator.data:
            return {}
        
        data = self._coordinator.data
        
        if self._sensor_type == "zones":
            return {"zones": data.get("zones", {})}
        elif self._sensor_type == "tags":
            return {"tags": data.get("tags", {})}
        elif self._sensor_type == "character":
            return {"character": data.get("character", {})}
        elif self._sensor_type == "mood":
            return {"mood": data.get("mood", {})}
        
        return {}
