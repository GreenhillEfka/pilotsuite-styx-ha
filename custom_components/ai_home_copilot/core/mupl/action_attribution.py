"""Multi-User Preference Learning - Action Attribution Module

Phase 2: Attribute Home Assistant actions to specific users
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from homeassistant.core import HomeAssistant, Event
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


@dataclass
class AttributionResult:
    """Result of action attribution"""
    user_id: str
    confidence: float
    sources: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=dt_util.utcnow)
    entity_id: str = ""
    action: str = ""


@dataclass
class UserAction:
    """Recorded user action with attribution"""
    user_id: str
    entity_id: str
    action: str
    confidence: float
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    sources: Dict[str, float] = field(default_factory=dict)


class AttributionSource:
    """Base class for attribution sources"""
    
    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight
    
    async def get_attribution(self, hass: HomeAssistant, entity_id: str, action: str) -> Optional[AttributionResult]:
        """Return attribution result if this source can determine the user"""
        raise NotImplementedError


class PresenceAttribution(AttributionSource):
    """Attribution based on presence sensors"""
    
    def __init__(self, hass: HomeAssistant, presence_entities: Dict[str, str]):
        """
        Args:
            presence_entities: Mapping of user_id -> presence_entity_id
        """
        super().__init__("presence", weight=0.4)
        self.hass = hass
        self.presence_entities = presence_entities
    
    async def get_attribution(self, hass: HomeAssistant, entity_id: str, action: str) -> Optional[AttributionResult]:
        """Check who is home and likely to have triggered the action"""
        present_users = []
        
        for user_id, presence_entity in self.presence_entities.items():
            state = hass.states.get(presence_entity)
            if state and state.state == "home":
                present_users.append(user_id)
        
        if len(present_users) == 1:
            return AttributionResult(
                user_id=present_users[0],
                confidence=0.4 * self.weight,
                sources={"presence": 0.4}
            )
        elif len(present_users) > 1:
            # Multiple users present - lower confidence
            return AttributionResult(
                user_id=present_users[0],  # First user as fallback
                confidence=0.2 * self.weight,
                sources={"presence": 0.2, "multiple_present": len(present_users)}
            )
        
        return None


class DeviceOwnershipAttribution(AttributionSource):
    """Attribution based on device ownership"""
    
    def __init__(self, hass: HomeAssistant, device_owners: Dict[str, str]):
        """
        Args:
            device_owners: Mapping of device_entity_id -> user_id
        """
        super().__init__("device_ownership", weight=0.3)
        self.hass = hass
        self.device_owners = device_owners
    
    async def get_attribution(self, hass: HomeAssistant, entity_id: str, action: str) -> Optional[AttributionResult]:
        """Check if entity is owned by a specific user"""
        if entity_id in self.device_owners:
            return AttributionResult(
                user_id=self.device_owners[entity_id],
                confidence=0.3 * self.weight,
                sources={"device_ownership": 0.3}
            )
        return None


class RoomLocationAttribution(AttributionSource):
    """Attribution based on room location"""
    
    def __init__(self, hass: HomeAssistant, room_presence: Dict[str, str]):
        """
        Args:
            room_presence: Mapping of room_id -> presence_sensor_id
        """
        super().__init__("room_location", weight=0.3)
        self.hass = hass
        self.room_presence = room_presence
    
    async def get_attribution(self, hass: HomeAssistant, entity_id: str, action: str) -> Optional[AttributionResult]:
        """Check who is in the room where the entity is located"""
        # Get entity's area/room
        registry = hass.data.get("entity_registry")
        if registry:
            entity_entry = registry.async_get(entity_id)
            if entity_entry and entity_entry.area_id:
                # Check presence in this area
                area_presence_entity = self.room_presence.get(entity_entry.area_id)
                if area_presence_entity:
                    state = hass.states.get(area_presence_entity)
                    if state and state.state not in ["off", "unknown", "unavailable"]:
                        # Extract user from presence sensor name
                        return AttributionResult(
                            user_id=state.state.lower(),
                            confidence=0.3 * self.weight,
                            sources={"room_location": 0.3}
                        )
        return None


class TimePatternAttribution(AttributionSource):
    """Attribution based on historical time patterns"""
    
    def __init__(self, hass: HomeAssistant, time_patterns: Dict[str, Dict[str, str]]):
        """
        Args:
            time_patterns: Mapping of entity_id -> {time_of_day -> user_id}
        """
        super().__init__("time_pattern", weight=0.2)
        self.hass = hass
        self.time_patterns = time_patterns
    
    async def get_attribution(self, hass: HomeAssistant, entity_id: str, action: str) -> Optional[AttributionResult]:
        """Check historical patterns for who usually acts at this time"""
        patterns = self.time_patterns.get(entity_id)
        if not patterns:
            return None
        
        now = dt_util.utcnow()
        hour = now.hour
        
        # Determine time of day
        if 6 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 18:
            time_of_day = "afternoon"
        elif 18 <= hour < 22:
            time_of_day = "evening"
        else:
            time_of_day = "night"
        
        if time_of_day in patterns:
            return AttributionResult(
                user_id=patterns[time_of_day],
                confidence=0.2 * self.weight,
                sources={"time_pattern": 0.2, "time_of_day": time_of_day}
            )
        
        return None


class ActionAttributor:
    """Main Action Attribution Engine"""
    
    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        self.hass = hass
        self.config = config
        
        # Initialize attribution sources
        self.sources: List[AttributionSource] = []
        
        # Storage
        self._action_history: List[UserAction] = []
        self._max_history = config.get("max_history", 1000)
        
        # User mapping
        self.presence_entities = config.get("presence_entities", {})
        self.device_owners = config.get("device_owners", {})
        self.room_presence = config.get("room_presence", {})
        self.time_patterns = config.get("time_patterns", {})
    
    async def async_setup(self):
        """Setup attribution sources"""
        if self.presence_entities:
            self.sources.append(PresenceAttribution(self.hass, self.presence_entities))
        
        if self.device_owners:
            self.sources.append(DeviceOwnershipAttribution(self.hass, self.device_owners))
        
        if self.room_presence:
            self.sources.append(RoomLocationAttribution(self.hass, self.room_presence))
        
        if self.time_patterns:
            self.sources.append(TimePatternAttribution(self.hass, self.time_patterns))
        
        _LOGGER.info("ActionAttributor initialized with %d sources", len(self.sources))
    
    async def attribute_action(self, entity_id: str, action: str, 
                                service_data: Optional[Dict] = None) -> Optional[UserAction]:
        """
        Attribute an action to a user.
        
        Args:
            entity_id: The entity that was acted upon
            action: The action (turn_on, turn_off, etc.)
            service_data: Additional service data
            
        Returns:
            UserAction with attribution, or None if no attribution possible
        """
        if not self.sources:
            _LOGGER.warning("No attribution sources configured")
            return None
        
        # Collect attributions from all sources
        attributions = []
        for source in self.sources:
            try:
                result = await source.get_attribution(self.hass, entity_id, action)
                if result:
                    attributions.append(result)
            except Exception as e:
                _LOGGER.error("Error in attribution source %s: %s", source.name, e)
        
        if not attributions:
            return None
        
        # Combine attributions with weighted confidence
        user_scores: Dict[str, float] = {}
        user_sources: Dict[str, Dict[str, float]] = {}
        
        for attr in attributions:
            if attr.user_id not in user_scores:
                user_scores[attr.user_id] = 0
                user_sources[attr.user_id] = {}
            
            user_scores[attr.user_id] += attr.confidence
            user_sources[attr.user_id].update(attr.sources)
        
        # Find user with highest confidence
        best_user = max(user_scores.keys(), key=lambda u: user_scores[u])
        best_confidence = min(user_scores[best_user], 1.0)  # Cap at 1.0
        
        # Create action record
        user_action = UserAction(
            user_id=best_user,
            entity_id=entity_id,
            action=action,
            confidence=best_confidence,
            timestamp=dt_util.utcnow(),
            sources=user_sources[best_user],
            context={
                "service_data": service_data,
                "all_candidates": {u: s for u, s in user_scores.items() if u != best_user}
            }
        )
        
        # Store in history
        self._action_history.append(user_action)
        if len(self._action_history) > self._max_history:
            self._action_history = self._action_history[-self._max_history:]
        
        _LOGGER.debug(
            "Attributed action %s on %s to user %s (confidence: %.2f)",
            action, entity_id, best_user, best_confidence
        )
        
        return user_action
    
    def get_user_actions(self, user_id: str, limit: int = 100) -> List[UserAction]:
        """Get recent actions for a specific user"""
        return [
            a for a in self._action_history
            if a.user_id == user_id
        ][-limit:]
    
    def get_entity_actions(self, entity_id: str, limit: int = 100) -> List[UserAction]:
        """Get recent actions for a specific entity"""
        return [
            a for a in self._action_history
            if a.entity_id == entity_id
        ][-limit:]
    
    def get_action_history(self, limit: int = 100) -> List[UserAction]:
        """Get all recent actions"""
        return self._action_history[-limit:]