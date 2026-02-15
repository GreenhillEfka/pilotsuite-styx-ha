"""Unit test configuration - Mocks for Home Assistant modules."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import pytest

# ============================================================================
# MOCK HOME ASSISTANT MODULES
# ============================================================================

# Create mock homeassistant package structure
mock_ha = MagicMock()
mock_ha_helpers = MagicMock()
mock_ha_components = MagicMock()

# Mock specific modules used in imports
mock_ha_helpers.aiohttp_client = MagicMock()
mock_ha_helpers.aiohttp_client.async_get_clientsession = MagicMock(return_value=MagicMock())

mock_ha_helpers.storage = MagicMock()
mock_ha_helpers.storage.Store = MagicMock()

mock_ha_helpers.update_coordinator = MagicMock()
mock_ha_helpers.update_coordinator.DataUpdateCoordinator = MagicMock()

mock_ha_components.repairs = MagicMock()
mock_ha_components.repairs.RepairsFlow = MagicMock()

mock_ha_core = MagicMock()
mock_ha_core.HomeAssistant = MagicMock()

# Inject mocks into sys.modules BEFORE importing custom_components
sys.modules['homeassistant'] = mock_ha
sys.modules['homeassistant.core'] = mock_ha_core
sys.modules['homeassistant.helpers'] = mock_ha_helpers
sys.modules['homeassistant.helpers.aiohttp_client'] = mock_ha_helpers.aiohttp_client
sys.modules['homeassistant.helpers.storage'] = mock_ha_helpers.storage
sys.modules['homeassistant.helpers.update_coordinator'] = mock_ha_helpers.update_coordinator
sys.modules['homeassistant.components'] = mock_ha_components
sys.modules['homeassistant.components.repairs'] = mock_ha_components.repairs
sys.modules['homeassistant.exceptions'] = MagicMock()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.loop = MagicMock()
    hass.bus = MagicMock()
    hass.bus.async_listen = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        "host": "localhost",
        "port": 8099,
        "token": "test_token",
    }
    entry.options = {}
    entry.add_update_listener = MagicMock()
    return entry


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    client = MagicMock()
    client.host = "localhost"
    client.port = 8099
    client.token = "test_token"
    client.async_get_status = AsyncMock(return_value={"ok": True, "version": "test"})
    client.async_get_mood = AsyncMock(return_value={"mood": "relax", "confidence": 0.9})
    client.async_get_neurons = AsyncMock(return_value={"neurons": {}})
    return client


@pytest.fixture
def mock_store():
    """Create a mock storage store."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value={})
    store.async_save = AsyncMock()
    return store


# ============================================================================
# MARKERS
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Mark all tests in unit/ with 'unit' marker."""
    unit_dir = Path(__file__).parent
    
    for item in items:
        # Check if test is in unit directory
        if str(item.fspath).startswith(str(unit_dir)):
            item.add_marker(pytest.mark.unit)