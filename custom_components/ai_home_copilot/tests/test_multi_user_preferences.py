"""Tests for Multi-User Preference Learning Module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from custom_components.ai_home_copilot.multi_user_preferences import (
    MultiUserPreferenceModule,
    UserPreferences,
    DeviceAffinity,
    get_mupl_module,
    set_mupl_module,
)


class TestUserPreferences:
    """Tests for UserPreferences dataclass."""

    def test_default_preferences(self):
        """Test default preference structure."""
        user = UserPreferences(user_id="person.test")
        
        assert user.user_id == "person.test"
        assert user.name == "Unknown"
        assert "light_brightness" in user.preferences
        assert "media_volume" in user.preferences
        assert "temperature" in user.preferences
        assert "mood_weights" in user.preferences
        assert user.interaction_count == 0
        assert user.priority == 0.5

    def test_custom_preferences(self):
        """Test custom preference values."""
        user = UserPreferences(
            user_id="person.test",
            name="Test User",
            preferences={"light_brightness": {"default": 0.6}},
            priority=0.8,
        )
        
        assert user.name == "Test User"
        assert user.preferences["light_brightness"]["default"] == 0.6
        assert user.priority == 0.8


class TestDeviceAffinity:
    """Tests for DeviceAffinity dataclass."""

    def test_default_affinity(self):
        """Test default device affinity."""
        aff = DeviceAffinity(entity_id="light.test")
        
        assert aff.entity_id == "light.test"
        assert aff.primary_user is None
        assert aff.usage_distribution == {}

    def test_affinity_with_users(self):
        """Test device affinity with user distribution."""
        aff = DeviceAffinity(
            entity_id="light.test",
            primary_user="person.test",
            usage_distribution={"person.test": 0.8, "person.other": 0.2},
        )
        
        assert aff.primary_user == "person.test"
        assert aff.usage_distribution["person.test"] == 0.8


class TestMultiUserPreferenceModule:
    """Tests for MultiUserPreferenceModule."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = MagicMock()
        hass.data = {}
        hass.states = MagicMock()
        hass.states.get = MagicMock(return_value=None)
        hass.states.async_all = MagicMock(return_value=[])
        hass.async_create_task = MagicMock()
        return hass

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry"
        entry.options = {
            "mupl_enabled": True,
            "mupl_privacy_mode": "opt-in",
        }
        return entry

    def test_module_initialization(self, mock_hass, mock_config_entry):
        """Test module initialization."""
        module = MultiUserPreferenceModule(mock_hass, mock_config_entry)
        
        assert module.hass == mock_hass
        assert module._enabled is True
        assert module._privacy_mode == "opt-in"
        assert module._users == {}
        assert module._device_affinities == {}

    @pytest.mark.asyncio
    async def test_discover_persons(self, mock_hass, mock_config_entry):
        """Test person discovery."""
        # Mock person entities
        person1 = MagicMock()
        person1.entity_id = "person.test"
        person1.attributes = {"friendly_name": "Test User"}
        
        person2 = MagicMock()
        person2.entity_id = "person.other"
        person2.attributes = {"friendly_name": "Other User"}
        
        mock_hass.states.async_all = MagicMock(return_value=[person1, person2])
        
        module = MultiUserPreferenceModule(mock_hass, mock_config_entry)
        
        # Mock storage
        with patch.object(module._store, "async_load", return_value=None):
            with patch.object(module._store, "async_save"):
                await module._async_discover_persons()
        
        assert "person.test" in module._users
        assert "person.other" in module._users
        assert module._users["person.test"].name == "Test User"

    def test_get_user_name(self, mock_hass, mock_config_entry):
        """Test getting user name."""
        module = MultiUserPreferenceModule(mock_hass, mock_config_entry)
        module._users["person.test"] = UserPreferences(
            user_id="person.test",
            name="Test User",
        )
        
        assert module.get_user_name("person.test") == "Test User"
        assert module.get_user_name("person.unknown") == "person.unknown"

    def test_get_aggregated_mood_single_user(self, mock_hass, mock_config_entry):
        """Test mood aggregation with single user."""
        module = MultiUserPreferenceModule(mock_hass, mock_config_entry)
        module._users["person.test"] = UserPreferences(
            user_id="person.test",
            preferences={"mood_weights": {"comfort": 0.7, "frugality": 0.3, "joy": 0.5}},
        )
        
        mood = module.get_aggregated_mood(["person.test"])
        
        assert mood["comfort"] == 0.7
        assert mood["frugality"] == 0.3
        assert mood["joy"] == 0.5

    def test_get_aggregated_mood_multiple_users(self, mock_hass, mock_config_entry):
        """Test mood aggregation with multiple users."""
        module = MultiUserPreferenceModule(mock_hass, mock_config_entry)
        module._users["person.test"] = UserPreferences(
            user_id="person.test",
            priority=0.8,
            preferences={"mood_weights": {"comfort": 0.8, "frugality": 0.2, "joy": 0.6}},
        )
        module._users["person.other"] = UserPreferences(
            user_id="person.other",
            priority=0.4,
            preferences={"mood_weights": {"comfort": 0.4, "frugality": 0.6, "joy": 0.3}},
        )
        
        mood = module.get_aggregated_mood(["person.test", "person.other"])
        
        # Weighted average: (0.8*0.8 + 0.4*0.4) / (0.8+0.4) = 0.667
        assert 0.6 < mood["comfort"] < 0.7
        assert mood["frugality"] > 0.3
        assert mood["joy"] > 0.4

    def test_get_aggregated_mood_empty(self, mock_hass, mock_config_entry):
        """Test mood aggregation with no users."""
        module = MultiUserPreferenceModule(mock_hass, mock_config_entry)
        
        mood = module.get_aggregated_mood([])
        
        assert mood == {"comfort": 0.5, "frugality": 0.5, "joy": 0.5}


class TestModuleAccessors:
    """Tests for module accessor helpers."""

    def test_set_and_get_mupl_module(self):
        """Test setting and getting MUPL module."""
        from custom_components.ai_home_copilot.multi_user_preferences import (
            _MUPL_MODULE_KEY,
            DOMAIN,
        )
        
        hass = MagicMock()
        hass.data = {
            DOMAIN: {
                "test_entry": {},
            }
        }
        
        module = MagicMock()
        set_mupl_module(hass, "test_entry", module)
        
        assert _MUPL_MODULE_KEY in hass.data[DOMAIN]["test_entry"]
        assert get_mupl_module(hass) == module

    def test_get_mupl_module_not_found(self):
        """Test getting MUPL module when not set."""
        hass = MagicMock()
        hass.data = {}
        
        result = get_mupl_module(hass)
        
        assert result is None