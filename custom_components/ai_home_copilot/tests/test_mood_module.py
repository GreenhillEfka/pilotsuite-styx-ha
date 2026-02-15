"""Tests for Mood Module v0.2."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime

import sys
import os

# Add custom_components to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import DOMAIN
from custom_components.ai_home_copilot.const import DOMAIN


class TestMoodModule:
    """Test suite for MoodModule."""

    @pytest.fixture
    def mock_hass(self):
        """Create mock Home Assistant instance."""
        hass = MagicMock()
        hass.data = {}
        
        # Mock states.get
        mock_state = MagicMock()
        mock_state.state = "on"
        mock_state.attributes = {"brightness": 255}
        mock_state.last_changed = datetime.now()
        mock_state.last_updated = datetime.now()
        hass.states.get.return_value = mock_state
        
        # Mock services
        hass.services = MagicMock()
        hass.services.has_service.return_value = False
        
        return hass

    @pytest.fixture
    def mock_entry(self):
        """Create mock ConfigEntry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        return entry

    @pytest.fixture
    def mock_ctx(self, mock_hass, mock_entry):
        """Create mock ModuleContext."""
        from custom_components.ai_home_copilot.core.module import ModuleContext
        return ModuleContext(hass=mock_hass, entry=mock_entry)

    def test_module_name(self):
        """Test that module returns correct name."""
        from custom_components.ai_home_copilot.core.modules.mood_module import MoodModule
        
        module = MoodModule()
        assert module.name == "mood_module"

    @pytest.mark.asyncio
    async def test_async_setup_entry(self, mock_ctx):
        """Test module setup initializes correctly."""
        from custom_components.ai_home_copilot.core.modules.mood_module import MoodModule
        
        module = MoodModule()
        result = await module.async_setup_entry(mock_ctx)
        
        assert result is True
        assert "mood_module" in mock_ctx.hass.data[DOMAIN][mock_ctx.entry.entry_id]
        
        # Verify config was created
        mood_data = mock_ctx.hass.data[DOMAIN][mock_ctx.entry.entry_id]["mood_module"]
        assert "config" in mood_data
        assert "zones" in mood_data["config"]

    @pytest.mark.asyncio
    async def test_async_unload_entry(self, mock_ctx):
        """Test module cleanup on unload."""
        from custom_components.ai_home_copilot.core.modules.mood_module import MoodModule
        
        module = MoodModule()
        
        # First setup
        await module.async_setup_entry(mock_ctx)
        
        # Then unload
        result = await module.async_unload_entry(mock_ctx)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_orchestrate_zone(self, mock_ctx):
        """Test zone orchestration."""
        from custom_components.ai_home_copilot.core.modules.mood_module import MoodModule
        
        module = MoodModule()
        await module.async_setup_entry(mock_ctx)
        
        # Should not raise
        await module._orchestrate_zone(
            mock_ctx.hass, 
            mock_ctx.entry.entry_id, 
            "wohnbereich",
            dry_run=True
        )

    @pytest.mark.asyncio
    async def test_orchestrate_all_zones(self, mock_ctx):
        """Test all zones orchestration."""
        from custom_components.ai_home_copilot.core.modules.mood_module import MoodModule
        
        module = MoodModule()
        await module.async_setup_entry(mock_ctx)
        
        # Should not raise
        await module._orchestrate_all_zones(
            mock_ctx.hass,
            mock_ctx.entry.entry_id,
            dry_run=True
        )

    @pytest.mark.asyncio
    async def test_collect_sensor_data(self, mock_ctx):
        """Test sensor data collection."""
        from custom_components.ai_home_copilot.core.modules.mood_module import MoodModule
        
        module = MoodModule()
        await module.async_setup_entry(mock_ctx)
        
        zone_config = {
            "motion_entities": ["binary_sensor.motion_wohnzimmer"],
            "light_entities": ["light.wohnzimmer"],
            "media_entities": ["media_player.wohnbereich"],
            "illuminance_entity": "sensor.illuminance_wohnzimmer"
        }
        
        sensor_data = await module._collect_sensor_data(mock_ctx.hass, zone_config)
        
        # Should have collected some data
        assert isinstance(sensor_data, dict)

    @pytest.mark.asyncio
    async def test_force_mood(self, mock_ctx):
        """Test force mood functionality."""
        from custom_components.ai_home_copilot.core.modules.mood_module import MoodModule
        
        module = MoodModule()
        await module.async_setup_entry(mock_ctx)
        
        # Should not raise
        await module._force_mood(
            mock_ctx.hass,
            mock_ctx.entry.entry_id,
            "wohnbereich",
            "focus",
            duration_minutes=30
        )

    def test_default_config(self, mock_hass):
        """Test default configuration creation."""
        from custom_components.ai_home_copilot.core.modules.mood_module import MoodModule
        
        module = MoodModule()
        config = module._create_default_config(mock_hass)
        
        assert "zones" in config
        assert "min_dwell_time_seconds" in config
        assert config["min_dwell_time_seconds"] == 600

    def test_config_validation(self):
        """Test configuration validation."""
        from custom_components.ai_home_copilot.core.modules.mood_module import MoodModule
        
        module = MoodModule()
        
        # Valid config
        valid_config = {
            "zones": {
                "test_zone": {
                    "motion_entities": ["sensor.motion"],
                    "light_entities": ["light.test"],
                    "media_entities": ["media_player.test"]
                }
            }
        }
        
        # Should not raise
        module._validate_config(valid_config)


class TestMoodModuleCharacterIntegration:
    """Test character system integration."""

    @pytest.mark.asyncio
    async def test_character_service_connection(self):
        """Test that character service can be connected."""
        from custom_components.ai_home_copilot.core.modules.mood_module import MoodModule
        from custom_components.ai_home_copilot.core.character.service import CharacterService
        
        # Create mock with character service
        mock_hass = MagicMock()
        mock_hass.data = {
            "ai_home_copilot": {
                "test_entry": {
                    "character_service": CharacterService()
                }
            }
        }
        
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry"
        
        from custom_components.ai_home_copilot.core.module import ModuleContext
        ctx = ModuleContext(hass=mock_hass, entry=mock_entry)
        
        module = MoodModule()
        await module._init_character_service(ctx)
        
        # Character service should be connected
        assert module._character_service is not None


class TestMoodModuleErrors:
    """Test error handling."""

    @pytest.fixture
    def mock_hass_error(self):
        """Create mock HA with error conditions."""
        hass = MagicMock()
        hass.data = {}  # Empty data to trigger errors
        hass.states.get.return_value = None
        return hass

    @pytest.mark.asyncio
    async def test_orchestrate_invalid_zone(self):
        """Test handling of invalid zone name."""
        from custom_components.ai_home_copilot.core.modules.mood_module import MoodModule
        from custom_components.ai_home_copilot.core.module import ModuleContext
        
        mock_hass = MagicMock()
        mock_hass.data = {}
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_123"
        mock_hass.data[DOMAIN] = {mock_entry.entry_id: {"mood_module": {
            "config": {"zones": {"wohnbereich": {}}},
            "tracked_entities": [],
            "last_orchestration": {},
            "polling_unsub": None,
            "event_unsubs": []
        }}}
        
        ctx = ModuleContext(hass=mock_hass, entry=mock_entry)
        
        module = MoodModule()
        module._hass = mock_hass
        module._entry_id = mock_entry.entry_id
        
        # Should handle gracefully
        await module._orchestrate_zone(
            mock_hass,
            mock_entry.entry_id,
            "invalid_zone_name",
            dry_run=True
        )

    @pytest.mark.asyncio
    async def test_unload_not_initialized(self):
        """Test unload when module not initialized."""
        from custom_components.ai_home_copilot.core.modules.mood_module import MoodModule
        from custom_components.ai_home_copilot.core.module import ModuleContext
        
        module = MoodModule()
        # Don't set _hass or _entry_id to simulate uninitialized state
        
        mock_hass = MagicMock()
        # Empty data simulates module never having been set up
        mock_hass.data = {}  
        mock_entry = MagicMock()
        mock_entry.entry_id = "test"
        
        ctx = ModuleContext(hass=mock_hass, entry=mock_entry)
        
        # When no mood_module data exists, returns True (successful cleanup of nothing)
        # This is correct behavior - nothing to clean up
        result = await module.async_unload_entry(ctx)
        assert result is True


# Run tests with: python -m pytest tests/test_mood_module.py -v
