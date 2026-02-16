# Add-on Changelog – AI Home CoPilot Core (MVP)

This file exists so Home Assistant can show an add-on changelog.
For full history, see the repository-level `CHANGELOG.md`.

## 0.8.5
- **Phase 5 Feature: Cross-Home Sync API v0.2**
  - `/api/v1/sharing/discover` - mDNS peer discovery
  - `/api/v1/sharing/share` - Entity sharing registration
  - `/api/v1/sharing/unshare` - Stop sharing entity
  - `/api/v1/sharing/sync` - Real-time state synchronization
  - `/api/v1/sharing/resolve` - Conflict resolution strategies
- **Phase 5 Feature: Collective Intelligence API v0.2**
  - `/api/v1/federated/models` - Local model registration
  - `/api/v1/federated/patterns` - Pattern creation and sharing
  - `/api/v1/federated/peers` - Peer discovery
  - `/api/v1/federated/aggregates` - Aggregate stats from collective
- **Phase 5 Feature: Brain Graph Panel v0.8**
  - Interactive HTML generation with D3.js visualization
  - Zoom/pan support for large graphs (200 nodes, 400 edges)
  - Node filtering by kind, zone, or search
  - Click nodes for detailed metadata display
  - Local-only rendering (no external dependencies)
- **Core API**: `/api/v1/sharing/*` and `/api/v1/federated/*` endpoints fully documented
- **Tests**: 44+ tests passing ✅ (federated_learning + privacy_preserver fixed)

## 0.5.0
- **Knowledge Graph Module**: Neo4j-backed graph storage with SQLite fallback
  - Captures relationships between entities, patterns, moods, and contexts
  - Node types: ENTITY, DOMAIN, AREA, ZONE, PATTERN, MOOD, CAPABILITY, TAG, TIME_CONTEXT
  - Edge types: BELONGS_TO, HAS_CAPABILITY, HAS_TAG, TRIGGERS, CORRELATES_WITH, ACTIVE_DURING, RELATES_TO_MOOD
  - Dual backend: Neo4j (preferred) or SQLite (fallback)
- **Graph Builder**: Build graph from HA states, entities, areas, and tags
- **Pattern Importer**: Import Habitus A→B rules as PATTERN nodes
- **API Endpoints**: `/api/v1/kg/*` for graph queries and management
  - `GET /api/v1/kg/stats` - Graph statistics
  - `GET/POST /api/v1/kg/nodes` - Node CRUD
  - `GET/POST /api/v1/kg/edges` - Edge CRUD
  - `POST /api/v1/kg/query` - Custom graph queries
  - `GET /api/v1/kg/entity/{id}/related` - Get related entities
  - `GET /api/v1/kg/zone/{id}/entities` - Get zone entities
  - `GET /api/v1/kg/mood/{mood}/patterns` - Get mood-related patterns
  - `POST /api/v1/kg/import/entities` - Import from HA states
  - `POST /api/v1/kg/import/patterns` - Import from Habitus miner
- Environment variables for Neo4j:
  - `COPILOT_NEO4J_URI` (default: none, uses SQLite)
  - `COPILOT_NEO4J_USER` (default: neo4j)
  - `COPILOT_NEO4J_PASSWORD`
  - `COPILOT_NEO4J_ENABLED` (default: true)
  - `COPILOT_KG_SQLITE_PATH` (default: /data/knowledge_graph.db)

## 0.2.7
- Brain Graph Ops: `POST /api/v1/graph/ops` (v0.1: touch_edge; idempotent; allowlist: observed_with, controls).

## 0.2.6
- Dev Surface: `GET /api/v1/dev/status`.
- Diagnostics Contract: `GET /api/v1/dev/support_bundle` liefert ein privacy-first, bounded ZIP.
- DevLogs ingest: Payloads werden vor Persistenz best-effort sanitisiert.
- Graph→Candidates Bridge: `GET /api/v1/candidates/graph_candidates` (Preview, bounded).

## 0.2.5
- Brain Graph wird jetzt aus eingehenden `/api/v1/events` Batches gefüttert (privacy-first, bounded).
- Capabilities zeigen `brain_graph.feeding_enabled`.

## 0.2.4
- Events ingest ist jetzt idempotent (TTL+LRU Dedupe); Retries erzeugen keine doppelten Events.
- Neu: Brain Graph Skeleton API (v0.1) unter `/api/v1/graph/state` + `snapshot.svg` (Placeholder).

## 0.2.3
- Logs the listening port on startup.
- `/health` includes the effective port.
- Respects add-on `log_level` option.

## 0.2.2
- Default port changed from 8099 to 8909.

## 0.2.1
- Fix startup crash (DevLogs used current_app at import time).
