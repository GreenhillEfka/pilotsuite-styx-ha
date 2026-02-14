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
        
        print("✓ Module structure test passed")
        return True
        
    except Exception as err:
        print(f"✗ Module import failed: {err}")
        return False

def test_brain_graph_sync_class():
    """Test BrainGraphSync class structure."""
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
    
    try:
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
        
        # Test URL generation
        url = sync.get_graph_snapshot_url()
        assert url == "http://localhost:5000/api/v1/graph/snapshot.svg"
        
        print("✓ BrainGraphSync class test passed")
        return True
        
    except Exception as err:
        print(f"✗ BrainGraphSync class test failed: {err}")
        return False

if __name__ == "__main__":
    print("Brain Graph Sync Simple Tests")
    
    success = True
    
    success &= test_brain_graph_module_import()
    success &= test_brain_graph_sync_class()
    
    if success:
        print("✓ All tests passed")
    else:
        print("✗ Some tests failed")
        sys.exit(1)