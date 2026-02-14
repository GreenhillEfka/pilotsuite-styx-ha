"""Unit tests for MoodContextModule."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Note: This test mocks HA components since we're testing in isolation
def mock_async_get_clientsession(hass):
    """Mock Home Assistant's async_get_clientsession."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_mood_context_initialization():
    """Test MoodContextModule initialization."""
    # Mock hass
    hass = MagicMock()
    
    # Would normally import and test, but avoiding HA dependency in this test
    # Just validate the module structure exists
    from custom_components.ai_home_copilot.core.modules.mood_context_module import MoodContextModule
    
    module = MoodContextModule(
        hass=hass,
        core_api_base_url="http://localhost:8099",
        api_token="test_token"
    )
    
    assert module.core_api_base_url == "http://localhost:8099"
    assert module.api_token == "test_token"
    assert module._zone_moods == {}
    assert module._last_update is None
    assert module._polling_interval_seconds == 30


@pytest.mark.asyncio
async def test_mood_should_suppress_energy_saving():
    """Test energy-saving suppression logic."""
    from custom_components.ai_home_copilot.core.modules.mood_context_module import MoodContextModule
    
    hass = MagicMock()
    module = MoodContextModule(hass, "http://localhost:8099", "token")
    
    # Case 1: Joy > 0.6 should suppress energy-saving
    module._zone_moods["living_room"] = {
        "zone_id": "living_room",
        "comfort": 0.5,
        "frugality": 0.5,
        "joy": 0.7,  # Entertainment happening
        "media_active": True,
        "time_of_day": "evening"
    }
    
    assert module.should_suppress_energy_saving("living_room") is True, \
        "Should suppress energy-saving when joy > 0.6"
    
    # Case 2: High comfort + low frugality should suppress
    module._zone_moods["bedroom"] = {
        "zone_id": "bedroom",
        "comfort": 0.8,  # User prioritizes comfort
        "frugality": 0.3,  # User doesn't prioritize efficiency
        "joy": 0.4,
        "media_active": False,
        "time_of_day": "night"
    }
    
    assert module.should_suppress_energy_saving("bedroom") is True, \
        "Should suppress energy-saving when comfort > 0.7 and frugality < 0.5"
    
    # Case 3: Low joy + high frugality = OK to suggest energy-saving
    module._zone_moods["kitchen"] = {
        "zone_id": "kitchen",
        "comfort": 0.4,
        "frugality": 0.8,
        "joy": 0.2,
        "media_active": False,
        "time_of_day": "morning"
    }
    
    assert module.should_suppress_energy_saving("kitchen") is False, \
        "Should allow energy-saving when joy is low and frugality is high"
    
    # Case 4: No mood data for zone
    assert module.should_suppress_energy_saving("unknown_zone") is False, \
        "Should return False (allow energy-saving) if no mood data"


def test_mood_suggestion_context():
    """Test suggestion relevance multiplier calculation."""
    from custom_components.ai_home_copilot.core.modules.mood_context_module import MoodContextModule
    
    hass = MagicMock()
    module = MoodContextModule(hass, "http://localhost:8099", "token")
    
    # Setup zone with specific mood
    module._zone_moods["living_room"] = {
        "zone_id": "living_room",
        "comfort": 0.7,
        "frugality": 0.4,
        "joy": 0.8,  # High entertainment
        "media_active": True,
        "time_of_day": "evening"
    }
    
    context = module.get_suggestion_context("living_room")
    
    # Verify multipliers
    assert "energy_saving" in context
    assert "comfort" in context
    assert "entertainment" in context
    assert "security" in context
    
    # Energy-saving should be low (high joy, low frugality)
    # Expected: max(0, (1 - 0.8) * 0.4) = max(0, 0.2 * 0.4) = 0.08
    assert context["energy_saving"] < 0.2, \
        "Energy-saving multiplier should be low when joy is high"
    
    # Entertainment should be high (joy = 0.8)
    assert context["entertainment"] > 0.7, \
        "Entertainment multiplier should match high joy"
    
    # Comfort should be 0.7
    assert context["comfort"] == 0.7, \
        "Comfort multiplier should match comfort value"
    
    # Security should always be 1.0
    assert context["security"] == 1.0, \
        "Security multiplier should always be 1.0"
    
    # Raw mood should be included
    assert "raw_mood" in context
    assert context["raw_mood"]["joy"] == 0.8


def test_mood_summary():
    """Test summary generation across zones."""
    from custom_components.ai_home_copilot.core.modules.mood_context_module import MoodContextModule
    
    hass = MagicMock()
    module = MoodContextModule(hass, "http://localhost:8099", "token")
    
    # Setup multiple zones
    module._zone_moods = {
        "living_room": {
            "comfort": 0.8, "frugality": 0.4, "joy": 0.9,
            "media_active": True, "time_of_day": "evening"
        },
        "bedroom": {
            "comfort": 0.6, "frugality": 0.5, "joy": 0.2,
            "media_active": False, "time_of_day": "night"
        },
        "kitchen": {
            "comfort": 0.5, "frugality": 0.7, "joy": 0.3,
            "media_active": False, "time_of_day": "morning"
        }
    }
    
    summary = module.get_summary()
    
    assert summary["zones_tracked"] == 3
    assert summary["zones_with_media"] == 1
    
    # Verify averages
    avg_comfort = (0.8 + 0.6 + 0.5) / 3  # ≈ 0.63
    avg_frugality = (0.4 + 0.5 + 0.7) / 3  # ≈ 0.53
    avg_joy = (0.9 + 0.2 + 0.3) / 3  # ≈ 0.47
    
    assert abs(summary["average_comfort"] - avg_comfort) < 0.01
    assert abs(summary["average_frugality"] - avg_frugality) < 0.01
    assert abs(summary["average_joy"] - avg_joy) < 0.01


def test_mood_get_zone_mood():
    """Test retrieving specific zone mood."""
    from custom_components.ai_home_copilot.core.modules.mood_context_module import MoodContextModule
    
    hass = MagicMock()
    module = MoodContextModule(hass, "http://localhost:8099", "token")
    
    # Add mood data
    mood_data = {
        "comfort": 0.6,
        "frugality": 0.7,
        "joy": 0.5,
        "media_active": False,
        "time_of_day": "afternoon"
    }
    module._zone_moods["office"] = mood_data
    
    # Retrieve
    retrieved = module.get_zone_mood("office")
    assert retrieved == mood_data
    
    # Non-existent zone
    assert module.get_zone_mood("unknown") is None


def test_mood_empty_state():
    """Test module behavior when no moods are cached."""
    from custom_components.ai_home_copilot.core.modules.mood_context_module import MoodContextModule
    
    hass = MagicMock()
    module = MoodContextModule(hass, "http://localhost:8099", "token")
    
    # Empty state
    assert module.get_all_moods() == {}
    assert module.get_zone_mood("any") is None
    assert module.should_suppress_energy_saving("any") is False
    
    # Summary on empty state
    summary = module.get_summary()
    assert summary["zones_tracked"] == 0
    assert summary["average_comfort"] == 0.5  # Default
    assert summary["average_frugality"] == 0.5  # Default
    assert summary["average_joy"] == 0.5  # Default


if __name__ == "__main__":
    # Run pytest
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
