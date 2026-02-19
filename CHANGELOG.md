# CHANGELOG - PilotSuite HA Integration

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