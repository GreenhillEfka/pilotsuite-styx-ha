"""Root pytest configuration for AI Home CoPilot tests.

Test Categories:
- Unit tests: Don't import HA integration, mock everything
- Integration tests: Import HA integration, require HA installation

Unit tests should import specific modules directly and mock dependencies.
Integration tests are skipped if HA is not installed.
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Add custom_components to path
custom_components = project_root / "custom_components"
if custom_components.exists():
    sys.path.insert(0, str(custom_components))


# =============================================================================
# MOCK HOME ASSISTANT MODULES GLOBALLY
# =============================================================================

# Helper class for subscriptable mocks
class SubscriptableMagicMock(MagicMock):
    """MagicMock that supports subscripting (Type[Generic])."""
    def __class_getitem__(cls, item):
        return MagicMock


# Create a proper CoordinatorEntity mock class that can be used as a base class
class MockCoordinatorEntity:
    """Mock CoordinatorEntity that can be used as a real base class."""
    def __init__(self, coordinator=None):
        self.coordinator = coordinator
    
    @classmethod
    def __class_getitem__(cls, item):
        return cls


# Create a proper RepairsFlow mock that can be used as a real base class
class MockRepairsFlow:
    """Mock RepairsFlow that can be subclassed."""
    def __init__(self, *args, **kwargs):
        self.hass = None
    
    async def async_step_init(self, user_input=None):
        pass


# Create mock entity classes that can be subclassed
class MockEntityBase:
    """Mock base for all entity classes."""
    def __init__(self, *args, **kwargs):
        pass
    
    _attr_entity_registry_enabled_default = True
    _attr_has_entity_name = True
    _attr_name = None
    _attr_unique_id = None
    _attr_icon = None


class MockSensorEntity(MockEntityBase):
    """Mock SensorEntity."""
    pass


class MockBinarySensorEntity(MockEntityBase):
    """Mock BinarySensorEntity."""
    pass


class MockButtonEntity(MockEntityBase):
    """Mock ButtonEntity."""
    async def async_press(self):
        pass


class MockSelectEntity(MockEntityBase):
    """Mock SelectEntity."""
    _attr_options = []
    _attr_current_option = None
    
    async def async_select_option(self, option: str):
        pass


class MockSwitchEntity(MockEntityBase):
    """Mock SwitchEntity."""
    _attr_is_on = False
    
    async def async_turn_on(self, **kwargs):
        pass
    
    async def async_turn_off(self, **kwargs):
        pass


class MockNumberEntity(MockEntityBase):
    """Mock NumberEntity."""
    _attr_native_value = None
    _attr_native_min_value = 0
    _attr_native_max_value = 100


class MockTextEntity(MockEntityBase):
    """Mock TextEntity."""
    _attr_native_value = ""
    _attr_mode = "text"
    _attr_native_max = 255


class MockMediaPlayerEntity(MockEntityBase):
    """Mock MediaPlayerEntity."""
    _attr_state = None


class MockCamera(MockEntityBase):
    """Mock Camera."""
    pass


class MockCalendarEntity(MockEntityBase):
    """Mock CalendarEntity."""
    pass


class MockDeviceTrackerEntity(MockEntityBase):
    """Mock DeviceTrackerEntity."""
    pass


class MockWeatherEntity(MockEntityBase):
    """Mock WeatherEntity."""
    pass

# Create base mock modules
mock_ha = MagicMock()
mock_ha_core = MagicMock()
mock_ha_core.HomeAssistant = MagicMock
mock_ha_helpers = MagicMock()
mock_ha_components = MagicMock()
mock_ha_const = MagicMock()
mock_ha_config_entries = MagicMock()
mock_ha_config_entries.ConfigEntry = MagicMock
mock_ha_exceptions = MagicMock()
mock_ha_exceptions.HomeAssistantError = Exception
mock_ha_data_entry_flow = MagicMock()
mock_ha_data_entry_flow.UnknownFlow = Exception
mock_ha_util = MagicMock()

# Set up const values
mock_ha_const.EVENT_STATE_CHANGED = "state_changed"
mock_ha_const.EVENT_CALL_SERVICE = "call_service"
mock_ha_const.EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
mock_ha_const.STATE_UNAVAILABLE = "unavailable"
mock_ha_const.STATE_UNKNOWN = "unknown"
mock_ha_const.STATE_ON = "on"
mock_ha_const.STATE_OFF = "off"

# Set up helpers submodules
mock_ha_helpers.aiohttp_client = MagicMock()
mock_ha_helpers.aiohttp_client.async_get_clientsession = MagicMock(return_value=MagicMock())
mock_ha_helpers.storage = MagicMock()
mock_ha_helpers.storage.Store = MagicMock
mock_ha_helpers.update_coordinator = SubscriptableMagicMock()
mock_ha_helpers.update_coordinator.DataUpdateCoordinator = SubscriptableMagicMock
mock_ha_helpers.update_coordinator.CoordinatorEntity = MockCoordinatorEntity
mock_ha_helpers.area_registry = MagicMock()
mock_ha_helpers.device_registry = MagicMock()
mock_ha_helpers.entity_registry = MagicMock()
mock_ha_helpers.entity_platform = MagicMock()
mock_ha_helpers.entity_platform.AddEntitiesCallback = MagicMock
mock_ha_helpers.entity = MagicMock()
mock_ha_helpers.entity.EntityCategory = type('EntityCategory', (), {'DIAGNOSTIC': 'diagnostic', 'CONFIG': 'config', 'SERVICE': 'service'})
mock_ha_helpers.event = MagicMock()
mock_ha_helpers.event.async_track_state_change_event = MagicMock()
mock_ha_helpers.event.async_call_later = MagicMock()
mock_ha_helpers.typing = MagicMock()
mock_ha_helpers.typing.ConfigType = dict
mock_ha_helpers.dispatcher = MagicMock()
mock_ha_helpers.dispatcher.async_dispatcher_connect = MagicMock()
mock_ha_helpers.dispatcher.async_dispatcher_send = MagicMock()
mock_ha_helpers.selector = MagicMock()

# Set up components submodules with entity classes
mock_ha_components.repairs = MagicMock()
mock_ha_components.repairs.RepairsFlow = MockRepairsFlow

mock_ha_components.sensor = MagicMock()
mock_ha_components.sensor.SensorEntity = MockSensorEntity

mock_ha_components.binary_sensor = MagicMock()
mock_ha_components.binary_sensor.BinarySensorEntity = MockBinarySensorEntity

mock_ha_components.button = MagicMock()
mock_ha_components.button.ButtonEntity = MockButtonEntity

mock_ha_components.select = MagicMock()
mock_ha_components.select.SelectEntity = MockSelectEntity

mock_ha_components.switch = MagicMock()
mock_ha_components.switch.SwitchEntity = MockSwitchEntity

mock_ha_components.number = MagicMock()
mock_ha_components.number.NumberEntity = MockNumberEntity

mock_ha_components.text = MagicMock()
mock_ha_components.text.TextEntity = MockTextEntity

mock_ha_components.media_player = MagicMock()
mock_ha_components.media_player.MediaPlayerEntity = MockMediaPlayerEntity
mock_ha_components.media_player.MediaPlayerEntityFeature = MagicMock
mock_ha_components.media_player.MediaType = MagicMock

mock_ha_components.camera = MagicMock()
mock_ha_components.camera.Camera = MockCamera

mock_ha_components.calendar = MagicMock()
mock_ha_components.calendar.CalendarEntity = MockCalendarEntity

mock_ha_components.device_tracker = MagicMock()
mock_ha_components.device_tracker.DeviceTrackerEntity = MockDeviceTrackerEntity

mock_ha_components.diagnostics = MagicMock()

mock_ha_components.http = MagicMock()

mock_ha_components.person = MagicMock()

mock_ha_components.weather = MagicMock()
mock_ha_components.weather.WeatherEntity = MockWeatherEntity

mock_ha_components.persistent_notification = MagicMock()

# ============================================================================
# INJECT ALL MOCKS INTO sys.modules
# ============================================================================

# Core modules
sys.modules['homeassistant'] = mock_ha
sys.modules['homeassistant.core'] = mock_ha_core
sys.modules['homeassistant.const'] = mock_ha_const
sys.modules['homeassistant.config_entries'] = mock_ha_config_entries
sys.modules['homeassistant.exceptions'] = mock_ha_exceptions
sys.modules['homeassistant.data_entry_flow'] = mock_ha_data_entry_flow
sys.modules['homeassistant.util'] = mock_ha_util
sys.modules['homeassistant.util.dt'] = mock_ha_util

# Helpers
sys.modules['homeassistant.helpers'] = mock_ha_helpers
sys.modules['homeassistant.helpers.aiohttp_client'] = mock_ha_helpers.aiohttp_client
sys.modules['homeassistant.helpers.storage'] = mock_ha_helpers.storage
sys.modules['homeassistant.helpers.update_coordinator'] = mock_ha_helpers.update_coordinator
sys.modules['homeassistant.helpers.area_registry'] = mock_ha_helpers.area_registry
sys.modules['homeassistant.helpers.device_registry'] = mock_ha_helpers.device_registry
sys.modules['homeassistant.helpers.entity_registry'] = mock_ha_helpers.entity_registry
sys.modules['homeassistant.helpers.entity_platform'] = mock_ha_helpers.entity_platform
sys.modules['homeassistant.helpers.entity'] = mock_ha_helpers.entity
sys.modules['homeassistant.helpers.event'] = mock_ha_helpers.event
sys.modules['homeassistant.helpers.typing'] = mock_ha_helpers.typing
sys.modules['homeassistant.helpers.dispatcher'] = mock_ha_helpers.dispatcher
sys.modules['homeassistant.helpers.selector'] = mock_ha_helpers.selector

# Components
sys.modules['homeassistant.components'] = mock_ha_components
sys.modules['homeassistant.components.repairs'] = mock_ha_components.repairs
sys.modules['homeassistant.components.sensor'] = mock_ha_components.sensor
sys.modules['homeassistant.components.binary_sensor'] = mock_ha_components.binary_sensor
sys.modules['homeassistant.components.button'] = mock_ha_components.button
sys.modules['homeassistant.components.select'] = mock_ha_components.select
sys.modules['homeassistant.components.switch'] = mock_ha_components.switch
sys.modules['homeassistant.components.number'] = mock_ha_components.number
sys.modules['homeassistant.components.text'] = mock_ha_components.text
sys.modules['homeassistant.components.media_player'] = mock_ha_components.media_player
sys.modules['homeassistant.components.camera'] = mock_ha_components.camera
sys.modules['homeassistant.components.calendar'] = mock_ha_components.calendar
sys.modules['homeassistant.components.device_tracker'] = mock_ha_components.device_tracker
sys.modules['homeassistant.components.diagnostics'] = mock_ha_components.diagnostics
sys.modules['homeassistant.components.http'] = mock_ha_components.http
sys.modules['homeassistant.components.person'] = mock_ha_components.person
sys.modules['homeassistant.components.weather'] = mock_ha_components.weather
sys.modules['homeassistant.components.persistent_notification'] = mock_ha_components.persistent_notification


# =============================================================================
# FIXTURES
# =============================================================================

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


# =============================================================================
# MARKERS
# =============================================================================

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests without HA dependency"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests with HA framework"
    )
    config.addinivalue_line(
        "markers", "slow: Slow integration tests"
    )
    config.addinivalue_line(
        "markers", "ha_required: Requires Home Assistant installation"
    )


def pytest_collection_modifyitems(session, config, items):
    """Mark tests appropriately."""
    for item in items:
        # Mark tests in unit/ directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)