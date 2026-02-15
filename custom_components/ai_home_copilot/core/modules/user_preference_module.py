"""User Preference Module - Stub for import compatibility."""
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

_LOGGER = logging.getLogger(__name__)


@dataclass
class LearnedPattern:
    """A learned user behavior pattern."""
    entity_id: str
    action: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    occurrences: int = 0
    last_triggered: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_id": self.entity_id,
            "action": self.action,
            "conditions": self.conditions,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class UserPreference:
    """User preference entry."""
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    patterns: List[LearnedPattern] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def add_pattern(self, pattern: LearnedPattern) -> None:
        """Add a learned pattern."""
        self.patterns.append(pattern)
        self.last_updated = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "preferences": self.preferences,
            "patterns": [p.to_dict() for p in self.patterns],
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
    
    def __init__(self, hass: Any, config: Dict[str, Any]):
        self.hass = hass
        self.config = config
        self._preferences: Dict[str, Dict] = {}
    
    async def async_setup(self) -> bool:
        """Set up the module."""
        return True
    
    async def async_unload(self) -> bool:
        """Unload the module."""
        return True
    
    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get user preference."""
        return self._preferences.get(user_id, {}).get(key, default)
    
    def set_preference(self, user_id: str, key: str, value: Any) -> None:
        """Set user preference."""
        if user_id not in self._preferences:
            self._preferences[user_id] = {}
        self._preferences[user_id][key] = value
