"""Entities for Multi-User Preference Learning Module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .multi_user_preferences import MultiUserPreferenceModule

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Multi-User Preference Learning entities."""
    data = hass.data[DOMAIN].get(config_entry.entry_id, {})
    mupl_module = data.get("multi_user_preferences")
    
    if not mupl_module:
        _LOGGER.warning("Multi-User Preference Learning module not available")
        return
        
    entities = [
        ActiveUsersSensor(mupl_module),
    ]
    
    # Add user-specific mood sensors
    for user_id, user_data in mupl_module.get_all_users().items():
        entities.append(UserMoodSensor(mupl_module, user_id, user_data.name))
        
    async_add_entities(entities, True)
    _LOGGER.info("Added %d Multi-User Preference Learning entities", len(entities))


class ActiveUsersSensor(SensorEntity):
    """Sensor showing active (home) users."""
    
    _attr_name = "AI CoPilot Active Users"
    _attr_icon = "mdi:account-group"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_unique_id = f"{DOMAIN}_active_users"
    
    def __init__(self, module: MultiUserPreferenceModule) -> None:
        """Initialize the sensor."""
        self._module = module
        self._attr_extra_state_attributes = {}
        
    async def async_update(self) -> None:
        """Update the sensor."""
        active_users = await self._module.detect_active_users()
        
        # State: count of active users
        self._attr_native_value = len(active_users)
        
        # Attributes: list of user names
        user_names = [self._module.get_user_name(uid) for uid in active_users]
        self._attr_extra_state_attributes = {
            "users": active_users,
            "user_names": user_names,
            "total_known_users": len(self._module.get_all_users()),
        }


class UserMoodSensor(SensorEntity):
    """Sensor showing mood for a specific user."""
    
    _attr_icon = "mdi:robot-happy-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(
        self,
        module: MultiUserPreferenceModule,
        user_id: str,
        user_name: str,
    ) -> None:
        """Initialize the sensor."""
        self._module = module
        self._user_id = user_id
        self._user_name = user_name
        
        self._attr_name = f"AI CoPilot Mood - {user_name}"
        self._attr_unique_id = f"{DOMAIN}_mood_{user_id.replace('.', '_')}"
        self._attr_extra_state_attributes = {}
        
    async def async_update(self) -> None:
        """Update the sensor."""
        prefs = self._module.get_user_preferences(self._user_id)
        
        if not prefs:
            self._attr_native_value = "unknown"
            return
            
        mood = prefs.get("mood_weights", {})
        comfort = mood.get("comfort", 0.5)
        frugality = mood.get("frugality", 0.5)
        joy = mood.get("joy", 0.5)
        
        # Determine dominant mood
        if joy > 0.7:
            state = "joyful"
        elif comfort > 0.7:
            state = "comfortable"
        elif frugality > 0.7:
            state = "frugal"
        elif joy > 0.5:
            state = "content"
        elif comfort > 0.5:
            state = "relaxed"
        else:
            state = "neutral"
            
        self._attr_native_value = state
        self._attr_extra_state_attributes = {
            "comfort": round(comfort, 2),
            "frugality": round(frugality, 2),
            "joy": round(joy, 2),
            "user_id": self._user_id,
            "user_name": self._user_name,
        }


class AggregatedMoodSensor(SensorEntity):
    """Sensor showing aggregated mood across all active users."""
    
    _attr_name = "AI CoPilot Aggregated Mood"
    _attr_icon = "mdi:robot-happy"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_unique_id = f"{DOMAIN}_aggregated_mood"
    
    def __init__(self, module: MultiUserPreferenceModule) -> None:
        """Initialize the sensor."""
        self._module = module
        self._attr_extra_state_attributes = {}
        
    async def async_update(self) -> None:
        """Update the sensor."""
        mood = self._module.get_aggregated_mood()
        active_users = self._module.get_active_users()
        
        comfort = mood.get("comfort", 0.5)
        frugality = mood.get("frugality", 0.5)
        joy = mood.get("joy", 0.5)
        
        # Determine dominant mood
        if joy > 0.7:
            state = "joyful"
        elif comfort > 0.7:
            state = "comfortable"
        elif frugality > 0.7:
            state = "frugal"
        elif joy > 0.5:
            state = "content"
        elif comfort > 0.5:
            state = "relaxed"
        else:
            state = "neutral"
            
        self._attr_native_value = state
        self._attr_extra_state_attributes = {
            "comfort": round(comfort, 2),
            "frugality": round(frugality, 2),
            "joy": round(joy, 2),
            "active_users": len(active_users),
            "active_user_names": [
                self._module.get_user_name(uid) for uid in active_users
            ],
        }