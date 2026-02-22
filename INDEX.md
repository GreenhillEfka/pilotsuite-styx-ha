# PilotSuite - HA Integration

## Quick Links
- **README.md** - Installation & Configuration
- **CHANGELOG.md** - Version History
- **custom_components/ai_home_copilot/** - Main Code
- **docs/openapi.yaml** - Service API Documentation (v0.8.2)

## Components

### Core Files
- `__init__.py` - Integration setup
- `config_flow.py` - UI configuration
- `const.py` - Constants
- `coordinator.py` - Data coordination

### Modules
- `brain_graph_*.py` - Neural graph visualization
- `habitus_*.py` - Pattern detection & zones
- `tag_registry.py` - Entity tagging
- `energy_context.py` - Energy monitoring
- `unifi_context.py` - Network context
- `media_context.py` - Media state
- `core/performance.py` - Caching & optimization (v0.8.1)
- `core/mupl/` - Multi-User Preference Learning (v0.8.0)

### Services
- `services_setup.py` - Service registration
- `services.yaml` - Service definitions

## Current Version
- **v0.8.2** - OpenAPI Specification for Services
- **v0.8.1** - Performance Optimization + MUPL Phase 2
- **v0.8.0** - Multi-User Preference Learning
- **v0.7.6** - Interactive Brain Graph Panel

## Features

| Feature | Version | Status |
|---------|---------|--------|
| Brain Graph v2 | v0.7.5 | ✅ |
| Tag System v0.2 | v0.7.5 | ✅ |
| Habitus Dashboard Cards | v0.7.5 | ✅ |
| Interactive Brain Graph | v0.7.6 | ✅ |
| Multi-User Preference Learning | v0.8.0 | ✅ |
| MUPL Phase 2: Action Attribution | v0.8.1 | ✅ |
| Performance Optimization | v0.8.1 | ✅ |
| OpenAPI Specification | v0.8.2 | ✅ |

## Related
- Core Add-on: https://github.com/GreenhillEfka/pilotsuite-styx-core
- Docs: https://github.com/GreenhillEfka/pilotsuite-styx-ha#readme

---

*Last updated: 2026-02-15*