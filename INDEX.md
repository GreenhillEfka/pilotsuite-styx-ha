# AI Home CoPilot - HA Integration

## Quick Links
- **README.md** - Installation & Configuration
- **CHANGELOG.md** - Version History
- **custom_components/ai_home_copilot/** - Main Code

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

### Services
- `services_setup.py` - Service registration
- `services.yaml` - Service definitions

## Current Version
- **v0.7.5** - Security fixes, Habitus Dashboard Cards

## Related
- Core Add-on: `/config/.openclaw/workspace/ha-copilot-repo`
- Docs: `/config/.openclaw/workspace/docs/`