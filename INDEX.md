# AI Home CoPilot - Project Index

> Quick reference for current status, structure, and next steps.

## Current Release

**Core Add-on v0.4.18** (2026-02-15) — `main` branch

### Latest Updates
- **Knowledge Graph Module**: Neo4j-backed graph storage with SQLite fallback
- **KG API Endpoints**: Full CRUD for nodes/edges, graph queries (semantic, structural, causal, temporal)
- **OpenAPI Specification**: Complete API documentation (`docs/openapi.yaml`)
- **Habitus Dashboard Cards API**: `/api/v1/habitus/dashboard_cards` endpoint
- **Habitus Miner v0.1**: Zone-aware pattern mining backend
- **Security**: log_fixer_tx API authentication

### Features
| Feature | Status |
|---------|--------|
| Knowledge Graph | ✅ Neo4j/SQLite dual backend |
| Habitus Zones v2 | ✅ Zone-aware pattern mining |
| Tag System v0.2 | ✅ Decision Matrix with HA Labels |
| Neurons | ✅ SystemHealth, UniFi, Energy |
| Brain Graph | ✅ Configurable limits |
| Event Deduplication | ✅ Idempotency-Key support |
| OpenAPI Spec | ✅ v0.4.18 |

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
| SystemHealth | `/api/v1/system-health/*` |

## Development Status

| Branch | Status | Description |
|--------|--------|-------------|
| `main` | ✅ Stable | Production releases (v0.4.18) |
| `dev-knowledge-graph` | ✅ Merged | Knowledge Graph module |

## Quick Links

| Doc | Path |
|-----|------|
| API Spec | `docs/openapi.yaml` |
| Start Here | `docs/START_HERE.md` |
| Ethics & Governance | `docs/ETHICS_GOVERNANCE.md` |
| Changelog | `CHANGELOG.md` |
| Install Guide | `README.md` |

## Repository Structure

```
ha-copilot-repo/
├── addons/              # HA Add-on (Core service)
├── custom_components/   # HA Integration (adapter)
├── docs/                # Documentation
│   └── openapi.yaml     # API specification
├── CHANGELOG.md         # Version history
├── INDEX.md             # This file
└── README.md            # Install guide
```

## Next Milestones

- [ ] Knowledge Graph Integration in HA Integration (connect to Core KG API)
- [ ] Client SDK generation from OpenAPI spec
- [ ] Interactive API documentation (Swagger UI)
- [ ] Performance benchmarks
- [ ] Extended neuron modules

---

*Last updated: 2026-02-15*