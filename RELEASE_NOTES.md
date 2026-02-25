# Release Notes - PilotSuite Core

## [7.26.0] - 2026-02-25 — INPUT NUMBER + ZONES + PATTERN APIs

### Added
- `input_number` API: `/api/v1/input_number` GET/POST
- `zones` API: `/api/v1/zones` GET
- `scene_patterns` API: `/api/v1/scenes/patterns` (record, suggest, summary, clear)
- `routine_patterns` API: `/api/v1/routines` (record, predict, typical, summary, clear)
- `push_notifications` API: `/api/v1/notifications` (send, channels, test)

### Changed
- Manifest v7.26.0
- All new APIs registered in blueprint.py

### Fixed
- Push notifications: fixed syntax error in validation

### Testing
- All API files syntax OK (py_compile)
- Blueprint registration validated

### Release Checklist
- [x] CHANGELOG.md aktualisiert
- [x] Version in `copilot_core/config.yaml` bumped
- [x] Commit mit `release: v7.26.0` prefix
- [x] Tag erstellt `v7.26.0`
- [x] Branch gepusht

---

## [7.8.9] - 2026-02-23 — ERROR ISOLATION + CONNECTION POOLING

### Added
- Module-Crash-Isolation über `ModuleErrorBoundary`
- Connection Pooling für HA-ClientSessions
- Error Dashboard Widget zur Visualisierung

### Changed
- Error handling in `__init__.py` überarbeitet
- Session-Management in `api/__init__.py`

### Fixed
- Haushalts-Error-Kaskaden verhindert
- Resource-Leaks bei HA-Updates

### Testing
- pytest passed: 520 tests
- hassfest: ✅ OK
- local Ollama: ✅ OK
