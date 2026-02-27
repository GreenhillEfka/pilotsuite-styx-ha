# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Projektueberblick

**PilotSuite Styx** ist eine Home Assistant Custom Integration, verteilt ueber HACS. Sie verbindet sich mit dem PilotSuite Core Add-on (Port 8909) und stellt 94+ Sensoren, 35 Module und Dashboard Cards in Home Assistant bereit.

**Gegenstueck:** [pilotsuite-styx-core](../pilotsuite-styx-core) -- Core Add-on (Backend, Brain Graph, Habitus, Mood Engine). Endpoint-/Payload-/Auth-Aenderungen muessen integrationskompatibel bleiben. Version in `manifest.json` muss mit Release-Tag uebereinstimmen.

- **Domain:** `ai_home_copilot` (technisch, **NICHT aendern**)
- **Sprache:** Python (asyncio, Home Assistant Framework)
- **Mindestversion:** HA 2024.1.0+
- **Version:** 11.0.0

---

## Entwicklungskommandos

```bash
# Syntax-Check (alle ~330 Python-Dateien)
python -m py_compile $(find custom_components/ai_home_copilot -name '*.py')

# Tests ausfuehren
python -m pytest tests/ -v --tb=short -x

# Einzelnen Test ausfuehren
python -m pytest tests/test_config_zones_flow.py -v -x

# Fokussierte Tests (Config/Zones/Identity/Migration)
python -m pytest -q tests/test_config_zones_flow.py tests/test_config_options_flow_merge.py tests/test_device_identity.py tests/test_connection_config_migration.py

# Tests mit Coverage
python -m pytest tests/ -v --tb=short --cov=custom_components/ai_home_copilot --cov-report=term-missing -x

# Security Scan
bandit -r custom_components/ai_home_copilot -ll --skip B101,B404,B603

# JSON/strings.json validieren
python -c "import json; json.load(open('custom_components/ai_home_copilot/strings.json'))"
```

---

## Architektur

### Dual-Repo-Struktur

```
Home Assistant
+-- HACS Integration (ai_home_copilot)      <-- dieses Repo
|     35 Module, 115+ Entities, 94+ Sensoren
|     HTTP REST + Webhook (Token-Auth)
|     v
+-- Core Add-on (copilot_core) Port 8909    <-- separates Repo
      Backend, Brain Graph, Habitus, Mood Engine, Neurons, LLM
```

### 4-Tier Modul-System

36+ Module in `__init__.py` (`_MODULE_IMPORTS` + `_TIER_*` Listen), geladen via `core/runtime.py`:

```
TIER 0 — KERNEL (6 Module, kein Opt-Out)
  legacy, coordinator_module, performance_scaling, events_forwarder, entity_tags, brain_graph_sync

TIER 1 — BRAIN (11 Module, immer wenn Core erreichbar)
  knowledge_graph_sync, habitus_miner, candidate_poller, mood, mood_context,
  zone_sync, history_backfill, entity_discovery, scene_module, person_tracking, automation_adoption

TIER 2 — KONTEXT (7 Module, nur wenn relevante Entities vorhanden)
  energy_context, weather_context, media_zones, camera_context, network, ml_context, voice_context

TIER 3 — ERWEITERUNGEN (12 Module, explizit aktivieren)
  homekit_bridge, frigate_bridge, calendar_module, home_alerts, character_module,
  waste_reminder, birthday_reminder, automation_analyzer, dev_surface, ops_runbook, unifi_module, quick_search
```

#### Wichtige Module (Referenz)

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
| UserPreferenceModule | `core/modules/user_preference_module.py` | Multi-User Preference Learning |
| ZoneBootstrapModule | `core/modules/zone_bootstrap.py` | Zone-Config in ZoneStore V2 laden |
| LiveMoodEngine | `core/modules/live_mood_engine.py` | Lokale Comfort/Joy/Frugality |
| AutomationAnalyzer | `core/modules/automation_analyzer.py` | HA-Automationen analysieren + Self-Healing Repair Issues |
| SuggestionLoader | `core/modules/suggestion_loader.py` | Suggestion-Queue aus allen Quellen befuellen |
| CharacterModule | `character_module.py` | CoPilot-Persoenlichkeit |
| HomeAlertsModule | `home_alerts_module.py` | Kritische Zustandsueberwachung |
| VoiceContext | `voice_context.py` | Sprachsteuerungs-Kontext |
| KnowledgeGraphSync | `knowledge_graph_sync.py` | Knowledge Graph Synchronisation |

Neue Module: `CopilotModule`-Interface aus `core/modules/module.py` implementieren, in `_MODULE_IMPORTS` + passende `_TIER_*` Liste eintragen. Boot-Reihenfolge: T0 → T1 → T2 → T3.

### Coordinator Pattern

`CopilotDataUpdateCoordinator` in `coordinator.py` ist der zentrale Datenhub:
- Polling-Intervall: 120s Fallback, primaer Webhook Push (Echtzeit)
- 12 parallele API-Calls via `asyncio.gather` in `_async_update_data()`
- Multi-URL Failover in `CopilotApiClient._request_json()`
- `coordinator.data`: `{ok, version, mood, neurons, brain_summary, habitus_rules, core_modules, override_modes, ...}`
- Mood v3.0: `coordinator.data["mood"] = {state, confidence, dimensions: {comfort, frugality, joy, energy, stress}}`

### Entity-Erstellung (sensor.py)

Entities werden in `sensor.py:async_setup_entry()` tiered erstellt (spiegelt Modul-Tiers):
- **TIER 0 (KERNEL)**: Immer — Version, API Status, Pipeline Health, LLM Health, System Health (15 Sensoren)
- **TIER 1 (BRAIN)**: Immer — 8 Mood-Sensoren, Brain Graph, Habitus, Neuron Layer (16 Sensoren)
- **TIER 2 (KONTEXT)**: Bedingt — Events Forwarder, Media, Camera, UniFi, Weather, Energy (je nach vorhandenen Entities)
- **TIER 3**: Feature-Sensoren (Anomaly, Prediction, Intelligence, etc.)

### Config Flow Architektur

3 Setup-Pfade (Zero Config / Quick Start / Manual), aufgeteilt in 10 Dateien:

| Datei | Verantwortung |
|-------|---------------|
| `config_flow.py` | Haupt-ConfigFlow + OptionsFlow Entry Points |
| `config_options_flow.py` | 29 Options-Flow Steps mit `_effective_config()` |
| `config_wizard_steps.py` | 7 Quick-Start Wizard Steps (Discovery → Zones → Entities → Features → Network → Review) |
| `config_zones_flow.py` | Zonen-Verwaltung (CRUD) innerhalb Options-Flow |
| `config_tags_flow.py` | Entity-Tag-Verwaltung innerhalb Options-Flow |
| `config_schema_builders.py` | Volselect/Schema-Builder fuer dynamische Formulare |
| `config_helpers.py` | Shared Utilities (Validierung, Konvertierung) |
| `config_snapshot.py` | Config-Snapshot Datenklassen |
| `config_snapshot_flow.py` | Snapshot Export/Import Flow |
| `config_snapshot_store.py` | Snapshot Persistenz |

### Auto-Setup (v10.4.2)

Drei Dateien fuer Zero-Config Onboarding:
- **`auto_setup.py`**: Erstellt Habitus-Zonen aus HA Areas + taggt Entities automatisch. Run-once Guard via `_auto_setup_done`.
- **`entity_classifier.py`**: 4-Signal ML-Classifier (domain → device_class → UOM → keywords). Confidence-Kaskade: 0.9 > 0.8 > 0.75 > 0.6.
- **`panel_setup.py`**: Registriert Sidebar-Panel (iframe zu Core Ingress). Nutzt direkte Imports aus `homeassistant.components.frontend`.

### Events Forwarder (forwarder_n3.py)

N3-Envelope-Format mit Batching (50 Events), PII-Redaktion, Idempotency, Debouncing, persistent Queue. **Registry-Zugriff ueber moderne Imports:**

```python
from homeassistant.helpers import entity_registry as er
entity_registry = er.async_get(self.hass)
```

**NICHT** `self.hass.helpers.entity_registry.async_get()` verwenden (removed in HA 2024.x).

---

## Konventionen

### Domain und Entity-IDs

- **DOMAIN bleibt `ai_home_copilot`** — technische Domain niemals aendern
- Entity-ID Prefix: `sensor.ai_home_copilot_*`
- Unique-ID Format: `ai_home_copilot_{feature}_{name}`

### Basisklasse

Alle Entities erben von `CopilotBaseEntity` (in `entity.py`):
- `DeviceInfo` Dataclass (nicht dict) fuer `device_info`
- Konsistente `unique_id` mit `ai_home_copilot_` Prefix
- Automatische Coordinator-Anbindung via `CoordinatorEntity`

### HA Registry-Zugriff (modernes Pattern)

```python
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
entity_reg = er.async_get(hass)
```

### Config Defaults (`const.py`)

`DEFAULTS_MAP` (62+ Keys) ist die zentrale Single Source of Truth fuer alle Config-Defaults. `ensure_defaults(config)` garantiert, dass jeder Config-Eintrag einen Wert hat — kritisch fuer Migration und ZeroConfig-Kompatibilitaet.

### Code-Stil

- Python asyncio (async/await)
- `TYPE_CHECKING` Pattern fuer zirkulaere Imports
- Deutsche Kommentare erlaubt, Code-Bezeichner auf Englisch
- Keine externen Cloud-Abhaengigkeiten
- `snake_case` (Funktionen/Variablen), `PascalCase` (Klassen), `UPPER_CASE` (Konstanten)
- Commit-Messages: `feat:`, `fix:`, `chore:` Prefix, paired Releases mit styx-core

---

## Tests

Tests in `tests/` mit pytest. `conftest.py` stellt globale HA-Mocks bereit:

- **`SubscriptableMagicMock`**: Unterstuetzt `Type[Generic]`-Subscripting fuer HA-Typen
- **`MockCoordinatorEntity`**: Echte Basisklasse (kein MagicMock), damit Entities davon erben koennen
- **`MockRepairsFlow`**: Echte Basisklasse fuer Repair-Flow-Tests
- **10 Mock-Entity-Klassen**: `MockSensorEntity`, `MockBinarySensorEntity`, `MockButtonEntity`, `MockSelectEntity`, `MockSwitchEntity`, `MockNumberEntity`, `MockTextEntity`, `MockMediaPlayerEntity`, `MockCamera`, `MockCalendarEntity`

Neue Tests muessen diese Mocks verwenden — **nicht** eigene HA-Mocks erstellen.

---

## Aktueller Stand (v11.0.0)

- **Tests:** 845 passed, 4 skipped
- **Python-Dateien:** 334 (alle kompilieren sauber)
- 36+ Module in 4 Tiers (Kernel, Brain, Context, Extensions), alle mit Status-Tracking via `ModuleStatusSensor`
- 140+ Entities (94+ Sensoren inkl. 3 Live-Mood-Dimensionen, 22+ Buttons, Numbers, Selects), 22+ Dashboard Cards
- 8 Mood-Sensoren v3.0 (State, Confidence, Comfort, Joy, Energy, Stress, Frugality, NeuronActivity)
- 14 Kontext-Neuronen + NeuronLayerSensor + NeuronTagResolver (4-Phasen Multi-Layer Pipeline)
- Brain Graph Visualization (vis.js) + Summary Sensor
- 3-Tab YAML Dashboard Generator (Habitus/Hausverwaltung/Styx) + 7-Tab Legacy Generator
- 9 Habitus-Zonen mit 141 realen Entity-IDs, 12 Entity-Rollen
- Live-Mood-Engine: Comfort/Joy/Frugality aus echten Entity-States
- Automation-Analyzer: Health-Scoring, Repair-Hints, Verbesserungsvorschlaege
- Auto-Setup: Zero-Config Zonen-Erstellung + ML Entity Classifier + Sidebar Panel
- 28/28 Options-Flow Steps mit `data_description` + `_effective_config()` Preservation
- `DEFAULTS_MAP` + `ensure_defaults()` fuer ZeroConfig/QuickStart-Kompatibilitaet
- `single_config_entry: true` in manifest.json
- DeviceInfo Dataclass (HA Best Practice)
- PilotSuite Branding durchgaengig

---

## Hinweise fuer KI-Assistenten

- Aenderungen am DOMAIN-String `ai_home_copilot` sind **NICHT** erlaubt
- Neue Entities muessen `CopilotBaseEntity` verwenden + `DeviceInfo` Dataclass
- Neue Module: `CopilotModule`-Interface implementieren, in `_MODULE_IMPORTS` + `_TIER_*` Liste eintragen
- Alle unique_ids mit Prefix `ai_home_copilot_`
- Neue Sensoren in `sensor.py:async_setup_entry()` im korrekten Tier instantiieren
- HA Registry: **nur** `from homeassistant.helpers import ...` Pattern, **nie** `hass.helpers.*`
- Frontend-Zugriff: **nur** `from homeassistant.components.frontend import ...`, **nie** `hass.components.*`
- Neue Config-Optionen: Key in `DEFAULTS_MAP` (const.py) eintragen + `ensure_defaults()` testen
- Tests: Mock-Klassen aus `conftest.py` verwenden, keine eigenen HA-Mocks
- Dokumentation in Deutsch bevorzugt

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
- [ ] Version in manifest.json matches release tag

---

## Wichtige Dateien

| Datei | Beschreibung |
|-------|-------------|
| `custom_components/ai_home_copilot/__init__.py` | Integration Setup, 4-Tier Modul-Registrierung |
| `custom_components/ai_home_copilot/coordinator.py` | DataUpdateCoordinator + CopilotApiClient |
| `custom_components/ai_home_copilot/sensor.py` | Entity-Erstellung (Tier 0-3) |
| `custom_components/ai_home_copilot/entity.py` | CopilotBaseEntity Basisklasse |
| `custom_components/ai_home_copilot/const.py` | Alle Konstanten, DEFAULTS_MAP (62+ Keys) |
| `custom_components/ai_home_copilot/config_flow.py` | 3 Setup-Pfade (Zero/Quick/Manual) |
| `custom_components/ai_home_copilot/config_options_flow.py` | 29 Options-Flow Steps |
| `custom_components/ai_home_copilot/config_wizard_steps.py` | 7-Step Quick-Start Wizard |
| `custom_components/ai_home_copilot/forwarder_n3.py` | N3 Event Forwarder (Batching, PII) |
| `custom_components/ai_home_copilot/auto_setup.py` | Zero-Config Zonen + Tags |
| `custom_components/ai_home_copilot/entity_classifier.py` | 4-Signal ML Entity Classifier |
| `custom_components/ai_home_copilot/panel_setup.py` | Sidebar Panel Registration |
| `custom_components/ai_home_copilot/core/runtime.py` | Modul-Lifecycle + ModuleStatus State Machine |
| `custom_components/ai_home_copilot/core/modules/entity_tags_module.py` | NeuronTagResolver |
| `custom_components/ai_home_copilot/habitus_zones_store_v2.py` | Zone Store |
| `custom_components/ai_home_copilot/sensors/mood_sensor.py` | 8 Mood-Sensoren v3.0 + 3 LiveMoodDimension |
| `custom_components/ai_home_copilot/sensors/neurons_14.py` | 14 Neuron-Sensoren |
| `custom_components/ai_home_copilot/data/zones_config.json` | 9 Habitus-Zonen, 141 Entities |
| `custom_components/ai_home_copilot/data/initial_suggestions.json` | Initiale Vorschlaege |
| `custom_components/ai_home_copilot/repairs.py` | Governance UI Flows |
| `custom_components/ai_home_copilot/dashboard_pipeline.py` | Unified Dashboard Orchestrator |
| `custom_components/ai_home_copilot/conversation_context.py` | Context-Rich System-Prompt Builder |
| `docs/INTEGRATION_CONCEPT_v10.5.md` | Integrationskonzept mit Architektur |
| `tests/conftest.py` | Globale HA-Mocks + Mock-Entity-Klassen |
| `docs/ARCHITECTURE.md` | Vollstaendige Architektur-Dokumentation |
