# Release Notes Template - PilotSuite Core

## [x.x.x] - YYYY-MM-DD — FEATURE/BUGFIX

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Testing
- pytest passed: X tests
- hassfest: ✅ OK
- local Ollama: ✅ OK

### Release Checklist
- [ ] CHANGELOG.md aktualisiert
- [ ] Version in `copilot_core/config.yaml` bumped
- [ ] Commit mit `release: v.x.x.y` prefix
- [ ] Tag erstellt `v.x.x.y`
- [ ] Branch gepusht

---

## Beispiel

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
