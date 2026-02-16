"""Integration test configuration.

Supports both:
1. pytest-homeassistant-custom-component plugin (full HA environment)
2. Standalone mode with mock fixtures (structure/unit-like tests)
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# ============================================================================
# FIXTURES (fallback if pytest-homeassistant-custom-component not installed)
# ============================================================================

@pytest.fixture
def hass():
    """Create a mock HomeAssistant instance.
    
    If pytest-homeassistant-custom-component is installed, its fixture
    will take precedence. Otherwise, this provides a minimal mock.
    """
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.loop = MagicMock()
    hass.bus = MagicMock()
    hass.bus.async_listen = MagicMock()
    hass.bus.async_fire = MagicMock()
    hass.states = MagicMock()
    hass.states.async_get = MagicMock(return_value=None)
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.helpers = MagicMock()
    # Entity registry mock
    hass.helpers.entity_registry = MagicMock()
    hass.helpers.entity_registry.async_get = MagicMock()
    # Area registry mock  
    hass.helpers.area_registry = MagicMock()
    hass.helpers.area_registry.async_get = MagicMock()
    return hass


# Mark all tests in this directory as integration tests
def pytest_collection_modifyitems(config, items):
    """Mark all tests in integration/ with 'integration' marker."""
    import_path = Path(__file__).parent
    
    for item in items:
        if str(item.fspath).startswith(str(import_path)):
            item.add_marker(pytest.mark.integration)