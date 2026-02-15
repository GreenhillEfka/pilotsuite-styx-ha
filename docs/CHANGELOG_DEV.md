# CHANGELOG_DEV (WIP)

Dieses Dokument listet **Work-in-progress** Änderungen, die noch **nicht** als Release getaggt sind.

- Stable Releases stehen in `CHANGELOG.md` (Tags `vX.Y.Z`).
- Dieser Dev-Log ist bewusst kurz: 1–3 Bulletpoints pro Thema.

## Unreleased (development)

### WIP: v0.8.0 (Multi-User Preference Learning)

**Status:** Phase 1 Implementation - User Detection + Preference Storage

#### Added
- **👥 Multi-User Preference Learning (MUPL) Module**: Phase 1 of user detection and preference learning
  - Automatic discovery of `person.*` entities from Home Assistant
  - Presence tracking via state change subscriptions
  - Preference storage with exponential smoothing (α=0.3)
  - Device affinity tracking (which user uses which device)
  - Privacy-first: All data stored locally in HA storage, opt-in by default
  - Services: `mupl_learn_preference`, `mupl_set_user_priority`, `mupl_delete_user_data`, `mupl_export_user_data`, `mupl_detect_active_users`, `mupl_get_aggregated_mood`
  - Entities: `sensor.ai_copilot_active_users`, `sensor.ai_copilot_mood_{user}`
  - Config options: `mupl_enabled`, `mupl_privacy_mode`, `mupl_min_interactions`, `mupl_retention_days`

- **📊 User-Specific Mood**: Extended mood context to support per-user mood tracking
  - Each user gets their own mood sensor with comfort/frugality/joy weights
  - Aggregated mood for multi-user conflict resolution (priority-weighted)
  - Integration with existing Mood Context module

- **🔒 Privacy Features**: GDPR-compliant data handling
  - `mupl_delete_user_data`: Delete all stored data for a user
  - `mupl_export_user_data`: Export all data for a user (data portability)
  - Configurable retention (default 90 days)
  - Opt-in privacy mode (default)

#### Design Document
- `docs/MUPL_DESIGN.md`: Complete architecture, data model, and implementation phases

#### Next Phases
- Phase 2: Action Attribution + Learning (service call context analysis)
- Phase 3: Multi-User Mood + Aggregation (conflict resolution UI)
- Phase 4: UI Integration + Services (dashboard cards, preference UI)

### WIP: v0.4.1 (Brain Graph Sync Integration)
**Status:** Implementation complete, compile-clean, integration ready.

#### Added
- **🧠 Brain Graph Sync Module**: Real-time synchronization of HA entities, relationships, and state transitions with Core Brain Graph
  - Syncs areas (zones), devices, entities, and their relationships to Core `/api/v1/graph` endpoints
  - Tracks state changes and service calls as graph nodes and edges  
  - Privacy-first design with essential metadata only and anonymized state patterns
  - Background synchronization with Core Brain Graph knowledge representation system
  - Complete initial sync of HA registries (area, device, entity) plus real-time event handling
  - Automatic deduplication and bounded event tracking to prevent memory leaks
  - Integration with existing runtime module system
  - API: `/api/v1/graph/stats`, `/api/v1/graph/state`, `/snapshot.svg` endpoints consumed
- **Module Framework Extension**: Added `brain_graph_sync` to standard module list with proper lifecycle management

### Candidate: v0.3.2-rc.1 (Tag System v0.1 HA Integration)
**Status:** Release-ready for approval (code-complete, compile-clean, integration tests scaffolding ready).

#### Added
- **Tag System Service (`tag_sync.py`):** Pulls canonical tag registry + assignments from Core.
  - `async_pull_tag_system_snapshot()`: Fetches `/api/v1/tag-system/tags` and `/assignments`, imports canonical tags, replaces assignment snapshot, materializes labels.
  - Respects tag materialization policy: `confirmed` tags → HA labels, `pending`/`learned`/`candidate` → skipped unless explicitly confirmed.
  - Stores tags/assignments/metadata in HA `.storage` for diffing and history tracking.

- **Tag Registry Store (HA-side `tag_registry.py`):**
  - Local tag registry mirroring Core canonical tags (title, icon, color, display names).
  - Assignment snapshot tracking (subject_kind:subject_id → tag_ids).
  - User-alias support: discovers existing HA labels as `user.*` read-only mirrors.
  - Labeling API adapters for entity/device/area registries (defensive signature compatibility for multiple HA versions).

- **Label Materialization (`async_sync_labels_now()`):**
  - Ensures HA labels exist for confirmed tags (creates with icon/color if available).
  - Applies labels to supported subjects (entity/device/area).
  - Imports and preserves existing HA labels as read-only `user.*` aliases.
  - Defensive error handling for older HA versions lacking label support.

#### Tests
- Unit tests: `test_tag_utils.py` (7 tests for tag logic, user-tag detection, materialization policy).
- Integration test scaffolding: `test_tag_sync_integration.py` (mock-based roundtrip validation, ready for pytest runner).
- Compilation: `python3 -m compileall custom_components/ai_home_copilot` ✓.

#### Security
- No external API calls except to Core (validated token-based auth inherited from integration config).
- Labels are materialized locally; no Habitus data or learning artifacts leave Home Assistant.

#### Breaking Changes
- None (new module).

#### Notes
- Full HA integration tests require pytest + Home Assistant test framework (deferred to CI phase).
- Pairs with Core v0.4.0-rc.1 or later.

### Just Completed (2026-02-10 04:09 CET)

#### Added: N3 Event Forwarder (Privacy-First HA→Core Event Pipeline)
- **`forwarder_n3.py`**: Complete implementation per N3 Worker specification.
  - **Privacy-first envelope**: Stable schema v1 with domain projections, redaction policy, zone enrichment.
  - **Minimal attribute projections**: Only actionable attributes forwarded (brightness, temperature, etc.), no metadata leakage.
  - **Automatic redaction**: GPS coordinates, tokens, context IDs truncated, friendly names opt-out by default.
  - **Zone mapping**: Entity→zone_id enrichment from HA area registry.
  - **Batching & persistence**: Configurable batch size (default 50), flush interval (500ms), persistent queue across HA restarts.
  - **Idempotency**: Context-based deduplication with configurable TTL (default 120s).

- **Dual event support**: 
  - `state_changed`: Full state delta with old/new projections.
  - `call_service`: Intent forwarding for safe domains (light, climate, etc.), blocked egress domains (notify, rest_command).

- **Services integration**: 
  - `forwarder_n3_start`: Initialize N3 forwarder for config entry.
  - `forwarder_n3_stop`: Gracefully shutdown with state persistence.
  - `forwarder_n3_stats`: Runtime statistics (queue sizes, zone mappings, throughput).

#### Tests
- Unit test scaffolding: `test_forwarder_n3_simple.py` (11 tests covering projections, redaction, envelope creation).
- Compilation: `python3 -m compileall custom_components/ai_home_copilot/forwarder_n3.py` ✓.

#### Why This Step
The existing EventsForwarderModule used legacy envelope format. N3 forwarder implements the privacy-first specification from Worker N3 report, completing the HA→Core data pipeline with proper redaction and governance policies.

#### Next
- Integration testing with Core `/api/v1/events` endpoint.
- Performance validation under high-frequency events.

### In Arbeit
- Repairs/Blueprints: governance-first Apply-Flow (confirm-first) + Transaction-Log (WIP)
- dev_surface: UI Buttons + PilotSuite toggle (WIP integriert)
- diagnostics_contract: contract-shaped Diagnostics + Support-Bundle (WIP integriert) 
