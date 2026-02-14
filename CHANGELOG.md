# CHANGELOG - AI Home CoPilot HA Integration

## [0.6.7] - 2026-02-14

### 🔧 Module Architecture Fix

Fixed missing base classes for all Copilot modules.

#### Fixed
- **Created `module.py`**: Added `CopilotModule` and `ModuleContext` base classes
- **All modules now compile**: mood_module, brain_graph_sync, unifi_module, etc.
- **Removed unused import**: `asdict` from unifi_module.py

#### Technical
- Base classes provide standard interface for module lifecycle:
  - `async_setup_entry(ctx)` → Module initialization
  - `async_unload_entry(ctx)` → Cleanup
  - `async_reload_entry(ctx)` → Optional reload
- ModuleContext provides hass instance and config entry access

### Contributors
- Autopilot (cron:10min)

## [0.6.6] - 2026-02-14

### 🔑 Enhanced Token Management UX v0.4.3

Improved user experience for OpenClaw Gateway authentication token management.

#### Enhanced
- Token field shows only new token (empty = keep existing)
- Clear Token checkbox added for explicit deletion
- Privacy: Token never displayed when already set

## [0.4.3] - 2026-02-10

### 🔑 Enhanced Token Management UX

Improved user experience for OpenClaw Gateway authentication token management in configuration flow.

#### Enhanced
- **Clear Token Guidance**: Better hints showing whether a token is currently set or empty
- **Token Clear Functionality**: Explicitly clear tokens by leaving field empty during reconfiguration
- **Helpful Descriptions**: Clear placeholder text for both initial setup and ongoing management
- **Visual Feedback**: Shows "** AKTUELL GESETZT **" when a token exists vs helpful hints when empty

#### Technical
- **Smart Token Handling**: Empty/whitespace-only input explicitly removes existing tokens
- **Better UX Flow**: Initial setup shows helpful guidance for optional token field
- **Improved Options Flow**: Configuration changes properly handle token clear operations
- **Privacy Maintained**: No token values displayed in UI, only status indicators

This makes token management more intuitive and reduces confusion during initial setup and ongoing configuration.

## [0.4.2] - 2026-02-10

### 🚨 Improved Error Diagnostics

Enhanced HA Errors Digest with better traceback analysis and grouping for cleaner debugging experience.

#### Enhanced
- **Intelligent Error Grouping**: Similar errors are now grouped by type and location to reduce noise
- **Traceback Signatures**: Automatic detection of error patterns for better deduplication
- **Frequency Counters**: Shows how often each error type occurs (e.g., "RuntimeError@api.py (3x)")
- **Summary Headers**: Clear overview of total errors and unique types in digest
- **Better Formatting**: Markdown formatting with collapsible code blocks for cleaner notifications

#### Technical
- **Enhanced `_parse_traceback_signature()`**: Extracts error type and source file location
- **New `_group_entries()`**: Groups similar errors by signature for deduplication
- **Improved `_format_grouped_entries()`**: Clean presentation with counts and latest examples
- **Increased tail size**: Now processes last 20 entries (up from 12) for better pattern detection
- **Maintained privacy**: All existing token/secret redaction remains intact

This improves debugging workflow by highlighting the most critical and frequent issues first.

## [0.4.1] - 2026-02-10

### 🧠 Brain Graph Sync Integration

Completes the HA↔Core integration with real-time knowledge graph synchronization.

#### Added
- **Brain Graph Sync Module**: Real-time synchronization of HA entities and relationships with Core Brain Graph
  - Automatically syncs areas (zones), devices, entities to Core `/api/v1/graph` endpoints
  - Real-time tracking of `state_changed` and `call_service` events as graph nodes and edges
  - Privacy-first design: essential metadata only, no sensitive data in graph
  - Complete initial sync of HA registries plus continuous event processing
  - Background operation with deduplication and bounded memory usage
  - Integration with runtime module system for proper lifecycle management

#### Technical
- **API Integration**: Consumes Core endpoints `/api/v1/graph/state`, `/stats`, `/snapshot.svg`
- **Event Processing**: Structured entity relationships (entity→device→area) in knowledge graph
- **Service Events**: Action nodes for significant service calls (light, climate, media_player)
- **Resilience**: Auto-reconnection, error handling, graceful degradation
- **Testing**: Syntax validation and module structure tests

This completes the full data pipeline: HA Events → Core Ingest → Brain Graph ← HA Sync

## [0.4.0] - 2026-02-10

### 🎉 Major Release: Tag System + Event Forwarding

This release establishes the complete HA→Core data pipeline and tag management system.

#### Added
- **Tag Synchronization**: Live sync between Core tag registry and HA labels
  - `tag_registry.py`: Pulls canonical tags from Core `/api/v1/tag-system`
  - `tag_sync.py`: Materializes tags as HA labels with conflict resolution
  - Service: `ai_home_copilot.sync_tags` for manual refresh

- **N3 Event Forwarder**: Privacy-first event streaming to Core
  - `forwarder_n3.py`: Implements envelope v1 schema with domain projections
  - Automatic zone enrichment from HA area registry
  - Comprehensive redaction policy (GPS, tokens, sensitive attributes)
  - Batching, persistence, and idempotency with TTL cleanup
  - Services: `forwarder_n3_start`, `forwarder_n3_stop`, `forwarder_n3_stats`

- **Event Processing**: Support for `state_changed` and `call_service` events
  - Minimal attribute projections (brightness, volume_level, temperature)
  - Trigger inference and intent capture
  - Privacy-first envelope with stable schema versioning

#### Technical
- **Testing**: Unit test coverage for tag utilities and forwarder logic
- **Storage**: Persistent forwarder queue across HA restarts
- **Security**: Token-based authentication with Core Add-on
- **Performance**: Bounded queues with drop-oldest policy under load

#### Developer Notes
- All modules compile cleanly ✓
- Integration tests scaffolded (require full HA environment)
- Ready for production deployment
- Coordinated release with Core Add-on v0.4.0

---

## [0.3.2] - 2026-02-07

### Added
- Enhanced error reporting and debugging capabilities
- Improved stability for diagnostic collection

## [0.3.1] - 2026-02-06

### Added
- Core integration foundations
- Basic diagnostic reporting

## [0.3.0] - 2026-02-05

### Added
- Initial HACS-compatible release
- Configuration flow setup