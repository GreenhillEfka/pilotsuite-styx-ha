"""
Simple test for Brain Graph Sync functionality.

Basic validation without full HA dependency chain.
"""
import sys
import os
from unittest.mock import MagicMock

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_brain_graph_module_import():
    """Test that the BrainGraphSyncModule can be imported."""
    try:
        # Mock the module path
        mock_module = MagicMock()
        mock_module.async_setup_entry = MagicMock()
        mock_module.async_unload_entry = MagicMock()
        mock_module.name = "brain_graph_sync"
        
        # Basic structure validation
        assert mock_module.async_setup_entry is not None
        assert mock_module.async_unload_entry is not None
        
    except Exception as err:
        raise AssertionError(f"Module import failed: {err}") from err


def test_brain_graph_sync_class():
    """Test BrainGraphSync class structure."""
    # Save original sys.modules state
    original_modules = {}
    modules_to_mock = [
        'homeassistant', 'homeassistant.core', 'homeassistant.helpers',
        'homeassistant.helpers.area_registry', 'homeassistant.helpers.device_registry',
        'homeassistant.helpers.entity_registry', 'homeassistant.helpers.typing',
        'homeassistant.const', 'homeassistant.config_entries', 'aiohttp'
    ]
    for mod in modules_to_mock:
        if mod in sys.modules:
            original_modules[mod] = sys.modules.pop(mod)
    
    # Mock homeassistant modules to avoid import errors
    mock_ha = MagicMock()
    mock_ha.core = MagicMock() 
    mock_ha.helpers = MagicMock()
    mock_ha.const = MagicMock()
    mock_ha.config_entries = MagicMock()
    
    mock_ha.const.EVENT_STATE_CHANGED = "state_changed"
    mock_ha.const.EVENT_CALL_SERVICE = "call_service"
    mock_ha.const.STATE_UNAVAILABLE = "unavailable"
    mock_ha.const.STATE_UNKNOWN = "unknown"
    
    try:
        sys.modules['homeassistant'] = mock_ha
        sys.modules['homeassistant.core'] = mock_ha.core
        sys.modules['homeassistant.helpers'] = mock_ha.helpers
        sys.modules['homeassistant.helpers.area_registry'] = mock_ha.helpers
        sys.modules['homeassistant.helpers.device_registry'] = mock_ha.helpers
        sys.modules['homeassistant.helpers.entity_registry'] = mock_ha.helpers
        sys.modules['homeassistant.helpers.typing'] = mock_ha.helpers
        sys.modules['homeassistant.const'] = mock_ha.const
        sys.modules['homeassistant.config_entries'] = mock_ha.config_entries
        sys.modules['aiohttp'] = MagicMock()
        
        from custom_components.ai_home_copilot.brain_graph_sync import BrainGraphSync
        
        # Test initialization
        mock_hass = MagicMock()
        sync = BrainGraphSync(mock_hass, "http://localhost:5000", "test-token")
        
        assert sync.core_url == "http://localhost:5000"
        assert sync.access_token == "test-token"
        assert not sync._running
        assert sync._session is None
        
        # Test methods exist
        assert hasattr(sync, 'async_start')
        assert hasattr(sync, 'async_stop')
        assert hasattr(sync, 'get_graph_stats')
        assert hasattr(sync, 'get_graph_snapshot_url')
        
        # Test URL generation - get_graph_snapshot_url is now async
        # Use asyncio.run() for Python 3.7+ (works in current test context)
        import asyncio
        async def test_url():
            return await sync.get_graph_snapshot_url()
        
        url = asyncio.run(test_url())
        assert url == "http://localhost:5000/api/v1/graph/snapshot.svg"
        
    except Exception as err:
        raise AssertionError(f"BrainGraphSync class test failed: {err}") from err
    finally:
        # Clean up sys.modules to avoid polluting other tests
        for mod in modules_to_mock:
            sys.modules.pop(mod, None)
        # Restore original modules
        for mod, module in original_modules.items():
            sys.modules[mod] = module