"""Root pytest configuration for AI Home CoPilot tests."""
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Add custom_components to path
custom_components = project_root / "custom_components"
if custom_components.exists():
    sys.path.insert(0, str(custom_components))


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests without HA dependency"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests with HA framework"
    )