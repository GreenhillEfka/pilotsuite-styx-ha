"""
Test Brain Graph Sync functionality.

Tests the integration between HA and Core Brain Graph module.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import pytest


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = MagicMock()
    hass.bus = MagicMock()
    hass.states = MagicMock()
    return hass


@pytest.fixture
def mock_registries():
    """Create mock registries."""
    area_reg = MagicMock()
    device_reg = MagicMock()
    entity_reg = MagicMock()
    
    # Mock area
    area = MagicMock()
    area.id = "living_room"
    area.name = "Living Room"
    area_reg.areas = {"living_room": area}
    
    # Mock device
    device = MagicMock()
    device.id = "device_123"
    device.name = "Smart Light"
    device.manufacturer = "Philips"
    device.model = "Hue"
    device.area_id = "living_room"
    device_reg.devices = {"device_123": device}
    
    # Mock entity
    entity = MagicMock()
    entity.entity_id = "light.living_room_lamp"
    entity.original_name = "Living Room Lamp"
    entity.platform = "hue"
    entity.device_id = "device_123"
    entity.area_id = None
    entity.disabled = False
    entity_reg.entities = {"light.living_room_lamp": entity}
    
    return area_reg, device_reg, entity_reg


@pytest.fixture
def brain_graph_sync(mock_hass, mock_registries):
    """Create BrainGraphSync instance."""
    from custom_components.ai_home_copilot.brain_graph_sync import BrainGraphSync
    
    with patch('custom_components.ai_home_copilot.brain_graph_sync.area_registry.async_get') as mock_area:
        with patch('custom_components.ai_home_copilot.brain_graph_sync.device_registry.async_get') as mock_device:
            with patch('custom_components.ai_home_copilot.brain_graph_sync.entity_registry.async_get') as mock_entity:
                area_reg, device_reg, entity_reg = mock_registries
                mock_area.return_value = area_reg
                mock_device.return_value = device_reg
                mock_entity.return_value = entity_reg
                
                sync = BrainGraphSync(mock_hass, "http://localhost:5000", "test-token")
                sync._area_reg = area_reg
                sync._device_reg = device_reg
                sync._entity_reg = entity_reg
                
                return sync


@pytest.fixture
def mock_session():
    """Create mock aiohttp session."""
    session = MagicMock()
    session.get = MagicMock()
    session.post = MagicMock()
    session.close = AsyncMock()
    return session


# =============================================================================
# TESTS
# =============================================================================

class TestBrainGraphSync:
    """Test Brain Graph sync functionality."""

    def test_init(self, mock_hass):
        """Test BrainGraphSync initialization."""
        from custom_components.ai_home_copilot.brain_graph_sync import BrainGraphSync
        sync = BrainGraphSync(mock_hass, "http://localhost:5000", "test-token")
        
        assert sync.hass == mock_hass
        assert sync.core_url == "http://localhost:5000"
        assert sync.access_token == "test-token"
        assert not sync._running
        assert sync._session is None

    @pytest.mark.asyncio
    async def test_get_graph_snapshot_url(self, brain_graph_sync):
        """Test getting graph snapshot URL."""
        url = await brain_graph_sync.get_graph_snapshot_url()
        assert url == "http://localhost:5000/api/v1/graph/snapshot.svg"


if __name__ == "__main__":
    # Simple test runner (no pytest dependency)
    print("Brain Graph Sync Tests")
    
    # Test initialization
    mock_hass = MagicMock()
    
    from custom_components.ai_home_copilot.brain_graph_sync import BrainGraphSync
    sync = BrainGraphSync(mock_hass, "http://localhost:5000", "test-token")
    assert sync.core_url == "http://localhost:5000"
    assert sync.access_token == "test-token"
    assert not sync._running
    print("✓ Initialization test passed")
    
    # Test URL generation  
    import asyncio
    url = asyncio.get_event_loop().run_until_complete(sync.get_graph_snapshot_url())
    assert url == "http://localhost:5000/api/v1/graph/snapshot.svg"
    print("✓ URL generation test passed")
    
    # Test processed events tracking
    sync._processed_events.add("test_event_1")
    assert "test_event_1" in sync._processed_events
    print("✓ Event tracking test passed")
    
    print("✓ All basic tests passed")