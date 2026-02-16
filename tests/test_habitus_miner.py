"""Tests for Habitus Miner Module.

These tests require Home Assistant to be installed because the module
uses HA's core modules.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from collections import deque

# Mark as integration test
pytestmark = pytest.mark.integration

import sys
sys.path.insert(0, '/config/.openclaw/workspace/ai_home_copilot_hacs_repo/custom_components/ai_home_copilot')

# Skip if HA not installed
try:
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry
    from ai_home_copilot.const import DOMAIN
    from ai_home_copilot.core.modules.habitus_miner import (
        HabitusMinerModule,
        ModuleData,
        HabitusRule,
        HabitusConfig,
    )
except ImportError:
    pytest.skip("Home Assistant not installed", allow_module_level=True)


class TestHabitusMinerModule:
    """Tests for the HabitusMinerModule class."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock()
        hass.data = {}
        hass.bus = MagicMock()
        hass.bus.async_fire = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_entries = MagicMock(return_value=[])
        return hass

    @pytest.fixture
    def mock_entry(self):
        """Create a mock ConfigEntry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_123"
        entry.data = {
            "core_url": "http://localhost:8099",
            "access_token": "test_token"
        }
        return entry

    @pytest.fixture
    def mock_ctx(self, mock_hass, mock_entry):
        """Create a mock ModuleContext."""
        ctx = MagicMock()
        ctx.hass = mock_hass
        ctx.entry = mock_entry
        return ctx

    @pytest.fixture
    def module(self):
        """Create a HabitusMinerModule instance."""
        return HabitusMinerModule()

    def test_module_name(self, module):
        """Test that module has correct name."""
        assert module.name == "habitus_miner"

    @pytest.mark.asyncio
    async def test_async_setup_entry(self, module, mock_ctx):
        """Test module setup."""
        # Mock services.has_service to return False
        with patch('homeassistant.core.HomeAssistant.services') as mock_services:
            mock_services.has_service = MagicMock(return_value=False)
            
            result = await module.async_setup_entry(mock_ctx)
            
            assert result is True
            assert "habitus_miner" in mock_ctx.hass.data[DOMAIN][mock_ctx.entry.entry_id]

    @pytest.mark.asyncio
    async def test_async_setup_registers_services(self, module, mock_ctx):
        """Test that services are registered on setup."""
        # Mock services on the hass instance directly
        mock_ctx.hass.services.has_service = MagicMock(return_value=False)
        mock_ctx.hass.services.async_register = MagicMock()
        
        await module.async_setup_entry(mock_ctx)
        
        # Check that services were registered
        assert mock_ctx.hass.services.async_register.called

    @pytest.mark.asyncio
    async def test_async_unload_entry(self, module, mock_ctx):
        """Test module unload."""
        # First setup
        with patch('homeassistant.core.HomeAssistant.services') as mock_services:
            mock_services.has_service = MagicMock(return_value=False)
            await module.async_setup_entry(mock_ctx)
        
        # Add a listener
        mock_listener = MagicMock()
        module_data = mock_ctx.hass.data[DOMAIN][mock_ctx.entry.entry_id]["habitus_miner"]
        module_data["listeners"].append(mock_listener)
        
        # Mock config_entries
        mock_ctx.hass.config_entries.async_entries = MagicMock(return_value=[])
        
        # Unload
        result = await module.async_unload_entry(mock_ctx)
        
        assert result is True
        assert mock_listener.called

    @pytest.mark.asyncio
    async def test_zone_affinity_initialization(self, module, mock_ctx):
        """Test zone affinity is initialized from zones store."""
        mock_ctx.hass.services.has_service = MagicMock(return_value=False)
        
        # Mock zones store - patch at the source module where async_get_zones is defined
        with patch('ai_home_copilot.habitus_zones_store.async_get_zones', new_callable=AsyncMock) as mock_zones:
            mock_zone = MagicMock()
            mock_zone.zone_id = "zone:wohnzimmer"
            mock_zone.entity_ids = ["light.wohnzimmer", "sensor.temp"]
            mock_zones.return_value = [mock_zone]
            
            await module.async_setup_entry(mock_ctx)
            
            # Zone affinity should be populated
            module_data = mock_ctx.hass.data[DOMAIN][mock_ctx.entry.entry_id]["habitus_miner"]
            assert "light.wohnzimmer" in module_data["zone_affinity"]

    @pytest.mark.asyncio
    async def test_handle_configure_mining_updates_config(self, module, mock_ctx):
        """Test that configuring mining updates config correctly."""
        # Setup first
        with patch('homeassistant.core.HomeAssistant.services') as mock_services:
            mock_services.has_service = MagicMock(return_value=False)
            await module.async_setup_entry(mock_ctx)
        
        # Create a mock service call
        mock_call = MagicMock()
        mock_call.data = {"buffer_max_size": 500, "auto_mining_enabled": True}
        
        # Handle configure
        result = await module._handle_configure_mining(mock_ctx.hass, mock_ctx.entry, mock_call)
        
        assert result is not None
        assert result["success"] is True
        assert "buffer_max_size" in result["updated"]

    @pytest.mark.asyncio
    async def test_handle_reset_cache_clears_data(self, module, mock_ctx):
        """Test that reset cache clears all data."""
        # Setup first - fix the mock path for services
        mock_ctx.hass.services.has_service = MagicMock(return_value=False)
        await module.async_setup_entry(mock_ctx)
        
        # Add some data
        module_data = mock_ctx.hass.data[DOMAIN][mock_ctx.entry.entry_id]["habitus_miner"]
        module_data["event_buffer"].append({"test": "event"})
        module_data["last_mining_ts"] = 12345
        module_data["discovered_rules"] = [{"A": "a", "B": "b"}]
        
        # Mock the coordinator import to avoid HA component issues
        mock_coordinator = MagicMock()
        mock_coordinator.api.post_with_auth = AsyncMock()
        
        with patch.dict('sys.modules', {'ai_home_copilot.coordinator': MagicMock(CopilotDataUpdateCoordinator=lambda *args: mock_coordinator)}):
            # Create mock call
            mock_call = MagicMock()
            mock_call.data = {}
            
            # Reset
            result = await module._handle_reset_cache(mock_ctx.hass, mock_ctx.entry, mock_call)
        
        assert result is not None
        assert result["success"] is True
        assert len(module_data["event_buffer"]) == 0
        assert module_data["last_mining_ts"] is None

    @pytest.mark.asyncio
    async def test_buffer_uses_deque(self, module, mock_ctx):
        """Test that event buffer uses deque for performance."""
        with patch('homeassistant.core.HomeAssistant.services') as mock_services:
            mock_services.has_service = MagicMock(return_value=False)
            await module.async_setup_entry(mock_ctx)
        
        module_data = mock_ctx.hass.data[DOMAIN][mock_ctx.entry.entry_id]["habitus_miner"]
        
        assert isinstance(module_data["event_buffer"], deque)

    @pytest.mark.asyncio
    async def test_get_zone_patterns(self, module, mock_ctx):
        """Test getting patterns for a specific zone."""
        # Setup with some rules
        with patch('homeassistant.core.HomeAssistant.services') as mock_services:
            mock_services.has_service = MagicMock(return_value=False)
            await module.async_setup_entry(mock_ctx)
        
        module_data = mock_ctx.hass.data[DOMAIN][mock_ctx.entry.entry_id]["habitus_miner"]
        module_data["discovered_rules"] = [
            {"A": "zone:wohnzimmer:light.on", "B": "zone:wohnzimmer:media.play", "confidence": 0.8},
            {"A": "zone:schlafzimmer:light.on", "B": "zone:schlafzimmer:media.play", "confidence": 0.6},
        ]
        
        patterns = await module.get_zone_patterns(mock_ctx.hass, mock_ctx.entry.entry_id, "zone:wohnzimmer")
        
        assert len(patterns) == 1
        assert patterns[0]["A"] == "zone:wohnzimmer:light.on"

    @pytest.mark.asyncio
    async def test_get_mood_integration(self, module, mock_ctx):
        """Test mood integration returns relevant patterns."""
        with patch('homeassistant.core.HomeAssistant.services') as mock_services:
            mock_services.has_service = MagicMock(return_value=False)
            await module.async_setup_entry(mock_ctx)
        
        module_data = mock_ctx.hass.data[DOMAIN][mock_ctx.entry.entry_id]["habitus_miner"]
        module_data["discovered_rules"] = [
            {"A": "light.on", "B": "media.play", "confidence": 0.8},
            {"A": "light.off", "B": "media.stop", "confidence": 0.3},  # Low confidence
        ]
        
        result = await module.get_mood_integration(mock_ctx.hass, mock_ctx.entry.entry_id)
        
        assert result["pattern_count"] == 1
        assert result["patterns"][0]["confidence"] > 0.7


class TestHabitusConfig:
    """Tests for config validation."""

    def test_module_data_structure(self):
        """Test ModuleData TypedDict structure."""
        # Create valid module data
        data: ModuleData = {
            "event_buffer": deque(maxlen=1000),
            "buffer_max_size": 1000,
            "buffer_max_age_hours": 24,
            "last_mining_ts": None,
            "auto_mining_enabled": False,
            "listeners": [],
            "discovered_rules": [],
            "zone_affinity": {},
        }

        assert data["buffer_max_size"] == 1000
        assert isinstance(data["event_buffer"], deque)

    def test_habitus_rule_structure(self):
        """Test HabitusRule TypedDict."""
        rule: HabitusRule = {
            "A": "light.wohnzimmer:on",
            "B": "media_player.wohnbereich:playing",
            "confidence": 0.85,
            "lift": 1.5,
            "support": 0.3,
        }

        assert rule["confidence"] == 0.85
        assert "A" in rule
        assert "B" in rule
