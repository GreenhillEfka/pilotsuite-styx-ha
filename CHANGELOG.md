# CHANGELOG - PilotSuite HA Integration

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