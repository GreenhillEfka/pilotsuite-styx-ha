# AI Home CoPilot - Project Index

> Quick reference for current status, structure, and next steps.

## Current Release

**Core Add-on v0.8.1** (2026-02-16) — `main` branch

### Latest Updates
- **SystemHealth API**: Blueprint registered, all tests passing
- **Interactive Visualization (Phase 5)**: Full D3.js + React visualization module
- **Brain Graph Panel**: Interactive force-directed graph with zoom/pan
- **Lovelace Cards**: Custom cards for mood, neurons, habitus
- **React Components**: Smooth animations with Framer Motion
- **Multi-User Preference Learning (v0.5.2)**: Persistent JSONL storage
- **Knowledge Graph Module**: Neo4j-backed graph storage with SQLite fallback
- **ML Pattern Recognition (v0.8.19)**: AnomalyDetector, HabitPredictor, EnergyOptimizer

### Features
| Feature | Status |
|---------|--------|
| Interactive Visualization | ✅ Phase 5 Complete |
| Knowledge Graph | ✅ Neo4j/SQLite dual backend |
| Habitus Zones v2 | ✅ Zone-aware pattern mining |
| Tag System v0.2 | ✅ Decision Matrix with HA Labels |
| Neurons | ✅ SystemHealth, UniFi, Energy |
| Brain Graph | ✅ D3.js + React |
| Event Deduplication | ✅ Idempotency-Key support |
| OpenAPI Spec | ✅ v0.7.0 |

### Visualization Components
| Component | Type | Description |
|----------|------|-------------|
| BrainGraphPanel | D3.js | Force-directed entity graph |
| MoodCard | Lovelace | Mood context visualization |
| NeuronsCard | Lovelace | Neuron activity display |
| HabitusCard | Lovelace | Habitus zone selector |
| React Visualization | React | Full dashboard with animations |

### API Endpoints
| Module | Endpoints |
|--------|-----------|
| Knowledge Graph | `/api/v1/kg/*` (stats, nodes, edges, query, import) |
| Habitus | `/api/v1/habitus/*` (status, rules, mine, dashboard_cards, zones) |
| Graph | `/api/v1/graph/*` (state, sync, patterns) |
| Mood | `/api/v1/mood` |
| Tags v2 | `/api/v1/tags2/*` (tags, subjects, assignments) |
| Events | `/api/v1/events` (with idempotency) |
| Candidates | `/api/v1/candidates` |
| UniFi | `/api/v1/unifi/*` (wan, clients, roaming, baselines) |
| Energy | `/api/v1/energy/*` |
| SystemHealth | `/api/v1/system_health/*` |
| User Preferences | `/api/v1/user/*` (preferences, zones, mood) |

## Development Status

| Branch | Status | Description |
|--------|--------|-------------|
| `main` | ✅ Stable | Production releases (v0.8.1) |
| `dev-knowledge-graph` | ✅ Merged | Knowledge Graph module |

## Quick Links

| Doc | Path |
|-----|------|
| API Spec | `docs/openapi.yaml` |
| Visualization Guide | `docs/visualization.md` |
| Start Here | `docs/START_HERE.md` |
| Ethics & Governance | `docs/ETHICS_GOVERNANCE.md` |
| Changelog | `CHANGELOG.md` |
| Install Guide | `README.md` |

## Repository Structure

```
ha-copilot-repo/
├── addons/              # HA Add-on (Core service)
│   └── copilot_core/    # Core service container
├── custom_components/   # HA Integration (adapter)
├── docs/                # Documentation
│   └── openapi.yaml     # API specification
├── sdk/                 # Client SDKs (Python/TypeScript)
├── src/                 # Source modules
│   └── visualizations/  # Phase 5 visualization
├── CHANGELOG.md         # Version history
├── INDEX.md             # This file
└── README.md            # Install guide
```

## Next Milestones

- [x] Interactive Visualization (Phase 5)
- [x] Cross-Home Sharing (v0.6.0)
- [x] Collective Intelligence (v0.6.1)
- [x] SystemHealth API registered
- [ ] Extended neuron modules
- [ ] Performance optimization (caching, connection pooling)

---

*Last updated: 2026-02-16 02:35*