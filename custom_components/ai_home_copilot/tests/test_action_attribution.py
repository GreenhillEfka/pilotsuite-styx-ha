"""Tests for Multi-User Preference Learning Action Attribution"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from custom_components.ai_home_copilot.core.mupl.action_attribution import (
    ActionAttributor,
    AttributionResult,
    UserAction,
    PresenceAttribution,
    DeviceOwnershipAttribution,
    TimePatternAttribution,
)


class TestPresenceAttribution:
    """Tests for presence-based attribution"""
    
    @pytest.fixture
    def hass(self):
        """Mock Home Assistant instance"""
        hass = Mock()
        hass.states = Mock()
        return hass
    
    @pytest.mark.asyncio
    async def test_single_user_present(self, hass):
        """Test attribution when only one user is home"""
        presence_entities = {"user_a": "person.user_a", "user_b": "person.user_b"}
        
        hass.states.get = Mock(side_effect=lambda entity_id: 
            Mock(state="home") if entity_id == "person.user_a" 
            else Mock(state="away"))
        
        source = PresenceAttribution(hass, presence_entities)
        result = await source.get_attribution(hass, "light.test", "turn_on")
        
        assert result is not None
        assert result.user_id == "user_a"
        assert result.confidence == 0.4
        assert result.sources.get("presence") == 0.4
    
    @pytest.mark.asyncio
    async def test_multiple_users_present(self, hass):
        """Test attribution when multiple users are home"""
        presence_entities = {"user_a": "person.user_a", "user_b": "person.user_b"}
        
        hass.states.get = Mock(return_value=Mock(state="home"))
        
        source = PresenceAttribution(hass, presence_entities)
        result = await source.get_attribution(hass, "light.test", "turn_on")
        
        assert result is not None
        assert result.confidence == 0.2  # Lower confidence for multiple users
        assert "multiple_present" in result.sources
    
    @pytest.mark.asyncio
    async def test_no_users_present(self, hass):
        """Test attribution when no one is home"""
        presence_entities = {"user_a": "person.user_a"}
        
        hass.states.get = Mock(return_value=Mock(state="away"))
        
        source = PresenceAttribution(hass, presence_entities)
        result = await source.get_attribution(hass, "light.test", "turn_on")
        
        assert result is None


class TestDeviceOwnershipAttribution:
    """Tests for device ownership attribution"""
    
    @pytest.fixture
    def hass(self):
        return Mock()
    
    @pytest.mark.asyncio
    async def test_owned_device(self, hass):
        """Test attribution for owned device"""
        device_owners = {"light.user_a_desk": "user_a", "light.user_b_desk": "user_b"}
        
        source = DeviceOwnershipAttribution(hass, device_owners)
        result = await source.get_attribution(hass, "light.user_a_desk", "turn_on")
        
        assert result is not None
        assert result.user_id == "user_a"
        assert result.confidence == 0.3
    
    @pytest.mark.asyncio
    async def test_unowned_device(self, hass):
        """Test attribution for unowned device"""
        device_owners = {"light.user_a_desk": "user_a"}
        
        source = DeviceOwnershipAttribution(hass, device_owners)
        result = await source.get_attribution(hass, "light.kitchen", "turn_on")
        
        assert result is None


class TestTimePatternAttribution:
    """Tests for time pattern attribution"""
    
    @pytest.fixture
    def hass(self):
        return Mock()
    
    @pytest.mark.asyncio
    async def test_morning_pattern(self, hass):
        """Test attribution based on morning pattern"""
        time_patterns = {
            "light.bedroom": {
                "morning": "user_a",
                "evening": "user_b"
            }
        }
        
        with patch('custom_components.ai_home_copilot.core.mupl.action_attribution.dt_util') as mock_dt:
            mock_dt.utcnow.return_value = datetime(2026, 2, 15, 7, 0)  # 7 AM
            
            source = TimePatternAttribution(hass, time_patterns)
            result = await source.get_attribution(hass, "light.bedroom", "turn_on")
            
            assert result is not None
            assert result.user_id == "user_a"
            assert result.sources.get("time_of_day") == "morning"
    
    @pytest.mark.asyncio
    async def test_no_pattern_for_entity(self, hass):
        """Test when no pattern exists for entity"""
        time_patterns = {"light.other": {"morning": "user_a"}}
        
        source = TimePatternAttribution(hass, time_patterns)
        result = await source.get_attribution(hass, "light.bedroom", "turn_on")
        
        assert result is None


class TestActionAttributor:
    """Tests for the main ActionAttributor class"""
    
    @pytest.fixture
    def hass(self):
        hass = Mock()
        hass.states = Mock()
        hass.data = {}
        return hass
    
    @pytest.mark.asyncio
    async def test_combine_multiple_sources(self, hass):
        """Test combining attributions from multiple sources"""
        config = {
            "presence_entities": {"user_a": "person.user_a"},
            "device_owners": {"light.test": "user_a"},
            "max_history": 100
        }
        
        hass.states.get = Mock(return_value=Mock(state="home"))
        
        attributor = ActionAttributor(hass, config)
        await attributor.async_setup()
        
        result = await attributor.attribute_action("light.test", "turn_on")
        
        assert result is not None
        assert result.user_id == "user_a"
        # Combined confidence from presence + device ownership
        assert result.confidence >= 0.5
    
    @pytest.mark.asyncio
    async def test_action_history(self, hass):
        """Test that actions are stored in history"""
        config = {"max_history": 10}
        
        attributor = ActionAttributor(hass, config)
        await attributor.async_setup()
        
        # Manually add sources for testing
        from custom_components.ai_home_copilot.core.mupl.action_attribution import (
            DeviceOwnershipAttribution
        )
        attributor.sources.append(
            DeviceOwnershipAttribution(hass, {"light.test": "user_a"})
        )
        
        await attributor.attribute_action("light.test", "turn_on")
        
        history = attributor.get_action_history()
        assert len(history) == 1
        assert history[0].user_id == "user_a"
        assert history[0].entity_id == "light.test"
    
    @pytest.mark.asyncio
    async def test_max_history_limit(self, hass):
        """Test that history is limited to max_history"""
        config = {"max_history": 5}
        
        attributor = ActionAttributor(hass, config)
        await attributor.async_setup()
        
        # Manually add sources
        from custom_components.ai_home_copilot.core.mupl.action_attribution import (
            DeviceOwnershipAttribution
        )
        attributor.sources.append(
            DeviceOwnershipAttribution(hass, {f"light.{i}": "user_a" for i in range(10)})
        )
        
        # Add 10 actions
        for i in range(10):
            await attributor.attribute_action(f"light.{i}", "turn_on")
        
        history = attributor.get_action_history()
        assert len(history) == 5  # Limited to max_history