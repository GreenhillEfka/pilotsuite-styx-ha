"""User Preference Services — Service handlers for Multi-User Preference Learning.

v0.8.0 - MVP Implementation
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from ..const import DOMAIN

logger = logging.getLogger(__name__)


SERVICE_SET_PREFERENCE = "set_user_preference"
SERVICE_LEARN_PATTERN = "learn_pattern"
SERVICE_CONFIRM_PATTERN = "confirm_pattern"
SERVICE_FORGET_PATTERN = "forget_pattern"
SERVICE_SET_LEARNING = "set_learning_enabled"
SERVICE_TRACK_USERS = "track_users"


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up user preference services."""
    
    async def handle_set_preference(call: ServiceCall) -> Dict[str, Any]:
        """Handle set_user_preference service call."""
        user_id = call.data.get("user_id")
        preference_key = call.data.get("preference_key")
        preference_value = call.data.get("preference_value")
        
        if not all([user_id, preference_key, preference_value is not None]):
            return {"success": False, "error": "Missing required fields: user_id, preference_key, preference_value"}
        
        module = hass.data.get(DOMAIN, {}).get("user_preference_module")
        if not module:
            return {"success": False, "error": "User preference module not loaded"}
        
        await module.set_preference(user_id, preference_key, preference_value)
        
        return {
            "success": True,
            "user_id": user_id,
            "preference_key": preference_key,
            "preference_value": preference_value,
        }
    
    async def handle_learn_pattern(call: ServiceCall) -> Dict[str, Any]:
        """Handle learn_pattern service call."""
        user_id = call.data.get("user_id")
        trigger = call.data.get("trigger")
        action = call.data.get("action")
        context = call.data.get("context", {})
        
        if not all([user_id, trigger, action]):
            return {"success": False, "error": "Missing required fields: user_id, trigger, action"}
        
        module = hass.data.get(DOMAIN, {}).get("user_preference_module")
        if not module:
            return {"success": False, "error": "User preference module not loaded"}
        
        pattern_id = await module.learn_pattern(user_id, trigger, action, context)
        
        return {
            "success": True,
            "user_id": user_id,
            "pattern_id": pattern_id,
            "trigger": trigger,
            "action": action,
        }
    
    async def handle_confirm_pattern(call: ServiceCall) -> Dict[str, Any]:
        """Handle confirm_pattern service call."""
        user_id = call.data.get("user_id")
        pattern_id = call.data.get("pattern_id")
        
        if not all([user_id, pattern_id]):
            return {"success": False, "error": "Missing required fields: user_id, pattern_id"}
        
        module = hass.data.get(DOMAIN, {}).get("user_preference_module")
        if not module:
            return {"success": False, "error": "User preference module not loaded"}
        
        success = await module.confirm_pattern(user_id, pattern_id)
        
        return {
            "success": success,
            "user_id": user_id,
            "pattern_id": pattern_id,
        }
    
    async def handle_forget_pattern(call: ServiceCall) -> Dict[str, Any]:
        """Handle forget_pattern service call."""
        user_id = call.data.get("user_id")
        pattern_id = call.data.get("pattern_id")
        
        if not all([user_id, pattern_id]):
            return {"success": False, "error": "Missing required fields: user_id, pattern_id"}
        
        module = hass.data.get(DOMAIN, {}).get("user_preference_module")
        if not module:
            return {"success": False, "error": "User preference module not loaded"}
        
        success = await module.forget_pattern(user_id, pattern_id)
        
        return {
            "success": success,
            "user_id": user_id,
            "pattern_id": pattern_id,
        }
    
    async def handle_set_learning(call: ServiceCall) -> Dict[str, Any]:
        """Handle set_learning_enabled service call."""
        enabled = call.data.get("enabled", True)
        
        module = hass.data.get(DOMAIN, {}).get("user_preference_module")
        if not module:
            return {"success": False, "error": "User preference module not loaded"}
        
        module.set_learning_enabled(enabled)
        
        return {
            "success": True,
            "learning_enabled": enabled,
        }
    
    async def handle_track_users(call: ServiceCall) -> Dict[str, Any]:
        """Handle track_users service call."""
        person_entities = call.data.get("person_entities", [])
        primary_user = call.data.get("primary_user")
        
        module = hass.data.get(DOMAIN, {}).get("user_preference_module")
        if not module:
            return {"success": False, "error": "User preference module not loaded"}
        
        await module.set_tracked_users(person_entities, primary_user)
        
        return {
            "success": True,
            "tracked_users": person_entities,
            "primary_user": primary_user,
        }
    
    # Register services
    hass.services.async_register(DOMAIN, SERVICE_SET_PREFERENCE, handle_set_preference)
    hass.services.async_register(DOMAIN, SERVICE_LEARN_PATTERN, handle_learn_pattern)
    hass.services.async_register(DOMAIN, SERVICE_CONFIRM_PATTERN, handle_confirm_pattern)
    hass.services.async_register(DOMAIN, SERVICE_FORGET_PATTERN, handle_forget_pattern)
    hass.services.async_register(DOMAIN, SERVICE_SET_LEARNING, handle_set_learning)
    hass.services.async_register(DOMAIN, SERVICE_TRACK_USERS, handle_track_users)
    
    logger.info(f"User preference services registered: {SERVICE_SET_PREFERENCE}, {SERVICE_LEARN_PATTERN}, {SERVICE_CONFIRM_PATTERN}, {SERVICE_FORGET_PATTERN}, {SERVICE_SET_LEARNING}, {SERVICE_TRACK_USERS}")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload user preference services."""
    hass.services.async_remove(DOMAIN, SERVICE_SET_PREFERENCE)
    hass.services.async_remove(DOMAIN, SERVICE_LEARN_PATTERN)
    hass.services.async_remove(DOMAIN, SERVICE_CONFIRM_PATTERN)
    hass.services.async_remove(DOMAIN, SERVICE_FORGET_PATTERN)
    hass.services.async_remove(DOMAIN, SERVICE_SET_LEARNING)
    hass.services.async_remove(DOMAIN, SERVICE_TRACK_USERS)
    
    logger.info("User preference services unloaded")