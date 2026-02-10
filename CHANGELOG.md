# CHANGELOG - AI Home CoPilot HA Integration

## [0.5.3] - 2026-02-10

### 📋 services.yaml — Developer Tools Auto-Discovery

All 28+ services are now discoverable in HA Developer Tools → Services with full descriptions, field schemas, and selectors.

#### Added
- **`services.yaml`**: Complete service definitions for all registered services
  - Tag Registry (5 services): upsert, assign, confirm, sync, pull
  - Media Context v2 (3 services): suggest zones, apply suggestions, clear overrides
  - N3 Event Forwarder (3 services): start, stop, stats
  - Ops Runbook (4 services): preflight, smoke test, execute action, run checklist
  - Dev Surface (4 services): enable debug, disable debug, clear errors, ping
  - Candidate Poller (1 service): trigger mining with slider selectors
  - UniFi Module (2 services): diagnostics, get report
  - Habitus Miner (4 services): mine rules, get rules, reset cache, configure mining
  - Proper HA selectors (number sliders, entity pickers, text inputs, booleans)
  - Bilingual descriptions (German primary, service names English)

#### Technical
- HA auto-discovers services from `services.yaml` alongside the `manifest.json`
- Enables autocomplete in HA automations, scripts, and Developer Tools
- No runtime changes — purely declarative metadata

---

## [0.5.2] - 2026-02-10

### 🩺 Pipeline Health + On-Demand Mining — N0 Observability

New sensor and service for operational visibility into the full CoPilot pipeline.

#### Added
- **`sensor.ai_home_copilot_pipeline_health`**: Consolidated health sensor showing overall pipeline state (`healthy` / `degraded` / `offline`)
  - Deep-checks Core endpoints: Candidates API, Habitus Mining, Brain Graph, Capabilities
  - Attributes expose per-component status for debugging
  - Updates on coordinator poll cycle
- **`ai_home_copilot.trigger_mining`**: On-demand service to request a mining run from Core
  - Optional parameters: `min_confidence`, `min_support`, `min_lift`
  - Fires `ai_home_copilot_mining_result` event with results
  - Automatically polls for new candidates after mining completes
  - Enables "analyze now" button in HA automations and dashboards

#### Technical
- Pipeline Health sensor leverages existing `CopilotApiClient` — no new dependencies
- Mining trigger wired into CandidatePollerModule for seamless candidate → Repairs flow
- Service removed cleanly on unload (last-entry check)

---

## [0.5.1] - 2026-02-10

### 🔄 Decision Sync-Back — Close the Feedback Loop

When a user accepts, dismisses, or defers a candidate in HA Repairs, the decision is now synced back to the Core Add-on. This closes the full feedback loop: Core knows which patterns the user found useful.

#### Added
- **`async_sync_decision_to_core()`**: Best-effort sync of accept/dismiss/defer decisions to Core via `PUT /api/v1/candidates/{id}`
- **`_put_json()` in CopilotApiClient**: New HTTP PUT method for Core API calls
- **All Repairs flows updated**: `CandidateRepairFlow` and `SeedRepairFlow` now sync decisions on accept, dismiss, and defer actions
- **`core_` prefix handling**: Automatically strips the HA-side `core_` prefix to recover the Core UUID

#### Technical
- Sync is best-effort (fire-and-forget with logging) — HA Repairs UX is never blocked by Core connectivity
- Deferred decisions include `retry_after_days` for Core to schedule re-offer
- Uses shared `CopilotApiClient` from coordinator — no additional auth config needed

#### Milestone
- ✅ **Full feedback loop complete**: Mine → Candidate → Offer → User Decision → Core learns

---

## [0.5.0] - 2026-02-10

### 🔌 Candidate Poller – Core → HA Integration Bridge

Connects the Core Add-on's pattern mining pipeline to HA's Repairs UI. This is the key integration piece that closes the end-to-end loop: **mine → candidate → offer → user decision**.

#### Added
- **CandidatePollerModule**: New runtime module that periodically polls Core's `/api/v1/candidates?state=pending` (every 5 min)
- **Automatic Repairs creation**: Pending candidates from Core are converted into HA Repairs issues with evidence display (support/confidence/lift)
- **Bidirectional state sync**: After offering a candidate, marks it as `offered` in Core to prevent duplicate offers
- **Ready-deferred support**: Also picks up deferred candidates whose retry window has passed
- **Pre-populated Blueprint inputs**: Trigger/target entities from the pattern metadata are pre-filled in the Blueprint apply flow
- **30s startup delay**: First poll waits for Core Add-on to be ready before querying

#### Technical
- New module: `core/modules/candidate_poller.py`
- Registered in CopilotRuntime alongside existing modules
- Uses shared `CopilotApiClient` from coordinator — no additional auth setup needed
- Poll count tracked in `hass.data` for diagnostics
- Privacy-first: all data stays local between Core and HA

#### Milestone
- 🎯 **v0.5.0 marks the first end-to-end integration release**: Core mines patterns → creates candidates → HA polls → offers via Repairs → user decides

---

## [0.4.9] - 2026-02-10

### 🔗 N1 Enhanced Blueprint Flow UX (Better Repairs Text)

Completes PROJECT_PLAN N1 UX improvements for the automation suggestion workflow.

#### Enhanced
- **Step-by-step Blueprint Instructions**: Repairs now provide clear numbered steps to implement suggestions
  1. Go to Settings → Automations & Scenes → Blueprints
  2. Import CoPilot blueprint using the provided link
  3. Configure automation
  4. Return and click Fix to complete
- **Direct Blueprint Links**: Each suggestion includes a clickable link to the CoPilot A→B Blueprint
- **Improved UX Flow**: Clearer guidance reduces confusion and makes automation creation more straightforward
- **Multilingual Support**: Enhanced instructions available in German and English

#### Technical
- `suggest.py`: Added blueprint_url to placeholders for candidate_suggestion 
- Updated translation files (de.json, en.json, strings.json) with enhanced Repairs text
- Better integration between Repairs UI and Blueprint workflow

This completes the N1 milestone for evidence display and Blueprint flow improvements.

## [0.4.8] - 2026-02-10

### 📊 N1 Enhanced Evidence Display (Transparency)

Implements PROJECT_PLAN N1 requirement to display evidence information in Repairs UI for better suggestion transparency.

#### Added
- **Evidence in Suggestion UI**: Candidate suggestions now display statistical confidence metrics
  - Support percentage: How often this pattern was observed
  - Confidence: Statistical confidence in the pattern recognition  
  - Lift: How much more likely this pattern is compared to random
  - Example: "CoPilot Vorschlag: A→B Pattern (Support: 85% | Konfidenz: 92% | Lift: 3.2)"

#### Enhanced
- **Transparent Automation Suggestions**: Users can now see the statistical basis behind CoPilot recommendations
- **Better UX Flow**: Evidence data is seamlessly integrated into existing Repairs and Blueprint workflows
- **Multilingual Support**: Evidence display works in both German and English interfaces

#### Technical
- Enhanced `suggest.py` to extract and format evidence data from candidate snapshots
- Updated translation strings (de.json, en.json, strings.json) with evidence placeholders
- Evidence formatting handles missing data gracefully (empty string when no evidence available)
- Maintains backward compatibility with candidates without evidence data

This enhancement addresses governance and transparency requirements by making the AI decision-making process more visible to users.

## [0.4.7] - 2026-02-10

### 🫀 N3 Forwarder Quality Enhancements

Enhanced N3 event forwarder with heartbeat monitoring and improved zone inference per Alpha Worker specification.

#### Added
- **Heartbeat Envelopes**: Periodic health monitoring messages sent to Core every 60 seconds
  - Contains entity counts by domain, pending events, and system health indicators
  - Configurable interval via `heartbeat_interval` (default: 60s)
  - Can be disabled via `heartbeat_enabled: false`
- **State-based Zone Inference**: Improved zone detection for `person` and `device_tracker` entities
  - Uses state value (e.g., "bedroom", "office") as zone when no static mapping exists
  - Handles common HA zone states like "home", "not_home" intelligently
  - Falls back to device/area-based static mapping

#### Technical
- Follows N3 specification for Core health monitoring
- Heartbeat envelope format: `{"v":1,"kind":"heartbeat","ts":"...","src":"ha","entity_count":142}`
- Enhanced statistics include heartbeat configuration
- Maintains backward compatibility with existing configurations

#### Configuration
```yaml
forwarder:
  heartbeat_enabled: true    # Enable heartbeat monitoring (default: true)  
  heartbeat_interval: 60     # Heartbeat interval in seconds (default: 60)
```

## [0.4.6] - 2026-02-10

### 🧠 Brain Dashboard Summary Button

New diagnostic button to fetch comprehensive brain graph health summary from Core Add-on.

#### Added
- **Brain Dashboard Summary Button** (`button.ai_home_copilot_brain_dashboard_summary`):
  - Fetches brain graph health metrics via new `/api/v1/dashboard/brain-summary` Core API
  - Displays consolidated summary: node/edge counts, 24h activity, health score (0-100)
  - Shows actionable recommendations for improving brain graph data collection
  - Enabled by default in diagnostic entity category

#### Enhanced
- **Better Brain Graph Visibility**: Users can quickly assess brain graph health without technical details
- **Actionable Insights**: Recommendations guide users on entity allowlist optimization
- **Health Scoring**: Clear 0-100 health score with status indicators (Healthy/Active/Learning/Initializing)

#### Technical Implementation
- Integrates with Core Add-on v0.4.9 dashboard APIs
- Uses existing `async_call_core_api` infrastructure for Core communication
- Formats technical data into user-friendly notification summaries
- Graceful error handling with informative error messages

#### Quality Assurance
- ✅ Full py_compile validation for button.py changes
- ✅ Backwards compatible with existing Core API infrastructure
- ✅ Error handling for Core Add-on unavailable scenarios
- ✅ Clear notification format with health status and recommendations

## [0.4.5] - 2026-02-10

### 🎯 Configurable Event Forwarder Entity Allowlist

Enhanced the events forwarder with configurable entity filtering for better privacy and performance control.

#### Enhanced
- **Flexible Entity Selection**: Choose which entity types to forward (Habitus zones, media players, additional entities)
- **Media Player Integration**: Automatically include configured music and TV media players in forwarder allowlist
- **Additional Entities**: Add custom entity IDs via comma-separated configuration field
- **Better Zone Mapping**: Media players automatically mapped to "media" zone for enhanced categorization
- **Privacy Controls**: Fine-grained control over which Home Assistant entities are shared with Core

#### Technical
- **Configurable Allowlist**: Three new config options for entity filtering control
- **Zone-aware Categorization**: Entities properly mapped to zones (Habitus, media, additional) for better context
- **Backwards Compatible**: Existing behavior preserved with sensible defaults (Habitus zones + media players enabled)
- **Performance Optimized**: Only subscribe to state changes for explicitly allowed entities

#### Added
- `events_forwarder_include_habitus_zones` (default: true) - Include entities from Habitus zones
- `events_forwarder_include_media_players` (default: true) - Include configured music/TV media players  
- `events_forwarder_additional_entities` - CSV list of additional entity IDs to forward

This enhancement provides users with granular control over data privacy while maintaining the intelligent defaults that work well for most setups.

## [0.4.4] - 2026-02-10

### 🔧 Enhanced Error Handling & Diagnostics

Improved error handling throughout the integration with better diagnostics and debugging information.

#### Enhanced
- **Structured Error Tracking**: New error handling framework with privacy-first traceback capture
- **Better Diagnostics**: Enhanced error digest with traceback summaries and context information
- **Improved Logging**: Context-aware error logging with sanitized tracebacks for easier debugging
- **Config Flow Debug**: Better error reporting during initial setup and configuration validation

#### Technical
- **Privacy-Safe Tracebacks**: Automatic path sanitization and sensitive data redaction in error logs
- **Error Classification**: Smart categorization of network, auth, and parsing errors with helpful hints
- **Diagnostic Integration**: Errors automatically captured in dev_surface error digest for support
- **Convenient API**: Simple `track_error()` function for consistent error handling across modules

#### Bug Fixes
- **Brain Graph Sync**: Better error context for connection failures and API timeouts
- **Config Validation**: More detailed logging when connection tests fail during setup

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