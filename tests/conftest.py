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
from unittest.mock import MagicMock

# Add project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Add custom_components to path
custom_components = project_root / "custom_components"
if custom_components.exists():
    sys.path.insert(0, str(custom_components))


# =============================================================================
# CHECK FOR HOME ASSISTANT AVAILABILITY
# =============================================================================

HA_AVAILABLE = False
try:
    import homeassistant
    HA_AVAILABLE = True
except ImportError:
    pass


def pytest_configure(config):
    """Configure custom markers and skip integration tests if HA unavailable."""
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
    """Skip HA-required tests if HA not installed."""
    if HA_AVAILABLE:
        return
    
    skip_ha = pytest.mark.skip(reason="Home Assistant not installed")
    for item in items:
        if "ha_required" in item.keywords or "integration" in item.keywords:
            item.add_marker(skip_ha)