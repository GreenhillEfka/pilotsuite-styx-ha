# Changelog - AI Home CoPilot Core Add-on

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
