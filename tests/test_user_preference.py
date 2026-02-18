"""Tests for User Preference Module — Multi-User Preference Learning.

v0.8.0 - MVP Implementation

NOTE: These tests require Home Assistant installation as they test the
MultiUserPreferenceModule which depends on HA storage and person entities.
"""
import pytest

# Mark entire file as integration tests requiring HA
pytestmark = pytest.mark.integration

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Lazy import HA components
try:
    from custom_components.ai_home_copilot.core.modules.user_preference_module import (
        UserPreferenceModule,
        UserPreference,
        LearnedPattern,
        ModuleContext,
    )
    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False
    UserPreferenceModule = None
    UserPreference = None
    LearnedPattern = None
    ModuleContext = None


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = Mock()
    hass.data = {}
    hass.states = Mock()
    hass.states.get = Mock(return_value=None)
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock ConfigEntry."""
    entry = Mock()
    entry.entry_id = "test_entry_id"
    entry.domain = "ai_home_copilot"
    entry.data = {
        "core_api_url": "http://localhost:8909",
        "api_token": "test_token",
    }
    return entry


@pytest.fixture
def mock_context(mock_hass, mock_entry):
    """Create a mock ModuleContext."""
    return ModuleContext(hass=mock_hass, entry=mock_entry)


@pytest.fixture
async def module(mock_hass, mock_entry, mock_context):
    """Create and setup a UserPreferenceModule instance."""
    # Skip if HA not available
    if not HA_AVAILABLE:
        pytest.skip("Home Assistant not installed")
    
    # UserPreferenceModule requires hass and config
    config = {
        "core_api_url": "http://localhost:8909",
        "api_token": "test_token",
    }
    mod = UserPreferenceModule(hass=mock_hass, config=config)
    
    # Store in hass.data
    mock_hass.data["ai_home_copilot"] = {"user_preference_module": mod}
    
    return mod


class TestUserPreferenceModule:
    """Test cases for UserPreferenceModule."""
    
    def test_module_name(self, module):
        """Test module name."""
        assert module.name == "user_preference"
    
    def test_module_version(self, module):
        """Test module version."""
        assert module.version == "0.9.0"
    
    def test_get_active_user_none_initially(self, module):
        """Test that active user is None initially."""
        assert module.get_active_user() is None
    
    def test_get_all_users_empty_initially(self, module):
        """Test that all users is empty initially."""
        assert module.get_all_users() == {}
    
    @pytest.mark.asyncio
    async def test_set_preference_creates_user(self, module):
        """Test that set_preference creates user if not exists."""
        # Mock store if needed
        if module._store is None:
            from unittest.mock import AsyncMock
            module._store = AsyncMock()
            module._store.async_load = AsyncMock(return_value=module._data)
        
        await module.set_preference("person.test_user", "light_brightness_default", 0.8)
        
        assert "person.test_user" in module._data["users"]
        assert module._data["users"]["person.test_user"]["preferences"]["light_brightness_default"] == 0.8
    
    @pytest.mark.asyncio
    async def test_set_preference_updates_existing(self, module):
        """Test that set_preference updates existing preference."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "display_name": "Test User",
            "preferences": {"light_brightness_default": 0.7},
            "learned_patterns": [],
            "mood_history": [],
        }
        
        await module.set_preference("person.test_user", "light_brightness_default", 0.9)
        
        assert module._data["users"]["person.test_user"]["preferences"]["light_brightness_default"] == 0.9
    
    def test_get_preference_returns_value(self, module):
        """Test that get_preference returns the correct value."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "preferences": {"temperature_comfort": 22.0},
        }
        
        value = module.get_preference("person.test_user", "temperature_comfort")
        assert value == 22.0
    
    def test_get_preference_returns_default_for_missing_user(self, module):
        """Test that get_preference returns default for missing user."""
        value = module.get_preference("person.unknown", "temperature_comfort", 20.0)
        assert value == 20.0
    
    def test_get_preference_returns_default_for_missing_key(self, module):
        """Test that get_preference returns default for missing key."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "preferences": {},
        }
        
        value = module.get_preference("person.test_user", "temperature_comfort", 21.0)
        assert value == 21.0
    
    @pytest.mark.asyncio
    async def test_learn_pattern_creates_new_pattern(self, module):
        """Test that learn_pattern creates a new pattern."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "preferences": {},
            "learned_patterns": [],
            "mood_history": [],
        }
        
        pattern_id = await module.learn_pattern(
            "person.test_user",
            "movie_mode",
            "dim_lights",
            {"zone": "wohnbereich"}
        )
        
        assert pattern_id == "movie_mode:dim_lights"
        assert len(module._data["users"]["person.test_user"]["learned_patterns"]) == 1
        
        pattern = module._data["users"]["person.test_user"]["learned_patterns"][0]
        assert pattern["trigger"] == "movie_mode"
        assert pattern["action"] == "dim_lights"
        assert pattern["occurrences"] == 1
        assert pattern["confidence"] == 0.2
        assert pattern["confirmed"] is False
    
    @pytest.mark.asyncio
    async def test_learn_pattern_updates_existing(self, module):
        """Test that learn_pattern updates existing pattern."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "preferences": {},
            "learned_patterns": [{
                "pattern_id": "movie_mode:dim_lights",
                "trigger": "movie_mode",
                "action": "dim_lights",
                "context": {},
                "confidence": 0.2,
                "occurrences": 1,
                "first_learned": "2026-02-15T00:00:00",
                "last_occurrence": "2026-02-15T00:00:00",
                "confirmed": False,
            }],
            "mood_history": [],
        }
        
        pattern_id = await module.learn_pattern(
            "person.test_user",
            "movie_mode",
            "dim_lights",
            {"brightness": 0.3}
        )
        
        assert pattern_id == "movie_mode:dim_lights"
        assert len(module._data["users"]["person.test_user"]["learned_patterns"]) == 1
        
        pattern = module._data["users"]["person.test_user"]["learned_patterns"][0]
        assert pattern["occurrences"] == 2
        assert pattern["confidence"] == 0.4  # min(1.0, 2/5)
        assert "brightness" in pattern["context"]
    
    @pytest.mark.asyncio
    async def test_learn_pattern_reaches_max_confidence(self, module):
        """Test that confidence reaches 1.0 after 5 occurrences."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "preferences": {},
            "learned_patterns": [{
                "pattern_id": "movie_mode:dim_lights",
                "trigger": "movie_mode",
                "action": "dim_lights",
                "context": {},
                "confidence": 0.8,
                "occurrences": 4,
                "first_learned": "2026-02-15T00:00:00",
                "last_occurrence": "2026-02-15T00:00:00",
                "confirmed": False,
            }],
            "mood_history": [],
        }
        
        await module.learn_pattern("person.test_user", "movie_mode", "dim_lights")
        
        pattern = module._data["users"]["person.test_user"]["learned_patterns"][0]
        assert pattern["occurrences"] == 5
        assert pattern["confidence"] == 1.0
    
    @pytest.mark.asyncio
    async def test_confirm_pattern(self, module):
        """Test confirming a pattern."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "learned_patterns": [{
                "pattern_id": "movie_mode:dim_lights",
                "confirmed": False,
                "confidence": 0.6,
            }],
        }
        
        result = await module.confirm_pattern("person.test_user", "movie_mode:dim_lights")
        
        assert result is True
        pattern = module._data["users"]["person.test_user"]["learned_patterns"][0]
        assert pattern["confirmed"] is True
        assert pattern["confidence"] == 1.0
    
    @pytest.mark.asyncio
    async def test_confirm_pattern_not_found(self, module):
        """Test confirming a non-existent pattern."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "learned_patterns": [],
        }
        
        result = await module.confirm_pattern("person.test_user", "nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_forget_pattern(self, module):
        """Test forgetting a pattern."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "learned_patterns": [
                {"pattern_id": "pattern1", "trigger": "a", "action": "b"},
                {"pattern_id": "pattern2", "trigger": "c", "action": "d"},
            ],
        }
        
        result = await module.forget_pattern("person.test_user", "pattern1")
        
        assert result is True
        assert len(module._data["users"]["person.test_user"]["learned_patterns"]) == 1
        assert module._data["users"]["person.test_user"]["learned_patterns"][0]["pattern_id"] == "pattern2"
    
    @pytest.mark.asyncio
    async def test_forget_pattern_not_found(self, module):
        """Test forgetting a non-existent pattern."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "learned_patterns": [],
        }
        
        result = await module.forget_pattern("person.test_user", "nonexistent")
        assert result is False
    
    def test_get_patterns_for_trigger(self, module):
        """Test getting patterns for a specific trigger."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "learned_patterns": [
                {"pattern_id": "movie_mode:dim_lights", "trigger": "movie_mode", "action": "dim_lights"},
                {"pattern_id": "movie_mode:set_temp", "trigger": "movie_mode", "action": "set_temperature"},
                {"pattern_id": "sleep_mode:off_lights", "trigger": "sleep_mode", "action": "turn_off_lights"},
            ],
        }
        
        patterns = module.get_patterns_for_trigger("person.test_user", "movie_mode")
        
        assert len(patterns) == 2
        assert all(p["trigger"] == "movie_mode" for p in patterns)
    
    def test_get_confirmed_patterns(self, module):
        """Test getting confirmed patterns."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "learned_patterns": [
                {"pattern_id": "p1", "confirmed": True},
                {"pattern_id": "p2", "confirmed": False},
                {"pattern_id": "p3", "confirmed": True},
            ],
        }
        
        patterns = module.get_confirmed_patterns("person.test_user")
        
        assert len(patterns) == 2
        assert all(p["confirmed"] for p in patterns)
    
    def test_get_suggestion_weight_neutral(self, module):
        """Test suggestion weight for unknown user."""
        weight = module.get_suggestion_weight("person.unknown", "energy_saving")
        assert weight == 1.0
    
    def test_get_suggestion_weight_energy_saving(self, module):
        """Test suggestion weight for energy saving with frugality preference."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "preferences": {"frugality": 0.8},
        }
        
        weight = module.get_suggestion_weight("person.test_user", "energy_saving")
        assert weight == 0.5 + 0.8  # 1.3
    
    def test_get_suggestion_weight_comfort(self, module):
        """Test suggestion weight for comfort preference."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "preferences": {"comfort": 0.9},
        }
        
        weight = module.get_suggestion_weight("person.test_user", "comfort")
        assert weight == 0.5 + 0.9  # 1.4
    
    @pytest.mark.asyncio
    async def test_record_mood(self, module):
        """Test recording mood observation."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "mood_history": [],
        }
        
        await module.record_mood(
            "person.test_user",
            "wohnbereich",
            {"comfort": 0.8, "joy": 0.6, "frugality": 0.3},
            0.9
        )
        
        mood_history = module._data["users"]["person.test_user"]["mood_history"]
        assert len(mood_history) == 1
        assert mood_history[0]["zone"] == "wohnbereich"
        assert mood_history[0]["mood"]["comfort"] == 0.8
        assert mood_history[0]["confidence"] == 0.9
    
    @pytest.mark.asyncio
    async def test_record_mood_limits_history(self, module):
        """Test that mood history is limited to 100 entries."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "mood_history": [{"timestamp": f"2026-02-15T{i:02d}:00"} for i in range(100)],
        }
        
        await module.record_mood("person.test_user", "wohnbereich", {"comfort": 0.5})
        
        mood_history = module._data["users"]["person.test_user"]["mood_history"]
        assert len(mood_history) == 100  # Still 100 after adding one
    
    def test_get_recent_moods(self, module):
        """Test getting recent mood history."""
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "mood_history": [{"timestamp": f"2026-02-15T{i:02d}:00"} for i in range(20)],
        }
        
        recent = module.get_recent_moods("person.test_user", limit=5)
        assert len(recent) == 5
    
    def test_get_summary(self, module):
        """Test module summary."""
        module._tracked_users.add("person.user1")
        module._tracked_users.add("person.user2")
        module._active_user = "person.user1"
        module._active_zone = "wohnbereich"
        module._learning_enabled = True
        module._data["users"] = {"person.user1": {}, "person.user2": {}}
        module._data["config"]["primary_user"] = "person.user1"
        
        summary = module.get_summary()
        
        assert len(summary["tracked_users"]) == 2
        assert summary["active_user"] == "person.user1"
        assert summary["active_zone"] == "wohnbereich"
        assert summary["learning_enabled"] is True
        assert summary["total_users"] == 2
        assert summary["primary_user"] == "person.user1"
    
    def test_set_learning_enabled(self, module):
        """Test setting learning enabled/disabled."""
        module.set_learning_enabled(False)
        assert module._learning_enabled is False
        assert module._data["config"]["learning_enabled"] is False
        
        module.set_learning_enabled(True)
        assert module._learning_enabled is True
        assert module._data["config"]["learning_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_learn_pattern_disabled_when_learning_off(self, module):
        """Test that learn_pattern does nothing when learning is disabled."""
        module.set_learning_enabled(False)
        module._data["users"]["person.test_user"] = {
            "user_id": "person.test_user",
            "learned_patterns": [],
        }
        
        pattern_id = await module.learn_pattern("person.test_user", "trigger", "action")
        
        assert pattern_id == ""
        assert len(module._data["users"]["person.test_user"]["learned_patterns"]) == 0


class TestUserPreferenceDataClasses:
    """Test cases for data classes."""
    
    def test_user_preference_defaults(self):
        """Test UserPreference default values."""
        pref = UserPreference(user_id="person.test")
        
        assert pref.user_id == "person.test"
        assert pref.display_name == ""
        assert "light_brightness_default" in pref.preferences
        assert pref.preferences["light_brightness_default"] == 0.7
        assert pref.learned_patterns == []
        assert pref.mood_history == []
    
    def test_learned_pattern_defaults(self):
        """Test LearnedPattern default values."""
        pattern = LearnedPattern(
            pattern_id="test:pattern",
            trigger="test",
            action="pattern"
        )
        
        assert pattern.pattern_id == "test:pattern"
        assert pattern.trigger == "test"
        assert pattern.action == "pattern"
        assert pattern.context == {}
        assert pattern.confidence == 0.0
        assert pattern.occurrences == 1
        assert pattern.confirmed is False