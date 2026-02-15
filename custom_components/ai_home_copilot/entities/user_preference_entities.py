"""User Preference Entities — Sensors and Services for Multi-User Preference Learning.

v0.8.0 - MVP Implementation
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory

from ..const import DOMAIN

logger = logging.getLogger(__name__)


class ActiveUserSensor(SensorEntity):
    """Sensor showing the currently active user."""
    
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:account"
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the sensor."""
        self.hass = hass
        self._attr_unique_id = f"{DOMAIN}_active_user"
        self._attr_name = "Active User"
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}
    
    @property
    def native_value(self) -> Optional[str]:
        """Return the active user ID."""
        return self._attr_native_value
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra attributes."""
        return self._attr_extra_state_attributes
    
    async def async_update(self) -> None:
        """Update the sensor."""
        module = self.hass.data.get(DOMAIN, {}).get("user_preference_module")
        if module:
            active_user = module.get_active_user()
            self._attr_native_value = active_user or "none"
            
            if active_user:
                user_data = module.get_user_preference(active_user)
                if user_data:
                    self._attr_extra_state_attributes = {
                        "display_name": user_data.get("display_name", ""),
                        "active_zone": module.get_active_zone() or "",
                        "learning_enabled": module._learning_enabled,
                    }


class UserPreferencesSensor(SensorEntity):
    """Sensor showing user preferences summary."""
    
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:account-cog"
    
    def __init__(self, hass: HomeAssistant, user_id: str):
        """Initialize the sensor."""
        self.hass = hass
        self._user_id = user_id
        self._attr_unique_id = f"{DOMAIN}_user_preferences_{user_id.replace('.', '_')}"
        self._attr_name = f"User Preferences {user_id.split('.')[-1].title()}"
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}
    
    @property
    def native_value(self) -> Optional[str]:
        """Return the user's primary preference state."""
        return self._attr_native_value
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return user preferences as attributes."""
        return self._attr_extra_state_attributes
    
    async def async_update(self) -> None:
        """Update the sensor."""
        module = self.hass.data.get(DOMAIN, {}).get("user_preference_module")
        if module:
            user_data = module.get_user_preference(self._user_id)
            if user_data:
                prefs = user_data.get("preferences", {})
                patterns = user_data.get("learned_patterns", [])
                
                self._attr_native_value = "configured" if prefs else "default"
                
                self._attr_extra_state_attributes = {
                    "display_name": user_data.get("display_name", ""),
                    "preferences": prefs,
                    "learned_patterns_count": len(patterns),
                    "confirmed_patterns_count": sum(1 for p in patterns if p.get("confirmed")),
                    "created_at": user_data.get("created_at", ""),
                    "updated_at": user_data.get("updated_at", ""),
                }
            else:
                self._attr_native_value = "unknown"
        else:
            self._attr_native_value = "unavailable"


class LearningStatusSensor(SensorEntity):
    """Sensor showing the learning status."""
    
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:school"
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the sensor."""
        self.hass = hass
        self._attr_unique_id = f"{DOMAIN}_learning_status"
        self._attr_name = "Learning Status"
        self._attr_native_value = "idle"
        self._attr_extra_state_attributes = {}
    
    @property
    def native_value(self) -> str:
        """Return the learning status."""
        return self._attr_native_value
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return learning statistics."""
        return self._attr_extra_state_attributes
    
    async def async_update(self) -> None:
        """Update the sensor."""
        module = self.hass.data.get(DOMAIN, {}).get("user_preference_module")
        if module:
            self._attr_native_value = "active" if module._learning_enabled else "paused"
            
            summary = module.get_summary()
            users = module.get_all_users()
            
            total_patterns = 0
            confirmed_patterns = 0
            
            for user_data in users.values():
                patterns = user_data.get("learned_patterns", [])
                total_patterns += len(patterns)
                confirmed_patterns += sum(1 for p in patterns if p.get("confirmed"))
            
            self._attr_extra_state_attributes = {
                "tracked_users": summary.get("tracked_users", []),
                "active_user": summary.get("active_user"),
                "total_users": summary.get("total_users", 0),
                "total_patterns_learned": total_patterns,
                "confirmed_patterns": confirmed_patterns,
                "pending_patterns": total_patterns - confirmed_patterns,
            }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up user preference sensors."""
    entities = []
    
    # Always add active user sensor and learning status sensor
    entities.append(ActiveUserSensor(hass))
    entities.append(LearningStatusSensor(hass))
    
    # Get tracked users and add per-user sensors
    module = hass.data.get(DOMAIN, {}).get("user_preference_module")
    if module:
        config = module.get_config()
        tracked_users = config.get("tracked_person_entities", [])
        
        for user_id in tracked_users:
            entities.append(UserPreferencesSensor(hass, user_id))
    
    async_add_entities(entities, update_before_add=True)
    logger.info(f"Set up {len(entities)} user preference sensors")