# Changelog

All notable changes to PilotSuite will be documented in this file.

> Hinweis (2026-02-22): Die aktive Release-Historie wird im Repository-Root gepflegt: `CHANGELOG.md` (7.7.x Linie).
> Diese Datei enthaelt vor allem aeltere 0.x Historie und bleibt als Archiv erhalten.

## [8.8.0] - 2026-02-25
- React-first Dashboardmodus fuer Habitus-Flow:
  - `habitus_zones` menu nutzt jetzt `dashboard_info` statt YAML-Aktionen als Standardpfad.
- Legacy YAML Dashboard-Generierung in Setup ist jetzt opt-in (`legacy_yaml_dashboards` / `PILOTSUITE_LEGACY_YAML_DASHBOARDS`).
- Strings und Tests fuer den neuen Dashboard-Flow aktualisiert.

## [8.7.0] - 2026-02-25
- RAG-Status in Coordinator integriert (`/api/v1/rag/status`).
- Neuer Sensor: `PilotSuite RAG Pipeline`.
- Performance-Memory-Alerts gehaertet:
  - automatische Schwellenanpassung an Host/Container-Limit
  - Hysterese gegen Warn-Flipflops
- Logger-Initialisierung in `sensor.py` vervollstaendigt.

## [8.4.1] - 2026-02-25
- Version sync release to match Core `v8.4.1`.
- No functional integration changes.

## [7.8.12] - 2026-02-24 — Phase 5: NotificationSensor + SceneIntelligenceSensor

### Added
- `NotificationSensor` — exponiert Notification Count und Alerts als HA Sensor
- `SceneIntelligenceSensor` — zeigt aktive Szene, Vorschläge, Cloud Status
- Integration in `sensors/__init__.py` für automatische Erkennung

### Fixed
- Sensor-Lazy-Loading in `sensors/__init__.py` aktualisiert

## [7.8.9] - 2026-02-23
- Hassfest-Fix: `assist_pipeline` in `manifest.json` als `after_dependencies` deklariert.
- Behebt CI-Fehler fuer die neue Pipeline-Default-Logik in `agent_auto_config.py`.

## [7.8.8] - 2026-02-23
- Auto-Config versucht jetzt, Styx als `conversation_engine` der bevorzugten Assist-Pipeline zu setzen.
- Damit bleibt Styx als Standard-Gespraechsagent ueber Neustarts/Updates stabiler.
- Notification-Text fuer `set_default_agent` auf Pipeline-Mechanik aktualisiert.

## [7.8.6] - 2026-02-22
- Habitus-Zonen-Validierung auf UX-freundliches Minimum umgestellt:
  - nicht mehr hart `motion + lights`
  - mindestens eine gueltige Entity-ID reicht
- Zone-Formular zeigt klare Fehlermeldung bei leerer Entitaetsauswahl.
- Dashboard-Wiring kann fehlende PilotSuite-Dashboard-Keys in bestehenden `lovelace: dashboards:` Block automatisch einpflegen.
- Neuer Service `show_installation_guide` (persistente Notification mit exakter Setup-Anleitung).
- Optionen/Übersetzungen aktualisiert auf primäre `pilotsuite-styx/` Dashboard-Pfade.

## [7.8.2] - 2026-02-22
- Primäre Dashboard-Dateipfade auf `pilotsuite-styx/` umgestellt, inklusive Legacy-Mirror nach `ai_home_copilot/`.
- Habitus-Dashboard-Generator robust gemacht (tuple/list/set Rollen, sichere Zone-Paths, YAML-quoting).
- Dashboard-Wiring akzeptiert und schreibt jetzt sowohl branded als auch legacy Include-Pfade.

## [7.8.1] - 2026-02-22
- Hub-Sensoren fuer `modes/scenes/presence/notifications/integration/brain/energy/media/templates` repariert (wieder korrekte API-Calls mit Auth-Headern).
- `CopilotBaseEntity._fetch()` als gemeinsamer, robuster Core-GET-Helper ergaenzt.
- Syntax-Regression abgesichert durch neuen Source-Syntax-Test.

## [7.7.26] - 2026-02-22
- Runtime-kompatible Lifecycle-Wrappers fuer `ops_runbook`, `mood_context`, `knowledge_graph_sync`, `person_tracking`.
- Konstruktoren fuer Modul-Registry ohne Pflichtparameter vereinheitlicht.
- verhindert stilles Skippen dieser Module beim Runtime-Setup.

## [7.7.25] - 2026-02-22
- MLContextModule Lifecycle auf Runtime-v2 kompatibel gemacht (`ModuleContext` Signaturen, Task-Cancel auf Unload).
- behebt stilles Skippen des Moduls bei Runtime-Setup.

## [7.7.24] - 2026-02-22
- Dashboard-Wiring automatisiert (Include-Datei + Auto-Append bei fehlendem `lovelace:` Block, sonst Merge-Hinweis).
- Habitus-Dashboard-Generierung auf konsistentes v2 (`async_get_zones_v2`) umgestellt.
- Setup/Zone-Refresh erzeugt jetzt PilotSuite- und Habitus-Dashboard gemeinsam.
- Dashboard-Generator referenziert nur noch vorhandene Entities (weniger tote Eintraege).

## [7.7.23] - 2026-02-22
- Nach Device-Konsolidierung werden verwaiste Legacy-PilotSuite-Devices (ohne Entities) nun automatisch bereinigt.
- Cleanup bleibt konservativ (nur reine `ai_home_copilot`-Devices) und bricht Setup bei Fehlern nicht.

## [7.7.22] - 2026-02-22
- Runtime unload now coerces module unload results to strict boolean values.
- Connection options flow now tolerates `test_light_entity_id: null` safely.
- Config/Options network schema accepts optional `None` test light values.
- Pipeline health checks now support Core variants without `/api/v1/capabilities` or `/api/v1/habitus/status`.
- Core v1 capabilities fetch now falls back to agent/chat status endpoints on 404.
- Lovelace resource registration now handles both mapping and object-based Lovelace data.
- Quick-search service registration fixed (valid schemas, URL-encoded query params, registry access cleanup).

## [7.7.21] - 2026-02-22
- Connection config normalization added (host/port/token) incl. legacy key migration.
- Failover no longer switches hosts on 401/403 auth errors.
- `host.docker.internal` fallback made opt-in instead of always-on.
- Brain Graph/HomeKit/Core-v1/Lovelace/N3 service paths now resolve merged entry config.
- Legacy CSV/testlight text entities cleaned up during setup.
- Added regression tests for connection normalization and host candidate behavior.

## [7.7.20] - 2026-02-22
- Unified sensor Core endpoints to use coordinator active failover base URL.
- Added shared Core auth header helper (`Authorization` + `X-Auth-Token`).
- Coordinator startup now normalizes legacy `auth_token` into `token`.
- Legacy host/port-based sensor unique_ids migrated to stable IDs at setup.
- Added tests for new base entity endpoint/auth helper behavior.

## [7.7.19] - 2026-02-22
- OptionsFlow merge fixed: token/host/port/module options persist across updates and step saves.
- Habitus zones: multi-area selection (`area_ids`) for create/edit, merged auto-suggestions, metadata persistence.
- Tag edit flow: two-step prefilled entity editor.
- API fallback hosts expanded (`homeassistant`, `supervisor`, `host.docker.internal`).
- Token handling harmonized in affected sensors (`token` + `auth_token` fallback).
- Deprecated CSV text entities for entity selection removed.

## [7.7.18] - 2026-02-22
- Deprecated CSV text entities for media player selection removed.

## [7.7.17] - 2026-02-22
- PilotSuite dashboard auto-refresh on Habitus zone changes.
- Dashboard generate/download buttons enabled for core entity profile.

## [0.9.6] - 2026-02-16

### Added
- **Cross-Home Sync Module** (`cross_home_sync.py`):
  - Multi-home entity sharing via Core Add-on API
  - Peer discovery for other CoPilot homes on network
  - Entity share/unshare with permission control (read/read_write)
  - State change sync to remote homes
  - Conflict resolution (local_wins, remote_wins, merge)
  - Shared entity registry with sync status tracking
  - Tests: 9 unit tests

---

## [0.9.5] - 2026-02-16

### Added
- **Collective Intelligence Module** (`collective_intelligence.py`):
  - Federated Learning support for distributed pattern sharing
  - Differential privacy with configurable epsilon (privacy-first)
  - Support for multiple model types: habit, anomaly, preference, energy
  - Pattern contribution threshold to ensure quality
  - Aggregated intelligence from multiple homes
  - Local model registration and versioning
  - Pattern expiration and cleanup
  - Tests: 11 unit tests

### Fixed
- **test_repairs_workflow.py**: Fix mock configuration for hass.data

---

## [0.9.4] - 2026-02-15

### Added
- **Quick Search Module** (`core/modules/quick_search.py`):
  - Entity Search: Search all HA entities by name, state, domain
  - Automation Search: Search automations by name, trigger, action
  - Service Search: Search available services by domain, service name
  - Quick Actions: Direct access to commonly used entities/services
  - Services: `ai_home_copilot.search_entities`, `ai_home_copilot.search_automations`, `ai_home_copilot.search_services`, `ai_home_copilot.quick_action`

- **Voice Context Module** (`core/modules/voice_context.py`):
  - Voice Command Parser: Parse voice commands into structured actions
  - TTS Output: Text-to-speech via HA TTS services
  - Voice State Tracking: Track voice assistant states
  - Command Templates: Predefined command patterns (German/English)
  - Supported commands: Light on/off, Climate control, Media control, Scene activation, Automation trigger, Status queries
  - Services: `ai_home_copilot.parse_command`, `ai_home_copilot.speak`, `ai_home_copilot.execute_command`, `ai_home_copilot.get_voice_state`

- **Calendar Integration** (existing: `calendar_context.py`):
  - Calendar Events → Neurons integration
  - calendar.load neuron (CalendarLoadSensor)
  - Termine-basiertes Context (Meeting detection, Focus/Social/Relax keywords)
  - Mood-Weight Berechnung aus Kalender

- **Mobile Dashboard** (existing: `mobile_dashboard_cards.py`):
  - Responsive Cards für mobile Geräte
  - Touch-friendly UI mit min 44px Tap-Targets
  - Quick Actions Card, Mood Status Card, Entity Quick Access Card
  - Notification Badge Card, Calendar Today Card, Quick Search Card

---

## [0.9.3] - 2026-02-15

### Added
- **Predictive Automation Sensors** (`sensors/predictive_automation.py`):
  - `predictive_automation_sensor`: Shows ML-based automation suggestion count
  - `predictive_automation_details_sensor`: Shows detailed suggestions with pattern, confidence, lift, support
  - Integration with `repairs_enhanced.py` for enhanced UX

- **Anomaly Alert Sensors** (`sensors/anomaly_alert.py`):
  - `anomaly_alert_sensor`: Real-time anomaly detection status (healthy/active/idle)
  - `alert_history_sensor`: Shows recent anomaly history with timestamps and scores
  - Integration with `AnomalyDetector` from `ml/patterns/anomaly_detector.py`

- **Energy Insights Sensors** (`sensors/energy_insights.py`):
  - `energy_insight_sensor`: Shows total energy consumption (kWh) with device breakdown
  - `energy_recommendation_sensor`: Shows active energy optimization recommendations
  - Integration with `EnergyOptimizer` from `ml/patterns/energy_optimizer.py`

- **Habit Learning v2 Sensors** (`sensors/habit_learning_v2.py`):
  - `habit_learning_sensor`: Shows number of learned habit patterns
  - `habit_prediction_sensor`: Shows habit predictions with confidence scores
  - `sequence_prediction_sensor`: Shows device sequence predictions (cross-device correlation)
  - Integration with `HabitPredictor` from `ml/patterns/habit_predictor.py`

### Services
- `predictive_automation_suggest_automation`: Suggest automation based on ML patterns
- `anomaly_alert_check_and_alert`: Check for anomalies and send alerts
- `anomaly_alert_clear_history`: Clear anomaly history
- `energy_insights_get`: Get energy insights and recommendations
- `habit_learning_learn`: Learn new habit pattern through observation
- `habit_learning_predict`: Predict future events or sequences

### Features
- Unified ML context via `MLContext` module
- All sensors integrate with existing ML subsystems
- Push notifications via HA system notifications
- Dashboard cards via existing `habitus_dashboard_cards.py`

### Configuration
- Enable via `ml_enabled: true` in config entry options
- Auto-sync of entity states to ML context every 60 seconds

---

## [0.8.16] - 2026-02-15

### Added
- **Knowledge Graph Integration** (`api/knowledge_graph.py`):
  - Full async client for Core Add-on Knowledge Graph API
  - Node operations: create, list, get by ID/type
  - Edge operations: create, list, relationships
  - Query operations: structural, causal, contextual, temporal queries
  - Pattern import from Habitus mining

- **Knowledge Graph Sync Module** (`core/modules/knowledge_graph_sync.py`):
  - Auto-syncs HA entities to Knowledge Graph
  - Creates BELONGS_TO edges for entity→area relationships
  - Creates HAS_CAPABILITY edges for entity features
  - Creates HAS_TAG edges from tag registry
  - Creates RELATES_TO_MOOD edges from neural system
  - Periodic full sync (configurable interval)
  - Real-time state change tracking

- **Knowledge Graph Sensors** (`knowledge_graph_entities.py`):
  - Knowledge Graph Stats sensor (node/edge counts)
  - Knowledge Graph Nodes sensor
  - Knowledge Graph Edges sensor
  - Sync Status sensor
  - Last Sync timestamp sensor

### Features
- Entities automatically added to graph when discovered
- Zone/Tag/Mood relationships synced in real-time
- Query related entities for suggestion context
- Foundation for Pattern-to-Entity mapping

### Configuration
- `knowledge_graph_enabled`: Enable/disable sync (default: true)
- `knowledge_graph_sync_interval`: Full sync interval in seconds (default: 3600)

### Technical
- All modules pass py_compile validation
- Async-safe client with error handling
- Module registry integration for runtime access

## [0.8.15] - 2026-02-15

### Added
- **Suggestion Panel** (`suggestion_panel.py`): Dedicated UI for PilotSuite suggestions
  - Timeline view of pending suggestions
  - Accept/Reject/Snooze actions via service calls
  - Confidence indicator and "Why?" explanations
  - Zone and Mood context display
  - Priority-based sorting (High/Medium/Low)
  - WebSocket API for real-time updates

- **Mood Dashboard** (`mood_dashboard.py`): Visualisierung der aktuellen Stimmung
  - MoodSensor with icon, color, and German name
  - MoodHistorySensor for tracking mood changes
  - MoodExplanationSensor with "Warum?" explanations
  - Lovelace card config generator
  - Top contributing factors display

- **Calendar Context Neuron** (`calendar_context.py`): Kalender-basierter Kontext
  - Meeting detection (now/soon)
  - Weekend/holiday detection
  - Vacation mode detection
  - Mood weight computation based on calendar events
  - Conflict detection
  - Keyword-based categorization (focus, social, relax, alert)

### Enhanced
- Extended `const.py` with new configuration options
- Added sensor entities: ZoneOccupancySensor, UserPresenceSensor, UserPreferenceSensor, SuggestionQueueSensor
- Added calendar context integration to sensor setup

### Technical
- All modules pass py_compile validation
- WebSocket API with proper error handling
- Async storage for suggestion persistence

## [0.8.14] - 2026-02-15

### Added
- Enhanced Repairs UX with zone and mood context
- Risk visualization for suggestions

## [0.8.0] - 2026-02-15

### Added
- Multi-User Preference Learning (MUPL) v0.8.0
- User-spezifische Mood-Gewichtung
- Debug Mode v0.8.0

## [0.4.33] - 2026-02-14

### Added
- Neuronen-System: Context, State, Mood, Weather, Presence, Energy, Camera
- Habitus Zones: Zone-basierte Muster-Erkennung
- Tag System v0.2
- Brain Graph
## [0.9.4] - 2026-02-15

### Added
- Complete SETUP_GUIDE.md - German installation guide
- OpenAPI Specification for HA Integration services
- LazyHistoryLoader for on-demand history caching
- MUPL Phase2 Caching and Query Optimization

### Merged
- dev/mupl-phase2-v0.8.1
- dev/openapi-spec-v0.8.2
- dev/vector-store-v0.8.3

## [0.9.3] - 2026-02-15

### Added
- Phase 6.1 Core Features:
  - Predictive Automation (suggest_automation service)
  - Anomaly Alert (check_and_alert service)
  - Energy Insights (get_energy_insights service)
  - Habit Learning V2 (learn_habits, predict_sequence services)

### Changed
- button.py refactored (40KB → 8 modules)
- Critical fixes: N+1 queries, memory leak, blocking I/O
- Tags API verified (Flask + Auth)

### Tests
- 100+ new tests (Core + Integration)
