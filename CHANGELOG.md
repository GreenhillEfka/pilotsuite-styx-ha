# CHANGELOG - AI Home CoPilot HA Integration

## [0.4.0] - 2026-02-10

### 🎉 Major Release: Tag System + Event Forwarding

This release establishes the complete HA→Core data pipeline and tag management system.

#### Added
- **Tag Synchronization**: Live sync between Core tag registry and HA labels
  - `tag_registry.py`: Pulls canonical tags from Core `/api/v1/tag-system`
  - `tag_sync.py`: Materializes tags as HA labels with conflict resolution
  - Service: `ai_home_copilot.sync_tags` for manual refresh

- **N3 Event Forwarder**: Privacy-first event streaming to Core
  - `forwarder_n3.py`: Implements envelope v1 schema with domain projections
  - Automatic zone enrichment from HA area registry
  - Comprehensive redaction policy (GPS, tokens, sensitive attributes)
  - Batching, persistence, and idempotency with TTL cleanup
  - Services: `forwarder_n3_start`, `forwarder_n3_stop`, `forwarder_n3_stats`

- **Event Processing**: Support for `state_changed` and `call_service` events
  - Minimal attribute projections (brightness, volume_level, temperature)
  - Trigger inference and intent capture
  - Privacy-first envelope with stable schema versioning

#### Technical
- **Testing**: Unit test coverage for tag utilities and forwarder logic
- **Storage**: Persistent forwarder queue across HA restarts
- **Security**: Token-based authentication with Core Add-on
- **Performance**: Bounded queues with drop-oldest policy under load

#### Developer Notes
- All modules compile cleanly ✓
- Integration tests scaffolded (require full HA environment)
- Ready for production deployment
- Coordinated release with Core Add-on v0.4.0

---

## [0.3.2] - 2026-02-07

### Added
- Enhanced error reporting and debugging capabilities
- Improved stability for diagnostic collection

## [0.3.1] - 2026-02-06

### Added
- Core integration foundations
- Basic diagnostic reporting

## [0.3.0] - 2026-02-05

### Added
- Initial HACS-compatible release
- Configuration flow setup