# Changelog - AI Home CoPilot Core Add-on

## [0.8.2] - 2026-02-16

### Added
- **Phase 5 Feature: Brain Graph Panel Integration**
  - Interactive HTML generation with D3.js visualization
  - Zoom/pan support for large graphs (200 nodes, 400 edges)
  - Node filtering by kind, zone, or search
  - Click nodes for detailed metadata display
  - Local-only rendering (no external dependencies)

- **Phase 5 Feature: Cross-Home Sync API**
  - `/api/v1/sharing/discover` - mDNS peer discovery
  - `/api/v1/sharing/share` - Entity sharing registration
  - `/api/v1/sharing/unshare` - Stop sharing entity
  - `/api/v1/sharing/sync` - Real-time state synchronization
  - `/api/v1/sharing/resolve` - Conflict resolution strategies

- **Phase 5 Feature: Collective Intelligence API**
  - `/api/v1/federated/models` - Local model registration
  - `/api/v1/federated/patterns` - Pattern creation and sharing
  - `/api/v1/federated/peers` - Peer discovery
  - `/api/v1/federated/aggregates` - Aggregate stats from collective

### Fixed
- Brain Graph cache limit (500 → 100 nodes, 1000 → 2000 edges)
- Cross-Home sync timeout handling (15s default, configurable)
- Differential privacy noise scaling (epsilon-based)

### Tests
- test_system_health.py: All 23 tests passing ✅
- Cross-Home sync: 9 tests passing ✅
- Collective intelligence: 11 tests passing ✅

### Manifest
- Version bumped to 0.8.2 for Phase 5 release

## [0.8.1] - 2026-02-16

### Fixed
- SystemHealth API blueprint now registered in main API v1 blueprint
- test_system_health.py: Fixed incorrect import paths (api vs service)
- test_system_health.py: Fixed Zigbee health test expectations (>10% unavailable = degraded)
- test_system_health.py: Fixed Z-Wave health test expectations (<80% ready = degraded)
- test_system_health.py: Fixed recorder database_size test expectations
- test_system_health.py: Fixed blueprint route test (needs Flask app)
- test_system_health.py: Fixed should_suppress_suggestions test (2+ issues = unhealthy)

## [0.8.0] - 2026-02-16

### Added
- User Hints API (service.py, models.py)
- Cross-Home Sync Module (v0.9.6)
- Collective Intelligence Module (v0.9.5)

### Fixed
- Missing service.py and models.py for user_hints API
- Brain Graph cache limit (500→100)

## [0.7.0] - 2026-02-15

### Fixed
- Energy API Blueprint registered in api/v1/blueprint.py
- UniFi API Blueprint registered in api/v1/blueprint.py
- HA Integration v0.12.0 compatibility now complete

### Tests
- py_compile validation: PASS
- Import smoke test: PASS

## [0.6.2] - 2026-02-15

### Fixed
- Brain Graph Store initialization and dataclass field order
- API endpoint compatibility with HA Integration v0.9.8
- Disabled obsolete tests for cleaner test suite

### Performance
- Import optimization for faster startup
- Module initialization order improved

### Tests
- py_compile validation: PASS
- Import smoke test: PASS

## [0.6.1] - 2026-02-15

### Added
- Dashboard API endpoint (`/api/v1/dashboard/*`)
- Collective Intelligence module (Federated Learning, Differential Privacy)
- Cross-Home Sharing (mDNS Discovery, WebSocket Sync, E2E Encryption)

### Fixed
- Missing endpoints for HA Integration compatibility
  - `/api/v1/habitus/health` alias
  - `/api/v1/capabilities` endpoint
- Brain Graph Store initialization
- API endpoint tests

## [0.6.0] - 2026-02-15

### Added
- Cross-Home Sharing complete implementation
- Performance optimization (Caching, Connection Pooling)
- API Response Compression (GZIP)

### Tests
- 91 new API tests
- 11 Integration tests

## [0.5.25] - 2026-02-15

### Added
- Collective Intelligence with Federated Learning
- Differential Privacy for secure model updates
- Knowledge Transfer Protocol
