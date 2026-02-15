"""Tests for User Preference Module."""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from custom_components.ai_home_copilot.core.modules.user_preference_module import (
    UserPreferenceModule,
    UserPreferenceData,
    get_time_period,
    TimePeriod,
)


class TestUserPreferenceData:
    """Tests for UserPreferenceData class."""
    
    def test_init_default(self):
        """Test default initialization."""
        user = UserPreferenceData("efka")
        assert user.user_id == "efka"
        assert user.display_name == "Efka"
        assert user.device_tracker is None
        assert "light_brightness" in user.preferences
        assert user.preferences["light_brightness"]["evening"] == 0.4
        assert user.zones_frequented == []
        assert user.learned_patterns == []
    
    def test_init_with_data(self):
        """Test initialization with provided data."""
        data = {
            "display_name": "Test User",
            "device_tracker": "device_tracker.test",
            "preferences": {"preferred_temp": 22.0},
            "zones_frequented": ["living_room"],
            "learned_patterns": [{"trigger": "sunset", "action": {"type": "dim_lights"}}],
        }
        user = UserPreferenceData("test", data)
        assert user.display_name == "Test User"
        assert user.device_tracker == "device_tracker.test"
        assert user.preferences["preferred_temp"] == 22.0
        assert user.zones_frequented == ["living_room"]
        assert len(user.learned_patterns) == 1
    
    def test_to_dict(self):
        """Test serialization."""
        user = UserPreferenceData("efka")
        user.set_preference("test_key", "test_value")
        user.record_zone_visit("wohnbereich")
        
        d = user.to_dict()
        assert d["user_id"] == "efka"
        assert d["preferences"]["test_key"] == "test_value"
        assert "wohnbereich" in d["zones_frequented"]
        assert d["last_seen_zone"] == "wohnbereich"
    
    def test_set_preference(self):
        """Test setting preferences."""
        user = UserPreferenceData("efka")
        user.set_preference("music_genre", "rock")
        assert user.preferences["music_genre"] == "rock"
    
    def test_get_preference(self):
        """Test getting preferences."""
        user = UserPreferenceData("efka")
        user.set_preference("preferred_temp", 22.0)
        assert user.get_preference("preferred_temp") == 22.0
        assert user.get_preference("nonexistent", "default") == "default"
    
    def test_record_zone_visit(self):
        """Test zone visit tracking."""
        user = UserPreferenceData("efka")
        
        user.record_zone_visit("wohnbereich")
        assert "wohnbereich" in user.zones_frequented
        assert user.last_seen_zone == "wohnbereich"
        assert user.last_seen_time is not None
        
        user.record_zone_visit("buero")
        assert "buero" in user.zones_frequented
        assert user.last_seen_zone == "buero"


class TestTimePeriod:
    """Tests for time period determination."""
    
    def test_morning(self):
        """Test morning period (5-10)."""
        dt = datetime(2024, 1, 15, 8, 0)  # 8 AM
        assert get_time_period(dt) == TimePeriod.MORNING
        
        dt = datetime(2024, 1, 15, 5, 30)  # 5:30 AM
        assert get_time_period(dt) == TimePeriod.MORNING
    
    def test_day(self):
        """Test day period (10-18)."""
        dt = datetime(2024, 1, 15, 12, 0)  # Noon
        assert get_time_period(dt) == TimePeriod.DAY
        
        dt = datetime(2024, 1, 15, 15, 30)  # 3:30 PM
        assert get_time_period(dt) == TimePeriod.DAY
    
    def test_evening(self):
        """Test evening period (18-22)."""
        dt = datetime(2024, 1, 15, 19, 0)  # 7 PM
        assert get_time_period(dt) == TimePeriod.EVENING
        
        dt = datetime(2024, 1, 15, 21, 30)  # 9:30 PM
        assert get_time_period(dt) == TimePeriod.EVENING
    
    def test_night(self):
        """Test night period (22-5)."""
        dt = datetime(2024, 1, 15, 23, 0)  # 11 PM
        assert get_time_period(dt) == TimePeriod.NIGHT
        
        dt = datetime(2024, 1, 15, 3, 0)  # 3 AM
        assert get_time_period(dt) == TimePeriod.NIGHT
        
        dt = datetime(2024, 1, 15, 0, 0)  # Midnight
        assert get_time_period(dt) == TimePeriod.NIGHT


class TestUserPreferenceModule:
    """Tests for UserPreferenceModule class."""
    
    def test_name_property(self):
        """Test module name."""
        module = UserPreferenceModule()
        assert module.name == "user_preference"
    
    @pytest.mark.asyncio
    async def test_get_zone_occupancy(self):
        """Test zone occupancy retrieval."""
        module = UserPreferenceModule()
        module_data = {
            "zone_occupancy": {
                "wohnbereich": ["efka"],
                "schlafbereich": [],
            }
        }
        
        occupancy = module.get_zone_occupancy(module_data)
        assert occupancy["wohnbereich"] == ["efka"]
        assert occupancy["schlafbereich"] == []
    
    @pytest.mark.asyncio
    async def test_get_users_in_zone(self):
        """Test getting users in a zone."""
        module = UserPreferenceModule()
        module_data = {
            "zone_occupancy": {
                "wohnbereich": ["efka", "partner"],
                "buero": ["efka"],
            }
        }
        
        users = module.get_users_in_zone(module_data, "wohnbereich")
        assert "efka" in users
        assert "partner" in users
        
        buero_users = module.get_users_in_zone(module_data, "buero")
        assert buero_users == ["efka"]
    
    def test_get_user_preference(self):
        """Test getting user preference."""
        module = UserPreferenceModule()
        user = UserPreferenceData("efka")
        user.set_preference("preferred_temp", 22.5)
        
        module_data = {"users": {"efka": user}}
        
        pref = module.get_user_preference(module_data, "efka", "preferred_temp")
        assert pref == 22.5
        
        # Non-existent user
        pref = module.get_user_preference(module_data, "nonexistent", "test", "default")
        assert pref == "default"
    
    def test_get_time_context_for_user(self):
        """Test getting time-contextualized preferences."""
        module = UserPreferenceModule()
        user = UserPreferenceData("efka")
        user.set_preference("light_brightness", {"morning": 1.0, "evening": 0.3})
        user.set_preference("preferred_temp", 21.5)
        
        module_data = {"users": {"efka": user}}
        
        # Mock evening time
        with patch('custom_components.ai_home_copilot.core.modules.user_preference_module.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 15, 20, 0)  # 8 PM
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            context = module.get_time_context_for_user(module_data, "efka")
            assert context["time_period"] == "evening"
            assert context["preferences"]["brightness"] == 0.3
    
    def test_get_enrichment_for_mood(self):
        """Test getting mood enrichment data."""
        module = UserPreferenceModule()
        
        user1 = UserPreferenceData("efka")
        user1.set_preference("light_brightness", {"evening": 0.3})
        user1.set_preference("preferred_temp", 21.0)
        
        user2 = UserPreferenceData("partner")
        user2.set_preference("light_brightness", {"evening": 0.5})
        user2.set_preference("preferred_temp", 22.0)
        
        module_data = {
            "users": {"efka": user1, "partner": user2},
            "zone_occupancy": {"wohnbereich": ["efka", "partner"]}
        }
        
        enrichment = module.get_enrichment_for_mood(module_data, "wohnbereich")
        
        assert "efka" in enrichment["users_present"]
        assert "partner" in enrichment["users_present"]
        assert enrichment["aggregated_preferences"]["user_count"] == 2
        # Average brightness: (0.3 + 0.5) / 2 = 0.4
        assert 0.39 < enrichment["aggregated_preferences"]["avg_brightness"] < 0.41
        # Average temp: (21.0 + 22.0) / 2 = 21.5
        assert 21.49 < enrichment["aggregated_preferences"]["avg_temp"] < 21.51
    
    def test_get_all_users(self):
        """Test getting all users."""
        module = UserPreferenceModule()
        user1 = UserPreferenceData("efka")
        user2 = UserPreferenceData("partner")
        
        module_data = {"users": {"efka": user1, "partner": user2}}
        
        users = module.get_all_users(module_data)
        assert len(users) == 2
        assert "efka" in users
        assert "partner" in users


if __name__ == "__main__":
    pytest.main([__file__, "-v"])