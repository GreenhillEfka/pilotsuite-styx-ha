# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Projektueberblick

**PilotSuite Styx** ist eine Home Assistant Custom Integration, verteilt ueber HACS. Sie verbindet sich mit dem PilotSuite Core Add-on (Port 8909) und stellt 94+ Sensoren, 30 Module und Dashboard Cards in Home Assistant bereit.

**Gegenstueck:** [pilotsuite-styx-core](../pilotsuite-styx-core) -- Core Add-on (Backend, Brain Graph, Habitus, Mood Engine)

- **Domain:** `ai_home_copilot` ( technisch, nicht aendern)
- **Sprache:** Python (asyncio, Home Assistant Framework)
- **Lizenz:** Privat, alle Rechte vorbehalten

---

## Entwicklungskommandos

```bash
# Syntax-Check
python -m py_compile $(find custom_components/ai_home_copilot -name '*.py')

# Tests ausfuehren
python -m pytest tests/ -v --tb=short -x

# Tests mit Coverage
python -m pytest tests/ -v --tb=short --cov=custom_components/ai_home_copilot --cov-report=term-missing -x

# Security Scan
bandit -r custom_components/ai_home_copilot -ll --skip B101,B404,B603

# JSON validieren
python -c "import json; json.load(open('custom_components/ai_home_copilot/strings.json'))"

# HACS validieren (lokal)
hacs validate custom_components/ai_home_copilot
```

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

## Aktueller Stand

### Version v7.7.23

- **Tests:** 538 passed, 5 skipped
- 30+ Module vollstaendig implementiert und registriert
- 110+ Entities (94+ Sensoren, 22+ Buttons, Numbers, Selects), 22+ Dashboard Cards
- DeviceInfo Dataclass (HA Best Practice)
- PilotSuite Branding durchgaengig
- HA 2024.1.0+ Mindestversion
- Connection-Normalisierung (Legacy-Token-Migration)
- Core Endpoint Unification (Sensor-API-Calls)
- Unique-ID-Migration (host:port → stabile IDs)
- Legacy-Device Cleanup

---

## Hinweise fuer KI-Assistenten

- Aenderungen am DOMAIN-String `ai_home_copilot` sind NICHT erlaubt
- Neue Entities muessen `CopilotBaseEntity` als Basisklasse verwenden
- `device_info` muss `DeviceInfo` Dataclass verwenden (nicht dict)
- Neue Module muessen das `CopilotModule`-Interface implementieren
- Alle unique_ids muessen global eindeutig sein (Prefix `ai_home_copilot_`)
- Tests liegen in `/tests/` und verwenden pytest
- Dokumentation in Deutsch bevorzugt

### Module Lifecycle

```python
class MyModule:
    @property
    def name(self) -> str:
        return "my_module"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        # Listener registrieren, Background-Tasks starten
        self._unsub = async_track_state_change_event(ctx.hass, ...)
        self._task = asyncio.create_task(self._background_loop())

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        # Listener entfernen, Tasks canceln
        if self._unsub:
            self._unsub()
        if self._task and not self._task.done():
            self._task.cancel()
        return True
```

### Coordinator Pattern

Der `CopilotDataUpdateCoordinator` (in `coordinator.py`) ist der zentrale Datenhub:
- Polling-Intervall: 120s (Fallback)
- Primaere Updates via Webhook Push (Echtzeit)
- `coordinator.data` enthaelt: status, mood, neurons, habit_summary, predictions

### Projektprinzipien

| Prinzip | Bedeutung |
|---------|-----------|
| **Local-first** | Alles lokal, keine Cloud |
| **Privacy-first** | PII-Redaktion, bounded Storage, opt-in |
| **Governance-first** | Vorschlaege vor Aktionen, Human-in-the-Loop |
| **Safe Defaults** | Sicherheitsrelevante Aktionen immer Manual Mode |

### PR-Checkliste

- [ ] Changelog updated (if user-visible)
- [ ] Docs updated (if applicable)
- [ ] Privacy-first (no secrets, no personal defaults)
- [ ] Safe defaults (caps/limits; persistence off by default)
- [ ] Governance-first (no silent actions)

---

## Wichtige Dateien

| Datei | Beschreibung |
|-------|-------------|
| `custom_components/ai_home_copilot/__init__.py` | Integration Setup, Modul-Registrierung |
| `custom_components/ai_home_copilot/coordinator.py` | DataUpdateCoordinator + API Client |
| `custom_components/ai_home_copilot/entity.py` | CopilotBaseEntity Basisklasse |
| `custom_components/ai_home_copilot/const.py` | Alle Konstanten und Defaults |
| `custom_components/ai_home_copilot/core/runtime.py` | Modul-Lifecycle |
| `custom_components/ai_home_copilot/core/module.py` | CopilotModule Protocol |
| `custom_components/ai_home_copilot/forwarder_n3.py` | N3 Event Forwarder |
| `custom_components/ai_home_copilot/habitus_zones_store_v2.py` | Zone Store |
| `custom_components/ai_home_copilot/repairs.py` | Governance UI Flows |
| `docs/ARCHITECTURE.md` | Vollstaendige Architektur-Dokumentation |
| `docs/HANDBOOK.md` | Setup und Troubleshooting |
