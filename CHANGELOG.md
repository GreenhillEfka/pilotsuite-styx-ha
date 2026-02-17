# Changelog - PilotSuite Core Add-on

## [0.9.1-alpha.1] - 2026-02-17

### Added
- **Mood Engine v0.2 API Endpoints**: Core Add-on `/api/v1/mood/*` API für Zone-Orchestration
  - `POST /api/v1/mood/zones/{zone_name}/orchestrate` - Mood inference + Action execution
  - `POST /api/v1/mood/zones/{zone_name}/force_mood` - Admin override mood
  - `GET /api/v1/mood/zones/{zone_name}/status` - Zone status query
  - `GET /api/v1/mood/zones/status` - All zones status
- **Error Isolation**: Try/except Wrapper für alle API Endpoints (500 Response + Logging)
- **Neural Neurons Integration**: Energy + UniFi Neurons im NeuronManager wiring

### Fixed
- **Security Bug (P0)**: Token-Auth Bug dokumentiert in PROJECT_STATUS.md – bereits in v0.9.0-alpha.1 behoben durch `d8be957` und `bf0c11f`
- **Button Debug Module**: Identifiziert als Wartbarkeits-Risiko (821 Zeilen, 44 functions) – Refactoring geplant für P1.2

### Documentation
- PROJECT_STATUS.md aktualisiert mit aktuellen Status (2026-02-17 16:15)
- PILOTSUITE_ROADMAP_2026.md aktualisiert mit P0.3 + P1.1 Fortschritt

### Tests
- Syntax-Check: ✅ Alle Python-Dateien kompilieren ohne Fehler (py_compile)
- Manifest: ✅ Synced (v0.9.1-alpha.1)

---

## [0.9.0-alpha.1] - 2026-02-16

### Added
- **PilotSuite Umbenennung**: Display-Namen in README, CHANGELOG und Dokumentation aktualisiert. Technische Bezeichner bleiben fuer Abwaertskompatibilitaet unveraendert.
- **NeuronManager Wiring**: Household-Modul und Webhook Callbacks im NeuronManager verdrahtet. Household-Daten fliessen in Neuron-Bewertungen ein.
- **Knowledge Graph/Vector/Neurons Blueprints**: Alle drei Blueprints sind in `api/v1/blueprint.py` registriert und aktiv.
- **Deutsche Dokumentation**: CLAUDE.md, HANDBUCH.md, PROJEKTSTRUKTUR.md erstellt. README.md und CHANGELOG.md aktualisiert.

### Fixed
- **Dockerfile Port-Fix**: Korrektur von Port 8909 zu 8099 im Dockerfile. Der korrekte Port ist 8099 (wie in `main.py` und `config.yaml` definiert).
- **Config durchreichen an init_services**: `_load_options_json()` Ergebnis wird jetzt korrekt als `config` Parameter an `init_services()` uebergeben. Vorher wurde die Konfiguration nicht an alle Services weitergeleitet.

### Documentation
- CLAUDE.md erstellt (Projektkontext fuer KI-Assistenten)
- HANDBUCH.md erstellt (Installations- und Benutzerhandbuch)
- PROJEKTSTRUKTUR.md erstellt (Moduluebersicht und Verzeichnisstruktur)
- README.md auf PilotSuite aktualisiert
- PROJECT_STATUS.md aktualisiert
