# CHANGELOG - PilotSuite HA Integration

## [5.5.0] - 2026-02-21

### Energy Schedule Sensor — Daily Device Schedule in HA

#### Energy Schedule Sensor (NEW)
- **sensors/energy_schedule_sensor.py** — `EnergyScheduleSensor` entity
- Shows next scheduled device as sensor state (e.g. "washer at 11:00")
- Exposes attributes: date, devices_scheduled, total cost estimate, PV coverage %, peak load
- Per-device schedule breakdown with hours, cost, and PV percentage
- URLs for daily schedule and next-device API endpoints
- Async fetches from Core `GET /api/v1/predict/schedule/daily`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.5.0

## [5.4.0] - 2026-02-21

### OpenAPI Spec v5.4.0 — Version Sync

#### Version Sync
- Synchronized with PilotSuite Core v5.4.0 (OpenAPI Spec update)
- Core now serves 49 API paths with 64 component schemas
- Complete Energy API documentation available at `/api/v1/docs`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.4.0

## [5.3.0] - 2026-02-21

### Test Coverage — Voice Context + Anomaly Detector

#### Voice Context Tests (NEW — 45+ tests)
- **tests/test_voice_context.py**
  - `TestCommandPattern` — Regex matching, case insensitivity, entity extraction, multiple patterns
  - `TestExtractors` — Temperature, scene, automation, entity extraction functions
  - `TestParseCommand` — All 16 intents: light on/off/toggle, climate warmer/cooler/set, media play/pause/stop, volume up/down, scene, automation, status, search, help, unknown
  - `TestVoiceTone` — Tone config switching (formal/friendly/casual/cautious), character service integration, response formatting fallbacks
  - `TestTTSDiscovery` — Priority-based entity discovery (Sonos, Google Home, TTS capability, fallback)
  - `TestSpeak` — TTS service calls, custom entity, failure fallback to media_player
  - `TestModuleProperties` — Name, version, help text
  - `TestDataclasses` — VoiceCommand, TTSRequest defaults and custom values
  - `TestCommandPatternsCoverage` — Ensures all defined intents are reachable

#### Anomaly Detector Tests (NEW — 35+ tests)
- **tests/test_anomaly_detector.py**
  - `TestInit` — Default/custom params, empty initial state
  - `TestFeatures` — Feature initialization, buffer sizes, vector extraction, missing/non-numeric values
  - `TestFit` — Model fitting, disabled state, random seed, error fallback
  - `TestUpdate` — Not-fitted, disabled, normal/anomalous values, history tracking, missing features
  - `TestScoring` — Score range validation, exception handling
  - `TestAdaptiveThreshold` — Default (cold start), high/low/medium anomaly rates
  - `TestSummary` — Empty, with data, time filter
  - `TestReset` — State clearing, feature history clearing
  - `TestContextAware` — ContextAwareAnomalyDetector: init, temporal analysis, relationship analysis, context defaults
  - `TestEdgeCases` — History/window max size, empty features, multiple sequential updates

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.3.0

## [5.2.0] - 2026-02-21

### Sankey Energy Flow Sensor

#### Energy Sankey Sensor (NEW)
- **sensors/energy_sankey_sensor.py** — `EnergySankeySensor` entity
- Exposes energy Sankey flow data from Core API as HA sensor
- Attributes: sankey_svg_url, sankey_json_url, sources, consumers, node/flow counts
- State shows node and flow count summary

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.2.0

## [5.1.0] - 2026-02-21

### Zone Energy Device Discovery — Auto-Association + Tagging

#### Zone Energy Discovery Module (NEW)
- **zone_energy_devices.py** — `ZoneEnergyDiscovery` class for automatic energy device detection per Habitzone
- `ZoneEnergyDevice` dataclass — entity_id, device_class, related_entities, association_method, tags
- 3 auto-discovery strategies:
  1. **Device-based**: Energy sensors sharing `device_id` with zone entities
  2. **Area-based**: Energy sensors in the same HA area
  3. **Name-based**: Energy sensor names matching zone entity/zone name patterns
- `discover_all_energy_entities()` — Scans HA entity registry for power/energy/current/voltage device classes
- `discover_for_zone(zone_entity_ids, zone_name)` — Auto-discovers energy devices for a specific Habitzone
- `get_zone_power_total(energy_entity_ids)` — Aggregates power with unit conversion (kW→W, mW→W)
- Uses HA registries: `entity_registry`, `device_registry`, `area_registry`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.1.0

## [5.0.0] - 2026-02-21

### Major Release — Performance Monitoring, Test Coverage

#### Performance Monitoring Module (EXPANDED)
- **performance_scaling.py** — Expanded from v0.1 stub (54 lines) to v1.0 kernel (314 lines)
- API response time tracking with rolling window (500 samples) and percentiles (p50/p90/p95/p99)
- Memory usage monitoring via `/proc/self/status` (Linux)
- Entity count metrics for PilotSuite entities
- Coordinator update latency tracking
- Configurable alert thresholds (API time, coordinator, entity count, memory, error rate)
- Background monitoring loop (60s interval) with alert generation
- Integration with existing PerformanceGuardrails rate limiting
- `get_snapshot()`, `get_percentiles()`, `get_guardrails_status()` query API

#### Test Coverage (+4 test files, ~60 new tests)
- **test_performance_scaling.py** (NEW) — 16 tests: recording, snapshot, percentiles, thresholds, alerts, edge cases
- **test_energy_context.py** (NEW) — 14 tests: frugality scoring, mood dict, snapshot, edge cases
- **entity.py** + **manifest.json** — Version 5.0.0

## [1.0.0] - 2026-02-21

### Stable Release — Feature-Complete

PilotSuite Styx HACS Integration erreicht **v1.0.0 Stable**. Alle geplanten Meilensteine sind abgeschlossen.

**Cumulative seit v4.0.0:**
- **v4.1.0** Race Conditions Fix (asyncio.Lock)
- **v4.2.0** History Backfill (HA Recorder → Core, einmalig)
- **v4.2.1** Hassfest + Config Flow Fix
- **v4.3.0** Mood Persistence (HA Storage API, 24h TTL Cache)
- **v4.4.0** Test Coverage: 14 neue Tests (Mood Store + Cache)
- **v4.5.0** Conflict Resolution Engine (ConflictResolver + PreferenceInputCard + 11 Tests)

**Gesamtbilanz:**
- 94+ Sensoren, 30 Module, 22+ Dashboard Cards
- 3 Native Lovelace Cards (Brain Graph, Mood, Habitus)
- HA Conversation Agent (Styx → Core `/v1/chat/completions`)
- Conflict Resolution (weighted/compromise/override)
- Config Flow (Zero Config, Quick Start, Manual)
- Deutsch + Englisch Translations
- CI/HACS/Hassfest gruen

## [4.5.0] - 2026-02-21

### Conflict Resolution Engine

- **conflict_resolution.py** — Neues Modul: Erkennt und loest Praeferenz-Konflikte zwischen aktiven Nutzern; paarweiser Divergenz-Check auf allen Mood-Achsen (Schwellenwert 0.3); drei Strategien: `weighted` (prioritaetsgewichtet), `compromise` (Durchschnitt), `override` (einzelner Nutzer gewinnt)
- **preference_input_card.py** — Umgeschrieben: Zeigt Konflikt-Status als HA-Entity mit `state: conflict|ok`; Extra-Attribute: aktive Konflikte, Strategie, beteiligte Nutzer, aufgeloester Mood, Konflikt-Details
- **test_conflict_resolution.py** — 11 neue Tests: Konflikt-Erkennung, alle 3 Strategien, Serialisierung, Edge Cases
- **manifest.json** + **entity.py** Version auf 4.5.0 synchronisiert

## [4.4.0] - 2026-02-21

### Test Coverage + Quality

- **test_mood_store.py** — 8 neue Tests fuer Mood State Persistence (save/load/TTL/roundtrip/edge cases)
- **test_mood_context_cache.py** — 6 neue Tests fuer MoodContextModule Cache-Integration (pre-load/fallback/idempotenz)
- **manifest.json** + **entity.py** Version auf 4.4.0 synchronisiert
- Gesamte Test Suite: 352 Tests bestanden, 0 Fehler

## [4.3.0] - 2026-02-20

### Mood Persistence + MUPL Role Sync

- **mood_store.py** — Neues Modul: Mood-Snapshots werden via HA Storage API lokal zwischengespeichert; bei HA-Restart wird gecachter Mood sofort geladen (kein Warten auf Core); Cache-TTL 24h, danach automatische Invalidierung
- **mood_context_module.py** — Beim Start: Pre-Load aus HA-Cache; bei jedem Core-Fetch: automatische Persistenz; bei Timeout: Fallback auf lokalen Cache statt leeres Mood-Objekt; `_using_cache` Flag für Diagnostik
- **manifest.json** + **entity.py** Version auf 4.3.0 synchronisiert

## [4.2.1] - 2026-02-20

### Bugfix — Hassfest + Config Flow Fix

- **manifest.json** — Ungültigen `homeassistant`-Key entfernt (hassfest: `extra keys not allowed @ data['homeassistant']`); dieser Key wurde von neueren HA-Versionen als invalide abgelehnt und verhinderte das Laden der Integration → "Invalid handler specified" Config Flow Error behoben
- **hacs.json** — Minimum HA-Version (`2024.1.0`) korrekt in `hacs.json` statt `manifest.json` deklariert
- **manifest.json** + **entity.py** Version auf 4.2.1 synchronisiert

## [4.2.0] - 2026-02-20

### History Backfill

- **history_backfill.py** — Neues Modul: Beim ersten Start werden letzte 24h aus dem HA Recorder geladen und als Events an Core gesendet; Brain Graph lernt sofort aus bestehender History; einmalig, Completion wird in HA Storage gespeichert
- **__init__.py** — History Backfill Modul registriert (nach events_forwarder)
- **manifest.json** + **entity.py** Version auf 4.2.0 synchronisiert

## [4.1.0] - 2026-02-20

### Race Conditions + Stability

- **events_forwarder.py** — `asyncio.Lock` ersetzt boolean `flushing` Flag; eliminiert Two-Phase-Flush Race Condition (flushing=False → re-acquire Pattern); Lock wird nie deadlocken
- **manifest.json** + **entity.py** Version auf 4.1.0 synchronisiert

## [4.0.1] - 2026-02-20

### Patch — Version-Fix, Branding-Cleanup, Add-on Store Fix

- **entity.py VERSION** auf 4.0.1 aktualisiert (war 3.13.0 — HACS zeigte falsche Version)
- **manifest.json version** auf 4.0.1 synchronisiert
- **README.md** Header von v3.9.1 auf v4.0.1 aktualisiert
- **camera_dashboard.py** Dashboard-Pfad `ai-home-copilot-camera` → `pilotsuite-camera`
- **docs/USER_MANUAL.md** Version-Header, Card-Types und Anchor-Links aktualisiert
- **PROJECT_STATUS.md** Alpha-Referenzen durch v4.0.x ersetzt
- Alte Version-Kommentare in `__init__.py` bereinigt

## [4.0.0] - 2026-02-20

### Official Release — Repository Rename + Feature-Complete

**Repository umbenannt:** `ai-home-copilot-ha` → `pilotsuite-styx-ha`
Alle internen URLs, Dokumentation und Konfigurationsdateien aktualisiert.
GitHub leitet alte URLs automatisch weiter (301 Redirect).

#### Warum v4.0.0?

Dies ist der erste offizielle Release von PilotSuite Styx als feature-complete Produkt.
Alle Komponenten sind synchron auf v4.0.0:

| Komponente | Repo | Version |
|-----------|------|---------|
| **Core Add-on** | `pilotsuite-styx-core` | 4.0.0 |
| **HACS Integration** | `pilotsuite-styx-ha` | 4.0.0 |
| **Adapter** | `pilotsuite-styx-core` (Unterverzeichnis) | 4.0.0 |

#### Feature-Ueberblick (Cumulative seit v0.14.x)

**30 Coordinator-Module**
- `events_forwarder` — Event Bridge zum Core Add-on (Quality Metrics, Queue)
- `brain_graph_sync` — Brain Graph Synchronisation (WebSocket + REST Fallback)
- `habitus_miner` — Pattern Mining aus Nutzerverhalten (Persistence, Cleanup)
- `mood` + `mood_context` — Mood Tracking + Context-Injection
- `energy_context` — Energieverbrauch pro Zone
- `weather_context` — Wetter-Einfluss auf Vorschlaege
- `network` (UniFi) — Netzwerk-Health, Client-Tracking
- `camera_context` — Kamera-Integration (Frigate Bridge)
- `ml_context` — ML Pattern Recognition
- `voice_context` — Sprach-Interaktions-Tracking
- `home_alerts` — Benachrichtigungen (Persistenz via HA Storage)
- `character_module` — Charakter-Presets fuer Styx
- `waste_reminder` — Muellabfuhr-Erinnerungen (TTS + Notifications)
- `birthday_reminder` — Geburtstags-Erinnerungen (14-Tage Vorschau)
- `entity_tags` — Manuelles Tag-System (Registry, Assignment, Sync)
- `person_tracking` — Anwesenheit (Presence Map, History)
- `frigate_bridge` — NVR-Integration (Person/Motion Detection)
- `scene_module` — Szenen (Capture, Apply, Presets)
- `homekit_bridge` — Apple HomeKit Expose
- `calendar_module` — HA Kalender-Integration
- `media_zones` — Musikwolke + Player-Zonen
- `candidate_poller` — Brain Graph Kandidaten
- `dev_surface` — Debug-Interface
- `performance_scaling` — Auto-Scaling
- `knowledge_graph_sync` — Knowledge Graph Sync
- `ops_runbook` — Operational Runbooks
- `quick_search` — Schnellsuche
- `legacy` — Abwaertskompatibilitaet
- `unifi_module` — UniFi-spezifische Features

**110+ HA Entities**
- 80+ Sensoren (Version, Status, Mood, Habitus, Energy, Network, Predictions, ...)
- 22+ Buttons (Debug, Forwarder, Brain Graph, Mood, Tags, ...)
- Numbers, Selects, Text-Entities, Binary Sensors

**30+ HA Services**
- Tag Registry (upsert, assign, confirm, sync, pull)
- Media Context v2 (suggest zones, apply, clear)
- Event Forwarder (start, stop, stats)
- Ops Runbook (preflight, smoke test, execute, checklist)
- Debug (enable, disable, clear errors, ping)
- Habitus Mining (mine, get rules, reset, configure)
- Multi-User Preferences (learn, priority, delete, export, detect, mood)
- Candidate Poller, UniFi, Energy, Anomaly, Habit Learning, Predictive, HomeKit

**Config Flow**
- Zero Config: Ein-Klick Installation mit Auto-Discovery
- Quick Start Wizard: 7-Schritt Konfiguration
- Manual Setup: Volle Kontrolle ueber alle Parameter
- Options Flow: Nachtraegliche Anpassung aller Einstellungen
- Entity Tags Management im Config Flow

**Dashboard Cards (22+ Typen)**
- Uebersicht, Brain Graph, Habitus Zonen, Mood, Energy
- Presence, Muellabfuhr, Geburtstage, Kalender
- Media Zonen, HomeKit, Szenen, Suggestions
- Mobile-Responsive, Dark Mode, Interactive Filters

**HA Conversation Agent**
- `StyxConversationAgent`: Nativ in HA Assist Pipeline
- Proxy zu Core `/v1/chat/completions`
- DE + EN Unterstuetzung

**3 Native Lovelace Cards**
- `styx-brain-card.js`: Brain Graph Force-Directed Layout
- `styx-mood-card.js`: Mood Circular Gauges
- `styx-habitus-card.js`: Pattern Liste mit Confidence Badges

**Translations**
- Deutsch (de.json) — 23KB, vollstaendig
- English (en.json) — 22KB, vollstaendig

#### Aenderungen in v4.0.0

- **Repository Rename**: `ai-home-copilot-ha` → `pilotsuite-styx-ha`
- **Alle URLs aktualisiert**: manifest.json, openapi.yaml, Docs, README
- **Cross-Referenzen**: `Home-Assistant-Copilot` → `pilotsuite-styx-core` in allen Docs
- **manifest.json**: `homeassistant: "2024.1.0"` Minimum-Version hinzugefuegt

## [3.9.1] - 2026-02-20

### HA Conformity & Cleanup Release

- **entity.py** — device_info now uses `DeviceInfo` dataclass (HA best practice)
  - `manufacturer`: "Custom" → "PilotSuite"
  - `model`: "MVP Core" → "HACS Integration"
  - `sw_version`: now reports current version (3.9.1)
- **coordinator.py** — removed redundant `_hass` attribute (already inherited from `DataUpdateCoordinator`)
  - Fixed: `Dict` → `dict` (Python 3.11+ built-in generics)
- **config_flow.py** — fixed "OpenClaw Gateway" → "PilotSuite Core Add-on" in manual setup
- **media_context.py** — removed module-level `warnings.warn()` that fired on every import
  - Cleaned docstring, kept as base class for media_context_v2
- **manifest.json** — added `homeassistant: "2024.1.0"` minimum version
- **Branding** — 30+ references updated from "AI Home CoPilot" → "PilotSuite":
  - camera_entities.py manufacturer fields (4x)
  - button_debug_ha_errors.py button name
  - ha_errors_digest.py notification titles (4x)
  - pilotsuite_dashboard.py titles and headers (4x)
  - config_wizard_steps.py entry title
  - debug.py device_info
  - setup_wizard.py entry title
  - services_setup.py docstring
- **Core Add-on** — config.json version bump 3.9.0 → 3.9.1, port description updated
- **Adapter** — manifest.json name updated to "PilotSuite (Adapter)", version 3.9.1

## [3.9.0] - 2026-02-20

### Full Consolidation — Alles in einer Version

- **Branch-Konsolidierung** — Alle Arbeit aus 15 Remote-Branches zusammengeführt:
  - `development` (v0.4.0–v0.7.5 Feature-History)
  - `dev/autopilot-2026-02-15` (ML, CI/CD, Knowledge Graph, Neural System, D3.js Brain Graph)
  - `dev/openapi-spec-v0.8.2` (OpenAPI Spec, LazyHistoryLoader)
  - `dev/vector-store-v0.8.3` (Vector Store Client)
  - `dev/mupl-phase2-v0.8.1` (Multi-User Preference Learning)
  - `wip/phase4-ml-patterns` (ML Pattern Recognition)
  - `wip/module-unifi_module` (Module Architecture Fixes)
  - `backup/pre-merge-20260216`, `backup/2026-02-19` (Docs, Reports, Archive)
  - `claude/research-repos-scope-4e3L6` (DeepSeek-R1 Audit)
- **79 Dateien konsolidiert** — Button-Module, Docs, Archive, Reports, Notes, OpenAPI Spec
- **Version vereinheitlicht** — manifest.json auf 3.9.0 (beide Repos synchron)
- **Nichts verloren** — Jede einzigartige Datei aus jedem Branch wurde eingesammelt

### Production-Ready Bug Sweep

- **CRITICAL: `sensor.py` — `data.version` AttributeError** — `CopilotVersionSensor` accessed
  `self.coordinator.data.version` but data is a `dict`. Fixed to `.get("version", "unknown")`.
  This crashed on every coordinator update.
- **`text.py` — unsafe coordinator access** — `async_setup_entry` used double bracket access
  `hass.data[DOMAIN][entry.entry_id]["coordinator"]`. Changed to safe `.get()` chain with
  guarded early-return. Prevents `KeyError` during platform setup.
- **`select.py` — unsafe `hass.data` access** — Same bracket-access pattern. Added safe
  `.get()` chain + coordinator None guard + logging.
- **`seed_adapter.py` — unsafe dict write** — Wrote to `hass.data[DOMAIN][entry.entry_id]`
  without checking existence. Changed to safe `.get()` with isinstance guard.
- **`habitus_dashboard_cards_service.py` — unsafe dict access** — Direct bracket access to
  `hass.data[DOMAIN][entry.entry_id]`. Changed to safe `.get()` chain.
- **`habitus_miner.py` — periodic task resource leak** — Two `async_track_time_interval()`
  calls (cleanup + persistence) did not store unsubscribe functions. Tasks leaked on module
  unload. Now stored in `module_data["listeners"]` for proper cleanup.

## [3.8.1] - 2026-02-19

### Startup Reliability Patch

- **Coordinator safety** — `binary_sensor.py`, `button.py`, `number.py`, `knowledge_graph_entities.py`
  all used unsafe `data["coordinator"]` direct dict access. Changed to `.get("coordinator")` with
  a guarded early-return and error log. Prevents `KeyError` if coordinator is not yet available
  during platform setup ordering.

## [3.8.0] - 2026-02-19

### Persistent State — Alerts & Mining Buffer

- **Alert State persistence** — HomeAlertsModule now persists acknowledged alert IDs
  and daily alert history (30 days) via HA Storage. Acknowledged alerts survive restarts.
  New `get_alert_history(days)` API for trend analysis.
- **Habitus Mining Buffer persistence** — HabitusMinerModule event buffer and discovered
  rules now persist via HA Storage. Buffer saved every 5 minutes + on unload.
  No more cold-start data loss after HA restart.
- **Documentation** — New `docs/QA_SYSTEM_WALKTHROUGH.md`: comprehensive Q&A covering
  all 33 modules, startup sequence, learning pipeline, and persistence guarantees.
- **Version references updated** — README.md, VISION.md, PROJECT_STATUS.md now reflect v3.8.0

## [3.7.1] - 2026-02-19

### Error Isolation — Modul-Setup

- **`__init__.py`** — Alle Modul-Registrierungen in `_get_runtime` einzeln in `try/except`
  - Ein defektes Modul crasht nicht mehr den kompletten Start
- **`async_setup_entry`** — `UserPreferenceModule` und `MultiUserPreferenceModule`
  Setup-Blöcke jeweils in `try/except` gekapselt
  - Optionale Module können ausfallen ohne die Integration zu blockieren
- Version: 3.7.0 → 3.7.1

## [3.7.0] - 2026-02-19

### Bug Fixes & Production Readiness

- **Brain Graph Sync** — Race condition fixes
  - `_processed_events.pop()` crash: replaced with atomic `set()` reset
  - `_send_node_update`/`_send_edge_update`: Null-guard for `_session`
- **Config Validation** — Bounds checking for all 15+ numeric parameters
  - `config_schema_builders.py`: `vol.Range()` on port, intervals, sizes, queue params
  - `validate_input()`: Validates host, port (1-65535), and critical bounds
- **User Hints** — `accept_suggestion()` now creates HA automations via `automation.create`
- **Active Learning** — `_learn_from_context()` records light brightness patterns
  per user/zone/time_slot (was: stub that only logged)
- **Habitus History** — `_fetch_ha_history()` fetches from HA Recorder
  via `state_changes_during_period` (was: always returned `[]`)
- Version: 3.6.0 → 3.7.0

## [3.6.0] - 2026-02-19

### Production Hardening

- **CI Pipeline erweitert** — Full pytest Suite + pytest-cov + bandit Security Scan
  - Vorher: Nur 3 isolierte Tests; jetzt: gesamtes `tests/` Verzeichnis
  - Neuer `security` Job: bandit scannt auf SQL-Injection, Command-Injection, etc.
- Version: 3.5.0 -> 3.6.0

## [3.5.0] - 2026-02-19

### RAG Pipeline + Kalender-Integration

- **Calendar Module** — Integriert alle HA `calendar.*` Entities
  - `core/modules/calendar_module.py`: Auto-Discovery, Event-Abruf, LLM-Kontext
  - `async_get_events_today()`, `async_get_events_upcoming(days)` via HA calendar.get_events
  - Sensor: `sensor.ai_home_copilot_calendar` — Kalender-Count + Liste
  - LLM-Kontext: Zeigt heutige/morgige Termine automatisch
- **Registrierung in __init__.py**: CalendarModule im CopilotRuntime
- Version: 3.4.0 -> 3.5.0

## [3.4.0] - 2026-02-19

### Scene Module + Auto Styx Tagging + HomeKit Bridge

- **Scene Module** — Speichert aktuelle Habituszonen-Zustaende als HA-Szenen
  - `scene_store.py`: HA Storage CRUD mit ZoneScene Dataclass
  - `core/modules/scene_module.py`: Capture, Apply, Delete, Presets, LLM-Kontext
  - 8 Built-in Presets: Morgen, Tag, Abend, Nacht, Film, Party, Konzentration, Abwesend
  - Sensor: `sensor.ai_home_copilot_zone_scenes` — Szenen-Count + Summary
  - Translations (en/de) fuer Config Flow
- **Auto Styx Tagging** — Jede Entitaet mit der Styx interagiert wird automatisch getaggt
  - `entity_tags_module.py` v0.2.0: `async_auto_tag_styx()` Method
  - STYX_TAG_ID "styx" mit lila Farbe + robot Icon
  - `is_styx_entity()`, `get_styx_entities()` Abfragen
  - LLM-Kontext zeigt Styx-getaggte Entitaeten + Anzahl
- **HomeKit Bridge Module** — Exponiert Habituszonen-Entitaeten an Apple HomeKit
  - `core/modules/homekit_bridge.py`: Zone Enable/Disable, Auto-Reload
  - HA Storage Persistenz, `homekit.reload` Service (Pairing bleibt erhalten)
  - Sensor: `sensor.ai_home_copilot_homekit_bridge` — Zonen/Entitaeten Count
  - LLM-Kontext: Zeigt HomeKit-aktive Zonen
- **Dashboard**: Szene-Speichern + HomeKit Button auf Habituszonen-Karten
- Version: 3.3.0 -> 3.4.0

## [3.3.0] - 2026-02-19

### Personen-Tracking + Frigate-Integration

- **Person Tracking Module** — Verfolgt Anwesenheit über HA `person.*` + `device_tracker.*`
  - Live-Presence-Map: Wer ist wo (Zone, seit wann, Quelle)
  - Ankunft/Abfahrt-History mit Event-Erkennung
  - LLM-Kontext: "Anwesend: Max (Wohnzimmer, seit 14:30). Abwesend: Lisa."
  - Sensor: `sensor.ai_home_copilot_persons_home` — Anzahl + Presence-Map
- **Frigate Bridge Module** — Optionale NVR-Integration (auto-disabled wenn kein Frigate)
  - Auto-Discovery von `binary_sensor.*_person` + `binary_sensor.*_motion`
  - Person/Motion-Events → CameraContext Bus-Events
  - Recent Detections Timeline + LLM-Kontext
  - Sensor: `sensor.ai_home_copilot_frigate_cameras`
- Version: 3.2.3 → 3.3.0

## [3.2.3] - 2026-02-19

### Bugfixes

- **Fix: Sensor-Crashes bei None-Modul** — 5 Sensoren hatten fehlende None-Guards in `native_value`:
  `WasteNextCollectionSensor`, `WasteTodayCountSensor`, `BirthdayTodayCountSensor`,
  `BirthdayNextSensor`, `EntityTagsSensor` — geben jetzt 0/None zurück statt AttributeError
- **Fix: Fehlende Translations** — `entity_tags`, `neurons`, `add_tag`, `edit_tag`, `delete_tag`
  Menü-Einträge fehlten in `en.json` + `de.json` → HA zeigte Rohschlüssel statt lesbaren Text
- Version: 3.2.2 → 3.2.3

## [3.2.2] - 2026-02-19

### Tags, Suggestions & Hauswirtschaft

- **Entity Tags System** — Manuelle Entitäts-Tags über den Config Flow verwalten
  - Tags definieren (Name, Farbe, Icon, Modul-Hints), beliebige HA-Entitäten zuordnen
  - Neues Config-Flow-Menü: *Entity-Tags* (Hinzufügen / Bearbeiten / Löschen)
  - `entity_tags_module.py` — CopilotModule: liefert Tag-Kontext an das LLM
  - `entity_tags_store.py` — HA Storage-Persistenz (Store-Key `ai_home_copilot.entity_tags`)
  - Sensor: `sensor.ai_home_copilot_entity_tags` — aktive Tag-Anzahl + Tag-Attribute
- **Entity Assignment Suggestions** — Vorschlagspanel auf der Habitus-Seite im Dashboard
  - Erkennt Entitäten, die keiner Habitus-Zone zugeordnet sind
  - Gruppiert nach Raum-Hint (heuristisch aus Entity-ID extrahiert)
  - Konfidenz-Score (Entitäten-Anzahl + Domain-Diversität)
  - Direkt auf der Habitus-Seite sichtbar

## [3.2.1] - 2026-02-19

### Fixes + Modul-Sweep

- **Fix: Enable-Flags enforced** — `waste_enabled: false` / `birthday_enabled: false` im Config Flow
  werden jetzt korrekt ausgewertet; Module überspringen das Setup vollständig wenn deaktiviert
- **Fix: Neue HA Sensor-Entities** (6 neue Sensoren)
  - `sensor.ai_home_copilot_waste_next_collection` — nächste Abfuhr (Typ + Tage)
  - `sensor.ai_home_copilot_waste_today_count` — Anzahl Abfuhren heute
  - `sensor.ai_home_copilot_birthday_today_count` — Anzahl Geburtstage heute
  - `sensor.ai_home_copilot_birthday_next` — nächster Geburtstag (Name + Tage)
  - `sensor.ai_home_copilot_character_preset` — aktives Charakter-Preset (Modul-Sweep)
  - `sensor.ai_home_copilot_network_health` — Netzwerk-Gesundheit: healthy/degraded/offline (Modul-Sweep)
- **Fix: pilotsuite.create_automation** — `numeric_state` Trigger + optionale Conditions
  - Ermöglicht feuchtigkeitsbasierte Automationen: "Wenn Bad > 70% Luftfeuchtigkeit"
  - `conditions` Array: numeric_state + template Bedingungen

## [3.2.0] - 2026-02-19

### Müllabfuhr + Geburtstags-Erinnerungen

- **Waste Reminder Module**: Optionales Modul für `waste_collection_schedule` Integration
  - Auto-Discovery von Waste-Sensoren (`daysTo` Attribut)
  - Abend-Erinnerung (Vorabend, konfigurierbare Uhrzeit)
  - Morgen-Erinnerung (Tag der Abfuhr)
  - TTS-Ansagen + Persistent Notifications
  - LLM-Kontext-Injection (Styx weiß wann welcher Müll abgeholt wird)
  - Forwarding an Core Addon
- **Birthday Reminder Module**: Kalender-basierte Geburtstags-Erinnerungen
  - Auto-Discovery von Geburtstags-Kalendern
  - Morgen-TTS: "Heute hat [Name] Geburtstag!"
  - 14-Tage Vorschau auf kommende Geburtstage
  - Alters-Erkennung aus Event-Titel
  - LLM-Kontext für Geburtstagsfragen
- **Config Flow**: 12 neue Einstellungen (Waste + Birthday, jeweils Entities, TTS, Uhrzeiten)
- **Translations**: EN + DE für alle neuen Config-Keys
- Versions-Sync: manifest.json auf 3.2.0

## [3.0.0] - 2026-02-19

### Kollektive Intelligenz — Federated Learning + A/B Testing

- **Federated Learning Integration**: Cross-Home Pattern-Sharing Entities
- **A/B Testing Support**: Experiment-Tracking fuer Automation-Varianten
- **Pattern Library**: Kollektiv gelernte Muster sichtbar in Dashboard
- **Versions-Sync**: manifest.json auf 3.0.0 synchronisiert mit Core

## [2.2.0] - 2026-02-19

### Praediktive Intelligenz — Ankunft + Energie

- **Prediction Entities**: Arrival Forecast, Energy Optimization Sensors
- **Energiepreis-Integration**: Tibber/aWATTar Sensor-Support
- **Versions-Sync**: manifest.json auf 2.2.0

## [2.1.0] - 2026-02-19

### Erklaerbarkeit + Multi-User

- **Explainability Entities**: "Warum?"-Sensor fuer Vorschlaege
- **Multi-User Profile Entities**: Pro-Person Praeferenz-Sensoren
- **Versions-Sync**: manifest.json auf 2.1.0

## [2.0.0] - 2026-02-19

### Native HA Integration — Lovelace Cards + Conversation Agent

- **3 Native Lovelace Cards**:
  - `styx-brain-card.js`: Brain Graph Visualisierung mit Force-Directed Layout
  - `styx-mood-card.js`: Mood Circular Gauges (Comfort/Joy/Frugality)
  - `styx-habitus-card.js`: Top-5 Pattern-Liste mit Confidence-Badges
- **HA Conversation Agent**: `StyxConversationAgent` in `conversation.py`,
  nativ in HA Assist Pipeline, Proxy zu Core `/v1/chat/completions`
- **Versions-Sync**: manifest.json auf 2.0.0

## [1.3.0] - 2026-02-19

### Module Control — Echte Backend-Steuerung

- **Versions-Sync**: manifest.json auf 1.3.0 synchronisiert mit Core v1.3.0
- **Module Control**: Dashboard-Toggles steuern jetzt echtes Backend
- **Automation Creator**: Akzeptierte Vorschlaege werden HA-Automationen

## [1.2.0] - 2026-02-19

### Qualitaetsoffensive — Stabile Integration fuer den Livetest

- **Versions-Sync**: manifest.json auf 1.2.0 synchronisiert mit Core Add-on v1.2.0
- **HA Kompatibilitaet**: Vollstaendig kompatibel mit HA 2024.x und 2025.x
- **Keine Breaking Changes**: Config Flow, Sensors, Translations, HACS-Installation
  unveraendert stabil

## [1.1.0] - 2026-02-19

### Styx — Die Verbindung beider Welten

- **Styx Naming in Config Flow**: Zero Config creates "Styx — PilotSuite" entry,
  manual setup includes `assistant_name` field (default: "Styx")
- **Translations**: EN + DE updated with Styx setup titles and descriptions
- **hacs.json**: Name updated to "PilotSuite — Styx"

---

## [1.0.0] - 2026-02-19

### PilotSuite v1.0.0 -- First Full Release

The PilotSuite HACS Integration is now fully installable with zero-config setup.

### Features
- **Zero Config Setup**: One-click installation -- PilotSuite discovers devices
  automatically and improves through conversation. No questions asked.
- **Quick Start Wizard**: Guided 7-step wizard for zone/device configuration
- **50+ Dashboard Cards**: Overview, Brain Graph, Habitus, Mood, Energy, Presence,
  Mobile-responsive, Mesh monitoring, Interactive filters
- **extended_openai_conversation_pilot**: OpenAI-compatible conversation agent
  for HA's Assist pipeline, connecting to PilotSuite Core at localhost:8909
- **23 Core Modules**: Events forwarder, Brain Graph sync, Habitus miner, Mood,
  Energy/Weather/Presence/UniFi/Camera/ML/Voice context, Home Alerts, and more
- **80+ Sensors**: Entity state tracking across all PilotSuite modules
- **Tag System v0.2**: Entity tagging with registry, assignment, and sync

### Breaking Changes
- Version jump from 0.15.2 to 1.0.0
- Default port changed to 8909

---

## [0.15.1] - 2026-02-18

### Features
- **MUPL Integration in Vector Client**
  - Vector Store Client nutzt jetzt echte Preferenzdaten von MUPL
  - `get_user_similarity_recommendations()` liefert reale User-Präferenzen
  - Fallback zu similarity-basierten Hints wenn MUPL nicht verfügbar

### Fixed
- **Logging**: print() → logger in transaction_log.py (Core Add-on)

---

## [0.14.2] - 2026-02-18

### Performance
- **TTLCache Memory Leak Fix:** Cleanup expired entries on every set()
- **Pydantic Models:** api/models.py for API validation (395 lines)

---

## [0.14.1] - 2026-02-18

### Refactored
- **button_debug.py Modularisierung:**
  - Aufteilung in 8 separate Module (brain, core, debug_controls, forwarder, ha_errors, logs, misc)
  - Reduzierung Hauptdatei von 821 auf 60 Zeilen
  - Bessere Wartbarkeit und Übersicht

### Fixed
- **Race Conditions:** asyncio.Lock für Event Forwarder Queue
- **Port-Konflikt:** DEFAULT_PORT auf 8099 (HA Add-on Standard)

---


## [0.14.1-alpha.6] - 2026-02-17

### Added
- **Preference Input Card:** Neue Card für delegation workflows
  - preference_input_card.py: Card Entity für preference workflows
  - Feature: Preference input workflows, conflict resolution UI, schedule automation
  - Card Type: Diagnostic Card mit state attributes

### Tests
- Syntax-Check: ✅ preference_input_card.py kompiliert
- Preference Input Card: ✅ Created and integrated

---

## [0.14.1-alpha.5] - 2026-02-17