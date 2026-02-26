# PilotSuite Styx — Strukturplan v9.2.0

## 1. IST-Zustand: Kritische Analyse

### 1.1 Module (HA Integration — `_MODULES` Boot-Kette)

Die Integration bootet **28 Module** sequentiell. Scheitert eines, wird es stillschweigend uebersprungen.

| # | Modul | Systemkritisch | Status | Problem |
|---|-------|----------------|--------|---------|
| 1 | `legacy` | **JA** | OK | Erstellt Coordinator + alle Entities. Ohne dieses Modul = keine Integration |
| 2 | `coordinator_module` | JA | OK | Zentrale Daten-Koordination |
| 3 | `performance_scaling` | JA | OK | Lastbegrenzung, verhindert HA-Ueberlastung |
| 4 | `events_forwarder` | **JA** | OK | HA→Core Event-Bridge, ohne diese kein Brain/Habitus |
| 5 | `history_backfill` | JA | OK | Historische Daten fuer Brain Graph beim Start |
| 6 | `dev_surface` | Nein | OK | Nur Debug-Oberflaeche |
| 7 | `habitus_miner` | JA | OK | A→B Regelextraktion |
| 8 | `ops_runbook` | Nein | OK | Betriebshandbuch/Reparatur-Hilfe |
| 9 | `unifi_module` | Nein | OK | UniFi-Integration (optional) |
| 10 | `brain_graph_sync` | JA | OK | Sync Brain Graph mit Core |
| 11 | `candidate_poller` | JA | OK | Polling von Automations-Kandidaten |
| 12 | `automation_adoption` | Nein | NEU v9.1 | HA-Automationen uebernehmen |
| 13 | `zone_sync` | JA | NEU v9.1 | Bidirektionaler Zonen-Sync HA↔Core |
| 14 | `media_zones` | Nein | OK | Media Player / Musikwolke |
| 15 | `mood` | JA | OK | Stimmungs-Engine |
| 16 | `mood_context` | JA | OK | Stimmungs-Kontext fuer Entscheidungen |
| 17 | `energy_context` | Nein | OK | PV/Grid/Verbrauch |
| 18 | `network` | Nein | OK | WLAN/LAN-Qualitaet |
| 19 | `weather_context` | Nein | OK | Wetter + DWD |
| 20 | `knowledge_graph_sync` | JA | OK | Semantisches Netzwerk sync |
| 21 | `ml_context` | Nein | OK | ML-basierte Anomalie/Habit-Erkennung |
| 22 | `camera_context` | Nein | OK | Kamera/Frigate |
| 23 | `quick_search` | Nein | OK | Entity-Schnellsuche |
| 24 | `voice_context` | Nein | OK | HA Assist Sprachkontext |
| 25 | `home_alerts` | Nein | OK | Batterie/Klima/Praesenz-Alarme |
| 26 | `character_module` | Nein | OK | Charakter-Presets |
| 27 | `waste_reminder` | Nein | OK | Muellabfuhr-Erinnerungen |
| 28 | `birthday_reminder` | Nein | OK | Geburtstags-Erinnerungen |
| 29 | `entity_tags` | **JA** | OK | Tag-System (Basis fuer Neuronenzuordnung) |
| 30 | `entity_discovery` | JA | NEU v9.1 | Entity-Erkennung mit Geraete-Details |
| 31 | `person_tracking` | Nein | OK | Personen-Tracking |
| 32 | `frigate_bridge` | Nein | OK | Frigate NVR |
| 33 | `scene_module` | Nein | OK | Szenen-Vorschlaege |
| 34 | `homekit_bridge` | Nein | OK | HomeKit-Export |
| 35 | `calendar_module` | Nein | OK | Kalender-Integration |

### 1.2 Sensor-Entities (aktuell ~120+ Sensoren)

**Problem: Massiver Entity-Bloat.** Jede Instanz erzeugt 120+ Sensor-Entities, viele davon sind:
- Immer `unknown`/`unavailable` (z.B. Fuel Price ohne Tankstellen-API)
- Duplikate (z.B. Habitus Zones v1 + v2 parallel)
- Debug-Only (Inspector-Sensoren)
- Hardware-spezifisch aber immer erstellt (Z-Wave/Zigbee Mesh ohne Mesh)

**Kategorisierung aller Sensoren:**

#### KERN (immer erstellen) — 15 Sensoren
| Sensor | Zweck |
|--------|-------|
| CopilotVersionSensor | Version der Integration |
| CoreApiV1StatusSensor | Core API erreichbar? |
| PipelineHealthSensor | Gesamtsystem-Gesundheit |
| LlmHealthSensor | LLM-Status + Circuit Breaker |
| AgentStatusSensor | Agent-Verfuegbarkeit |
| MoodSensor | Aktuelle Stimmung |
| MoodConfidenceSensor | Stimmungs-Konfidenz |
| NeuronActivitySensor | Neuronen-Aktivitaet |
| HabitusZonesSensor | Zonen-Uebersicht |
| HabitusZonesV2CountSensor | Zonen-Anzahl |
| HabitusZonesV2HealthSensor | Zonen-Gesundheit |
| HabitusMinerRuleCountSensor | Habitus-Regeln |
| HabitusMinerStatusSensor | Habitus-Engine Status |
| BrainArchitectureSensor | Brain Graph Architektur |
| BrainActivitySensor | Brain Graph Aktivitaet |

#### OPTIONAL (nur wenn Modul aktiv) — jeweils 2-5 Sensoren pro Modul
| Modul | Sensoren | Bedingung |
|-------|----------|-----------|
| Media Zones | 8 Sensoren | Wenn media_players konfiguriert |
| Camera | 6 Sensoren | Wenn Kameras entdeckt |
| UniFi | dynamisch | Wenn UniFi vorhanden |
| Weather | dynamisch | Wenn Wetter-Entities vorhanden |
| Energy | 4 Sensoren | Wenn Energie-Entities vorhanden |
| Z-Wave Mesh | 3 Sensoren | Wenn Z-Wave aktiv |
| Zigbee Mesh | 3 Sensoren | Wenn Zigbee aktiv |
| Waste | 2 Sensoren | Wenn konfiguriert |
| Birthday | 2 Sensoren | Wenn konfiguriert |

#### ZU ENTFERNEN / KONSOLIDIEREN
| Sensor | Grund |
|--------|-------|
| HabitusZonesV2StatesSensor | Redundant mit V2HealthSensor |
| DebugModeSensor | Nur fuer Dev |
| InspectorSensor (4x) | Debug-Only, Service stattdessen |
| MoodDashboardEntity + MoodHistoryEntity + MoodExplanationEntity | Besser als Attribute in MoodSensor |
| MobileDashboardSensor + MobileQuickActionsSensor + MobileEntityGridSensor | React-Dashboard ersetzt diese |
| FuelPriceSensor, TariffSensor | Ohne externe API immer `unknown` |
| HeatPumpSensor, EVChargingSensor, GasMeterSensor | Hardware-spezifisch, ohne Config immer `unknown` |
| BatteryOptimizerSensor | Ohne Config immer `unknown` |
| PredictiveMaintenanceSensor, AnomalyDetectionSensor | Ohne ML-Training immer `unknown` |
| OnboardingSensor | Einmal-Nutzung nach Setup |
| HubDashboardSensor, HubPluginsSensor, HubMultiHomeSensor | React-Dashboard ersetzt diese |

**Einsparung: ~40 Entities weniger pro Instanz**

### 1.3 Config Flow / Options Flow Probleme

| Problem | Detail |
|---------|--------|
| Quick Guide | **GEFIXT** — Wizard-Step-Handler fehlten, jetzt implementiert |
| Rekonfiguration | Bestehende Werte werden nicht vorbelegt (z.B. Ollama-Host) |
| Unbeschriftete Optionen | `_clear_token`, Entity-Selektoren ohne description |
| Neuronensystem | Manuelle Entity-Zuweisung statt Tag-basiert |
| Ollama/SearXNG | **GEFIXT** — Jetzt als separate Host/Port in Options Flow |

### 1.4 Dashboard (Core) — Tab-Struktur

Aktuell 8 Tabs mit teilweise chaotischer Struktur:

| Tab | Inhalt | Problem |
|-----|--------|---------|
| Styx (Chat) | Chat + Brain Graph + Vorschlaege | OK, aber Brain Graph nicht visualisiert |
| Habitus | Zonen + Regeln | OK |
| Stimmung | Mood + Trend | Chart-Daten fehlen oft |
| Module | 21 Module-Kacheln | Keine Unterscheidung System/Optional |
| System | Health + Diagnostik | OK |
| Haushalt | Muell + Geburtstage + Kalender | OK |
| Settings | LLM + Modelle + Routing + API | Zu viele Karten, unstrukturiert |

---

## 2. SOLL-Architektur: Strukturplan

### 2.1 Modul-Klassifikation: System vs. Optional

```
TIER 0 — KERNEL (immer laden, kein Opt-Out)
├── legacy              Coordinator + Entity-Erstellung
├── coordinator_module  Daten-Hub
├── events_forwarder    HA→Core Event-Bridge
├── performance_scaling Lastschutz
└── entity_tags         Tag-System (Basis fuer alles)

TIER 1 — BRAIN (immer laden wenn Core erreichbar)
├── brain_graph_sync    Brain Graph Synchronisation
├── knowledge_graph_sync Semantisches Netzwerk
├── habitus_miner       A→B Regelextraktion
├── candidate_poller    Automations-Kandidaten
├── mood                Stimmungs-Engine
├── mood_context        Stimmungs-Kontext
├── zone_sync           Zonen-Synchronisation
├── history_backfill    Historische Daten
└── entity_discovery    Entity-Erkennung

TIER 2 — KONTEXT (laden wenn relevante Entities vorhanden)
├── energy_context      Wenn energy/solar entities existieren
├── weather_context     Wenn weather entities existieren
├── media_zones         Wenn media_player entities konfiguriert
├── camera_context      Wenn camera entities existieren
├── network (unifi)     Wenn UniFi-Integration vorhanden
├── ml_context          Wenn genuegend History-Daten (>24h)
├── voice_context       Wenn HA Assist konfiguriert
└── person_tracking     Wenn person entities existieren

TIER 3 — ERWEITERUNGEN (explizit aktivieren)
├── scene_module        Szenen-Intelligenz
├── homekit_bridge      HomeKit-Export
├── frigate_bridge      Frigate NVR
├── calendar_module     Kalender-Integration
├── home_alerts         Warnungen
├── character_module    Charakter-Presets
├── waste_reminder      Muellabfuhr
├── birthday_reminder   Geburtstage
├── automation_adoption HA-Automationen uebernehmen
├── dev_surface         Debug-Oberflaeche
├── ops_runbook         Betriebshandbuch
├── unifi_module        UniFi Advanced
└── quick_search        Entity-Schnellsuche
```

### 2.2 Neuronensystem: Tag-basierte Auto-Zuordnung

**Aktuell:** Manuelle Entity-Listen in der Config (CONF_NEURON_CONTEXT_ENTITIES etc.)
**Neu:** Tag-basiertes System mit automatischer Uebernahme

#### Konzept: Tag → Neuron Mapping

```python
# Tag-Schema fuer Neuronenzuordnung
NEURON_TAG_MAPPING = {
    # Tag-Pattern → Neuronen-Kategorie
    "styx:neuron:kontext": "context",      # Kontext-Neuronen
    "styx:neuron:zustand": "state",        # Zustands-Neuronen
    "styx:neuron:stimmung": "mood",        # Stimmungs-Neuronen

    # Device-Klassen → automatische Zuordnung
    "licht": "context",                    # Licht → Kontext-Neuron
    "helligkeit": "context",               # Helligkeit → Kontext-Neuron
    "temperatur": "state",                 # Temperatur → Zustand
    "luftfeuchtigkeit": "state",           # Feuchtigkeit → Zustand
    "bewegung": "context",                 # Bewegung → Kontext
    "praesenz": "context",                 # Praesenz → Kontext
    "energie": "state",                    # Energie → Zustand
    "media_player": "mood",               # Media → Stimmung
    "musik": "mood",                       # Musik → Stimmung
    "klima": "state",                      # Klima → Zustand
    "wetter": "context",                   # Wetter → Kontext
    "kalender": "mood",                    # Kalender → Stimmung

    # Habitus-Zonen → automatische Zone-Zuordnung
    "zone:wohnbereich": "context",
    "zone:schlafzimmer": "mood",
    "zone:kueche": "context",
    "zone:bad": "state",
    "zone:buero": "context",
}

# Automatische Tag-Erkennung und -Uebernahme
class NeuronTagResolver:
    """Resolved Entities fuer Neuronen basierend auf Tags."""

    def resolve_entities(self, entity_tags: dict, zone_tags: dict) -> dict:
        """
        Input: Alle Entity-Tags + Zone-Tags aus dem Tag-System
        Output: {
            "context_entities": ["sensor.lux_wohnzimmer", "binary_sensor.motion_flur"],
            "state_entities": ["sensor.temperatur_bad", "sensor.energy_grid"],
            "mood_entities": ["media_player.wohnzimmer", "sensor.musik_aktiv"],
        }
        """
        result = {"context": [], "state": [], "mood": []}

        for entity_id, tags in entity_tags.items():
            for tag in tags:
                tag_lower = str(tag).lower()
                # 1. Explizite Neuronen-Tags (hoechste Prio)
                if tag_lower.startswith("styx:neuron:"):
                    category = NEURON_TAG_MAPPING.get(tag_lower)
                    if category:
                        result[category].append(entity_id)

                # 2. Device-Klassen Tags (HA Labels oder PilotSuite Tags)
                for pattern, category in NEURON_TAG_MAPPING.items():
                    if pattern in tag_lower and not tag_lower.startswith("styx:"):
                        if entity_id not in result[category]:
                            result[category].append(entity_id)

            # 3. Habitus-Zonen Zuordnung
            for zone_id, zone_info in zone_tags.items():
                zone_entities = zone_info.get("entities", [])
                zone_name = zone_info.get("name", "").lower()
                if entity_id in zone_entities:
                    # Zone-basierte Neuron-Zuordnung
                    for pattern, category in NEURON_TAG_MAPPING.items():
                        if pattern.startswith("zone:") and pattern.split(":")[1] in zone_name:
                            if entity_id not in result[category]:
                                result[category].append(entity_id)

        return {
            "context_entities": result["context"],
            "state_entities": result["state"],
            "mood_entities": result["mood"],
        }
```

#### Tag-Flow: Automatische Uebernahme

```
1. User erstellt Habituszone "Wohnbereich"
   └→ PilotSuite setzt Tags: "zone:wohnbereich", "styx:zone:wohnbereich"
   └→ Alle Entities in der Zone bekommen: "zone:wohnbereich"

2. User fuegt Lampe zu Zone hinzu
   └→ Entity hat bereits HA-Label "Licht" (oder device_class: light)
   └→ PilotSuite erkennt: "Licht" Tag vorhanden → uebernehmen
   └→ Entity bekommt: "styx:neuron:kontext" (weil Licht = Kontext)
   └→ Entity bekommt: "zone:wohnbereich" (von der Zone)

3. Neuronensystem liest Tags automatisch:
   └→ Alle Entities mit "styx:neuron:kontext" → Kontext-Neuronen
   └→ Alle Entities mit "styx:neuron:zustand" → Zustands-Neuronen
   └→ Alle Entities mit "styx:neuron:stimmung" → Stimmungs-Neuronen

4. Dashboard zeigt:
   └→ Welche Entities welchem Neuronen-Typ zugeordnet sind
   └→ Welche Tags die Zuordnung ausgeloest haben
   └→ Moeglichkeit, Tags manuell zu aendern/hinzufuegen
   └→ Entities ohne Zuordnung aber mit relevantem Tag (z.B. "Licht")
```

### 2.3 Dashboard-Redesign (Core)

#### Neues Tab-Layout (7 Tabs, sauber strukturiert)

```
TAB 1: UEBERSICHT (Home)
├── System-Gesundheit (Score + Ampel)
├── Brain Graph Visualisierung (Canvas/SVG)
│   ├── Knoten = Entities (Farbe nach Domain)
│   ├── Kanten = Beziehungen (Dicke nach Gewicht)
│   └── Hover: Entity-Details + Beziehungen
├── Neuronenlayer-Visualisierung
│   ├── 3 Ringe: Kontext → Zustand → Stimmung
│   ├── Neuronen als Punkte (Farbe nach Aktivitaet)
│   └── Verbindungen zwischen Schichten
├── Aktive Regeln (Top 5 Habitus)
├── Mood-Indikator (Rad mit Comfort/Joy/Frugality)
└── Letzte Aktivitaet (Timeline der letzten 10 Events)

TAB 2: CHAT (Styx)
├── Chat-Interface (wie bisher)
├── Modell-Auswahl (Dropdown)
├── Vorschlaege / Suggestions
└── Web-Suche (SearXNG)

TAB 3: HABITUS
├── Zonen-Uebersicht (Karte/Grid)
├── Regeln (sortiert nach Confidence)
├── Kandidaten (vorgeschlagene Automationen)
└── Mood pro Zone

TAB 4: MODULE
├── SYSTEM-MODULE (Tier 0+1) — immer sichtbar
│   ├── Status-Ampel pro Modul
│   ├── Letzte Aktivitaet
│   └── Health-Score
├── KONTEXT-MODULE (Tier 2) — Toggle an/aus
│   ├── Automatisch erkannte Module
│   └── Fehlende Voraussetzungen anzeigen
├── ERWEITERUNGEN (Tier 3) — Toggle an/aus
│   ├── Verfuegbare Erweiterungen
│   └── Konfiguration pro Erweiterung
└── Neuronensystem
    ├── Kontext-Neuronen (Entities + Tags)
    ├── Zustands-Neuronen (Entities + Tags)
    ├── Stimmungs-Neuronen (Entities + Tags)
    └── Nicht zugeordnet aber relevant (Tag-basiert)

TAB 5: EINSTELLUNGEN
├── Verbindung
│   ├── Core Host/Port
│   ├── Ollama Host/Port (separat)
│   └── SearXNG Host/Port (separat)
├── LLM Routing
│   ├── Primary/Secondary Provider
│   ├── Offline-Modell Auswahl
│   └── Cloud-Modell Auswahl
├── Modell-Verwaltung
│   ├── Installierte Modelle (mit Delete)
│   ├── Empfohlene Modelle (mit Download)
│   └── Manueller Modell-Download (Input)
├── API Endpoints (Referenz)
└── Backup/Restore

TAB 6: HAUSHALT
├── Muellabfuhr-Kalender
├── Geburtstage
├── Praesenz-Uebersicht
└── Kalender-Events

TAB 7: SYSTEM
├── Health Dashboard (CPU/RAM/Disk)
├── Circuit Breaker Status
├── Request Metrics
├── Dev Logs (letzte 50)
└── HA Entity Discovery (Status + Export)
```

### 2.4 Brain Graph + Neuronenlayer Visualisierung

#### Brain Graph (Canvas-basiert)
```javascript
// Neuer Brain Graph Renderer fuer Dashboard
class BrainGraphRenderer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.nodes = [];
        this.edges = [];
        this.hoveredNode = null;
    }

    async loadData() {
        const data = await api('/api/v1/dashboard/brain-summary');
        if (!data?.ok) return;
        this.nodes = data.top_nodes || [];
        this.edges = data.top_edges || [];
        this.layout();
        this.render();
    }

    layout() {
        // Force-directed Layout
        const cx = this.canvas.width / 2;
        const cy = this.canvas.height / 2;
        const radius = Math.min(cx, cy) * 0.7;
        this.nodes.forEach((n, i) => {
            const angle = (i / this.nodes.length) * Math.PI * 2;
            n.x = cx + Math.cos(angle) * radius * (0.5 + n.score * 0.5);
            n.y = cy + Math.sin(angle) * radius * (0.5 + n.score * 0.5);
            n.r = 4 + n.score * 12;  // Node size by score
            n.color = DOMAIN_COLORS[n.kind] || '#6b7a8d';
        });
    }

    render() {
        // Edges
        this.edges.forEach(e => {
            const from = this.nodes.find(n => n.id === e.from);
            const to = this.nodes.find(n => n.id === e.to);
            if (!from || !to) return;
            this.ctx.beginPath();
            this.ctx.strokeStyle = `rgba(124,106,239,${0.1 + e.weight * 0.4})`;
            this.ctx.lineWidth = 0.5 + e.weight * 3;
            this.ctx.moveTo(from.x, from.y);
            this.ctx.lineTo(to.x, to.y);
            this.ctx.stroke();
        });
        // Nodes
        this.nodes.forEach(n => {
            this.ctx.beginPath();
            this.ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
            this.ctx.fillStyle = n.color;
            this.ctx.fill();
            // Label
            this.ctx.fillStyle = '#ccc';
            this.ctx.font = '9px Inter';
            this.ctx.textAlign = 'center';
            this.ctx.fillText(n.label || n.id, n.x, n.y + n.r + 10);
        });
    }
}
```

#### Neuronenlayer (3-Ring-Visualisierung)
```javascript
class NeuronLayerRenderer {
    constructor(canvasId) { /* ... */ }

    render(neuronData) {
        // 3 konzentrische Ringe:
        // Ring 1 (aussen): Kontext-Neuronen (blau)
        // Ring 2 (mitte):  Zustands-Neuronen (gruen)
        // Ring 3 (innen):  Stimmungs-Neuronen (orange)
        //
        // Jeder Punkt = ein Neuron
        // Groesse = Aktivitaet
        // Linien zwischen Ringen = Abhaengigkeiten
    }
}
```

### 2.5 Options Flow: Rekonfiguration mit vorhandenen Werten

```python
# Problem: Bei Rekonfiguration sind bestehende Werte nicht vorbelegt
# Loesung: _effective_config() liefert merge aus entry.data + entry.options

# Zusaetzlich: Neuronensystem automatisch aus Tags befuellen
async def async_step_neurons(self, user_input=None):
    if user_input is not None:
        # Speichere manuelle Overrides
        return self._create_merged_entry(user_input)

    data = self._effective_config()

    # Auto-resolve aus Tag-System
    tags_mod = get_entity_tags_module(self.hass, self._entry.entry_id)
    if tags_mod:
        resolved = NeuronTagResolver().resolve_entities(
            entity_tags=tags_mod.get_all_tags(),
            zone_tags=tags_mod.get_zone_tags(),
        )
        # Vorbelegen mit auto-resolved + manuelle Overrides
        data.setdefault(CONF_NEURON_CONTEXT_ENTITIES,
                       resolved["context_entities"])
        data.setdefault(CONF_NEURON_STATE_ENTITIES,
                       resolved["state_entities"])
        data.setdefault(CONF_NEURON_MOOD_ENTITIES,
                       resolved["mood_entities"])

    schema = vol.Schema(build_neuron_schema(data))
    return self.async_show_form(step_id="neurons", data_schema=schema)
```

---

## 3. Implementierungsplan (Phasen)

### Phase 1: Aufraemen (v9.2.0-alpha) — 2 Tage
- [ ] Entity-Audit: Entferne ~40 Always-Unknown Sensoren
- [ ] Entity-Erstellung bedingt machen (nur wenn Modul aktiv)
- [ ] Options Flow: Bestehende Werte korrekt vorbelegen
- [ ] Options Flow: Alle Felder beschriften (strings.json)
- [ ] Dashboard-Tabs neu ordnen (s. 2.3)

### Phase 2: Tag-basiertes Neuronensystem (v9.2.0-beta) — 3 Tage
- [ ] `NeuronTagResolver` in entity_tags_module.py
- [ ] Automatische Tag-Vergabe bei Zonen-Erstellung
- [ ] Automatische Device-Class → Neuron-Mapping
- [ ] Tag-Uebernahme aus bestehenden HA-Labels
- [ ] Options Flow: Neuronen auto-befuellt aus Tags
- [ ] Dashboard: Neuronen-Zuordnungs-Ansicht

### Phase 3: Visualisierung (v9.2.0-rc) — 2 Tage
- [ ] Brain Graph Canvas-Renderer im Dashboard
- [ ] Neuronenlayer 3-Ring-Visualisierung
- [ ] Mood-Trend-Chart mit echten Daten
- [ ] Modul-Status Timeline (letzte Aktivitaet)

### Phase 4: Modul-Klassifikation (v9.2.0) — 1 Tag
- [ ] Tier 0/1/2/3 Klassifikation in __init__.py
- [ ] Dashboard: Getrennte Darstellung System/Optional
- [ ] Auto-Detection: Tier 2 Module automatisch aktivieren
- [ ] Modul-Status-API: Letzter Run + Health + Entity-Count

---

## 4. Dateien die geaendert werden muessen

### HA Integration (pilotsuite-styx-ha)
| Datei | Aenderung |
|-------|-----------|
| `__init__.py` | Tier-Klassifikation, bedingtes Laden |
| `sensor.py` | Entity-Audit, bedingte Erstellung |
| `config_options_flow.py` | Vorhandene Werte, Tag-auto-resolve |
| `config_schema_builders.py` | Neuron-Schema mit Tag-Hinweis |
| `strings.json` | Alle Felder beschriften |
| `core/modules/entity_tags_module.py` | NeuronTagResolver |
| `core/modules/legacy.py` | Entity-Count reduzieren |

### Core (pilotsuite-styx-core)
| Datei | Aenderung |
|-------|-----------|
| `templates/dashboard.html` | Tab-Redesign, Graph-Renderer, Neuronenlayer |
| `api/v1/conversation.py` | Config-Update Feedback |
| `main.py` | Modul-Status API |
| `core_setup.py` | Modul-Gesundheits-Tracking |

---

## 5. Verbesserungsvorschlaege

### 5.1 Performance
- **Lazy Entity Creation**: Nur Entities erstellen fuer aktive Module
- **Batch-Updates**: Coordinator-Updates buendeln statt einzeln
- **Entity-Caching**: Zonen-Aggregate nur bei Zustandsaenderung neu berechnen

### 5.2 UX
- **Onboarding-Flow**: Nach Setup automatisch relevante Module aktivieren basierend auf vorhandenen Entities
- **Status-Badges**: Jedes Modul zeigt klar "Aktiv/Inaktiv/Fehler"
- **Tag-Editor**: Im Dashboard Tags visuell zuweisen (Drag & Drop)

### 5.3 Architektur
- **Event-Bus Vereinheitlichung**: HA-seitiger EventBus der Module verbindet (statt jedes Modul einzeln)
- **Config-Schema Validation**: Zentrale Schema-Validierung fuer alle Module
- **Module-Dependencies**: Explizite Abhaengigkeiten statt impliziter Reihenfolge

### 5.4 Tags als universelles Verbindungssystem
```
Tags sind der Schluessel zum gesamten System:
- Habituszonen → vergeben Zone-Tags
- Entity Discovery → erkennt Device-Klassen → vergibt Typ-Tags
- Neuronensystem → liest Tags → ordnet Entities zu
- Vorschlagssystem → nutzt Tags fuer Kontext
- Brain Graph → nutzt Tags fuer Beziehungen
- Dashboard → zeigt Tag-basierte Gruppierungen

Jede Entity kann beliebig viele Tags tragen.
Tags werden automatisch (System) oder manuell (User) vergeben.
Das Tag-System ist die gemeinsame Sprache aller Module.
```
