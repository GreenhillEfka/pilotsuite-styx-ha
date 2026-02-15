# AI Home CoPilot - Project Index

> Quick reference for current status, structure, and next steps.

## Current Release

**Core Add-on v0.4.16** (2026-02-15) — `main` branch

### Features
- **Habitus Zones v2** — Zone-aware pattern mining
- **Tag System v0.2** — Decision Matrix with HA Labels integration
- **Neurons**: SystemHealth, UniFi, Energy
- **Brain Graph** — Configurable limits (nodes/edges/half-life)
- **Security** — log_fixer_tx API authentication (v0.4.16)

### API Endpoints
| Module | Endpoints |
|--------|-----------|
| Habitus | `/api/v1/habitus/*` (mine, zones, candidates) |
| Tags v2 | `/api/v1/tags2/*` (tags, subjects, assignments) |
| UniFi | `/api/v1/unifi/*` (wan, clients, roaming, baselines) |
| Energy | `/api/v1/energy/*` |
| SystemHealth | `/api/v1/system-health/*` |

## Development Branches

| Branch | Status | Description |
|--------|--------|-------------|
| `main` | ✅ Stable | Production releases |
| `dev-habitus-dashboard-cards` | 🚧 WIP | Dashboard cards API + Habitus Miner v0.1 |
| `dev-media-context-v2` | 🚧 WIP | Media context v2 docs |
| `dev-idempotency-dedupe-events` | 📋 Planned | Event deduplication |

## Quick Links

| Doc | Path |
|-----|------|
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
├── CHANGELOG.md         # Version history
├── INDEX.md             # This file
└── README.md            # Install guide
```

## Next Milestones

- [ ] Interactive Brain Graph Panel
- [ ] Multi-user learning
- [ ] Performance optimization
- [ ] Habitus Dashboard Cards release
- [ ] Path allowlist for log_fixer_tx rename operations (P0 follow-up)

---

*Last updated: 2026-02-15*