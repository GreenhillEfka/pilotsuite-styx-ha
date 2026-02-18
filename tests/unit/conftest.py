"""Unit test configuration - Mocks for Home Assistant modules.

NOTE: This file intentionally does NOT set up sys.modules mocks.
The root conftest.py already sets up proper mock classes that can be
subclassed (MockRepairsFlow, MockSensorEntity, etc.). Setting up mocks
here would override those and cause test pollution.

This file only provides fixtures and markers for unit tests.
"""
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import pytest


# ============================================================================
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
        "port": 8909,
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
    client.port = 8909
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