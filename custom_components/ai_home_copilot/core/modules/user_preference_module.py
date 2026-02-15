"""User Preference Module - Multi-User Preference Learning.

v0.8.0 - MVP Implementation
"""
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio

_LOGGER = logging.getLogger(__name__)


@dataclass
class LearnedPattern:
    """A learned user behavior pattern."""
    pattern_id: str
    trigger: str
    action: str
    context: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    occurrences: int = 1
    first_learned: Optional[str] = None
    last_occurrence: Optional[str] = None
    confirmed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "trigger": self.trigger,
            "action": self.action,
            "context": self.context,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "first_learned": self.first_learned,
            "last_occurrence": self.last_occurrence,
            "confirmed": self.confirmed,
        }


@dataclass
class UserPreference:
    """User preference entry."""
    user_id: str
    display_name: str = ""
    preferences: Dict[str, Any] = field(default_factory=lambda: {"light_brightness_default": 0.7})
    learned_patterns: List[Any] = field(default_factory=list)
    mood_history: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "preferences": self.preferences,
            "learned_patterns": self.learned_patterns if isinstance(self.learned_patterns, list) else [],
            "mood_history": self.mood_history,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class ModuleContext:
    """Context object for module operations."""
    
    def __init__(self, hass: Any, entry: Any = None):
        self.hass = hass
        self.entry = entry
        self.data: Dict[str, Any] = {}
    
    async def async_setup(self) -> bool:
        """Set up context."""
        return True


class UserPreferenceModule:
    """User preference handling module."""
    
    NAME = "user_preference"
    VERSION = "0.8.0"
    
    def __init__(self, hass: Any, config: Dict[str, Any]):
        self.hass = hass
        self.config = config
        self._data: Dict[str, Any] = {
            "users": {},
            "config": {"learning_enabled": True}
        }
        self._users: Dict[str, UserPreference] = {}
        self._active_user: Optional[str] = None
        self._active_zone: Optional[str] = None
        self._learning_enabled: bool = True
        self._mood_history: List[Dict[str, Any]] = []
        self._tracked_users: set = set()
        self._store = None  # HA storage store (injected or mocked in tests)
    
    @property
    def name(self) -> str:
        """Return module name."""
        return self.NAME
    
    @property
    def version(self) -> str:
        """Return module version."""
        return self.VERSION
    
    async def async_setup(self) -> bool:
        """Set up the module."""
        return True
    
    async def async_unload(self) -> bool:
        """Unload the module."""
        return True
    
    def get_active_user(self) -> Optional[str]:
        """Get the currently active user ID."""
        return self._active_user
    
    def get_all_users(self) -> Dict[str, UserPreference]:
        """Get all user preferences."""
        return self._users
    
    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get user preference from _data dict."""
        if user_id in self._data["users"]:
            return self._data["users"][user_id].get("preferences", {}).get(key, default)
        return default
    
    async def set_preference(self, user_id: str, key: str, value: Any) -> None:
        """Set user preference in _data dict."""
        if user_id not in self._data["users"]:
            self._data["users"][user_id] = {
                "user_id": user_id,
                "display_name": "",
                "preferences": {"light_brightness_default": 0.7},
                "learned_patterns": [],
                "mood_history": [],
            }
        self._data["users"][user_id]["preferences"][key] = value
        await asyncio.sleep(0)  # Yield control
    
    async def learn_pattern(self, user_id: str, trigger: str, action: str, 
                           context: Optional[Dict[str, Any]] = None) -> str:
        """Learn a new pattern for a user. Returns pattern_id or empty string if disabled."""
        if not self._learning_enabled:
            _LOGGER.debug("Learning disabled, pattern not stored")
            return ""
        
        # Ensure user exists in _data
        if user_id not in self._data["users"]:
            self._data["users"][user_id] = {
                "user_id": user_id,
                "display_name": "",
                "preferences": {"light_brightness_default": 0.7},
                "learned_patterns": [],
                "mood_history": [],
            }
        
        pattern_id = f"{trigger}:{action}"
        now = datetime.utcnow().isoformat()
        
        # Check if pattern already exists
        for pattern in self._data["users"][user_id]["learned_patterns"]:
            if pattern["pattern_id"] == pattern_id:
                pattern["occurrences"] += 1
                pattern["confidence"] = min(1.0, pattern["confidence"] + 0.2)
                pattern["last_occurrence"] = now
                # Merge new context with existing
                if context:
                    pattern["context"].update(context)
                return pattern_id
        
        # Create new pattern
        self._data["users"][user_id]["learned_patterns"].append({
            "pattern_id": pattern_id,
            "trigger": trigger,
            "action": action,
            "context": context or {},
            "confidence": 0.2,
            "occurrences": 1,
            "first_learned": now,
            "last_occurrence": now,
            "confirmed": False,
        })
        
        await asyncio.sleep(0)  # Yield control
        return pattern_id
    
    async def confirm_pattern(self, user_id: str, pattern_id: str) -> bool:
        """Confirm a learned pattern."""
        if user_id not in self._data["users"]:
            return False
        
        for pattern in self._data["users"][user_id]["learned_patterns"]:
            if pattern["pattern_id"] == pattern_id:
                pattern["confirmed"] = True
                pattern["confidence"] = 1.0
                await asyncio.sleep(0)
                return True
        return False
    
    async def forget_pattern(self, user_id: str, pattern_id: str) -> bool:
        """Remove a learned pattern."""
        if user_id not in self._data["users"]:
            return False
        
        patterns = self._data["users"][user_id]["learned_patterns"]
        for i, pattern in enumerate(patterns):
            if pattern["pattern_id"] == pattern_id:
                patterns.pop(i)
                await asyncio.sleep(0)
                return True
        return False
    
    def get_patterns_for_trigger(self, user_id: str, trigger: str) -> List[Dict[str, Any]]:
        """Get all patterns for a specific trigger for a user."""
        if user_id not in self._data["users"]:
            return []
        patterns = []
        for pattern in self._data["users"][user_id].get("learned_patterns", []):
            if pattern.get("trigger") == trigger:
                patterns.append(pattern)
        return patterns
    
    def get_confirmed_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all confirmed patterns for a user."""
        if user_id not in self._data["users"]:
            return []
        patterns = []
        for pattern in self._data["users"][user_id].get("learned_patterns", []):
            if pattern.get("confirmed"):
                patterns.append(pattern)
        return patterns
    
    def get_suggestion_weight(self, user_id: str, mode: str) -> float:
        """Get suggestion weight based on mode and user preference.
        
        Returns 1.0 for unknown users (neutral).
        For known users, adjusts based on frugality preference for energy_saving mode.
        """
        # Unknown user - return neutral weight
        if user_id not in self._data["users"]:
            return 1.0
        
        user_prefs = self._data["users"][user_id].get("preferences", {})
        
        if mode == "energy_saving":
            # Higher frugality = higher weight for energy saving
            frugality = user_prefs.get("frugality", 0.5)
            return 0.5 + frugality  # 0.5-1.5 range
        elif mode == "comfort":
            # Higher comfort preference = higher weight
            comfort = user_prefs.get("comfort", 0.5)
            return 0.5 + comfort
        else:
            return 1.0
    
    async def record_mood(self, user_id: str, zone: str, mood: Dict[str, Any], 
                          confidence: float = 1.0) -> None:
        """Record a mood entry for a user in a zone."""
        # Ensure user exists
        if user_id not in self._data["users"]:
            self._data["users"][user_id] = {
                "user_id": user_id,
                "display_name": "",
                "preferences": {"light_brightness_default": 0.7},
                "learned_patterns": [],
                "mood_history": [],
            }
        
        entry = {
            "zone": zone,
            "mood": mood,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._data["users"][user_id]["mood_history"].append(entry)
        
        # Limit history to 100 entries
        if len(self._data["users"][user_id]["mood_history"]) > 100:
            self._data["users"][user_id]["mood_history"] = self._data["users"][user_id]["mood_history"][-100:]
        
        await asyncio.sleep(0)  # Yield control
    
    def get_recent_moods(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent mood entries for a user."""
        if user_id not in self._data["users"]:
            return []
        return self._data["users"][user_id].get("mood_history", [])[-limit:]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of module state."""
        return {
            "tracked_users": list(self._tracked_users),
            "active_user": self._active_user,
            "active_zone": self._active_zone,
            "learning_enabled": self._learning_enabled,
            "total_users": len(self._data["users"]),
            "primary_user": self._data["config"].get("primary_user"),
        }
    
    def set_learning_enabled(self, enabled: bool) -> None:
        """Enable or disable learning."""
        self._learning_enabled = enabled
        self._data["config"]["learning_enabled"] = enabled