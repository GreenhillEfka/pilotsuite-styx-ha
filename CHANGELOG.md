# CHANGELOG - AI Home CoPilot Core

## [0.4.4] - 2026-02-10

### Added  
- **Candidate Storage System** — vollständige Automation-Vorschlag-Lifecycle-Verwaltung:
  - **REST API**: `/api/v1/candidates` für Create/Read/Update von Suggestion-Kandidaten
  - **Persistence**: JSON-basierte lokale Speicherung mit atomischen Schreibvorgängen
  - **Lifecycle States**: pending → offered → accepted/dismissed/deferred mit Retry-Logic
  - **Evidence Tracking**: Support/Confidence/Lift Metriken für jede Suggestion  
  - **Cleanup**: Automatische Entfernung alter accepted/dismissed Kandidaten

### Technical Details
- Candidate Store: `/data/candidates.json` mit atomischen Updates via temp files
- API Endpoints: GET/POST `/api/v1/candidates`, GET/PUT `/api/v1/candidates/{id}`, GET `/api/v1/candidates/stats`
- Privacy-First: Alle Daten bleiben lokal, keine externe Übertragung
- N2 Core API Milestone: Candidate storage foundations für HA Repairs Integration

## [0.4.3] - 2026-02-10

### Enhanced
- **Brain Graph Intelligence** — erweiterte Zone-Inferenz und Intent-Tracking basierend auf Alpha Worker N3/N4 Spezifikation:
  - **Zone-Inferenz**: Multi-Source Zone-Erkennung (state values, friendly_name patterns, entity_id patterns) mit konfidenz-basierter Gewichtung
  - **Intentional Actions**: Service Calls erhalten erhöhte Salienz (2.0x) + stärkere Edges zu betroffenen Entities (1.5x weight)
  - **Spatial Intent**: Service → Entity → Zone Ketten für räumliche Kontext-Ableitung  
  - **Trigger Inference**: Context parent_id basierte Kausalitäts-Erkennung zwischen Events
  - **Pattern API**: Neuer `/api/v1/graph/patterns` Endpunkt für häufig kontrollierte Entities und Zone-Activity-Hubs
  - **Device Integration**: device_id → Entity Verknüpfungen für Hardware-Context

### Technical Details
- Implementiert Alpha Worker N3 "Forwarder Quality" + N4 "Brain Graph Core" Empfehlungen
- Erhöhte Salience für interaktive Domains (light, switch, cover, media_player)  
- Confidence-weighted zone links: Direct state (1.0) > Friendly name (0.7) > Entity name (0.5)
- Pattern inference für Automation-Hints und UI-Priorisierung

## [0.4.2] - 2026-02-10

### Added
- **Event Processing Pipeline** — completes the real-time data flow from HA → EventStore → BrainGraph
  - `EventProcessor` bridges event ingest with Brain Graph service for automatic knowledge graph updates
  - State changes create entity + zone nodes with `located_in` relationship edges
  - Service calls create service nodes with `targets` edges to affected entities (higher salience for intentional actions)
  - Post-ingest callback hook (non-blocking) enables pluggable downstream consumers
  - `EventStore.ingest_batch` now returns accepted events for immediate downstream processing
  - **11 new unit tests** (total: 76 across all Core modules)

## [0.4.1] - 2026-02-10

### Added
- **Brain Graph Module** (`/api/v1/graph/*`): Complete knowledge representation system
  - **`/api/v1/graph/state`**: JSON API for bounded graph state with filtering (kind, domain, center/hops, limits)
  - **`/api/v1/graph/snapshot.svg`**: DOT/SVG visualization with themes (light/dark), layouts (dot/neato/fdp), hard render limits
  - **`/api/v1/graph/stats`**: Graph statistics + configuration (node/edge counts, limits, decay parameters)
  - **`/api/v1/graph/prune`**: Manual pruning trigger
  - **Privacy-first storage**: PII redaction, bounded metadata (2KB max), automatic salience management
  - **Exponential decay**: 24h half-life for nodes, 12h for edges with effective score calculation
  - **SQLite backend**: Bounded capacity (500 nodes, 1500 edges), automatic pruning, neighborhood queries
  - **HA event processing**: Hooks for state_changed and call_service events
  - **Complete test coverage**: 27 unit tests covering privacy, bounds, decay, pruning, neighborhood queries
- **Dependencies**: Added `graphviz` package to Dockerfile for SVG rendering

### Technical Details
- This establishes the central knowledge representation for entity/zone/device relationships
- Privacy-first design with automatic PII redaction and bounded storage
- No breaking changes, new endpoints accessible immediately
- All compile checks and unit tests passing ✓

---

## [0.4.0] - 2026-02-10

### 🎉 Major Release: Tag System + Event Pipeline Foundation

This release introduces the foundational data architecture for the AI Home CoPilot system.

#### Added
- **Tag System Module** (`/api/v1/tag-system`): Complete privacy-first tag registry and assignment management
  - Canonical tag definitions with multi-language support
  - Persistent tag-assignment store with CRUD operations
  - Subject validation (entity/device/area/automation/scene/script)
  - Default tags: `aicp.kind.light`, `aicp.role.safety_critical`, `aicp.state.needs_repair`, `sys.debug.no_export`

- **Event Ingest Pipeline** (`/api/v1/events`): HA→Core data forwarding infrastructure
  - Bounded ring buffer with JSONL persistence
  - Thread-safe deduplication with TTL-based cleanup
  - Privacy-first validation and context ID truncation
  - Query endpoints with domain/entity/zone/temporal filters
  - Comprehensive statistics and diagnostics

- **API Security**: Shared authentication helper for token-based endpoint protection

#### Technical
- **Dependencies**: Added PyYAML 6.0.1 for tag registry YAML parsing
- **Storage**: Configurable paths via environment variables
- **Testing**: 19+ unit tests covering core functionality (tag registry, event store, API validation)

#### Developer Notes
- All tests passing ✓
- Code compiles cleanly with `python3 -m compileall`
- Ready for production deployment
- Privacy-first design with automatic redaction policies

---

## [0.1.1] - 2026-02-07

### Added
- Initial MVP scaffold with health endpoints
- Basic service framework
- Ingress configuration for web UI access

## [0.1.0] - 2026-02-07

### Added
- Initial release
- Core service foundations