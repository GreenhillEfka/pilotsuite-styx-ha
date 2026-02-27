# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Projektueberblick

**PilotSuite Styx** ist eine Home Assistant Custom Integration, verteilt ueber HACS. Sie verbindet sich mit dem PilotSuite Core Add-on (Port 8909) und stellt 100+ Sensoren, 35 Module und Dashboard Cards in Home Assistant bereit.

**Gegenstueck:** [pilotsuite-styx-core](../pilotsuite-styx-core) -- Core Add-on (Backend, Brain Graph, Habitus, Mood Engine)

- **Domain:** `ai_home_copilot` (technisch, nicht aendern)
- **Sprache:** Python (asyncio, Home Assistant Framework)
- **Lizenz:** Privat, alle Rechte vorbehalten

---

## Entwicklungskommandos

```bash
# Syntax-Check
python -m py_compile $(find custom_components/ai_home_copilot -name '*.py')

# JSON validieren
python -c "import json; json.load(open('custom_components/ai_home_copilot/strings.json'))"

# Alle Tests
python -m pytest tests/ -v --tb=short -x

# Einzelne Test-Datei
python -m pytest tests/test_coordinator.py -v --tb=short

# Test nach Name
python -m pytest tests/ -v --tb=short -k "test_mood_sensor"

# Tests mit Coverage
python -m pytest tests/ -v --tb=short --cov=custom_components/ai_home_copilot --cov-report=term-missing -x

# Security Scan
bandit -r custom_components/ai_home_copilot -ll --skip B101,B404,B603
```

---

## Architektur

### Setup-Kette (Boot)

```
__init__.py
  ├── _MODULE_IMPORTS dict (35 Module)
  ├── _TIER_0..3 Listen (Boot-Reihenfolge)
  └── async_setup_entry()
        ├── CopilotRuntime (core/runtime.py)
        │     └── fuer jedes Modul: module.async_setup_entry(ctx)
        │           └── LegacyModule (Tier 0, erste)
        │                 ├── CopilotDataUpdateCoordinator erstellen
        │                 ├── async_config_entry_first_refresh()  ← try/except!
        │                 ├── Webhook registrieren
        │                 └── Platform Forwarding (sensor, button, binary_sensor, number, select, text)
        ├── async_register_all_services()
        └── Device-Registry Cleanup
```

**Kritisch:** Wenn `async_config_entry_first_refresh()` eine Exception wirft und diese nicht in `legacy.py` gefangen wird, ueberspringt die Runtime das gesamte Legacy-Modul → KEINE Entities werden erstellt. Fix: try/except mit leerer Baseline-Datenstruktur in `coordinator.data`.

### Modul-Tier-System (35 Module)

Module werden in `__init__.py` klassifiziert und in Tier-Reihenfolge gestartet:

| Tier | Name | Verhalten | Module |
|------|------|-----------|--------|
| 0 | KERNEL | Immer geladen, kein Opt-out | legacy, coordinator_module, performance_scaling, events_forwarder, entity_tags, brain_graph_sync |
| 1 | BRAIN | Geladen wenn Core erreichbar | knowledge_graph_sync, habitus_miner, candidate_poller, mood, mood_context, zone_sync, history_backfill, entity_discovery, scene_module, person_tracking, automation_adoption |
| 2 | CONTEXT | Geladen wenn relevante HA-Entities vorhanden | energy_context, weather_context, media_zones, camera_context, network, ml_context, voice_context |
| 3 | EXTENSIONS | Explizit aktiviert | homekit_bridge, frigate_bridge, calendar_module, home_alerts, character_module, waste_reminder, birthday_reminder, dev_surface, ops_runbook, unifi_module, quick_search |

Jedes Modul implementiert das `CopilotModule`-Protocol aus `core/module.py`:

```python
class CopilotModule(Protocol):
    @property
    def name(self) -> str: ...
    async def async_setup_entry(self, ctx: ModuleContext) -> None: ...
    async def async_unload_entry(self, ctx: ModuleContext) -> bool: ...
```

Module-Fehler werden gefangen und geloggt — ein fehlendes Modul stoppt nicht den Boot.

### Coordinator (Datenhub)

`CopilotDataUpdateCoordinator` in `coordinator.py` ist der zentrale Datenhub:

- Polling: 120s Fallback-Intervall
- Primaer: Webhook Push vom Core (Echtzeit)
- Endpoint-Failover: Primaere URL → Fallback-Kandidaten (host.docker.internal, internal_url, external_url)
- Auth: `Authorization: Bearer {token}` + `X-Auth-Token: {token}`
- Failover-Trigger: 404, 405, 408, 429, >= 500 (nicht bei 401/403)

**coordinator.data Shape:**
```python
{
    "ok": bool,              # Core erreichbar?
    "version": str,
    "mood": {"state": str, "confidence": float, "dimensions": {
        "comfort": float, "frugality": float, "joy": float,
        "energy": float, "stress": float
    }},
    "neurons": dict,         # Alle Neuron-Zustaende
    "dominant_mood": str,
    "habit_summary": dict,
    "predictions": list,     # Automation-Kandidaten
    "brain_summary": dict,
}
```

### Config Flow und Options Flow

**Zwei separate Dateien:**
- `config_flow.py` — Ersteinrichtung: `user` (Menu) → `zero_config` | `quick_start` | `manual_setup`
- `config_options_flow.py` — Nachtraegliche Konfiguration: `init` (Menu) → `connection` | `modules` | `habitus_zones` | `entity_tags` | `neurons` | `backup_restore` | `generate_dashboard`

**Wichtige Patterns:**
- `_effective_config()` = merge(entry.data, entry.options) — liest immer den aktuellen Stand
- `_create_merged_entry(updates)` — bewahrt alle nicht geaenderten Keys
- `ensure_defaults(config)` fuellt fehlende Keys aus `DEFAULTS_MAP` (const.py)
- `merged_entry_config()` aus `connection_config.py` — zentrale Config-Zusammenfuehrung
- `single_config_entry: true` in manifest.json — nur eine Instanz erlaubt

### Entity-Basisklasse

Alle Entities erben von `CopilotBaseEntity` (in `entity.py`), die `CoordinatorEntity` erweitert:
- `device_info` via `DeviceInfo` Dataclass (nicht dict)
- `_core_base_url()` mit Failover-Logik
- `_core_headers()` fuer Bearer + X-Auth-Token
- `_fetch(path, timeout_s)` fuer direkte Core-API-Aufrufe
- `unique_id` Prefix: `ai_home_copilot_`

---

## Konventionen

### Domain und Entity-IDs

- **DOMAIN bleibt `ai_home_copilot`** — auch nach Umbenennung zu PilotSuite aendert sich die technische Domain nicht
- Entity-ID Prefix: `sensor.ai_home_copilot_*`, `button.ai_home_copilot_*`, etc.
- Unique-ID Format: `ai_home_copilot_{feature}_{name}`

### Code-Stil

- Python asyncio (async/await)
- TYPE_CHECKING Pattern fuer zirkulaere Imports
- Deutsche Kommentare erlaubt, Code-Bezeichner auf Englisch
- Keine externen Cloud-Abhaengigkeiten

### Dateistruktur

```
custom_components/ai_home_copilot/
├── __init__.py              # Integration Setup, Modul-Registrierung, Tier-Klassifikation
├── coordinator.py           # DataUpdateCoordinator + API Client + Endpoint Failover
├── entity.py                # CopilotBaseEntity Basisklasse
├── const.py                 # Konstanten, DOMAIN, Config Keys, DEFAULTS_MAP
├── manifest.json            # HA Manifest (single_config_entry=true)
├── config_flow.py           # Config Flow (Ersteinrichtung)
├── config_options_flow.py   # Options Flow (29 Menu-Steps)
├── config_helpers.py        # CSV Parsing, Validierung, Discovery
├── config_schema_builders.py # Dynamische Schema-Generierung
├── connection_config.py     # merged_entry_config(), resolve_core_connection()
├── services_setup.py        # Service-Registrierungen
├── core/
│   ├── runtime.py           # CopilotRuntime, ModuleStatus, Lifecycle
│   ├── module.py            # CopilotModule Protocol, ModuleContext
│   ├── registry.py          # Dynamische Modul-Instanziierung
│   └── modules/             # 35 Module (CopilotModule Interface)
├── sensors/                 # Sensor-Entities (100+)
├── button*.py               # Button-Entities (30+)
├── api/                     # Knowledge Graph, User Preference APIs
├── dashboard_cards/         # Lovelace Card Generatoren
├── ml/                      # ML Pattern Recognition
├── translations/            # DE + EN Translations
└── strings.json             # UI Translations + Flow Descriptions (muss valides JSON sein)
```

---

## Hinweise fuer KI-Assistenten

- Aenderungen am DOMAIN-String `ai_home_copilot` sind NICHT erlaubt
- Neue Entities muessen `CopilotBaseEntity` als Basisklasse verwenden
- `device_info` muss `DeviceInfo` Dataclass verwenden (nicht dict)
- Neue Module muessen das `CopilotModule`-Protocol implementieren und in `_MODULE_IMPORTS` + passenden Tier in `__init__.py` registriert werden
- Alle unique_ids muessen global eindeutig sein (Prefix `ai_home_copilot_`)
- `coordinator.data` ist `None` bis zum ersten Refresh → Entities muessen mit `if self.data` absichern
- `strings.json` Struktur: `config.step` = nur Config-Flow-Steps, `options.step` = Options-Flow-Steps, `issues` = HA Repair Definitions
- `class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):` ist valide Python Metaclass-Syntax; `config_entries.FlowHandler` existiert NICHT
- Wenn ein Import in der Kette von `config_flow.py` auf Modul-Ebene fehlschlaegt → "Invalid handler specified"

### Projektprinzipien

| Prinzip | Bedeutung |
|---------|-----------|
| **Local-first** | Alles lokal, keine Cloud |
| **Privacy-first** | PII-Redaktion, bounded Storage, opt-in |
| **Governance-first** | Vorschlaege vor Aktionen, Human-in-the-Loop |
| **Safe Defaults** | Sicherheitsrelevante Aktionen immer Manual Mode |

---

## Wichtige Dateien

| Datei | Beschreibung |
|-------|-------------|
| `custom_components/ai_home_copilot/__init__.py` | Integration Setup, Modul-Registrierung, Tier-System |
| `custom_components/ai_home_copilot/coordinator.py` | DataUpdateCoordinator + API Client + Failover |
| `custom_components/ai_home_copilot/entity.py` | CopilotBaseEntity Basisklasse |
| `custom_components/ai_home_copilot/const.py` | Alle Konstanten, DEFAULTS_MAP, ensure_defaults() |
| `custom_components/ai_home_copilot/config_flow.py` | Config Flow (3 Entry Points) |
| `custom_components/ai_home_copilot/config_options_flow.py` | Options Flow (29 Steps) |
| `custom_components/ai_home_copilot/connection_config.py` | Config Merge + Core Connection Resolution |
| `custom_components/ai_home_copilot/core/runtime.py` | Modul-Lifecycle, ModuleStatus |
| `custom_components/ai_home_copilot/core/module.py` | CopilotModule Protocol |
| `custom_components/ai_home_copilot/core/modules/legacy.py` | Platform Forwarding, Coordinator Setup, Webhook |
| `custom_components/ai_home_copilot/strings.json` | i18n + Flow Descriptions (muss valides JSON sein) |
