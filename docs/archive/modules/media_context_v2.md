# Media Context v2 Module

**Status**: v0.1 Implemented  
**Type**: Privacy-first local module  
**Location**: HA Integration only (no Core components)

## Overview
Media Context v2 extends the existing read-only media context with zone mapping and volume control capabilities. The module is designed to be fully local and privacy-first - all configuration and state is stored locally in the HA Integration.

## Components

### HA Integration (ai_home_copilot_hacs_repo)
- `media_context_v2.py` - Main coordinator with zone mapping and volume control
- `media_context_v2_entities.py` - Comprehensive entity set (sensors, controls, selects)
- `media_context_v2_setup.py` - Configuration management and persistence
- Integration with existing Legacy module

### Core Components
None - this module is fully self-contained in the HA Integration for privacy.

## Features Implemented
- ✅ Zone mapping between habitus zones and media players
- ✅ Active target selection with TV vs Music routing logic
- ✅ Volume control with guardrails (step, limits, ramping, big jump detection)
- ✅ Manual override support with TTL
- ✅ Configuration validation and auto-suggestion
- ✅ Privacy-first local storage
- ✅ Services for configuration management
- ✅ Comprehensive entity set for UX

## Privacy Design
All configuration, zone mappings, and state are stored locally using HA's Store mechanism. No data is sent to the Core server, maintaining complete privacy.

## Future Extensions
- Integration with habitus_zones_v2 when available
- Enhanced auto-suggestion based on device capabilities
- Sonos grouping support
- Multi-user preferences (local only)