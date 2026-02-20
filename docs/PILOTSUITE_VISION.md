# PILOTSUITE_VISION.md - AI Home CoPilot Vision & Architecture

> **Project:** AI Home CoPilot (AI Home Copilot)  
> **Version:** 0.12.1 (HA Integration) + 0.7.0 (Core Add-on)  
> **Status:** Active Development

---

## 🎯 Vision

AI Home CoPilot is a privacy-first, local AI assistant for Home Assistant that learns your home's patterns and suggests intelligent automations. It transforms raw entity data into actionable insights while keeping all data on-premises.

**Core Principles:**
- **Local-first** — No cloud dependency, all processing happens locally
- **Privacy-first** — PII redaction, bounded storage, no external calls
- **Governance-first** — Suggestions before actions, human-in-the-loop
- **Safe defaults** — Bounded stores, optional persistence

---

## 🏗️ Current Architecture

### Two-Project Model

AI Home CoPilot consists of two separate but tightly integrated projects:

| Project | Version | Purpose |
|---------|---------|---------|
| **HA Integration** | v0.12.1 | Frontend, Entities, Dashboard Cards, Services |
| **Core Add-on** | v0.7.0 | Backend, API, Brain Graph, Tag System, Habitus Mining |

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Home Assistant                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              HA Integration (ai_home_copilot)            │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │   Entities  │  │   Cards     │  │   Services      │  │  │
│  │  │ (Sensors,   │  │  (Lovelace) │  │  (User Prefs,   │  │  │
│  │  │  Buttons,   │  │             │  │   Dashboard)    │  │  │
│  │  │  Media)     │  │             │  │                 │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                    Events Forwarder                             │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Core Add-on (copilot_core)                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │  Tag System │  │   Brain     │  │   Habitus       │  │  │
│  │  │  (Tags,     │  │   Graph     │  │   Mining         │  │  │
│  │  │  Assignments│  │   (SQLite)  │  │   (Rules)       │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │   Mood      │  │   Vector     │  │   Knowledge     │  │  │
│  │  │   Engine    │  │   Store      │  │   Graph         │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Event Collection:** HA Integration forwards state changes → Core Add-on
2. **Processing:** Core processes events through EventProcessor → Brain Graph + Knowledge Graph
3. **Learning:** Habitus Miner discovers patterns → Rules stored in Core
4. **Visualization:** Dashboard Cards render insights in Lovelace UI
5. **Interaction:** User interacts via Entities, Buttons, and Services

---

## 🗺️ Zone System

The Zone System provides hierarchical spatial awareness for the smart home.

### Hierarchy

```
Floor (EG, OG, UG)
  └── Area (Wohnbereich, Schlafbereich)
        └── Room (Wohnzimmer, Küche, Bad)
```

### Zone Types

| Type | Description |
|------|-------------|
| `floor` | Entire floors (ground, first, basement) |
| `area` | Logical areas (living space, sleeping area) |
| `room` | Individual rooms |
| `outdoor` | External areas (garden, driveway) |

### Zone Entity Roles

Each entity in a zone can have specific roles:

```python
KNOWN_ROLES = {
    "motion",      # Motion sensors
    "lights",      # Light entities
    "temperature", # Temperature sensors
    "humidity",    # Humidity sensors
    "co2",         # CO2 sensors
    "pressure",    # Pressure sensors
    "noise",       # Noise sensors
    "heating",     # Heating controllers
    "door",        # Door sensors/locks
    "window",      # Window sensors
    "cover",       # Blinds, curtains
    "lock",        # Door locks
    "media",       # Media players
    "power",       # Power monitors
    "energy",      # Energy consumption
    "brightness",  # Brightness sensors
    "other"        # Miscellaneous
}
```

### Zone States

Zones operate in a state machine:

| State | Description |
|-------|-------------|
| `idle` | Normal state, no activity |
| `active` | Currently occupied/active |
| `transitioning` | State change in progress |
| `disabled` | Zone disabled |
| `error` | Error condition |

### Brain Graph Integration

- Each zone has a `graph_node_id` in the Brain Graph
- Automatic edge connections to entities via `located_in` relationships
- Bidirectional links (Zone ↔ Entity) for bidirectional queries

### Storage

Zones are persisted in `habitus_zones_store_v2.py` with:
- JSON/YAML bulk editor support
- Real-time signal updates for UI synchronization

---

## 🏷️ Tag System Integration

The Tag System provides semantic labeling for entities and devices.

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Tag Registry  │────▶│ Tag Assignments │────▶│   Materialize  │
│   (YAML defs)   │     │   (JSON store)   │     │   to HA Labels │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Tag Structure

Tags follow a hierarchical naming convention:

```
aicp.<category>.<name>
```

**Default Tags:**

| Category | Examples |
|----------|----------|
| `kind` | `aicp.kind.light`, `aicp.kind.switch`, `aicp.kind.sensor` |
| `role` | `aicp.role.safety_critical`, `aicp.role.security` |
| `state` | `aicp.state.needs_repair`, `aicp.state.low_battery` |
| `sys` | `aicp.sys.debug.no_export` |

### Subject Types

Tags can be assigned to:

- `entity` — Home Assistant entities
- `device` — Devices
- `area` — Areas/Zones
- `automation` — Automations
- `scene` — Scenes
- `script` — Scripts
- `helper` — Helpers

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/tag-system/tags` | GET | Get canonical tag registry |
| `/api/v1/tag-system/assignments` | GET | List tag assignments (filtered) |
| `/api/v1/tag-system/assignments` | POST | Upsert tag assignment |

### Tag → Zone Integration

Tags and Zones work together:

1. **Tag-based Zone Rules:** Tags can define zone membership criteria
2. **Zone-based Tag Suggestions:** Zones suggest relevant tags for entities
3. **Cross-referencing:** Brain Graph links tags ↔ zones ↔ entities

---

## 🔐 Security Features

### Current Security Implementation

| Feature | Status | Location |
|---------|--------|----------|
| JWT Authentication | ✅ Implemented | `copilot_core/api/security.py` |
| Input Validation | ⚠️ Partial | Various API endpoints |
| Rate Limiting | ⚠️ Partial | Event ingest |
| PII Redaction | ✅ Implemented | Brain Graph, Event Store |
| Bounded Storage | ✅ Implemented | All stores |
| Source Allowlisting | ✅ Implemented | Event ingest |

### Authentication

All Core API endpoints require `X-Auth-Token` header:

```http
X-Auth-Token: your-secret-token
```

Token validation is handled by `copilot_core/api/security.py`.

### Privacy-First Design

- **No PII Storage:** Sensitive data is redacted before storage
- **Bounded Metadata:** Max 2KB per node metadata
- **Local-Only:** No external API calls, all processing on-prem
- **Optional Persistence:** Users can disable JSONL persistence

### Known Security Issues (Addressing)

| Issue | Priority | Status |
|-------|----------|--------|
| Auth Bypass | P0 | In Progress |
| Command Injection | P0 | In Progress |
| Rate Limiting | P1 | Partial |
| Input Validation | P1 | In Progress |
| Hashing (SHA1→BLAKE2) | P2 | Planned |

### Event Security

- Source allowlisting for incoming events
- Context ID truncation (12 chars) for privacy
- TTL-based deduplication prevents replay attacks

---

## 📊 Brain Graph

The Brain Graph is the central knowledge representation for entity/zone/device relationships.

### Features

- **SQLite-backed:** Persistent storage with automatic pruning
- **Bounded Capacity:** Default 500 nodes, 1500 edges
- **Exponential Decay:** Node weights decrease over time
- **Privacy-First:** PII redaction, bounded metadata
- **Visualization:** DOT/SVG rendering with themes

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v1/graph/state` | JSON state with filtering |
| `/api/v1/graph/snapshot.svg` | Visual graph export |
| `/api/v1/graph/stats` | Graph statistics |
| `/api/v1/graph/prune` | Manual prune trigger |

### Node Types

- **Entity Nodes:** HA entities with state
- **Zone Nodes:** Zone hierarchy
- **Service Nodes:** Service calls
- **Event Nodes:** Significant events

---

## 🔄 Module Overview

### HA Integration Modules (20+)

| Module | Purpose |
|--------|---------|
| `brain_graph_sync` | Sync entities to Brain Graph |
| `habitus_miner` | Pattern discovery |
| `candidate_poller` | Poll for automation candidates |
| `media_context` | Media player context |
| `mood` / `mood_context` | Mood tracking |
| `energy_context` | Energy monitoring |
| `weather_context` | Weather integration |
| `camera_context` | Camera feeds |
| `knowledge_graph_sync` | Knowledge Graph sync |
| `unifi_context` | UniFi network integration |

### Core Add-on APIs (25+)

| API | Purpose |
|-----|---------|
| `blueprint.py` | Blueprint management |
| `candidates.py` | Candidate system |
| `habitus.py` | Habitus rules |
| `tag_system.py` | Tag management |
| `mood.py` | Mood tracking |
| `neurons.py` | Neuron entities |
| `graph.py` | Brain Graph operations |
| `search.py` | Search API |

---

## 🚀 Getting Started

1. **Install Core Add-on:** Install via Home Assistant Add-on Store
2. **Install HA Integration:** Install via HACS
3. **Configure:** Set up authentication token
4. **Enjoy:** Let AI Home CoPilot learn your home

**Default Port:** 8909  
**Health Check:** `http://<HA_IP>:8909/health`

---

## 📈 Roadmap

### Q1 2026
- [ ] P0 Security Fixes (Auth Bypass, Command Injection)
- [ ] Input Validation Complete
- [ ] Dashboard Auto-Import

### Q2 2026
- [ ] ML Training Pipeline
- [ ] ReactBoard Integration
- [ ] Full v1.0 Feature Parity

---

*Last Updated: 2026-02-16*
