# CHANGELOG - AI Home CoPilot Core

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