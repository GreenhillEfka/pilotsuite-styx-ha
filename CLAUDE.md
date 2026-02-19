# CLAUDE.md -- PilotSuite HACS Integration

> Kontextdatei fuer KI-Assistenten. Beschreibt Projekt, Architektur, Konventionen und Status.

---

## Projektueberblick

**PilotSuite** (ehemals AI Home CoPilot) ist eine Home Assistant Custom Integration, verteilt ueber HACS. Sie verbindet sich mit dem PilotSuite Core Add-on (Port 8909) und stellt 80+ Sensoren, 15+ Dashboard Cards und 22+ Module in Home Assistant bereit.

Das Projekt verfolgt einen **Privacy-first, Local-first** Ansatz: alle Daten bleiben lokal, keine Cloud-Abhaengigkeit, Human-in-the-Loop Governance.

- **Repo:** HACS Integration (Frontend, Sensoren, Dashboard)
- **Gegenstueck:** PilotSuite Core Add-on (Backend, Brain Graph, Habitus, Mood Engine)
- **Sprache:** Python (asyncio, Home Assistant Framework)
- **Lizenz:** Privat, alle Rechte vorbehalten

---

## Architektur

### Dual-Repo-Struktur

```
Home Assistant
+-- HACS Integration (ai_home_copilot)      <-- dieses Repo
|     Sensoren, Buttons, Dashboard Cards
|     HTTP REST API (Token-Auth)
|     v
+-- Core Add-on (copilot_core) Port 8909    <-- separates Repo
      Backend, Brain Graph, Habitus, Mood Engine
```

### Custom Component mit 22+ Modulen

Die Integration nutzt ein **Coordinator-Pattern** (Home Assistant `DataUpdateCoordinator`). Alle Module implementieren das `CopilotModule`-Interface aus `core/modules/module.py` mit standardisiertem Lifecycle:

- `async_setup_entry()` -- Modul initialisieren
- `async_unload_entry()` -- Modul entladen
- `async_reload_entry()` -- Modul neu laden (optional)

Module werden ueber `core/runtime.py` registriert und gestartet.

### Wichtige Module

| Modul | Datei | Funktion |
|-------|-------|----------|
| EventsForwarder | `events_forwarder.py` | HA Events an Core senden (batched, PII-redacted) |
| HabitusMiner | `habitus_miner.py` | Pattern-Discovery und Zone-Management |
| CandidatePoller | `candidate_poller.py` | Vorschlaege vom Core abholen |
| BrainGraphSync | `brain_graph_sync.py` | Brain Graph Synchronisation |
| MoodContextModule | `mood_context_module.py` | Mood-Integration und Kontext |
| MediaContextModule | `media_context_module.py` | Media-Player Tracking |
| EnergyContextModule | `energy_context_module.py` | Energiemonitoring |
| WeatherContextModule | `weather_context_module.py` | Wetter-Integration |
| UniFiModule | `unifi_module.py` | Netzwerk-Ueberwachung |
| MLContextModule | `ml_context_module.py` | ML-Kontext und Features |
| UserPreferenceModule | `user_preference_module.py` | Multi-User Preference Learning |
| CharacterModule | `character_module.py` | CoPilot-Persoenlichkeit |
| HomeAlertsModule | `home_alerts_module.py` | Kritische Zustandsueberwachung |
| VoiceContext | `voice_context.py` | Sprachsteuerungs-Kontext |
| KnowledgeGraphSync | `knowledge_graph_sync.py` | Knowledge Graph Synchronisation |
| HouseholdModule | (neu) | Familienkonfiguration und Altersgruppen |

### Kommunikation mit Core Add-on

- HTTP REST API ueber `CopilotApiClient` (in `coordinator.py`)
- Token-basierte Authentifizierung (X-Auth-Token / Bearer)
- Webhook Push fuer Echtzeit-Updates vom Core
- Standard-Port: 8909

---

## Konventionen

### Domain und Entity-IDs

- **DOMAIN bleibt `ai_home_copilot`** -- auch nach Umbenennung zu PilotSuite aendert sich die technische Domain nicht
- Entity-ID Prefix: `sensor.ai_home_copilot_*`, `button.ai_home_copilot_*`, etc.
- Unique-ID Format: `ai_home_copilot_{feature}_{name}`

### Basisklasse

Alle Entities erben von `CopilotBaseEntity` (in `entity.py`), die wiederum `CoordinatorEntity` erweitert. Dies stellt sicher:

- Einheitliche `device_info` fuer das Geraet im HA-Device-Registry
- Konsistente `unique_id`-Generierung
- Automatische Coordinator-Anbindung

### Code-Stil

- Python asyncio (async/await)
- TYPE_CHECKING Pattern fuer zirkulaere Imports
- Deutsche Kommentare erlaubt, Code-Bezeichner auf Englisch
- Keine externen Cloud-Abhaengigkeiten

### Dateistruktur

```
custom_components/ai_home_copilot/
+-- __init__.py              # Integration Setup
+-- coordinator.py           # DataUpdateCoordinator + API Client
+-- entity.py                # CopilotBaseEntity Basisklasse
+-- const.py                 # Konstanten, DOMAIN, Config Keys
+-- manifest.json            # HA Manifest
+-- config_flow.py           # Config + Options Flow
+-- services_setup.py        # Service-Registrierungen
+-- core/
|   +-- runtime.py           # Modul-Registry und Lifecycle
|   +-- modules/             # 22+ Module (CopilotModule Interface)
+-- sensors/                 # Sensor-Entities (80+)
+-- button*.py               # Button-Entities
+-- dashboard_cards/         # Lovelace Card Generatoren
+-- ml/                      # ML Pattern Recognition
+-- translations/            # DE + EN Translations
```

---

## Wo kommen wir her

### Version v0.13.5 -- Feature-Complete

- 22+ Module vollstaendig implementiert und registriert
- 80+ Sensoren, 15+ Dashboard Cards
- Events Forwarder mit Batching, Rate Limiting, PII-Redaktion, Persistent Queue
- Habitus Miner mit Zone-Management und Pattern-Discovery
- Brain Graph Sync mit D3.js interaktiver Visualisierung
- Mood Context Integration mit Suggestion-Suppression
- Multi-User Preference Learning (MUPL) mit Action Attribution
- Camera Context, Energy, Weather, UniFi Module
- Home Alerts mit Severity Levels und Health Score
- Cross-Home Sync und Collective Intelligence (Phase 5)

### Bekannte Probleme (aus PROJECT_STATUS.md)

- Doppelte Entity Unique-IDs in Button-Modulen (teilweise behoben)
- Fehlende Error-Isolation im Modul-System
- Race Condition in Events Forwarder (flushing Flag)
- Background Tasks nicht supervised

### Neue Features (v0.14.0-alpha.1)

- **Household/Altersgruppen-Modul**: Familienkonfiguration, Bettzeit-Empfehlungen
- **Webhook Push Integration**: Echtzeit-Updates vom Core
- **Zone Aggregation Pattern**: Aggregierte Zonen-Daten
- **PilotSuite Umbenennung**: Display-Namen aktualisiert (Domain bleibt)

---

## Naechste Schritte

### Alpha Testing (aktuell)

- Funktionale Tests aller 22+ Module
- Entity-ID Audit (keine Duplikate)
- Config Flow End-to-End Test
- Dashboard Cards Validierung

### Bugfixes (Prioritaet)

- Error-Isolation in `runtime.py` (try/except um Modul-Setup)
- Events Forwarder Race Condition (try/finally)
- Sensor unique_id Coverage Audit
- Button-Module Konsolidierung

### Performance

- TTLCache und EntityStateCache Optimierung
- DomainFilter fuer effiziente State-Queries
- Background Task Supervision mit Cancel-on-Unload

### ML Pipeline

- TFLite/ONNX Integration fuer On-Device Inference
- Anomaly Detection mit Isolation Forest
- Habit Prediction mit Zeitreihen-Analyse
- Energy Optimization mit Load Shifting

---

## Hinweise fuer KI-Assistenten

- Aenderungen am DOMAIN-String `ai_home_copilot` sind NICHT erlaubt
- Neue Entities muessen `CopilotBaseEntity` als Basisklasse verwenden
- Neue Module muessen das `CopilotModule`-Interface implementieren
- Alle unique_ids muessen global eindeutig sein (Prefix `ai_home_copilot_`)
- Tests liegen in `/tests/` und verwenden pytest
- Dokumentation in Deutsch bevorzugt
