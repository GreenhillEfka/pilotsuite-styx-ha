# AI Home CoPilot Developer Guide

## Table of Contents

- [Getting Started](#getting-started)
- [Architecture Overview](#architecture-overview)
- [Setting Up Development Environment](#setting-up-development-environment)
- [Coding Standards](#coding-standards)
- [Adding New Features](#adding-new-features)
- [Testing](#testing)
- [Contributing](#contributing)
- [Release Process](#release-process)

---

## Getting Started

### Repository Structure

```
ai-home-copilot-ha/              # Home Assistant Integration
├── custom_components/
│   └── ai_home_copilot/
│       ├── __init__.py           # Integration entry point
│       ├── manifest.json         # Integration metadata
│       ├── const.py              # Constants and configuration keys
│       ├── config_flow.py        # Configuration UI
│       ├── core/                 # Core logic
│       │   ├── runtime.py        # Module orchestrator
│       │   └── modules/          # Individual modules
│       ├── services_setup.py     # Service registration
│       ├── blueprints.py         # Blueprint management
│       ├── repairs.py            # Repair system integration
│       └── tests/

Home-Assistant-Copilot/          # Core Add-on
├── addons/
│   └── copilot_core/
│       ├── manifest.json         # Add-on metadata
│       └── rootfs/
│           └── usr/
│               └── src/
│                   └── app/
│                       ├── main.py               # Flask app entry
│                       ├── app.py                # Core application
│                       ├── routes/               # API routes
│                       └── copilot_core/         # Core modules
├── sdk/                          # Language SDKs
│   ├── python/                   # Python SDK
│   └── typescript/               # TypeScript SDK
├── docs/                         # Documentation
│   ├── API.md                    # API reference
│   ├── ARCHITECTURE.md           # Architecture overview
│   └── openapi.yaml              # OpenAPI specification
└── tests/
```

### Key Concepts

1. **Modular Architecture**: Each feature is a separate module that can be enabled/disabled
2. **Event-Driven**: System responds to Home Assistant events
3. **Privacy-First**: No external data sharing, all processing local
4. **Governance-First**: User must explicitly confirm automation suggestions

---

## Architecture Overview

### Module System

Modules are the building blocks of the integration. Each module handles a specific concern:

```python
# Module lifecycle
1. Registration: Module registers itself with the runtime
2. Setup: Module sets up its components (sensors, services, etc.)
3. Operation: Module processes events and provides functionality
4. Cleanup: Module cleans up resources on shutdown

# Example module structure
custom_components/ai_home_copilot/core/modules/
├── __init__.py
├── base.py                       # Base module class
├── habitus_miner.py             # Pattern mining module
├── brain_graph_sync.py          # Graph synchronization
└── mood_context.py              # Mood context module
```

### Core Runtime

The runtime orchestrates all modules:

```python
# custom_components/ai_home_copilot/core/runtime.py

class CopilotRuntime:
    """Orchestrates all modules and coordinates their operation."""
    
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.registry = ModuleRegistry()
        self.coordinator = DataUpdateCoordinator(...)
    
    async def async_setup_entry(self, entry: ConfigEntry, modules: list[str]):
        """Set up all registered modules."""
        for module_name in modules:
            module = self.registry.get(module_name)
            await module.async_setup()
```

### Data Flow

```
HA Event Bus
    │
    ▼
EventsForwarderModule
    │
    ▼
POST /api/v1/events (Core)
    │
    ├─▶ Event Store (JSONL)
    ├─▶ Brain Graph
    ├─▶ Pattern Mining
    └─▶ Candidate Generator
```

---

## Setting Up Development Environment

### Prerequisites

- Python 3.11+
- Node.js 18+
- Home Assistant Dev container or local dev environment
- Git

### Integration Development (HA)

```bash
# Clone repository
git clone https://github.com/GreenhillEfka/ai-home-copilot-ha.git
cd ai-home-copilot-ha

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Install Home Assistant dev requirements
pip install homeassistant
```

### Core Add-on Development

```bash
# Clone repository
git clone https://github.com/GreenhillEfka/Home-Assistant-Copilot.git
cd Home-Assistant-Copilot/addons/copilot_core/rootfs/usr/src/app

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies (if needed)
npm install
```

### Docker Development

```bash
# Build dev image
docker build -t copilot-core:dev .

# Run container with volume mounts
docker run -it --rm \
  --name copilot-core-dev \
  -p 8909:8909 \
  -v $(pwd):/usr/src/app \
  -v /path/to/data:/data \
  copilot-core:dev
```

### Home Assistant Dev Container

```bash
# Clone HA dev container
git clone https://github.com/home-assistant/home-assistant.git
cd home-assistant

# Add integration to custom components
ln -s /path/to/ai-home-copilot-ha/custom_components/ai_home_copilot \
      custom_components/
```

---

## Coding Standards

### Python Style Guide

```python
# Follow PEP 8
- 4 spaces per indentation
- Maximum line length: 100 characters
- Use type hints
- Docstrings for all public functions

# Naming conventions
- Classes: PascalCase
- Functions/variables: snake_case
- Constants: UPPERCASE
- Private: _leading_underscore

# Error handling
try:
    result = expensive_operation()
except (ValueError, RuntimeError) as err:
    _LOGGER.error("Operation failed: %s", err)
    raise HomeAssistantError("Failed to complete operation") from err
```

### Module Template

```python
# custom_components/ai_home_copilot/core/modules/my_feature.py

"""My Feature Module."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform

from .base import CopilotModule
from .const import DOMAIN

class MyFeatureModule(CopilotModule):
    """Module for my feature."""
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the module."""
        super().__init__(hass, entry)
        self._name = "my_feature"
        self._platforms = [Platform.SENSOR]
    
    async def async_setup(self) -> bool:
        """Set up the module."""
        if not await super().async_setup():
            return False
        
        # Register services
        self.hass.services.async_register(
            DOMAIN, "my_service", self._handle_my_service
        )
        
        # Setup sensors
        self.async_add_entities([MyFeatureSensor(self.hass)])
        
        return True
    
    async def async_unload(self) -> bool:
        """Unload the module."""
        # Remove services
        self.hass.services.async_remove(DOMAIN, "my_service")
        
        return await super().async_unload()
    
    async def _handle_my_service(self, call) -> None:
        """Handle service call."""
        # Service implementation
        pass
```

### Type Hints

```python
from typing import Optional, List, Dict, Any

async def process_events(
    events: list[dict[str, Any]],
    config: dict[str, Any],
    timeout: int = 30
) -> dict[str, Any]:
    """Process events and return results."""
    # Implementation
    pass
```

### Logging

```python
import logging

_LOGGER = logging.getLogger(__name__)

# Use appropriate log levels
_LOGGER.debug("Detailed debug info")
_LOGGER.info("Informational message")
_LOGGER.warning("Warning condition")
_LOGGER.error("Error condition")
_LOGGER.critical("Critical error")
```

---

## Adding New Features

### Step 1: Plan Your Feature

1. Define the feature scope
2. Identify required modules
3. Design data structures
4. Plan API endpoints (if Core changes needed)

### Step 2: Create Module

1. Create module file in `core/modules/`
2. Implement `CopilotModule` base class
3. Add configuration options
4. Implement setup/teardown methods

### Step 3: Add Core API (if needed)

1. Create route handler in `routes/`
2. Implement data models
3. Add tests
4. Update OpenAPI spec

### Step 4: Update Documentation

1. Add API documentation
2. Update architecture diagrams
3. Add usage examples

### Example: Adding a New Feature

```python
# custom_components/ai_home_copilot/core/modules/my_feature.py

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .base import CopilotModule
from .const import DOMAIN

class MyFeatureModule(CopilotModule):
    """My Feature Module."""
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry)
        self._name = "my_feature"
    
    async def async_setup(self) -> bool:
        """Set up the module."""
        # Your setup code
        return True
    
    async def async_unload(self) -> bool:
        """Unload the module."""
        # Your cleanup code
        return True
```

---

## Testing

### Integration Tests

```python
# tests/test_my_feature.py

"""Tests for My Feature module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ai_home_copilot.core.modules.my_feature import MyFeatureModule
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    return hass

@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.options = {}
    entry.data = {}
    return entry

@pytest.mark.asyncio
async def test_module_setup(mock_hass, mock_entry):
    """Test module setup."""
    module = MyFeatureModule(mock_hass, mock_entry)
    result = await module.async_setup()
    assert result is True
```

### Core API Tests

```python
# tests/test_my_feature_api.py

import pytest
from app import app

@pytest.fixture
def client():
    """Create test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_get_status(client):
    """Test status endpoint."""
    response = client.get("/api/v1/habitus/status")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
```

### Running Tests

```bash
# Integration tests
cd ai-home-copilot-ha
python -m pytest tests/

# Core API tests
cd Home-Assistant-Copilot/addons/copilot_core/rootfs/usr/src/app
python -m pytest tests/
```

---

## Contributing

### Pull Request Checklist

- [ ] Code follows style guide
- [ ] Type hints included
- [ ] Docstrings added
- [ ] Tests passing
- [ ] Documentation updated
- [ ] Changelog updated

### Commit Message Format

```
type(scope): description

type: feat|fix|docs|style|refactor|test|chore
scope: integration|core|sdk|docs|config

Examples:
feat(habitus): add new mining algorithm
fix(graph): correct node filtering logic
docs(api): add endpoint documentation
```

### Code Review Process

1. Create pull request
2. Automated checks run (lint, tests)
3. Reviewer checks code quality
4. Merge to development branch
5. Version bump and release

---

## Release Process

### Versioning

- **Major**: Breaking changes
- **Minor**: New features (backward-compatible)
- **Patch**: Bug fixes (backward-compatible)

### Steps

1. Update version in `manifest.json` and `package.json`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v1.2.3`
4. Push changes and tags: `git push && git push --tags`
5. Create GitHub release

### HACS Release

1. Push changes to main branch
2. Create GitHub release
3. HACS automatically detects new version

### Add-on Release

1. Push changes to main branch
2. Create GitHub release
3. Add-on automatically updates in Home Assistant

---

## Common Tasks

### Adding a New API Endpoint

```python
# routes/my_feature.py

from flask import Blueprint, request, jsonify
from ..app import app

blueprint = Blueprint("my_feature", __name__)

@blueprint.route("/api/v1/my_feature/status", methods=["GET"])
def get_status():
    """Get my feature status."""
    return jsonify({"status": "ok"})

# Register blueprint
app.register_blueprint(blueprint)
```

### Adding a New Sensor Type

```python
# entities/my_feature_sensor.py

from homeassistant.helpers.entity import Entity

from .const import DOMAIN

class MyFeatureSensor(Entity):
    """My Feature Sensor."""
    
    def __init__(self, hass):
        self.hass = hass
        self._attr_name = "My Feature Sensor"
        self._attr_unique_id = "my_feature_sensor"
    
    @property
    def state(self):
        """Return the state."""
        return self.hass.data[DOMAIN].get("my_feature_value")
```

---

## Resources

- [Home Assistant Developer Documentation](https://developers.home-assistant.io/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [OpenAPI Specification](https://spec.openapis.org/oas/v3.1.0)

## Support

- GitHub Issues
- GitHub Discussions
- Home Assistant Community Forum
