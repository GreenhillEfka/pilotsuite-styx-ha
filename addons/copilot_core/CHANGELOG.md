## 1.0.0 - 2026-02-19

### PilotSuite v1.0.0 -- First Full Release

The first complete, installable PilotSuite release. A local, privacy-first
AI system that makes your Home Assistant smart home truly intelligent.

### Highlights

- **Web Dashboard**: Beautiful dark-themed ingress panel with live Brain Graph
  visualization, Mood gauges, Habitus patterns, built-in Chat, and system overview.
- **LLM Provider Chain**: Ollama (local, default) with automatic cloud fallback
  (OpenClaw, OpenAI, or any OpenAI-compatible API).
- **Tool-Calling**: 9 HA tools executable via LLM function calling
  (call_service, get_states, get_history, scenes, events, calendar, weather).
- **PilotSuite MCP Server**: `/mcp` endpoint exposing 8 PilotSuite skills
  (mood, brain_graph, habitus, neurons, preferences, household, memory, energy)
  for external AI clients (OpenClaw, Claude Desktop).
- **Telegram Bot**: Long-polling bot forwarding messages through the full chat
  pipeline with tool execution. Config: `telegram.enabled`, `telegram.token`.
- **Obligatory Offline Model**: `qwen3:0.6b` (400MB) always pulled at install,
  guaranteeing offline AI. `qwen3:4b` (2.5GB) as recommended default.
- **Lifelong Learning**: ConversationMemory stores every interaction, extracts
  preferences, and injects learned context into the LLM system prompt.
- **6 Character Presets**: CoPilot, Butler, Energiemanager, Sicherheitswache,
  Freundlicher Assistent, Minimal -- each with unique system prompts.

### New Files
- `llm_provider.py` -- Unified LLM provider with Ollama + Cloud fallback
- `mcp_server.py` -- PilotSuite MCP Server (JSON-RPC 2.0)
- `telegram/` -- Telegram bot module (bot.py, api.py)
- `conversation_memory.py` -- SQLite lifelong learning store
- `templates/dashboard.html` -- Web dashboard (HTML/CSS/JS)

### Breaking Changes
- Default model changed from `lfm2.5-thinking` to `qwen3:4b`
- Default port changed from 8099 to 8909
- Version jump from 0.9.9 to 1.0.0

---

## 0.9.1-alpha.8 - 2026-02-18
- **button_debug.py Modularisierung** (HA Integration)
  - Refactoring: 821 → 60 Zeilen Hauptdatei
  - 8 separate Module für bessere Wartbarkeit
- **HA Integration v0.14.1** released
  - Race Condition Fixes
  - Port-Konflikt behoben (8099)


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
