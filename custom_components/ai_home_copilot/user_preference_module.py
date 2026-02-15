"""User Preference Module v0.1 - Multi-user preference learning for AI Home CoPilot.

Implements user recognition via person.* entities and preference storage.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, Event, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "ai_home_copilot_user_preferences"
STORAGE_VERSION = 1

# Default preferences
DEFAULT_PREFERENCES = {
    "light_brightness_default": 0.7,
    "light_color_temp_default": "warm",
    "music_volume_default": 0.5,
    "preferred_zones": [],
    "sleep_time": "23:00",
    "wake_time": "07:00",
    "temperature_comfort": 21.5,
}

SERVICE_SET_PREFERENCE = "set_user_preference"
SERVICE_LEARN_PATTERN = "learn_pattern"
SERVICE_FORGET_PATTERN = "forget_pattern"
SERVICE_RESET_PREFERENCES = "reset_user_preferences"

# Schemas
SET_PREFERENCE_SCHEMA = vol.Schema({
    vol.Required("user_id"): str,
    vol.Required("preference_key"): str,
    vol.Required("preference_value"): vol.Any(str, int, float, bool, list, dict),
})

LEARN_PATTERN_SCHEMA = vol.Schema({
    vol.Required("user_id"): str,
    vol.Required("trigger"): str,
    vol.Required("action"): str,
    vol.Optional("confidence", default=0.5): vol.Coerce(float),
    vol.Optional("zone"): str,
})

FORGET_PATTERN_SCHEMA = vol.Schema({
    vol.Required("user_id"): str,
    vol.Required("pattern_id"): str,
})

RESET_PREFERENCES_SCHEMA = vol.Schema({
    vol.Required("user_id"): str,
})


class UserPreferenceModule:
    """User Preference Module for multi-user preference learning."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the user preference module."""
        self.hass = hass
        self.entry = entry
        self._store = Store[Dict[str, Any]](hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: Dict[str, Any] = {}
        self._tracked_users: Set[str] = set()
        self._event_unsubs: List = []
        self._active_users: Dict[str, str] = {}  # zone -> user_id
        self._learning_mode: str = "passive"  # active, passive, off
        self._primary_user: Optional[str] = None
        self._initialized = False

    @property
    def name(self) -> str:
        """Return module name."""
        return "user_preference_module"

    async def async_setup(self) -> None:
        """Set up the user preference module."""
        # Load stored data
        self._data = await self._store.async_load() or {"users": {}}

        # Get config
        config = self.entry.options or self.entry.data
        self._learning_mode = config.get("user_learning_mode", "passive")
        self._primary_user = config.get("primary_user")
        tracked_users = config.get("tracked_users", [])

        # Track user entities
        if tracked_users:
            await self._setup_user_tracking(tracked_users)

        # Register services
        await self._register_services()

        self._initialized = True
        _LOGGER.info(
            "User preference module initialized (mode=%s, users=%s)",
            self._learning_mode,
            tracked_users,
        )

    async def async_unload(self) -> None:
        """Unload the user preference module."""
        # Cancel event tracking
        for unsub in self._event_unsubs:
            unsub()
        self._event_unsubs.clear()

        # Unregister services
        for service_name in [
            SERVICE_SET_PREFERENCE,
            SERVICE_LEARN_PATTERN,
            SERVICE_FORGET_PATTERN,
            SERVICE_RESET_PREFERENCES,
        ]:
            if self.hass.services.has_service(DOMAIN, service_name):
                self.hass.services.async_remove(DOMAIN, service_name)

        _LOGGER.info("User preference module unloaded")

    async def _setup_user_tracking(self, user_entities: List[str]) -> None:
        """Set up tracking for user entities."""
        self._tracked_users = set(user_entities)

        @callback
        def _handle_user_state_change(event: Event) -> None:
            """Handle user state change events."""
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")

            if not new_state:
                return

            user_id = entity_id
            zone = new_state.attributes.get("zone")
            state = new_state.state

            # Update active user tracking
            if zone and state == "home":
                self._active_users[zone] = user_id
            elif zone and user_id in self._active_users.values():
                # User left zone
                for z, uid in list(self._active_users.items()):
                    if uid == user_id:
                        del self._active_users[z]

            _LOGGER.debug(
                "User state change: %s -> %s (zone=%s)",
                user_id,
                state,
                zone,
            )

            # Trigger preference learning if enabled
            if self._learning_mode == "active":
                asyncio.create_task(self._learn_from_context(user_id))

        # Track state changes
        unsub = async_track_state_change_event(
            self.hass, list(self._tracked_users), _handle_user_state_change
        )
        self._event_unsubs.append(unsub)

    async def _register_services(self) -> None:
        """Register user preference services."""

        async def _handle_set_preference(call: ServiceCall) -> None:
            """Handle set_user_preference service call."""
            user_id = call.data["user_id"]
            key = call.data["preference_key"]
            value = call.data["preference_value"]

            await self.set_preference(user_id, key, value)
            _LOGGER.info("Set preference %s = %s for user %s", key, value, user_id)

        async def _handle_learn_pattern(call: ServiceCall) -> None:
            """Handle learn_pattern service call."""
            user_id = call.data["user_id"]
            trigger = call.data["trigger"]
            action = call.data["action"]
            confidence = call.data.get("confidence", 0.5)
            zone = call.data.get("zone")

            pattern_id = await self.learn_pattern(user_id, trigger, action, confidence, zone)
            _LOGGER.info("Learned pattern %s for user %s", pattern_id, user_id)

        async def _handle_forget_pattern(call: ServiceCall) -> None:
            """Handle forget_pattern service call."""
            user_id = call.data["user_id"]
            pattern_id = call.data["pattern_id"]

            await self.forget_pattern(user_id, pattern_id)
            _LOGGER.info("Forgot pattern %s for user %s", pattern_id, user_id)

        async def _handle_reset_preferences(call: ServiceCall) -> None:
            """Handle reset_user_preferences service call."""
            user_id = call.data["user_id"]

            await self.reset_preferences(user_id)
            _LOGGER.info("Reset preferences for user %s", user_id)

        # Register services (idempotent)
        if not self.hass.services.has_service(DOMAIN, SERVICE_SET_PREFERENCE):
            self.hass.services.async_register(
                DOMAIN, SERVICE_SET_PREFERENCE, _handle_set_preference, schema=SET_PREFERENCE_SCHEMA
            )

        if not self.hass.services.has_service(DOMAIN, SERVICE_LEARN_PATTERN):
            self.hass.services.async_register(
                DOMAIN, SERVICE_LEARN_PATTERN, _handle_learn_pattern, schema=LEARN_PATTERN_SCHEMA
            )

        if not self.hass.services.has_service(DOMAIN, SERVICE_FORGET_PATTERN):
            self.hass.services.async_register(
                DOMAIN, SERVICE_FORGET_PATTERN, _handle_forget_pattern, schema=FORGET_PATTERN_SCHEMA
            )

        if not self.hass.services.has_service(DOMAIN, SERVICE_RESET_PREFERENCES):
            self.hass.services.async_register(
                DOMAIN, SERVICE_RESET_PREFERENCES, _handle_reset_preferences, schema=RESET_PREFERENCES_SCHEMA
            )

    # --- Public API ---

    async def set_preference(self, user_id: str, key: str, value: Any) -> None:
        """Set a preference for a user."""
        if user_id not in self._data["users"]:
            await self._ensure_user(user_id)

        self._data["users"][user_id]["preferences"][key] = value
        self._data["users"][user_id]["updated_at"] = dt_util.utcnow().isoformat()

        await self._store.async_save(self._data)

    async def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get a preference for a user."""
        user_data = self._data.get("users", {}).get(user_id, {})
        preferences = user_data.get("preferences", DEFAULT_PREFERENCES)
        return preferences.get(key, default)

    async def get_all_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get all preferences for a user."""
        user_data = self._data.get("users", {}).get(user_id, {})
        return user_data.get("preferences", DEFAULT_PREFERENCES.copy())

    async def learn_pattern(
        self,
        user_id: str,
        trigger: str,
        action: str,
        confidence: float = 0.5,
        zone: Optional[str] = None,
    ) -> str:
        """Learn a pattern for a user."""
        if user_id not in self._data["users"]:
            await self._ensure_user(user_id)

        pattern_id = f"{trigger}_{action}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        pattern = {
            "id": pattern_id,
            "trigger": trigger,
            "action": action,
            "confidence": confidence,
            "zone": zone,
            "learned_at": dt_util.utcnow().isoformat(),
            "confirmed": False,
            "confirmation_count": 0,
        }

        self._data["users"][user_id]["learned_patterns"].append(pattern)
        await self._store.async_save(self._data)

        return pattern_id

    async def confirm_pattern(self, user_id: str, pattern_id: str) -> None:
        """Confirm a learned pattern."""
        patterns = self._data.get("users", {}).get(user_id, {}).get("learned_patterns", [])

        for pattern in patterns:
            if pattern["id"] == pattern_id:
                pattern["confirmed"] = True
                pattern["confirmation_count"] += 1
                pattern["confirmed_at"] = dt_util.utcnow().isoformat()
                break

        await self._store.async_save(self._data)

    async def forget_pattern(self, user_id: str, pattern_id: str) -> None:
        """Forget a learned pattern."""
        patterns = self._data.get("users", {}).get(user_id, {}).get("learned_patterns", [])

        self._data["users"][user_id]["learned_patterns"] = [
            p for p in patterns if p["id"] != pattern_id
        ]

        await self._store.async_save(self._data)

    async def get_patterns(self, user_id: str, confirmed_only: bool = False) -> List[Dict[str, Any]]:
        """Get learned patterns for a user."""
        patterns = self._data.get("users", {}).get(user_id, {}).get("learned_patterns", [])

        if confirmed_only:
            return [p for p in patterns if p.get("confirmed")]

        return patterns

    async def reset_preferences(self, user_id: str) -> None:
        """Reset all preferences for a user."""
        self._data["users"][user_id] = {
            "preferences": DEFAULT_PREFERENCES.copy(),
            "learned_patterns": [],
            "mood_history": [],
            "created_at": dt_util.utcnow().isoformat(),
            "updated_at": dt_util.utcnow().isoformat(),
        }

        await self._store.async_save(self._data)

    def get_active_user(self, zone: Optional[str] = None) -> Optional[str]:
        """Get the currently active user, optionally for a specific zone."""
        if zone:
            return self._active_users.get(zone)

        # Return primary user if no zone specified
        if self._primary_user:
            return self._primary_user

        # Return first active user
        if self._active_users:
            return next(iter(self._active_users.values()))

        return None

    def get_active_users(self) -> Dict[str, str]:
        """Get all active users by zone."""
        return dict(self._active_users)

    async def record_mood(self, user_id: str, zone: str, mood: str, confidence: float) -> None:
        """Record a mood observation for a user."""
        if user_id not in self._data["users"]:
            await self._ensure_user(user_id)

        mood_entry = {
            "timestamp": dt_util.utcnow().isoformat(),
            "zone": zone,
            "mood": mood,
            "confidence": confidence,
        }

        # Keep last 100 mood entries
        history = self._data["users"][user_id].get("mood_history", [])
        history.append(mood_entry)
        self._data["users"][user_id]["mood_history"] = history[-100:]

        await self._store.async_save(self._data)

    def get_mood_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get mood history for a user."""
        history = self._data.get("users", {}).get(user_id, {}).get("mood_history", [])
        return history[-limit:]

    # --- Internal ---

    async def _ensure_user(self, user_id: str) -> None:
        """Ensure a user entry exists."""
        if user_id not in self._data["users"]:
            self._data["users"][user_id] = {
                "preferences": DEFAULT_PREFERENCES.copy(),
                "learned_patterns": [],
                "mood_history": [],
                "created_at": dt_util.utcnow().isoformat(),
                "updated_at": dt_util.utcnow().isoformat(),
            }

    async def _learn_from_context(self, user_id: str) -> None:
        """Learn preferences from current context (active learning mode)."""
        # This is called when user state changes in active mode
        # In a real implementation, this would analyze the context and learn patterns
        _LOGGER.debug("Active learning for user %s (not implemented yet)", user_id)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the module state."""
        return {
            "learning_mode": self._learning_mode,
            "primary_user": self._primary_user,
            "tracked_users": list(self._tracked_users),
            "active_users": self._active_users,
            "total_users": len(self._data.get("users", {})),
            "initialized": self._initialized,
        }