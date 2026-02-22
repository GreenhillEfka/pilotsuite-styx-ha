# PilotSuite HACS Integration -- Systemarchitektur

> Domain: `ai_home_copilot` | 303 Python-Dateien | 31 Runtime-Module | 94+ Sensoren
>
> Version: 7.7.16 | IoT-Klasse: `local_push` | Abhaengigkeit: `webhook`

---

## Inhaltsverzeichnis

1. [Dual-Repo Architektur](#1-dual-repo-architektur)
2. [Coordinator Pattern](#2-coordinator-pattern)
3. [Module Lifecycle](#3-module-lifecycle)
4. [Entity Pattern](#4-entity-pattern)
5. [Config Flow](#5-config-flow)
6. [Events Forwarder](#6-events-forwarder)
7. [Habitus Zones v2](#7-habitus-zones-v2)
8. [Data Flow](#8-data-flow)
9. [Persistence](#9-persistence)
10. [File Structure](#10-file-structure)

---

## 1. Dual-Repo Architektur

PilotSuite besteht aus zwei getrennten Repositories, die zusammen ein vollstaendiges System bilden:

```
Home Assistant
|
+-- HACS Integration (ai_home_copilot)           <-- DIESES REPO
|     - 303 Python-Dateien
|     - Sensoren, Buttons, Select, Text, Number
|     - Dashboard Cards (Lovelace YAML-Generatoren)
|     - Config Flow + Options Flow
|     - Events Forwarder (HA -> Core)
|     - Webhook-Empfaenger (Core -> HA)
|     - Repairs UI fuer Governance
|
|   HTTP REST API (Token-Auth, Port 8909)
|     POST /api/v1/events         (Forwarder -> Core)
|     GET  /api/v1/status         (Coordinator Polling)
|     GET  /api/v1/neurons/mood   (Mood-Abfrage)
|     GET  /api/v1/neurons        (Neuron-States)
|     GET  /api/v1/candidates     (Vorschlaege abholen)
|     PUT  /api/v1/candidates/:id (Entscheidung zurueckmelden)
|     POST /api/v1/graph/ops      (Graph-Operationen)
|     v
|
+-- Core Add-on (copilot_core)                    <-- SEPARATES REPO
      - Flask + Waitress auf Port 8909
      - Brain Graph (Wissens- und Beziehungsgraph)
      - Habitus Engine (Muster-Erkennung)
      - Mood Engine (Stimmungsberechnung)
      - Ollama LLM (lokal, bundled)
      - RAG / VectorStore
```

### Kommunikationsrichtungen

| Richtung | Mechanismus | Zweck |
|----------|-------------|-------|
| Integration -> Core | HTTP REST (aiohttp) | Events weiterleiten, Status abfragen, Entscheidungen melden |
| Core -> Integration | Webhook Push | Echtzeit-Updates (Mood, Suggestions, Neuron-States) |
| Integration -> Core | Polling (120s Fallback) | Sicherstellen, dass Daten aktuell bleiben |

Die Authentifizierung erfolgt ueber Token-basierte Header (`Authorization: Bearer <token>` bzw. `X-Auth-Token`). Ein leerer Token erlaubt alle Anfragen (First-Run-Experience).

Identity-Hardening (ab `7.7.14`, erweitert in `7.7.16`):
- Config-Flow ist als Single-Instance abgesichert (keine neuen Doppel-Entries bei erneutem Hinzufuegen).
- Haupt-Device nutzt stabile Identifier (`styx_hub`) mit Legacy-Alias (`host:port`) fuer Update-Kompatibilitaet.

---

## 2. Coordinator Pattern

Die Integration nutzt Home Assistants `DataUpdateCoordinator` als zentralen Datenhub. Alle Sensoren abonnieren den Coordinator und werden automatisch aktualisiert.

### Klasse: `CopilotDataUpdateCoordinator`

**Datei:** `coordinator.py`

```python
class CopilotDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        # Hybrid-Modus: 120s Fallback-Polling
        # Echtzeit-Updates kommen via Webhook Push
        super().__init__(
            hass, logger=_LOGGER,
            name="ai_home_copilot_coordinator",
            update_interval=timedelta(seconds=120),
        )
        self.api = CopilotApiClient(session, base_url, token)
```

### Polling-Intervall

- **120 Sekunden** als Fallback (Safety Net)
- Primaer kommen Updates via Webhook Push in Echtzeit
- Der Coordinator fusioniert beide Datenstroeme

### Daten-Dict Struktur (`coordinator.data`)

```python
{
    "ok": True,                          # Core erreichbar?
    "version": "7.7.15",                  # Core-Version
    "mood": {                            # Aktuelle Stimmung
        "mood": "relaxed",
        "confidence": 0.85
    },
    "neurons": {                         # Neuron-Zustaende
        "presence_room": "wohnzimmer",
        "activity_level": "low",
        ...
    },
    "dominant_mood": "relaxed",          # Shortcut
    "mood_confidence": 0.85,             # Shortcut
    "habit_summary": {                   # ML Habit Learning
        "total_patterns": 42,
        "time_patterns": {...},
        "device_patterns": {...},
    },
    "predictions": [...],                # Habit-Vorhersagen
    "sequences": [...],                  # Sequenz-Muster
}
```

### API Client (`CopilotApiClient`)

Der eingebettete `CopilotApiClient` kapselt alle HTTP-Aufrufe zum Core Add-on:

- `async_get_status()` -- Basis-Status (Version, OK)
- `async_get_mood()` -- Aktuelle Stimmung aus dem Neural System
- `async_get_neurons()` -- Alle Neuron-States
- `async_evaluate_neurons(context)` -- Neural Pipeline mit HA-States evaluieren

### Webhook Push (Core -> Integration)

Der Webhook-Handler (`webhook.py`) empfaengt Echtzeit-Events vom Core:

| Event-Typ | Beschreibung |
|-----------|-------------|
| `status` | Core-Status-Update |
| `mood_changed` | Stimmungsaenderung |
| `suggestion_new` | Neuer Vorschlag |
| `neuron_update` | Neuron-State-Aenderung |

Updates werden direkt in `coordinator.data` gemerged und lassen alle abonnierten Entities aktualisieren.

---

## 3. Module Lifecycle

### CopilotModule Interface

**Datei:** `core/module.py`

```python
@runtime_checkable
class CopilotModule(Protocol):
    @property
    def name(self) -> str: ...

    async def async_setup_entry(self, ctx: ModuleContext) -> None: ...

    async def async_unload_entry(self, ctx: ModuleContext) -> bool: ...
```

Der `ModuleContext` ist ein schlankes, immutables Datenpaket:

```python
@dataclass(frozen=True, slots=True)
class ModuleContext:
    hass: HomeAssistant
    entry: ConfigEntry
```

Module speichern entry-spezifische Daten unter `hass.data[DOMAIN][entry_id]` nach Bedarf.

### Registry und Runtime

**Dateien:** `core/registry.py`, `core/runtime.py`

```
ModuleRegistry        CopilotRuntime
+-- _factories {}     +-- registry: ModuleRegistry
    name -> class     +-- _live_modules: {entry_id: {name: instance}}
                      +-- get(hass) -> Singleton
                      +-- async_setup_entry(entry, modules)
                      +-- async_unload_entry(entry, modules)
```

**Registrierung (in `__init__.py`):**

1. `_get_runtime(hass)` holt oder erstellt den Singleton `CopilotRuntime`
2. Jede Modulklasse wird per `registry.register(name, class)` registriert
3. `runtime.async_setup_entry()` iteriert ueber die Modulliste und ruft `mod.async_setup_entry(ctx)` auf
4. Fehler in einzelnen Modulen werden gefangen und geloggt -- andere Module starten trotzdem

**Entladen (umgekehrte Reihenfolge):**

```python
async def async_unload_entry(self, entry, modules):
    for name in reversed(list(modules)):
        mod = entry_modules.get(name)
        await mod.async_unload_entry(ctx)
```

### Aktive Module (28+)

| Modul | Datei | Funktion |
|-------|-------|----------|
| `legacy` | `legacy.py` | Basismodul, Coordinator + Entity-Plattformen |
| `events_forwarder` | `events_forwarder.py` | HA-Events an Core weiterleiten |
| `habitus_miner` | `habitus_miner.py` | Muster-Erkennung und Zone-Management |
| `candidate_poller` | `candidate_poller.py` | Vorschlaege vom Core abholen |
| `brain_graph_sync` | `brain_graph_sync.py` | Brain Graph Synchronisation |
| `mood` | `mood_module.py` | Mood-Berechnung |
| `mood_context` | `mood_context_module.py` | Mood-Integration und Kontext |
| `media_zones` | `media_context_module.py` | Media-Player-Tracking |
| `energy_context` | `energy_context_module.py` | Energiemonitoring |
| `weather_context` | `weather_context_module.py` | Wetter-Integration |
| `network` | `unifi_context_module.py` | Netzwerk-Ueberwachung (UniFi) |
| `unifi_module` | `unifi_module.py` | UniFi-Hardware-Integration |
| `ml_context` | `ml_context_module.py` | ML-Kontext (Anomalien, Habits) |
| `camera_context` | `camera_context_module.py` | Kamera-Kontext (Frigate, etc.) |
| `quick_search` | `quick_search.py` | Entitaets-Schnellsuche |
| `voice_context` | `voice_context.py` | Sprachsteuerungs-Kontext |
| `knowledge_graph_sync` | `knowledge_graph_sync.py` | Knowledge Graph Sync |
| `performance_scaling` | `performance_scaling.py` | Performance-Skalierung |
| `dev_surface` | `dev_surface.py` | Debug-Oberflaeche und DevLog |
| `ops_runbook` | `ops_runbook.py` | Betriebshandbuch-Verwaltung |
| `home_alerts` | `home_alerts_module.py` | Kritische Zustandsueberwachung |
| `character_module` | `character_module.py` | CoPilot-Persoenlichkeit |
| `waste_reminder` | `waste_reminder_module.py` | Abfallkalender-Erinnerungen |
| `birthday_reminder` | `birthday_reminder_module.py` | Geburtstags-Erinnerungen |
| `entity_tags` | `entity_tags_module.py` | Entity-Tag-Verwaltung |
| `person_tracking` | `person_tracking_module.py` | Personen-Tracking |
| `frigate_bridge` | `frigate_bridge.py` | Frigate NVR Bridge |
| `scene_module` | `scene_module.py` | Szenen-Verwaltung |
| `homekit_bridge` | `homekit_bridge.py` | HomeKit-Bridge |
| `calendar_module` | `calendar_module.py` | Kalender-Integration |

### Listener-Cleanup

Jedes Modul ist fuer das Aufraumen seiner eigenen Listener verantwortlich. Das typische Muster:

```python
class MyModule:
    async def async_setup_entry(self, ctx):
        self._unsub = async_track_state_change_event(ctx.hass, ...)
        self._task = asyncio.create_task(self._background_loop())

    async def async_unload_entry(self, ctx):
        if self._unsub:
            self._unsub()
        if self._task and not self._task.done():
            self._task.cancel()
        return True
```

---

## 4. Entity Pattern

### Basisklasse: `CopilotBaseEntity`

**Datei:** `entity.py`

```python
class CopilotBaseEntity(CoordinatorEntity["CopilotDataUpdateCoordinator"]):
    _attr_has_entity_name = True

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._host = coordinator._config.get("host")
        self._port = coordinator._config.get("port")

    @property
    def device_info(self):
        return {
            "identifiers": {("ai_home_copilot", f"{self._host}:{self._port}")},
            "name": "PilotSuite Core",
            "manufacturer": "Custom",
            "model": "MVP Core",
        }
```

**Garantien der Basisklasse:**

- Einheitliche `device_info` -- alle Entities gruppieren sich unter einem Geraet im Device Registry
- Konsistentes Identifier-Format: `("ai_home_copilot", "<host>:<port>")`
- Automatische Coordinator-Anbindung via `CoordinatorEntity`
- `_attr_has_entity_name = True` fuer saubere Namensgebung

### Unique-ID Format

Alle Unique-IDs folgen dem Schema:

```
ai_home_copilot_{feature}_{name}
```

Beispiele:
- `ai_home_copilot_habitus_zones_v2_json`
- `ai_home_copilot_mood_sensor`
- `ai_home_copilot_debug_level_select`
- `ai_home_copilot_forwarder_queue_depth`

### Entity-Plattformen

| Plattform | Datei(en) | Anzahl | Beschreibung |
|-----------|-----------|--------|-------------|
| **sensor** | `sensor.py`, `sensors/*.py`, `*_entities.py` | 94+ | Mood, Neuronen, Habits, Energie, Mesh, Pipeline, etc. |
| **button** | `button.py`, `button_*.py` | 40+ | Aktionen: Generate, Fetch, Sync, Debug, Backup |
| **select** | `select.py` | 4+ | Debug-Level, Media-Zone, Habitus Global State |
| **text** | `text.py` | 2+ | Zones Bulk-Editor (YAML/JSON, max 65535 Zeichen) |
| **number** | `number.py` | 3+ | Seed-Limits (Offers/Hour, Offers/Update, Min Interval) |
| **binary_sensor** | `binary_sensor.py` | 2+ | Verbindungsstatus, Feature-Flags |
| **camera** | `camera_entities.py` | 2 | Activity-Camera, Zone-Camera (Frigate) |

### Sensor-Kategorien (Auszug der 94+ Sensoren)

| Kategorie | Beispiele |
|-----------|----------|
| Neuronen (14 Stueck) | PresenceRoom, ActivityLevel, TimeOfDay, LightLevel, NoiseLevel, WeatherContext, CalendarLoad, StressProxy, ... |
| Mood | MoodSensor, MoodConfidenceSensor, MoodDashboard, MoodHistory, MoodExplanation |
| Habitus | ZonesV2Count, ZonesV2States, ZonesV2Health, MinerRuleCount, MinerStatus, MinerTopRule |
| Media | MusicActiveCount, MusicNowPlaying, TvActiveCount, ActiveMode, ActiveZone |
| Energie | EnergyInsight, EnergyRecommendation |
| ML | HabitLearning, HabitPrediction, SequencePrediction, AnomalyAlert, PredictiveAutomation |
| Mesh | ZWaveNetworkHealth, ZigbeeDevicesOnline, MeshTopology |
| System | CoreApiV1Status, PipelineHealth, DebugMode, SystemHealthEntityCount, SqliteDbSize |
| Forwarder | QueueDepth, DroppedTotal, ErrorStreak |
| Mobile | MobileDashboard, QuickActions, EntityGrid |

---

## 5. Config Flow

### ConfigFlow (Ersteinrichtung)

**Datei:** `config_flow.py` (duenner Koordinator), Logik aufgeteilt in:
- `config_helpers.py` -- CSV-Utils, Konstanten
- `config_schema_builders.py` -- Schema-Builder-Funktionen
- `config_wizard_steps.py` -- Wizard-Schritt-Handler
- `config_zones_flow.py` -- Zone-Management + Helfer

#### Hauptmenue (`async_step_user`)

```
PilotSuite Setup
+-- Zero Config    -> Sofort starten mit Smart Defaults (Styx)
+-- Quick Start    -> Gefuehrter Wizard (~2 Min)
+-- Manual Setup   -> Experten-Konfiguration
```

**Zero Config:** Erstellt sofort einen Config-Entry mit Defaults (`homeassistant.local:8909`, Name "Styx"). Kein einziges Formular.

**Quick Start (Wizard):** Mehrstufiger Assistent mit folgenden Schritten:

```
discovery -> zones -> zone_entities -> entities -> features -> network -> review
```

| Schritt | Inhalt |
|---------|--------|
| `discovery` | Auto-Discovery von Entities |
| `zones` | Raeume/Zonen auswaehlen |
| `zone_entities` | Entities den Zonen zuordnen |
| `entities` | Zusaetzliche Entities konfigurieren |
| `features` | Feature-Toggles (Forwarder, ML, etc.) |
| `network` | Host, Port, Token |
| `review` | Zusammenfassung und Bestaetigung |

**Manual Setup:** Direktes Formular mit Host, Port, Token, Test-Light. Validiert die Verbindung zum Core.

### OptionsFlowHandler (Laufzeit-Konfiguration)

**Datei:** `config_options_flow.py`

#### Hauptmenue (`async_step_init`)

```
Optionen
+-- settings          -> Verbindung, Features, Entity-Listen
+-- habitus_zones     -> Zone-Verwaltung (CRUD)
+-- entity_tags       -> Entity-Tag-Verwaltung
+-- neurons           -> Neural System Entities konfigurieren
+-- backup_restore    -> Config Snapshots (Export/Import)
```

#### Habitus Zones Submenue

```
habitus_zones
+-- create_zone         -> Neue Zone erstellen
+-- edit_zone           -> Bestehende Zone bearbeiten
+-- delete_zone         -> Zone loeschen
+-- generate_dashboard  -> Lovelace YAML generieren
+-- publish_dashboard   -> Dashboard in www/ publizieren
+-- bulk_edit           -> YAML/JSON Bulk-Editor
+-- back                -> Zurueck zum Hauptmenue
```

#### Entity Tags Submenue

```
entity_tags
+-- add_tag     -> Neuen Tag hinzufuegen
+-- edit_tag    -> Tag bearbeiten
+-- delete_tag  -> Tag entfernen
+-- back        -> Zurueck
```

---

## 6. Events Forwarder

### Ueberblick

Der N3 Events Forwarder (`forwarder_n3.py`) leitet HA-Events in einem privacy-konformen Envelope-Format an den Core weiter. Er ist das zentrale Bindeglied fuer die Muster-Erkennung im Brain Graph.

### N3 Envelope Format

```json
{
    "v": 1,
    "ts": "2025-01-15T14:30:00Z",
    "src": "ha",
    "kind": "state_changed",
    "entity_id": "light.wohnzimmer",
    "domain": "light",
    "zone_id": "wohnzimmer",
    "trigger": "user",
    "context_id": "abc123def456",
    "old": { "state": "off", "attrs": {} },
    "new": { "state": "on", "attrs": {"brightness": 255} }
}
```

### Batching

- Events werden in einer In-Memory-Queue gesammelt
- **Flush-Intervall:** 0.5 Sekunden (konfigurierbar ueber `flush_interval`)
- **Batch-Groesse:** 50 Events (konfigurierbar ueber `batch_size`)
- **Max Queue:** 1000 Events -- bei Ueberlauf werden die aeltesten verworfen
- Bei vollem Batch wird sofort geflusht (ohne auf das Intervall zu warten)

### Persistent Queue

- Nutzt Home Assistants `Store`-API (JSON-basiert in `.storage/`)
- Speicherort: `.storage/ai_home_copilot_n3_forwarder`
- Bei Stop werden ausstehende Events persistiert
- Bei Start werden persistierte Events wieder geladen
- Beinhaltet auch: Debounce-Cache, Seen-Events-Cache

### PII-Redaktion (Privacy)

Der Forwarder implementiert mehrere Datenschutz-Schichten:

| Massnahme | Detail |
|-----------|--------|
| **Domain-Projektionen** | Nur erlaubte Attribute pro Domain (z.B. `light`: brightness, color_temp, rgb_color) |
| **Globale Redaktion** | GPS-Koordinaten, Tokens, Zugangsschluessel immer entfernt |
| **Sensitive-Key-Pattern** | Regex `/token\|key\|secret\|password/i` matcht und entfernt |
| **Context-ID-Trunkierung** | Context-IDs werden auf 12 Zeichen gekuerzt (Korrelation moeglich, Reversierung nicht) |
| **Friendly-Name** | Standardmaessig entfernt (opt-in ueber Konfiguration) |
| **Extra-Strip** | Benutzerdefinierte Attribute koennen zusaetzlich entfernt werden |

### Idempotency

- Jedes Event erhaelt einen Key aus `{kind}:{context_id}`
- Bereits gesehene Keys werden fuer `idempotency_ttl` Sekunden (default: 120s) gecacht
- Cache wird bei >1000 Eintraegen automatisch bereinigt
- Verhindert doppelte Verarbeitung bei Webhook-Redeliveries

### Debounce

Hochfrequente Domains werden gedrosselt:

| Domain | Debounce-Intervall |
|--------|-------------------|
| `sensor` | 1.0 Sekunden |
| `binary_sensor` | 0.5 Sekunden |
| Alle anderen | Kein Debounce |

### Heartbeat

- Optionaler Heartbeat-Mechanismus (standardmaessig aktiviert)
- Sendet alle 60 Sekunden ein `kind: "heartbeat"` Envelope
- Enthaelt: Entity-Count, Domain-Verteilung, Queue-Tiefe
- Ermoeglicht dem Core die Integration-Health zu ueberwachen

### Erlaubte Domains

```python
DOMAIN_PROJECTIONS = {
    "light", "climate", "media_player", "binary_sensor",
    "sensor", "cover", "lock", "person", "device_tracker", "weather"
}
```

Service-Call-Forwarding ist separat konfigurierbar und auf sichere Domains beschraenkt (`light`, `media_player`, `climate`, `cover`, `lock`, `switch`, `scene`, `script`). Blockierte Domains: `notify`, `rest_command`, `shell_command`, `tts`.

---

## 7. Habitus Zones v2

### Ueberblick

Habitus Zones modellieren die raeumliche Struktur des Zuhauses. Jede Zone hat Entities mit Rollen, eine Hierarchie-Ebene und einen Zustand.

**Datei:** `habitus_zones_store_v2.py`

### Zone-Datenmodell (`HabitusZoneV2`)

```python
@dataclass(frozen=True, slots=True)
class HabitusZoneV2:
    # Core Identity
    zone_id: str                    # "zone:wohnzimmer"
    name: str                       # "Wohnzimmer"
    zone_type: ZONE_TYPE            # "room" | "area" | "floor" | "outdoor"

    # Entity Membership
    entity_ids: tuple[str, ...]     # Flache Liste (Legacy)
    entities: dict[str, tuple]      # Rollenbasiert: {"motion": [...], "lights": [...]}

    # Hierarchie
    parent_zone_id: str | None      # "zone:living_area"
    child_zone_ids: tuple[str, ...]
    floor: str | None               # "EG", "OG", "UG"

    # Brain Graph Integration
    graph_node_id: str | None       # Auto-Sync: "zone:wohnzimmer"
    in_edges: tuple[str, ...]       # Entity-IDs in Zone
    out_edges: tuple[str, ...]      # Zone -> Entity Controls

    # State Machine
    current_state: ZONE_STATE       # "idle" | "active" | "transitioning" | "disabled" | "error"
    state_since_ms: int | None

    # Metadata
    priority: int                   # 0=niedrig, 10=hoch
    tags: tuple[str, ...]
    metadata: dict | None
```

### Entity-Rollen

Jede Zone ordnet ihren Entities semantische Rollen zu:

```python
KNOWN_ROLES = {
    "motion",       # Bewegungsmelder
    "lights",       # Beleuchtung
    "temperature",  # Temperatursensor
    "humidity",     # Luftfeuchte
    "co2",          # CO2-Sensor
    "pressure",     # Luftdruck
    "noise",        # Laermsensor
    "heating",      # Heizung/Klima
    "door",         # Tuerkontakt
    "window",       # Fensterkontakt
    "cover",        # Rolladen
    "lock",         # Schloss
    "media",        # Mediaplayer
    "power",        # Leistungsmessung
    "energy",       # Energiemessung
    "brightness",   # Helligkeitssensor
    "other",        # Sonstige
}
```

Rollen-Aliase sorgen dafuer, dass deutsche und englische Bezeichnungen erkannt werden (z.B. `"luftfeuchte"` -> `"humidity"`, `"rollo"` -> `"cover"`).

### Zone CRUD

| Funktion | Beschreibung |
|----------|-------------|
| `async_get_zones_v2(hass, entry_id)` | Alle Zones laden |
| `async_set_zones_v2(hass, entry_id, zones)` | Zones speichern (mit Validierung) |
| `async_set_zones_v2_from_raw(hass, entry_id, raw)` | YAML/JSON parsen, normalisieren, speichern |
| `_normalize_zone_v2(obj)` | Dict in `HabitusZoneV2` konvertieren |
| `_validate_zone_v2(hass, zone)` | Jede Zone braucht mind. 1 Motion + 1 Light Entity |

### Validierungsregel

Jede Zone **muss** mindestens enthalten:
- 1x Motion/Presence Entity (binary_sensor mit device_class `motion`/`presence`/`occupancy`)
- 1x Light Entity (domain `light`)

Zones ohne diese Minimum-Ausstattung werden beim Speichern abgelehnt (`ValueError`).

### Konfliktaufloesung (`ZoneConflictResolver`)

Wenn Entities zu mehreren Zones gehoeren, muss ein Konflikt aufgeloest werden:

| Strategie | Beschreibung |
|-----------|-------------|
| `HIERARCHY` | Spezifischere Zone (Kind) gewinnt (Default) |
| `PRIORITY` | Hoehere Prioritaet gewinnt |
| `USER_PROMPT` | HA-Event feuern, Nutzer entscheidet |
| `MERGE` | Ueberlappende Entities zusammenfuehren |
| `FIRST_WINS` | Erste aktive Zone gewinnt |

Konflikte werden per `async_dispatcher_send` als HA-Signal gefeuert und in einer History gespeichert.

### HabitusZonesV2GlobalStateSelect

Ein `SelectEntity`, das den globalen Zustand aller Zones steuert (z.B. alle auf "idle" oder "active" setzen). Aenderungen werden ueber Dispatcher-Signale propagiert.

### Entities

| Entity | Typ | Beschreibung |
|--------|-----|-------------|
| `HabitusZonesV2CountSensor` | Sensor | Anzahl konfigurierter Zones |
| `HabitusZonesV2StatesSensor` | Sensor | JSON der aktuellen Zone-States |
| `HabitusZonesV2HealthSensor` | Sensor | Gesundheitsstatus aller Zones |
| `HabitusZonesV2JsonText` | Text | Bulk-Editor (YAML/JSON) |
| `HabitusZonesV2ValidateButton` | Button | Zones validieren |
| `HabitusZonesV2SyncGraphButton` | Button | Zones mit Brain Graph synchronisieren |
| `HabitusZonesV2ReloadButton` | Button | Zones neu laden |
| `HabitusZonesV2GlobalStateSelect` | Select | Globalen Zone-State setzen |

---

## 8. Data Flow

Der Datenfluss durch das System laesst sich in zwei Richtungen beschreiben:

### Hinweg: HA -> Core -> Analyse

```
HA Entity States
    |
    v
Events Forwarder (N3)
    | Batched, PII-redacted, Idempotency-gesichert
    v
POST /api/v1/events -> Core Add-on (Port 8909)
    |
    v
Brain Graph Engine
    | Pattern-Erkennung, Korrelationsanalyse
    v
Habitus Patterns
    | Muster werden zu Kandidaten
    v
Candidate Store (Core-seitig)
```

### Rueckweg: Core -> HA -> Nutzer

```
Candidate Store (Core)
    |
    v
GET /api/v1/candidates <- Candidate Poller (Integration)
    |
    v
storage.py (CandidateState: NEW -> OFFERED)
    |
    v
HA Repairs UI (issue_registry)
    | Nutzer sieht Vorschlaege als "Reparaturen"
    v
Nutzer-Entscheidung
    | "Akzeptiert" / "Spaeter" / "Abgelehnt"
    v
repairs.py -> CandidateRepairFlow / SeedRepairFlow / RepairsBlueprintApplyFlow
    |
    v
PUT /api/v1/candidates/:id -> Feedback an Core
    | Schliesst den Regelkreis
    v
Brain Graph lernt aus Entscheidung
```

### Echtzeit-Kanal (Webhook)

```
Core erkennt Aenderung (Mood, Suggestion, Neuron)
    |
    v
POST /api/webhook/<webhook_id> -> HA Webhook Handler
    |
    v
coordinator.data wird gemerged
    |
    v
Alle CoordinatorEntities aktualisieren sich
    |
    v
HA Frontend zeigt aktualisierte Werte
```

### Governance-First Prinzip

Kein Vorschlag wird automatisch umgesetzt. Jeder Vorschlag durchlaeuft:

1. **Erkennung** (Core: Brain Graph / Habitus Miner)
2. **Transport** (Candidate Poller holt Vorschlaege)
3. **Praesentation** (HA Repairs UI zeigt Vorschlag)
4. **Entscheidung** (Nutzer: Akzeptieren / Verschieben / Ablehnen)
5. **Feedback** (Entscheidung wird an Core zurueckgemeldet)

Bei Blueprint-Kandidaten gibt es zusaetzlich einen **Vorschau-** und **Bestaetigung-Schritt**. Hochrisiko-Aktionen (`risk: "high"`) erfordern die manuelle Eingabe von "CONFIRM".

---

## 9. Persistence

### Was ueberlebt einen Neustart?

| Daten | Speicherort | Mechanismus |
|-------|-------------|-------------|
| Habitus Zones (Definition) | `.storage/ai_home_copilot.habitus_zones_v2` | HA `Store` API (JSON) |
| Habitus Zone States | `.storage/ai_home_copilot.habitus_zones_state` | HA `Store` API (JSON) |
| Config Entry Options | HA ConfigEntry | HA internes ConfigEntry-System |
| Candidates (Status) | `.storage/ai_home_copilot.candidates` | HA `Store` API (JSON) |
| Events Forwarder Queue | `.storage/ai_home_copilot_n3_forwarder` | HA `Store` API (JSON) |
| Entity Tags | `.storage/ai_home_copilot.entity_tags` | HA `Store` API (JSON) |
| Config Snapshots | `.storage/ai_home_copilot.config_snapshots` | HA `Store` API (JSON) |
| Ops Runbook | `.storage/ai_home_copilot.ops_runbook` | HA `Store` API (JSON) |
| Overview Store | `.storage/` | HA `Store` API (JSON) |
| Dashboard-Generierungen | `www/ai_home_copilot/` | Dateisystem (YAML) |

### Was geht bei Neustart verloren?

- In-Memory Caches (Debounce, Idempotency -- werden aber aus Store restauriert)
- Laufende Background Tasks (werden bei `async_setup_entry` neu gestartet)
- Conflict Resolver History (nur In-Memory)
- Coordinator Data (wird beim ersten Poll neu geladen)

### Zone State Persistence

Zone-Zustaende werden ueber Neustarts hinweg beibehalten:

```python
# Beim Stoppen: Alle Zone-States speichern
await async_persist_all_zone_states(hass, entry_id, zones)

# Beim Starten: Zone-States wiederherstellen
zones = await async_restore_zone_states(hass, entry_id, zones)
```

Jeder Zone-State enthaelt:
- `current_state`: Aktueller Zustand
- `state_since_ms`: Seit wann in diesem Zustand
- `last_transition_ms`: Letzte Zustandsaenderung
- `previous_state`: Vorheriger Zustand

---

## 10. File Structure

```
custom_components/ai_home_copilot/
|
|-- __init__.py                         # Integration Setup, Modul-Registrierung
|-- manifest.json                       # HA Manifest (domain, version, dependencies)
|-- const.py                            # Alle Konstanten, DOMAIN, Config Keys, Defaults
|-- coordinator.py                      # DataUpdateCoordinator + CopilotApiClient
|-- entity.py                           # CopilotBaseEntity Basisklasse
|-- config_flow.py                      # ConfigFlow (User, Zero Config, Quick Start, Manual)
|-- config_options_flow.py              # OptionsFlowHandler (Settings, Zones, Tags, Neurons)
|-- config_helpers.py                   # CSV-Utils, Validierung, Wizard-Konstanten
|-- config_schema_builders.py           # voluptuous Schema-Builder
|-- config_wizard_steps.py              # Wizard-Schritt-Handler
|-- config_zones_flow.py                # Zone CRUD in Config Flow
|-- config_tags_flow.py                 # Entity Tags in Config Flow
|-- config_snapshot.py                  # Config Snapshot Export/Import
|-- config_snapshot_flow.py             # Snapshot Flow Mixin
|-- config_snapshot_store.py            # Snapshot Storage
|-- setup_wizard.py                     # SetupWizard (Auto-Discovery)
|-- webhook.py                          # Webhook Handler (Core -> HA Push)
|-- strings.json                        # UI-Strings (Basis)
|
|-- core/
|   |-- module.py                       # CopilotModule Protocol + ModuleContext
|   |-- registry.py                     # ModuleRegistry (Factory-Pattern)
|   |-- runtime.py                      # CopilotRuntime (Singleton, Lifecycle)
|   |-- performance.py                  # EntityStateCache, DomainFilter, TTLCache
|   |-- performance_guardrails.py       # Performance-Grenzen
|   |-- interface.py                    # Modul-Interface-Definitionen
|   +-- modules/                        # 31 Runtime-Module (je eine Datei)
|       |-- legacy.py                   # Basis-Modul (Coordinator, Platforms)
|       |-- events_forwarder.py         # N3 Events Forwarder Modul-Wrapper
|       |-- habitus_miner.py            # Muster-Erkennung
|       |-- candidate_poller.py         # Vorschlaege vom Core abholen
|       |-- brain_graph_sync.py         # Brain Graph Synchronisation
|       |-- mood_module.py              # Mood-Berechnung
|       |-- mood_context_module.py      # Mood-Integration
|       |-- media_context_module.py     # Media-Player-Tracking
|       |-- energy_context_module.py    # Energiemonitoring
|       |-- weather_context_module.py   # Wetter-Integration
|       |-- unifi_context_module.py     # Netzwerk (UniFi)
|       |-- unifi_module.py             # UniFi-Hardware
|       |-- ml_context_module.py        # ML-Kontext
|       |-- camera_context_module.py    # Kamera-Kontext
|       |-- quick_search.py             # Entity-Schnellsuche
|       |-- voice_context.py            # Sprachsteuerung
|       |-- knowledge_graph_sync.py     # Knowledge Graph
|       |-- performance_scaling.py      # Performance-Skalierung
|       |-- dev_surface.py              # Debug/DevLog
|       |-- ops_runbook.py              # Betriebshandbuch
|       |-- home_alerts_module.py       # Kritische Zustandsueberwachung
|       |-- character_module.py         # CoPilot-Persoenlichkeit
|       |-- waste_reminder_module.py    # Abfallkalender
|       |-- birthday_reminder_module.py # Geburtstage
|       |-- entity_tags_module.py       # Entity-Tags
|       |-- person_tracking_module.py   # Personen-Tracking
|       |-- frigate_bridge.py           # Frigate NVR
|       |-- scene_module.py             # Szenen
|       |-- homekit_bridge.py           # HomeKit
|       +-- calendar_module.py          # Kalender
|
|-- sensors/                            # Sensor-Entity-Dateien
|   |-- mood_sensor.py                  # Mood, MoodConfidence, NeuronActivity
|   |-- neuron_dashboard.py             # NeuronDashboard, MoodHistory, Suggestion
|   |-- neurons_14.py                   # 14 Neuronen-Sensoren (Presence, Activity, ...)
|   |-- voice_context.py                # VoiceContext, VoicePrompt
|   |-- energy_insights.py              # EnergyInsight, EnergyRecommendation
|   |-- habit_learning_v2.py            # HabitLearning, HabitPrediction, Sequence
|   |-- anomaly_alert.py                # AnomalyAlert, AlertHistory
|   |-- predictive_automation.py        # PredictiveAutomation
|   |-- inspector_sensor.py             # Inspector (Diagnose)
|   |-- presence_sensors.py             # Praesenz-Sensoren
|   |-- activity_sensors.py             # Aktivitaets-Sensoren
|   |-- environment_sensors.py          # Umgebungs-Sensoren
|   |-- energy_sensors.py               # Energie-Sensoren
|   |-- media_sensors.py                # Media-Sensoren
|   |-- cognitive_sensors.py            # Kognitive Sensoren
|   |-- calendar_sensors.py             # Kalender-Sensoren
|   +-- time_sensors.py                 # Zeit-Sensoren
|
|-- entities/
|   +-- user_preference_entities.py     # Multi-User Preference Entities
|
|-- ml/                                 # ML Pipeline
|   +-- (Pattern Recognition, Anomaly Detection, Habit Learning)
|
|-- dashboard_cards/                    # Lovelace Card Generatoren
|
|-- translations/                       # DE + EN Uebersetzungen
|   |-- de.json
|   +-- en.json
|
|-- www/                                # Statische Assets (Frontend)
|
|-- services.yaml                       # Service-Definitionen
|-- services_setup.py                   # Service-Registrierung
|
|-- forwarder_n3.py                     # N3EventForwarder Implementierung
|-- habitus_zones_store_v2.py           # Zone Store v2 + Conflict Resolver
|-- habitus_zones_entities_v2.py        # Zone Entities (Sensors, Buttons, Select, Text)
|-- habitus_zone_aggregates.py          # Aggregierte Zone-Sensoren
|-- storage.py                          # Candidate Storage (CandidateState)
|-- repairs.py                          # Repairs UI Flows (Governance)
|-- repairs_blueprints.py               # Blueprint Apply Flow
|-- repairs_enhanced.py                 # Erweiterte Repairs
|
|-- sensor.py                           # Sensor Platform Setup
|-- button.py                           # Button Platform Setup
|-- button_*.py                         # Weitere Button-Dateien (10+)
|-- select.py                           # Select Platform Setup
|-- text.py                             # Text Platform Setup
|-- number.py                           # Number Platform Setup
|-- binary_sensor.py                    # Binary Sensor Platform Setup
|-- camera_entities.py                  # Camera Entities + Dataclasses
|
|-- diagnostics.py                      # HA Diagnostics Support
|-- privacy.py                          # Privacy Utilities
|-- error_tracking.py                   # Error Tracking
+-- zone_detector.py                    # Zone Detector (proaktive Weiterleitung)
```

### Schluessel-Dateien auf einen Blick

| Datei | Zeilen (ca.) | Aufgabe |
|-------|-------------|---------|
| `__init__.py` | 315 | Einstiegspunkt: Module registrieren, Setup/Unload orchestrieren |
| `coordinator.py` | 460 | Zentrale Datenquelle: API-Client, Polling, Camera State |
| `entity.py` | 27 | Basisklasse fuer alle Entities |
| `const.py` | 260+ | Alle Konfigurationsschluessel und Defaults |
| `forwarder_n3.py` | 775 | Vollstaendiger N3 Event Forwarder |
| `habitus_zones_store_v2.py` | 1050 | Zone Store, Conflict Resolver, State Persistence |
| `config_flow.py` | 216 | Config Flow Koordinator |
| `config_options_flow.py` | 316 | Options Flow mit allen Submenues |
| `repairs.py` | 630 | Governance UI (Candidate/Seed/Blueprint Repair Flows) |
| `core/runtime.py` | 66 | Modul-Lifecycle-Management |
| `core/module.py` | 38 | CopilotModule Protocol Definition |
| `sensor.py` | 250+ | Sensor Platform: 94+ Entities registrieren |

---

*Dieses Dokument beschreibt die Architektur der PilotSuite HACS Integration (Repository `pilotsuite-styx-ha`). Das Core Add-on (Repository `pilotsuite-styx-core`) wird separat dokumentiert.*
