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

# Mock sensor component for debug.py
mock_ha_components.sensor = MagicMock()
mock_ha_components.sensor.SensorEntity = MagicMock

# Mock other components used by various modules
mock_ha_components.binary_sensor = MagicMock()
mock_ha_components.binary_sensor.BinarySensorEntity = MagicMock
mock_ha_components.button = MagicMock()
mock_ha_components.button.ButtonEntity = MagicMock
mock_ha_components.persistent_notification = MagicMock()

mock_ha_core = MagicMock()
mock_ha_core.HomeAssistant = MagicMock

# Mock additional helpers
mock_ha_helpers.area_registry = MagicMock()
mock_ha_helpers.device_registry = MagicMock()
mock_ha_helpers.entity_registry = MagicMock()
mock_ha_helpers.entity_platform = MagicMock()
mock_ha_helpers.entity_platform.AddEntitiesCallback = MagicMock
mock_ha_helpers.entity = MagicMock()
mock_ha_helpers.entity.EntityCategory = MagicMock

# Mock const module
mock_ha_const = MagicMock()
mock_ha_const.EVENT_STATE_CHANGED = "state_changed"
mock_ha_const.EVENT_CALL_SERVICE = "call_service"
mock_ha_const.STATE_UNAVAILABLE = "unavailable"
mock_ha_const.STATE_UNKNOWN = "unknown"
mock_ha_const.STATE_ON = "on"
mock_ha_const.STATE_OFF = "off"

# Mock config_entries
mock_ha_config_entries = MagicMock()
mock_ha_config_entries.ConfigEntry = MagicMock

# Mock exceptions
mock_ha_exceptions = MagicMock()
mock_ha_exceptions.HomeAssistantError = Exception

# Mock util
mock_ha_util = MagicMock()
mock_ha_util.dt = MagicMock()

# Inject mocks into sys.modules BEFORE importing custom_components
sys.modules['homeassistant'] = mock_ha
sys.modules['homeassistant.core'] = mock_ha_core
sys.modules['homeassistant.helpers'] = mock_ha_helpers
sys.modules['homeassistant.helpers.aiohttp_client'] = mock_ha_helpers.aiohttp_client
sys.modules['homeassistant.helpers.storage'] = mock_ha_helpers.storage
sys.modules['homeassistant.helpers.update_coordinator'] = mock_ha_helpers.update_coordinator
sys.modules['homeassistant.helpers.area_registry'] = mock_ha_helpers.area_registry
sys.modules['homeassistant.helpers.device_registry'] = mock_ha_helpers.device_registry
sys.modules['homeassistant.helpers.entity_registry'] = mock_ha_helpers.entity_registry
sys.modules['homeassistant.helpers.entity_platform'] = mock_ha_helpers.entity_platform
sys.modules['homeassistant.helpers.entity'] = mock_ha_helpers.entity
sys.modules['homeassistant.components'] = mock_ha_components
sys.modules['homeassistant.components.repairs'] = mock_ha_components.repairs
sys.modules['homeassistant.components.sensor'] = mock_ha_components.sensor
sys.modules['homeassistant.components.binary_sensor'] = mock_ha_components.binary_sensor
sys.modules['homeassistant.components.button'] = mock_ha_components.button
sys.modules['homeassistant.components.persistent_notification'] = mock_ha_components.persistent_notification
sys.modules['homeassistant.const'] = mock_ha_const
sys.modules['homeassistant.config_entries'] = mock_ha_config_entries
sys.modules['homeassistant.exceptions'] = mock_ha_exceptions
sys.modules['homeassistant.util'] = mock_ha_util
sys.modules['homeassistant.util.dt'] = mock_ha_util.dt


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