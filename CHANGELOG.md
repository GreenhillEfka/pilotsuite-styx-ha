# CHANGELOG - PilotSuite HA Integration

## [0.14.1-alpha.2] - 2026-02-17

### Fixed
- **Port-Konflikt:** DEFAULT_PORT 8099 → 8909 korrigiert
  - `const.py`: DEFAULT_PORT auf 8909
  - `forwarder_n3.py`: core_url Fallback auf localhost:8909
  - `services_setup.py`: core_url Fallback auf localhost:8909
  - `README.md`: Alle Port-Referenzen auf 8909

### Tests
- Syntax-Check: ✅ const.py, forwarder_n3.py, services_setup.py kompilieren
- Port-Konfiguration: ✅ HACS Integration mit Port 8909 konfigurierbar

---

## [0.14.1-alpha.1] - 2026-02-17

### Added
- **Mood Module v0.2 Integration**: API-Integration mit Core Add-on `/api/v1/mood/*` endpoints
  - Zone orchestration via `mood_module.py`
  - Entity tracking für motion/light/media/illuminance
  - Event-driven + polling-based re-evaluation
  - Character system integration für mood weighting
- **Error Isolation**: Modul-Setup mit try/except + `_LOGGER.exception`
- **Performance Module**: `performance.py` mit TTLCache für Mood-Inference

### Changed
- **PilotSuite Umbenennung** (Display-Namen, Domain bleibt `ai_home_copilot`)
- **Duplicate Entity ID Fix** (`CopilotBrainDashboardSummaryButton` aus `button_system.py` entfernt, kanonische Quelle ist `button_debug.py`)

### Fixed
- **Token-Auth Bug (P0)**: Bereits in v0.14.0-alpha.1 behoben – dokumentiert in PROJECT_STATUS.md
- **Security Fixes**: Alle Endpoints mit try/except abgesichert

### Documentation
- Updated PILOTSUITE_ROADMAP_2026.md mit P0.3 + P1.1 Fortschritt

### Tests
- Mood Module: ✅ Syntax validated
- Core Integration: ✅ HTTP API Endpoints synced

---

## [0.14.0-alpha.1] - 2026-02-16

### Changed
- **PilotSuite Umbenennung** (Display-Namen, Domain bleibt `ai_home_copilot`)
- **Duplicate Entity ID Fix** (`CopilotBrainDashboardSummaryButton` aus `button_system.py` entfernt, kanonische Quelle ist `button_debug.py`)
- **Household/Altersgruppen-Modul**
- **Webhook Push Integration**
- **Zone Aggregation Pattern**
- **Deutsche Dokumentation** (CLAUDE.md, USER_MANUAL.md)
- **Multi-User Test Suite**
