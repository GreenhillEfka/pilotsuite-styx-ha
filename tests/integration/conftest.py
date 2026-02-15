"""Integration test configuration - Requires Home Assistant framework.

These tests run with the pytest-homeassistant-custom-component plugin.

Install: pip install pytest-homeassistant-custom-component
Run: pytest tests/integration/ -v -m integration
"""
import pytest
from pathlib import Path

# Integration tests require HA environment
# The pytest-homeassistant-custom-component provides fixtures:
# - hass: HomeAssistant instance
# - hass_client: aiohttp client
# - hass_ws_client: WebSocket client

# Mark all tests in this directory as integration tests
def pytest_collection_modifyitems(config, items):
    """Mark all tests in integration/ with 'integration' marker."""
    import_path = Path(__file__).parent
    
    for item in items:
        if str(item.fspath).startswith(str(import_path)):
            item.add_marker(pytest.mark.integration)
            # Note: 'slow' marker removed - use explicit marker for slow tests
            # item.add_marker(pytest.mark.slow)