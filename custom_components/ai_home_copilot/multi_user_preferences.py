"""Multi-User Preference Learning Module.

This module provides user detection, action attribution, and preference learning
for multi-user households. Phase 1 focuses on user detection and preference storage.

Design Doc: docs/MUPL_DESIGN.md
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    PREF_RETENTION_DAYS,
    PREF_SMOOTHING_ALPHA,
    PREF_MIN_INTERACTIONS,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = f"{DOMAIN}_preferences"
STORAGE_VERSION = 1


@dataclass
class UserPreferences:
    """Preferences for a single user."""
    
    user_id: str
    name: str = "Unknown"
    preferences: dict[str, Any] = field(default_factory=lambda: {
        "light_brightness": {"default": 0.8, "by_zone": {}},
        "media_volume": {"default": 0.5, "by_zone": {}},
        "temperature": {"default": 21.0, "by_zone": {}},
        "mood_weights": {"comfort": 0.5, "frugality": 0.5, "joy": 0.5},
    })
    patterns: dict[str, Any] = field(default_factory=dict)
    last_seen: str | None = None
    interaction_count: int = 0
    priority: float = 0.5  # For conflict resolution in multi-user scenarios
    

@dataclass
class DeviceAffinity:
    """Affinity of devices to users."""
    
    entity_id: str
    primary_user: str | None = None
    usage_distribution: dict[str, float] = field(default_factory=dict)


class MultiUserPreferenceModule:
    """Multi-User Preference Learning Module.
    
    Phase 1: User Detection + Preference Storage
    Phase 2: Action Attribution + Learning
    Phase 3: Multi-User Mood + Aggregation
    """
    
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the module."""
        self.hass = hass
        self.config_entry = config_entry
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, STORAGE_KEY)
        
        # Internal state
        self._users: dict[str, UserPreferences] = {}
        self._device_affinities: dict[str, DeviceAffinity] = {}
        self._person_entities: list[str] = []
        self._active_users: list[str] = []
        self._unsub_trackers: list[Any] = []
        
        # Config
        self._enabled = config_entry.options.get("mupl_enabled", True)
        self._privacy_mode = config_entry.options.get("mupl_privacy_mode", "opt-in")
        
    async def async_setup(self) -> None:
        """Set up the module."""
        _LOGGER.info("Setting up Multi-User Preference Learning Module")
        
        # Load stored preferences
        await self._async_load_preferences()
        
        # Discover person entities
        await self._async_discover_persons()
        
        # Subscribe to presence changes
        await self._async_subscribe_presence()
        
        _LOGGER.info(
            "Multi-User Preference Learning Module initialized: %d users, %d persons tracked",
            len(self._users),
            len(self._person_entities),
        )
        
    async def async_unload(self) -> None:
        """Unload the module."""
        for unsub in self._unsub_trackers:
            unsub()
        self._unsub_trackers.clear()
        
    # ==================== User Detection (Phase 1) ====================
    
    async def _async_discover_persons(self) -> None:
        """Discover person entities in Home Assistant."""
        self._person_entities = []
        
        for state in self.hass.states.async_all("person"):
            self._person_entities.append(state.entity_id)
            _LOGGER.debug("Discovered person entity: %s", state.entity_id)
            
            # Initialize user if not exists
            if state.entity_id not in self._users:
                self._users[state.entity_id] = UserPreferences(
                    user_id=state.entity_id,
                    name=state.attributes.get("friendly_name", state.entity_id),
                )
                
        _LOGGER.info("Discovered %d person entities", len(self._person_entities))
        
    async def _async_subscribe_presence(self) -> None:
        """Subscribe to person state changes for presence tracking."""
        if not self._person_entities:
            return
            
        @callback
        def _person_state_changed(event):
            """Handle person state change."""
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            
            if not new_state:
                return
                
            # Update last_seen
            if entity_id in self._users:
                self._users[entity_id].last_seen = new_state.last_updated.isoformat()
                
            # Update active users
            if new_state.state == "home" and old_state and old_state.state != "home":
                # User arrived
                if entity_id not in self._active_users:
                    self._active_users.append(entity_id)
                _LOGGER.info("User arrived: %s", entity_id)
            elif new_state.state != "home" and old_state and old_state.state == "home":
                # User left
                if entity_id in self._active_users:
                    self._active_users.remove(entity_id)
                _LOGGER.info("User left: %s", entity_id)
                
            # Save on presence change
            self.hass.async_create_task(self._async_save_preferences())
            
        unsub = async_track_state_change_event(
            self.hass,
            self._person_entities,
            _person_state_changed,
        )
        self._unsub_trackers.append(unsub)
        
    async def detect_active_users(self) -> list[str]:
        """Detect currently active (home) users.
        
        Returns:
            List of person entity_ids that are currently home.
        """
        active = []
        
        for entity_id in self._person_entities:
            state = self.hass.states.get(entity_id)
            if state and state.state == "home":
                active.append(entity_id)
                
        self._active_users = active
        return active
        
    def get_active_users(self) -> list[str]:
        """Get cached list of active users."""
        return self._active_users.copy()
        
    def get_user_name(self, user_id: str) -> str:
        """Get friendly name for a user."""
        if user_id in self._users:
            return self._users[user_id].name
        state = self.hass.states.get(user_id)
        if state:
            return state.attributes.get("friendly_name", user_id)
        return user_id
        
    # ==================== Preference Storage (Phase 1) ====================
    
    async def _async_load_preferences(self) -> None:
        """Load preferences from storage."""
        data = await self._store.async_load()
        
        if data is None:
            _LOGGER.info("No stored preferences found, starting fresh")
            return
            
        users_data = data.get("users", {})
        for user_id, user_dict in users_data.items():
            self._users[user_id] = UserPreferences(
                user_id=user_id,
                name=user_dict.get("name", user_id),
                preferences=user_dict.get("preferences", {}),
                patterns=user_dict.get("patterns", {}),
                last_seen=user_dict.get("last_seen"),
                interaction_count=user_dict.get("interaction_count", 0),
                priority=user_dict.get("priority", 0.5),
            )
            
        affinities_data = data.get("device_affinities", {})
        for entity_id, aff_dict in affinities_data.items():
            self._device_affinities[entity_id] = DeviceAffinity(
                entity_id=entity_id,
                primary_user=aff_dict.get("primary_user"),
                usage_distribution=aff_dict.get("usage_distribution", {}),
            )
            
        _LOGGER.info("Loaded preferences for %d users", len(self._users))
        
    async def _async_save_preferences(self) -> None:
        """Save preferences to storage."""
        data = {
            "users": {
                user_id: {
                    "name": user.name,
                    "preferences": user.preferences,
                    "patterns": user.patterns,
                    "last_seen": user.last_seen,
                    "interaction_count": user.interaction_count,
                    "priority": user.priority,
                }
                for user_id, user in self._users.items()
            },
            "device_affinities": {
                entity_id: {
                    "primary_user": aff.primary_user,
                    "usage_distribution": aff.usage_distribution,
                }
                for entity_id, aff in self._device_affinities.items()
            },
            "version": STORAGE_VERSION,
            "updated_at": datetime.now().isoformat(),
        }
        
        await self._store.async_save(data)
        _LOGGER.debug("Saved preferences for %d users", len(self._users))
        
    def get_user_preferences(self, user_id: str) -> dict[str, Any] | None:
        """Get preferences for a specific user."""
        if user_id not in self._users:
            return None
        return self._users[user_id].preferences
        
    def get_all_users(self) -> dict[str, UserPreferences]:
        """Get all user data."""
        return self._users.copy()
        
    # ==================== Action Attribution (Phase 2) ====================
    
    async def attribute_action(self, context_user_id: str | None, entity_id: str) -> str | None:
        """Attribute an action to a user.
        
        Priority:
        1. Context user_id (highest confidence)
        2. Device affinity
        3. Proximity (zone)
        4. First active user (fallback)
        
        Args:
            context_user_id: User ID from service call context
            entity_id: Entity that was acted upon
            
        Returns:
            Attributed user_id or None
        """
        # High confidence: explicit context
        if context_user_id and context_user_id in self._users:
            return context_user_id
            
        # Medium confidence: device affinity
        if entity_id in self._device_affinities:
            aff = self._device_affinities[entity_id]
            if aff.primary_user and aff.primary_user in self._active_users:
                return aff.primary_user
                
        # Low confidence: first active user
        if self._active_users:
            return self._active_users[0]
            
        return None
        
    async def update_device_affinity(self, entity_id: str, user_id: str) -> None:
        """Update device affinity based on usage."""
        if entity_id not in self._device_affinities:
            self._device_affinities[entity_id] = DeviceAffinity(entity_id=entity_id)
            
        aff = self._device_affinities[entity_id]
        
        # Update usage distribution with smoothing
        if user_id not in aff.usage_distribution:
            aff.usage_distribution[user_id] = 0.0
            
        # Boost this user, decay others
        total = sum(aff.usage_distribution.values())
        for uid in aff.usage_distribution:
            if uid == user_id:
                aff.usage_distribution[uid] += 0.1
            else:
                aff.usage_distribution[uid] *= 0.95
                
        # Normalize
        total = sum(aff.usage_distribution.values())
        if total > 0:
            for uid in aff.usage_distribution:
                aff.usage_distribution[uid] /= total
                
        # Update primary user
        if aff.usage_distribution:
            aff.primary_user = max(
                aff.usage_distribution.keys(),
                key=lambda uid: aff.usage_distribution[uid],
            )
            
        await self._async_save_preferences()
        
    # ==================== Preference Learning (Phase 2) ====================
    
    async def learn_from_action(
        self,
        user_id: str,
        domain: str,
        entity_id: str,
        data: dict[str, Any],
        zone: str | None = None,
    ) -> None:
        """Learn preferences from a user action.
        
        Args:
            user_id: User who performed the action
            domain: Domain (light, climate, media_player)
            entity_id: Entity that was acted upon
            data: Action data (brightness, temperature, volume, etc.)
            zone: Optional zone for zone-specific preferences
        """
        if user_id not in self._users:
            _LOGGER.warning("Unknown user: %s", user_id)
            return
            
        user = self._users[user_id]
        user.interaction_count += 1
        user.last_seen = datetime.now().isoformat()
        
        prefs = user.preferences
        
        # Light brightness
        if domain == "light" and "brightness_pct" in data:
            value = data["brightness_pct"] / 100.0
            await self._update_preference(
                prefs, "light_brightness", value, zone
            )
            _LOGGER.debug("Learned brightness %.2f for %s in %s", value, user_id, zone or "default")
            
        # Climate temperature
        elif domain == "climate" and "temperature" in data:
            value = float(data["temperature"])
            await self._update_preference(
                prefs, "temperature", value, zone
            )
            _LOGGER.debug("Learned temperature %.1f for %s in %s", value, user_id, zone or "default")
            
        # Media volume
        elif domain == "media_player" and "volume_level" in data:
            value = float(data["volume_level"])
            await self._update_preference(
                prefs, "media_volume", value, zone
            )
            _LOGGER.debug("Learned volume %.2f for %s in %s", value, user_id, zone or "default")
            
        # Update device affinity
        await self.update_device_affinity(entity_id, user_id)
        
        # Save
        await self._async_save_preferences()
        
    async def _update_preference(
        self,
        prefs: dict[str, Any],
        pref_type: str,
        value: float,
        zone: str | None = None,
    ) -> None:
        """Update a preference with exponential smoothing."""
        if pref_type not in prefs:
            prefs[pref_type] = {"default": 0.5, "by_zone": {}}
            
        # Zone-specific update
        if zone:
            if "by_zone" not in prefs[pref_type]:
                prefs[pref_type]["by_zone"] = {}
            current = prefs[pref_type]["by_zone"].get(zone, prefs[pref_type]["default"])
            # Exponential smoothing
            updated = current * (1 - PREF_SMOOTHING_ALPHA) + value * PREF_SMOOTHING_ALPHA
            prefs[pref_type]["by_zone"][zone] = round(updated, 2)
        else:
            # Global default update
            current = prefs[pref_type].get("default", 0.5)
            updated = current * (1 - PREF_SMOOTHING_ALPHA) + value * PREF_SMOOTHING_ALPHA
            prefs[pref_type]["default"] = round(updated, 2)
            
    # ==================== Explicit Preference Setting ====================
    
    async def set_preference(
        self,
        user_id: str,
        pref_type: str,
        value: float | dict,
        zone: str | None = None,
    ) -> bool:
        """Explicitly set a preference for a user.
        
        Args:
            user_id: User to set preference for
            pref_type: Type of preference (light_brightness, temperature, etc.)
            value: Preference value (float or dict for mood_weights)
            zone: Optional zone for zone-specific preference
            
        Returns:
            True if successful
        """
        if user_id not in self._users:
            _LOGGER.warning("Unknown user: %s", user_id)
            return False
            
        prefs = self._users[user_id].preferences
        
        # Special handling for mood_weights (dict)
        if pref_type == "mood_weights" and isinstance(value, dict):
            prefs["mood_weights"] = value
        elif isinstance(value, (int, float)):
            if pref_type not in prefs:
                prefs[pref_type] = {"default": 0.5, "by_zone": {}}
                
            if zone:
                if "by_zone" not in prefs[pref_type]:
                    prefs[pref_type]["by_zone"] = {}
                prefs[pref_type]["by_zone"][zone] = float(value)
            else:
                prefs[pref_type]["default"] = float(value)
                
        await self._async_save_preferences()
        _LOGGER.info("Set preference %s=%s for %s (zone=%s)", pref_type, value, user_id, zone)
        return True
        
    async def set_user_priority(self, user_id: str, priority: float) -> bool:
        """Set user priority for conflict resolution.
        
        Args:
            user_id: User to set priority for
            priority: Priority (0.0-1.0, higher = more important)
            
        Returns:
            True if successful
        """
        if user_id not in self._users:
            return False
            
        priority = max(0.0, min(1.0, priority))
        self._users[user_id].priority = priority
        await self._async_save_preferences()
        _LOGGER.info("Set priority %.2f for %s", priority, user_id)
        return True
        
    # ==================== Multi-User Mood (Phase 3) ====================
    
    def get_aggregated_mood(self, user_ids: list[str] | None = None) -> dict[str, float]:
        """Aggregate mood for multiple users.
        
        Args:
            user_ids: Users to aggregate (default: active users)
            
        Returns:
            Aggregated mood dict with comfort, frugality, joy
        """
        if user_ids is None:
            user_ids = self._active_users
            
        if not user_ids:
            return {"comfort": 0.5, "frugality": 0.5, "joy": 0.5}
            
        if len(user_ids) == 1:
            user_id = user_ids[0]
            if user_id in self._users:
                return self._users[user_id].preferences.get("mood_weights", {})
            return {"comfort": 0.5, "frugality": 0.5, "joy": 0.5}
            
        # Weighted aggregation by priority
        total_weight = 0.0
        mood = {"comfort": 0.0, "frugality": 0.0, "joy": 0.0}
        
        for user_id in user_ids:
            if user_id not in self._users:
                continue
            user = self._users[user_id]
            weight = user.priority
            user_mood = user.preferences.get("mood_weights", {})
            
            mood["comfort"] += user_mood.get("comfort", 0.5) * weight
            mood["frugality"] += user_mood.get("frugality", 0.5) * weight
            mood["joy"] += user_mood.get("joy", 0.5) * weight
            total_weight += weight
            
        if total_weight > 0:
            mood = {k: v / total_weight for k, v in mood.items()}
            
        return mood
        
    # ==================== Privacy ====================
    
    async def delete_user_data(self, user_id: str) -> bool:
        """Delete all data for a user (privacy/GDPR).
        
        Args:
            user_id: User to delete
            
        Returns:
            True if successful
        """
        if user_id not in self._users:
            return False
            
        del self._users[user_id]
        
        # Remove from device affinities
        for entity_id, aff in self._device_affinities.items():
            if aff.primary_user == user_id:
                aff.primary_user = None
            if user_id in aff.usage_distribution:
                del aff.usage_distribution[user_id]
                
        # Remove from active users
        if user_id in self._active_users:
            self._active_users.remove(user_id)
            
        await self._async_save_preferences()
        _LOGGER.info("Deleted all data for user: %s", user_id)
        return True
        
    async def export_user_data(self, user_id: str) -> dict[str, Any] | None:
        """Export all data for a user (privacy/GDPR).
        
        Args:
            user_id: User to export
            
        Returns:
            User data dict or None
        """
        if user_id not in self._users:
            return None
            
        user = self._users[user_id]
        
        # Include relevant device affinities
        affinities = {
            entity_id: aff.usage_distribution
            for entity_id, aff in self._device_affinities.items()
            if user_id in aff.usage_distribution
        }
        
        return {
            "user_id": user.user_id,
            "name": user.name,
            "preferences": user.preferences,
            "patterns": user.patterns,
            "last_seen": user.last_seen,
            "interaction_count": user.interaction_count,
            "priority": user.priority,
            "device_affinities": affinities,
        }


# ---------------------------------------------------------------------------
# Module accessor helpers
# ---------------------------------------------------------------------------

_MUPL_MODULE_KEY = f"{DOMAIN}_mupl_module"


def get_mupl_module(hass: HomeAssistant) -> MultiUserPreferenceModule | None:
    """Get the MUPL module from hass.data."""
    for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
        if isinstance(entry_data, dict) and _MUPL_MODULE_KEY in entry_data:
            return entry_data[_MUPL_MODULE_KEY]
    return None


def set_mupl_module(hass: HomeAssistant, entry_id: str, module: MultiUserPreferenceModule) -> None:
    """Store the MUPL module in hass.data."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if entry_id not in hass.data[DOMAIN]:
        hass.data[DOMAIN][entry_id] = {}
    hass.data[DOMAIN][entry_id][_MUPL_MODULE_KEY] = module