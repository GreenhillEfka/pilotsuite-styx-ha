# AI Home CoPilot Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Home Assistant                                   │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Custom Integration: ai_home_copilot                             │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────────────┐ │  │
│  │  │  Webhook    │ │  Services   │ │  Core Runtime (Modular)       │ │  │
│  │  │  Receiver   │ │  Registry   │ │  ┌─────────┐ ┌───────────────┐ │ │  │
│  │  └─────────────┘ └─────────────┘ │  │ Modules │ │   Coordinator │ │ │  │
│  │                                  │  └─────────┘ └───────────────┘ │ │  │
│  │                                  └─────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                              │                                            │
│                              │ HTTP/REST API                              │
│                              ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  AI Home CoPilot Core Add-on (Port 8909)                         │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │  Flask REST API Server                                       │ │  │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────────────┐  │ │  │
│  │  │  │ Habitus │ │  Graph  │ │  Mood   │ │  Candidates       │  │ │  │
│  │  │  │  Miner  │ │  Brain  │ │  Core   │ │  Generator        │  │ │  │
│  │  │  └─────────┘ └─────────┘ └─────────┘ └───────────────────┘  │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │  Modules: Vector Store | Tags v2 | Knowledge Graph          │ │  │
│  │  │  │ Neurons | Weather | Multi-User Preferences               │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              │ OpenAPI / Swagger
                              ▼
                    ┌───────────────────────┐
                    │   /docs/              │
                    │   - OpenAPI Spec      │
                    │   - Architecture SVG  │
                    │   - API Examples      │
                    └───────────────────────┘
```

## Module Architecture

### Home Assistant Integration Modules

```
ai_home_copilot/
├── core/
│   ├── modules/
│   │   ├── legacy.py                    # Legacy compatibility wrapper
│   │   ├── events_forwarder.py          # Forward HA events to Core
│   │   ├── habitus_miner.py            # Trigger habitus mining
│   │   ├── candidate_poller.py         # Poll candidates from Core
│   │   ├── brain_graph_sync.py         # Sync graph with HA entities
│   │   ├── mood_context.py             # Poll mood from Core
│   │   ├── media_context.py            # Media playback context
│   │   └── ... (more modules)
│   └── runtime.py                       # Module orchestrator
├── services_setup.py                    # Service registration
├── config_flow.py                       # Integration setup UI
├── blueprints.py                        # Blueprint management
├── repairs.py                           # Repair system integration
├── brain_graph_panel.py                 # Lovelace visualization
├── sensors/
│   ├── ai_home_copilot_online.py
│   ├── ai_home_copilot_version.py
│   └── ai_home_copilot_pipeline_health.py
├── entities/
│   ├── button.py
│   ├── select.py
│   └── text.py
└── custom_components/
    ├── ai_home_copilot/
        ├── tests/
        └── ml/
```

### Core Add-on Modules

```
copilot_core/
├── app.py                               # Main Flask application
├── routes/                              # API route handlers
│   ├── habitus.py                       # A→B rule discovery
│   ├── graph.py                         # Brain graph visualization
│   ├── mood.py                          # Mood context aggregation
│   ├── candidates.py                    # Candidate management
│   ├── neurons.py                       # Neural system state
│   ├── tags.py                          # Tagging system v2
│   ├── vector_store.py                  # Vector embeddings
│   ├── knowledge_graph.py               # Neo4j/SQLite backend
│   ├── weather.py                       # Weather context
│   └── events.py                        # Event ingestion
├── data/                                # Data stores
│   ├── events.py                        # Event storage (JSONL)
│   ├── candidates.py                    # Candidate storage
│   ├── graph_store.py                   # Graph database
│   └── vector_store.py                  # Vector embeddings
├── habitus_miner/                       # Pattern mining engine
│   ├── miner.py                         # A→B rule mining
│   └── scoring.py                       # Confidence scoring
├── brain_graph/                         # Visualization backend
│   ├── builder.py                       # Graph construction
│   └── renderer.py                      # SVG generation
├── neurons/                             # Neural evaluation
│   ├── system_health.py                 # HA system monitoring
│   ├── unifi.py                         # UniFi network analysis
│   └── energy.py                        # Energy consumption analysis
├── collective_intelligence/             # Multi-user learning
│   ├── user_preferences.py              # Preference learning
│   └── mood_scoring.py                  # Mood aggregation
└── tests/                               # Test suite
```

## Data Flow

### Event Ingestion Pipeline

```
Home Assistant Event Bus
          │
          ▼
   EventsForwarderModule
          │
          ▼
   POST /api/v1/events (Core)
          │
          ├───▶ Event Store (JSONL)
          │
          ├───▶ Brain Graph (nodes/edges)
          │
          ├───▶ Pattern Mining (Habitus)
          │
          └───▶ Candidate Generator
                   │
                   ▼
          /api/v1/candidates
                   │
                   ▼
   CandidatePollerModule (HA)
                   │
                   ▼
          Repairs System
                   │
                   ▼
          Blueprint Import
```

### Mood Context Pipeline

```
Core Mood Aggregation
          │
          ├── Media Context (Spotify/Sonos)
          │
          ├── Habitus Patterns (time-based)
          │
          └── User Preferences (per-zone)
                   │
                   ▼
      GET /api/v1/mood
                   │
                   ▼
   MoodContextModule (HA)
                   │
                   ▼
     sensor.ai_home_copilot_mood
                   │
                   ▼
          Repairs Weighting
```

## API Contract

### Authentication

```yaml
securitySchemes:
  ApiKeyAuth:
    type: apiKey
    in: header
    name: X-Auth-Token
```

All endpoints require `X-Auth-Token` header when authentication is enabled.

### Idempotency

Event endpoints support `Idempotency-Key` header for deduplication.

### Response Format

```json
{
  "status": "ok" | "error",
  "data": { ... },
  "message": "optional description"
}
```

## Entity Mapping

### Home Assistant Entities

| Entity Type | Name | Description |
|-------------|------|-------------|
| Binary Sensor | `ai_home_copilot_online` | Core connectivity |
| Sensor | `ai_home_copilot_version` | Integration version |
| Sensor | `ai_home_copilot_pipeline_health` | Core component status |
| Button | `ai_home_copilot_toggle_light` | Test action |
| Sensor | `ai_home_copilot_mood` | Current mood context |

### Core API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/habitus/status` | GET | Miner status |
| `/api/v1/habitus/rules` | GET | Discovered A→B rules |
| `/api/v1/habitus/mine` | POST | Trigger mining |
| `/api/v1/graph/state` | GET | Brain graph data |
| `/api/v1/mood` | GET | Current mood |
| `/api/v1/events` | POST | Ingest events |
| `/api/v1/candidates` | GET | Automation candidates |
| `/api/v1/system-health` | GET | System status |

## Deployment

### HACS Integration

```yaml
repositories:
  - name: AI Home CoPilot
    url: https://github.com/GreenhillEfka/ai-home-copilot-ha
    type: integration
```

### Core Add-on

```yaml
repositories:
  - name: AI Home CoPilot
    url: https://github.com/GreenhillEfka/Home-Assistant-Copilot
    type: git
```

## Versioning

- **HA Integration**: `0.x.y` (HACS version)
- **Core Add-on**: `0.x.y` (Add-on version)
- **API**: `v1` (backward-compatible updates)
