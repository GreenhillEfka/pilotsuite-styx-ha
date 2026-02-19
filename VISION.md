# PilotSuite - Unified Vision & Architecture

> **Single Source of Truth** for the entire PilotSuite project.
> Both repos (Core Add-on + HACS Integration) reference this document.
> Last Updated: 2026-02-19 | Core v3.0.0 | Integration v3.0.0

---

## 1. Was ist PilotSuite?

Ein **privacy-first, lokaler KI-Assistent** fuer Home Assistant, der die Muster deines Zuhauses lernt und intelligente Automatisierungen vorschlaegt. Alle Daten bleiben lokal. Kein Cloud-Dependency. Der Mensch entscheidet immer.

**In einem Satz:**
> Erklaerend, begrenzt, dialogisch - bewertet (Neuronen), buendelt Bedeutung (Moods), berechnet Relevanz (Synapsen), erzeugt Vorschlaege, erhaelt Freigaben, laesst Home Assistant ausfuehren.

**Styx** ist die Identitaet des Systems - ein eigenstaendiger Charakter mit Persoenlichkeit, der das Zuhause respektvoll begleitet.

---

## 2. Philosophie: Die 4 Grundprinzipien

| Prinzip | Bedeutung | Konsequenz |
|---------|-----------|------------|
| **Local-first** | Alles laeuft lokal, keine Cloud | Kein externer API-Call, kein Log-Shipping |
| **Privacy-first** | PII-Redaktion, bounded Storage | Max 2KB Metadata/Node, Context-ID auf 12 Zeichen gekuerzt |
| **Governance-first** | Vorschlaege vor Aktionen | Human-in-the-Loop, kein stilles Automatisieren |
| **Safe Defaults** | Begrenzte Speicher, opt-in Persistenz | Max 500 Nodes, 1500 Edges, optional JSONL |
| **Offline Voice** | Lokale Sprachsteuerung | Ollama-Integration, kein Cloud-TTS/STT |

---

## 3. Die Normative Kette (unverletzbar)

```
States -> Neuronen -> Moods -> Synapsen -> Vorschlaege -> Dialog/Freigabe -> HA-Aktion
```

**Regeln:**
- Kein direkter Sprung State -> Mood (Neuronen sind zwingende Zwischenschicht)
- Mood kennt keine Sensoren/Geraete - nur Bedeutung
- Vorschlaege werden NIE ohne explizite Freigabe ausgefuehrt
- Unsicherheit/Konflikt reduziert Handlungsspielraum

### Rollenmodell

| Rolle | Verhalten | Standard |
|-------|-----------|----------|
| **CoPilot/Berater** | Schlaegt vor + begruendet | **Default** |
| **Agent** | Handelt autonom, NUR nach Freigabe | Opt-in pro Scope |
| **Autopilot** | Uebernimmt komplett, NUR wenn aktiviert | Explizit |
| **Nutzer** | Entscheidet final | Immer |

### Risikoklassen

| Klasse | Beispiele | Policy |
|--------|-----------|--------|
| **Sicherheit** | Tueren, Alarm, Heizung | Immer Manual Mode |
| **Privatsphaere** | Kameras, Mikrofone | Lokale Auswertung bevorzugen |
| **Komfort** | Licht, Musik, Klima | Assisted nach Opt-in |
| **Info** | Status, Wetter, Kalender | Sofort (read-only) |

---

## 4. Das Lernende Zuhause (Habitus)

**Habitus** (lat. "Zustand") ist die Pattern-Discovery-Engine. Sie beobachtet Verhaltensmuster und schlaegt passende Automatisierungen vor.

### Kernprinzipien

1. **Beobachten, nicht annehmen** - Lernt aus tatsaechlichem Verhalten, nicht aus Regeln
2. **Vorschlagen, nicht handeln** - Proposes automations, never executes without permission
3. **Kontinuierlich lernen** - Passt sich Lifestyle-Aenderungen an
4. **Privacy respektieren** - Alles lokal, opt-in, loeschbar

### Was Habitus entdeckt

| Mustertyp | Beispiel | Ergebnis |
|-----------|----------|----------|
| **Zeitbasiert** | Licht an um 7:00 Werktags | Morgenroutine-Vorschlag |
| **Trigger-basiert** | Bewegung -> Licht an | Anwesenheits-Automatisierung |
| **Sequenz** | Tuer auf -> Flur-Licht -> Thermostat | Ankunftsroutine |
| **Kontextuell** | Filmabend -> Licht dimmen | Aktivitaetsbasierte Szene |

### Confidence-System

```
Confidence = (Support x Consistency x Recency) / Complexity
```

| Confidence | Bedeutung | Aktion |
|------------|-----------|--------|
| 0.9+ | Sehr starkes Muster | Hohe Empfehlung |
| 0.7-0.9 | Starkes Muster | Guter Vorschlag |
| 0.5-0.7 | Moderates Muster | Test empfohlen |
| <0.5 | Schwaches Muster | Nur informativ |

### Feedback-Loop

```
Vorschlag angezeigt -> User Feedback -> Lernen
   +-- Akzeptiert -> Aehnliche boosten
   +-- Modifiziert -> Parameter anpassen
   +-- Abgelehnt -> Gewicht reduzieren
```

---

## 5. Architektur: Zwei Projekte

### Warum zwei Repos?

1. **HACS-Anforderung**: HA-Integration muss eigenstaendiges HACS-Repo sein
2. **Unabhaengige Skalierung**: Backend und Frontend separat entwickelbar
3. **Flexibilitaet**: Headless-Betrieb moeglich (Core ohne Frontend)
4. **Bekanntes Muster**: ESPHome, Node-RED, etc. nutzen dasselbe Pattern

### Repo-Uebersicht

| Repo | Rolle | Version | Port |
|------|-------|---------|------|
| **Home-Assistant-Copilot** | Core Add-on (Backend) | v3.0.0 | 8909 |
| **ai-home-copilot-ha** | HACS Integration (Frontend) | v3.0.0 | - (verbindet sich zum Core) |

### Systemarchitektur

```
+------------------------------------------------------------------+
|                      Home Assistant                               |
|                                                                   |
|  +------------------------------------------------------------+  |
|  |         HACS Integration (ai_home_copilot) v3.0.0          |  |
|  |                                                             |  |
|  |  25 Core-Module    80+ Sensoren   20+ Dashboard Cards      |  |
|  |  +---------------+ +------------+ +---------------------+  |  |
|  |  | Forwarder     | | Mood       | | Brain Graph Card    |  |  |
|  |  | Habitus       | | Presence   | | Mood Card           |  |  |
|  |  | Candidates    | | Activity   | | Neurons Card        |  |  |
|  |  | Brain Sync    | | Energy     | | Habitus Card        |  |  |
|  |  | Mood Context  | | Neurons14  | | Automation Manager  |  |  |
|  |  | Media         | | Weather    | | Module Control      |  |  |
|  |  | Energy        | | Anomaly    | | Prediction Cards    |  |  |
|  |  | Weather       | | Predictive | |                     |  |  |
|  |  | UniFi         | | Calendar   | | 3 Native Lovelace:  |  |  |
|  |  | ML Context    | | Cognitive  | |   styx-mood-card    |  |  |
|  |  | MUPL          | | Media      | |   styx-brain-card   |  |  |
|  |  | Conversation  | | Habit v2   | |   styx-habitus-card |  |  |
|  |  | Module Ctrl   | | ...        | |                     |  |  |
|  |  +---------------+ +------------+ +---------------------+  |  |
|  |                                                             |  |
|  |  StyxConversationAgent (HA Assist Pipeline Integration)     |  |
|  +---------------------------+----+----------------------------+  |
|                              |    |                               |
|              HTTP REST API --+    +-- WebSocket (real-time)       |
|              (Token-Auth)    v                                    |
|  +------------------------------------------------------------+  |
|  |         Core Add-on (copilot_core) v3.0.0 - Port 8909      |  |
|  |                                                             |  |
|  |  +----------+ +----------+ +----------+ +--------------+   |  |
|  |  | Brain    | | Habitus  | | Mood     | | Candidates   |   |  |
|  |  | Graph    | | Miner    | | Engine   | | Generator    |   |  |
|  |  +----------+ +----------+ +----------+ +--------------+   |  |
|  |  +----------+ +----------+ +----------+ +--------------+   |  |
|  |  | Tag      | | Vector   | | Knowledge| | Collective   |   |  |
|  |  | System   | | Store    | | Graph    | | Intel.       |   |  |
|  |  +----------+ +----------+ +----------+ +--------------+   |  |
|  |  +----------+ +----------+ +----------+ +--------------+   |  |
|  |  | Neurons  | | Search   | | Weather  | | Performance  |   |  |
|  |  | (14+)    | | API      | | API      | | Monitor      |   |  |
|  |  +----------+ +----------+ +----------+ +--------------+   |  |
|  |  +----------+ +----------+ +----------+ +--------------+   |  |
|  |  | Module   | | Automat. | | Explain  | | Predict      |   |  |
|  |  | Control  | | Creator  | | Engine   | | Intelligence |   |  |
|  |  +----------+ +----------+ +----------+ +--------------+   |  |
|  |  +----------+ +----------+                                  |  |
|  |  | A/B Test | | Federated|                                  |  |
|  |  | Engine   | | Learning |                                  |  |
|  |  +----------+ +----------+                                  |  |
|  |                                                             |  |
|  |  40+ API-Blueprints | 30+ Module-Packages | SQLite + JSONL  |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### Datenfluss

```
1. HA Event Bus
      |
      v
2. EventsForwarder (batched, rate-limited, PII-redacted)
      |
      v
3. POST /api/v1/events -> Core
      |
      +-->  Event Store (JSONL, bounded)
      +-->  Brain Graph (Nodes + Edges, exponential decay)
      +-->  Knowledge Graph (SQLite/Neo4j)
      +-->  Habitus Miner (A->B Pattern Mining)
      |        |
      |        v
      +-->  Predictive Intelligence (Zeitreihen, Arrival, Energy)
               |
               v
4. Candidate Generator (confidence scoring)
      |
      v
5. GET /api/v1/candidates <- CandidatePollerModule (5min)
      |
      v
6. HA Repairs System (Vorschlag anzeigen)
      |
      v
7. User: Akzeptieren / Modifizieren / Ablehnen
      |
      v
8. Automation Creator -> POST supervisor/core/api/config/automation/config
      |
      v
9. Echte HA-Automatisierung erstellt + Automation Manager
```

---

## 6. Neuronales System

### Neuronen (Core Add-on)

14+ Neuron-Module bewerten jeweils einen Aspekt des Zuhauses:

| Neuron | Aspekt | Bewertung |
|--------|--------|-----------|
| `presence.py` | Anwesenheit | Wer ist wo? |
| `mood.py` | Stimmung | Comfort/Joy/Frugality |
| `energy.py` | Energie | PV-Forecast, Kosten, Grid |
| `weather.py` | Wetter | Bedingungen + Empfehlungen |
| `unifi.py` | Netzwerk | WAN-Qualitaet, Latenz |
| `camera.py` | Kameras | Status + Presence |
| `context.py` | Kontext | Tageszeit, Saison |
| `state.py` | Zustaende | Entity-State-Tracking |
| `calendar.py` | Kalender | Termine + Zeitfenster |
| `cognitive.py` | Kognitive Last | Aktivitaetskomplexitaet |
| `media.py` | Media | Player-Status, Inhalte |
| `time_pattern.py` | Zeitmuster | Tages-/Wochenzyklen |
| `base.py` | Basis | Abstrakte Neuron-Klasse |
| `manager.py` | Orchestrierung | NeuronManager |

### Sensoren (HACS Integration)

80+ Sensoren machen Neuron-Daten in HA sichtbar (17 Sensor-Module + Inspector):

| Sensor | Funktion |
|--------|----------|
| `mood_sensor` | Mood-Entity fuer HA |
| `presence_sensors` | Anwesenheitserkennung |
| `activity_sensors` | Aktivitaetserkennung |
| `energy_sensors` / `energy_insights` | Energieueberwachung |
| `neurons_14` | 14+ Basis-Neuronen (Time, Calendar, Cognitive, etc.) |
| `neuron_dashboard` | Dashboard-Integration |
| `anomaly_alert` | Anomalie-Erkennung |
| `predictive_automation` | Praediktive Vorschlaege |
| `environment_sensors` | Temperatur, Feuchtigkeit |
| `calendar_sensors` | Kalender-Integration |
| `cognitive_sensors` | Kognitive Last |
| `media_sensors` | Media-Player Tracking |
| `habit_learning_v2` | Habit-Learning |
| `time_sensors` | Zeitbasierte Trigger |
| `voice_context` | Sprachsteuerung |

---

## 7. Zone & Tag System

### Zone-Hierarchie

```
Floor (EG, OG, UG)
  +-- Area (Wohnbereich, Schlafbereich)
        +-- Room (Wohnzimmer, Kueche, Bad)
```

### Tag-Konvention

| Kategorie | Beispiele |
|-----------|-----------|
| `kind` | `aicp.kind.light`, `aicp.kind.sensor` |
| `role` | `aicp.role.safety_critical`, `aicp.role.morning` |
| `state` | `aicp.state.needs_repair`, `aicp.state.low_battery` |
| `place` | `aicp.place.wohnzimmer` (auto-erstellt bei Zone) |

Brain Graph verlinkt: Tag <-> Zone <-> Entity (bidirektional).

---

## 8. Multi-User Preference Learning (MUPL)

| Phase | Funktion | Status |
|-------|----------|--------|
| **User Detection** | Wer ist zu Hause? (person.*, device_tracker.*) | Implementiert |
| **Action Attribution** | Wer hat was gemacht? (context.user_id) | Implementiert |
| **Preference Learning** | Was mag wer? (Exponential Smoothing) | Implementiert |
| **Multi-User Aggregation** | Konsens/Priority/Konflikt bei mehreren Usern | Implementiert |
| **User Profiles** | Individuelle Einstellungen pro Person | Implementiert |
| **Profile Switching** | Automatischer Profilwechsel bei Anwesenheit | Implementiert |

**Privacy:** Opt-in, 90 Tage Retention, lokal in HA Storage, User kann eigene Daten loeschen.

---

## 9. Sicherheit

| Feature | Status |
|---------|--------|
| Token-Auth (X-Auth-Token / Bearer) | Implementiert |
| PII-Redaktion | Implementiert |
| Bounded Storage (alle Stores) | Implementiert |
| Source Allowlisting (Events) | Implementiert |
| Rate Limiting (Event Ingest) | Implementiert |
| Idempotency-Key Deduplication | Implementiert |
| `exec()` -> `ast.parse()` (Security Fix) | Implementiert |
| SHA256 Hashing | Implementiert |
| XSS-Schutz (Output Encoding) | Implementiert |
| Input Validation (Pydantic) | Implementiert |
| CSRF Protection | Implementiert |
| Content Security Policy Headers | Implementiert |
| Differential Privacy (Federated Learning) | Implementiert |

**Safety-First Checklist:**
- Sicherheitsrelevante Aktionen (Tueren, Alarm): IMMER Manual Mode
- Destructive Actions: Erst fragen, dann handeln
- Secrets: Nie in Logs, immer in Config/Env
- Updates: Governance-Event mit Persistent Notification

---

## 10. Module Control System

Das Module Control System erlaubt feingranulare Steuerung jedes PilotSuite-Moduls ueber API und Dashboard.

### Modulzustaende

| Zustand | Bedeutung | Verhalten |
|---------|-----------|-----------|
| **active** | Modul vollstaendig aktiv | Daten sammeln + Vorschlaege erzeugen |
| **learning** | Beobachtungsmodus | Daten sammeln, aber KEINE Vorschlaege erzeugen |
| **off** | Modul deaktiviert | Kein Datensammeln, kein Processing |

### API

```
POST /api/v1/modules/{id}/configure
Body: { "state": "active" | "learning" | "off", "config": { ... } }

GET  /api/v1/modules
GET  /api/v1/modules/{id}
GET  /api/v1/modules/{id}/status
```

### Persistenz

- Modulzustaende in SQLite (`/data/module_states.db`), ueberleben Neustarts
- Dashboard-Toggle synchronisiert mit dem realen Backend-Zustand
- Jede Zustandsaenderung erzeugt ein Governance-Event

### Anwendungsfaelle

- **Neues Modul testen:** Auf `learning` setzen, Datenqualitaet pruefen, dann `active`
- **Modul pausieren:** Auf `off` setzen waehrend Renovierung oder Urlaub
- **Schrittweise Aktivierung:** Module einzeln von `learning` auf `active` hochfahren

---

## 11. Automation Creator

Akzeptierte Vorschlaege werden zu echten Home Assistant Automatisierungen.

### Architektur

```
Vorschlag akzeptiert -> Template Mapping -> POST supervisor/core/api/config/automation/config
      -> Echte HA-Automatisierung erstellt -> Automation Manager (Dashboard)
```

### Template Mapping

| Mustertyp | HA Trigger | HA Action |
|-----------|------------|-----------|
| **Zeitbasiert** | `trigger: time` mit Wochentag-Condition | `service: light.turn_on` etc. |
| **State-Trigger** | `trigger: state` auf Entity | `service: *` basierend auf Pattern |
| **Sequenz** | `trigger: state` + `condition: time` | Mehrere Actions in Reihenfolge |

### API

```
POST /api/v1/automations/create       # Vorschlag -> HA Automation
GET  /api/v1/automations              # Alle erstellten Automations
GET  /api/v1/automations/{id}         # Einzelne Automation
PUT  /api/v1/automations/{id}         # Automation bearbeiten
DELETE /api/v1/automations/{id}       # Automation entfernen
POST /api/v1/automations/{id}/toggle  # Aktivieren/Deaktivieren
```

### Automation Manager

- Dashboard-Seite zeigt alle von PilotSuite erstellten Automatisierungen
- Status-Anzeige: aktiv, pausiert, fehlerhaft
- Performance-Metriken: Wie oft wurde die Automation ausgefuehrt?
- Ein-Klick Deaktivierung und Loeschung

---

## 12. Native Lovelace Cards

Drei native Lovelace-Karten fuer direkte Integration in HA-Dashboards.

| Karte | Custom Element | Funktion |
|-------|---------------|----------|
| **styx-mood-card** | `<styx-mood-card>` | Echtzeit-Stimmungsanzeige mit 3D-Visualisierung (Comfort/Joy/Frugality) |
| **styx-brain-card** | `<styx-brain-card>` | Interaktiver Brain Graph mit Zoom, Filter und Node-Details |
| **styx-habitus-card** | `<styx-habitus-card>` | Pattern-Uebersicht mit Confidence-Bars und Trend-Anzeige |

### Technische Details

- Custom Elements registriert fuer HACS-Distribution
- Echtzeit-Updates ueber WebSocket-Verbindung zum Core
- Responsive Design fuer Desktop und Mobile
- Dark/Light Theme Support (folgt HA Theme)
- Konfiguration ueber YAML oder Visual Editor

```yaml
# Lovelace Dashboard YAML Beispiel
type: custom:styx-mood-card
entity: sensor.styx_mood
show_history: true
animation: true
```

---

## 13. HA Conversation Agent

`StyxConversationAgent` erweitert `AbstractConversationAgent` und ist nativ in der HA Assist Pipeline verfuegbar.

### Architektur

```
User Spracheingabe -> HA Assist Pipeline (STT -> Intent -> Conversation Agent)
      -> StyxConversationAgent.async_process()
      -> POST Core:8909/v1/chat/completions (OpenAI-kompatibel)
      -> Ollama (lfm2.5-thinking / qwen3:4b fuer Tool-Calling)
      -> Response mit optionalem Tool-Aufruf -> HA Action
```

### Features

- **Nativ in HA:** Erscheint als Conversation Agent in der Assist-Konfiguration
- **OpenAI-kompatibel:** Nutzt `/v1/chat/completions` Endpunkt des Core
- **Kontextanreicherung:** User-Kontext (Mood, Neuronen, Haushalt) wird ins System-Prompt injiziert
- **Tool-Calling:** 9+ HA-Tools (Licht, Klima, Szenen, etc.) ueber `qwen3:4b`
- **Conversation Memory:** SQLite-basiertes Langzeitgedaechtnis fuer Kontextkontinuitaet
- **Offline:** 100% lokal, keine externen API-Calls

### Konfiguration

| Option | Default | Beschreibung |
|--------|---------|--------------|
| `ollama_url` | `http://localhost:11434` | Ollama Server URL |
| `ollama_model` | `lfm2.5-thinking:latest` | Modell fuer Konversation |
| `tool_model` | `qwen3:4b` | Modell fuer Tool-Calling (lfm2.5 unterstuetzt kein Tool-Calling) |

---

## 14. Explainability Engine

Jeder Vorschlag kann erklaert werden - warum wurde er erzeugt und wie sicher ist das System?

### API

```
GET /api/v1/explain/suggestions/{id}
GET /api/v1/explain/neurons/{neuron_id}
GET /api/v1/explain/mood/current
GET /api/v1/explain/patterns/{pattern_id}
```

### Brain Graph Causal Chain

```
Trigger-Event (z.B. motion_sensor.flur = on)
      -> Brain Graph Edge Traversal (Kausalitaetskette)
      -> Pattern Match (Habitus Miner: Confidence 0.85)
      -> Natuerlichsprachliche Erklaerung via LLM
```

### Erklaerungsformat

```json
{
  "suggestion_id": "abc123",
  "explanation": "Ich habe bemerkt, dass du werktags gegen 7:00 das Flurlicht einschaltest...",
  "confidence": 0.85,
  "evidence": [
    { "type": "pattern", "occurrences": 23, "period_days": 30 },
    { "type": "brain_edge", "from": "motion_sensor.flur", "to": "light.flur", "weight": 0.92 }
  ],
  "causal_chain": ["motion_sensor.flur", "light.flur", "thermostat.flur"]
}
```

### Confidence-Transparenz

- Confidence-Scores sind in allen Vorschlaegen sichtbar
- Brain Graph Kanten-Gewichte zeigen Staerke der Verbindung
- Habitus-Patterns zeigen Support, Consistency und Recency einzeln
- LLM generiert menschenlesbare Zusammenfassung der Kausalitaetskette

---

## 15. Predictive Intelligence

Vorausschauende Intelligenz auf Basis historischer Daten - ohne Cloud, ohne externe APIs.

### Arrival Prediction

```
Person-Entity Historie (person.max, person.anna)
      -> Zeitreihen-Analyse (Moving Average + Time-of-Day Weights)
      -> Ankunftsvorhersage: "Max kommt voraussichtlich um 17:45 nach Hause"
      -> Pre-Heating / Pre-Lighting Vorschlag
```

### Energy Price Optimization

| Datenquelle | Integration | Funktion |
|-------------|-------------|----------|
| **Tibber** | Tibber HA Integration | Stundenbasierte Strompreise |
| **aWATTar** | aWATTar HA Integration | Day-Ahead Preise |
| **PV-Forecast** | Forecast.Solar | Eigenproduktion vorhersagen |

Optimierungslogik: Strompreis-Forecast + PV-Forecast + Verbrauchsmuster = optimaler Zeitpunkt fuer energieintensive Geraete.

### Zeitreihen-Forecasting

- **Methode:** Moving Average + Time-of-Day + Day-of-Week Gewichtung
- **Lookback:** Konfigurierbar (Standard: 30 Tage)
- **Vorhersagefenster:** 1-24 Stunden
- **Anwendungen:** Temperatur, Energieverbrauch, Anwesenheit, Aktivitaetsmuster

### API

```
GET  /api/v1/predict/arrival/{person_id}
GET  /api/v1/predict/energy/optimal-time
GET  /api/v1/predict/forecast/{entity_id}
POST /api/v1/predict/configure
```

---

## 16. Collective Intelligence

Freiwilliges, datenschutzkonformes Lernen ueber Haushaltsgrenzen hinweg.

### Federated Learning

```
Haushalt A: Lokales Modell trainieren
      -> Gradient berechnen + Differential Privacy (Epsilon aus Config)
      -> Verschluesselter Gradient-Upload (nur Gradienten, keine Rohdaten)
      -> Aggregation Server (Federated Averaging)
      -> Verbessertes globales Modell -> zurueck an alle Teilnehmer
```

**Differential Privacy:**
- Epsilon-Wert konfigurierbar (`config.collective.epsilon`, Default: 1.0)
- Niedrigeres Epsilon = mehr Privacy, weniger Nutzen
- Gaussian Noise wird vor Upload auf Gradienten addiert
- Mathematische Garantie: Einzelne Datenpunkte nicht rekonstruierbar

### Cross-Home Model Gradient Sharing

- Nur Modell-Gradienten werden geteilt, NIEMALS Rohdaten
- Verschluesselung in Transit (TLS 1.3)
- Opt-in pro Kategorie (Energie, Komfort, Anwesenheit)
- Jederzeit widerrufbar, lokale Daten werden nicht beeinflusst

### A/B Testing fuer Automationen

| Feature | Beschreibung |
|---------|-------------|
| **Split-Testing** | Zwei Varianten einer Automation parallel testen |
| **Metriken** | Energieverbrauch, User-Zufriedenheit, Ausfuehrungshaeufigkeit |
| **Auto-Promotion** | Bessere Variante wird nach Testphase automatisch Standard |
| **Testdauer** | Konfigurierbar (Standard: 14 Tage) |
| **Mindest-Samples** | Mindestens 20 Ausfuehrungen pro Variante vor Entscheidung |

### Pattern Library

- Erprobte Muster aus dem Federated Learning als Pattern Library
- Patterns mit hoher Cross-Home Confidence werden priorisiert
- Nutzer koennen Patterns uebernehmen oder ignorieren
- Kein automatisches Anwenden - immer Governance-first

### API

```
GET  /api/v1/collective/status
POST /api/v1/collective/opt-in
POST /api/v1/collective/opt-out
GET  /api/v1/collective/patterns
GET  /api/v1/collective/ab-tests
POST /api/v1/collective/ab-tests/create
GET  /api/v1/collective/ab-tests/{id}/results
```

---

## 17. API-Uebersicht (Core Add-on)

### Basis

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/health` | GET | Health Check |
| `/version` | GET | Version Info |
| `/api/v1/status` | GET | System Status |
| `/api/v1/capabilities` | GET | Feature Discovery |

### Kernmodule

| Modul | Endpoints | Beschreibung |
|-------|-----------|-------------|
| **Events** | `/api/v1/events` | Event Ingest + Query |
| **Brain Graph** | `/api/v1/graph/*` | State, Snapshot, Stats, Prune, Patterns |
| **Habitus** | `/api/v1/habitus/*` | Status, Rules, Mine, Dashboard Cards |
| **Candidates** | `/api/v1/candidates/*` | CRUD + Stats + Cleanup |
| **Mood** | `/api/v1/mood/*` | Mood Query + Update |
| **Tags** | `/api/v1/tag-system/*` | Tags, Assignments |
| **Neurons** | `/api/v1/neurons/*` | Neuron State |
| **Search** | `/api/v1/search/*` | Entity Search + Index |

### Steuerung & Automatisierung

| Modul | Endpoints | Beschreibung |
|-------|-----------|-------------|
| **Module Control** | `/api/v1/modules/*` | Modulzustaende (active/learning/off) |
| **Automation** | `/api/v1/automations/*` | Automation Creator + Manager |
| **Explain** | `/api/v1/explain/*` | Explainability Engine |
| **Predict** | `/api/v1/predict/*` | Predictive Intelligence |

### Erweiterungen

| Modul | Endpoints | Beschreibung |
|-------|-----------|-------------|
| **Knowledge Graph** | `/api/v1/kg/*` | Nodes, Edges, Query |
| **Vector Store** | `/api/v1/vector/*` | Store, Search, Stats |
| **Weather** | `/api/v1/weather/*` | Wetterdaten |
| **Energy** | `/api/v1/energy/*` | Energiemonitoring |
| **UniFi** | `/api/v1/unifi/*` | WAN, Clients, Roaming |
| **SystemHealth** | `/api/v1/system_health/*` | Zigbee/Z-Wave/Recorder |
| **Performance** | `/api/v1/performance/*` | Cache, Pool, Metrics |
| **Dashboard** | `/api/v1/dashboard/*` | Brain Summary |
| **Notifications** | `/api/v1/notifications/*` | Push System |
| **User Preferences** | `/api/v1/user/*` | Preferences, Mood, Profiles |
| **Collective Intel.** | `/api/v1/collective/*` | Federated Learning + A/B Tests |
| **Dev Logs** | `/api/v1/dev/logs` | Debug Pipeline |

### OpenAI-kompatibel

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/v1/chat/completions` | POST | Chat Completions (Ollama Backend) |
| `/v1/models` | GET | Verfuegbare Modelle |

---

## 18. Codebase-Metriken

| Metrik | Core Add-on | HACS Integration |
|--------|-------------|------------------|
| Python-Dateien | 160+ | 250+ |
| Test-Dateien | 80+ | 60+ |
| API-Blueprints | 40+ | - |
| Module-Packages | 30+ | 25 Core-Module |
| Sensoren | - | 80+ (inkl. Inspector) |
| Dashboard Cards | - | 20+ |
| Lovelace Cards | - | 3 (styx-mood, styx-brain, styx-habitus) |
| Neuronen | 14+ | 14+ (via neurons_14.py) |

---

## 19. Completed Milestones

### Pre-Release (v0.x)

| Milestone | Version | Beschreibung |
|-----------|---------|-------------|
| M0: Foundation | v0.4.x | Grundarchitektur, Flask, erste Neuronen |
| M1: Suggestions E2E | v0.5.x | Kompletter Vorschlags-Workflow |
| M2: Mood Ranking | v0.5.7 | Mood-basierte Priorisierung |
| M3: SystemHealth/UniFi/Energy | v0.4.9-v0.4.13 | Hardware-Neuronen |
| N0: Modular Runtime | v0.5.4 | Plugin-faehige Architektur |
| N1: Candidate Lifecycle + UX | v0.5.0-v0.5.2 | Governance-Workflow |
| N2: Core API v1 | v0.4.3-v0.4.5 | REST API Grundgeruest |
| N3: HA -> Core Event Forwarder | v0.5.x | Event-Bridge |
| N4: Brain Graph | v0.6.x | Graph Store + Patterns |
| N5: Core <-> HA Bridge | v0.5.0-v0.5.2 | Bidirektionale Kommunikation |
| Tag System v0.2 | v0.4.14 | Tag-basierte Organisation |
| Habitus Zones v2 | v0.4.15 | Zonenbasiertes Mining |
| Character System v0.1 | v0.12.x | Styx Persoenlichkeit |
| Interactive Brain Graph | v0.8.x | Visuelle Graph-Exploration |
| Multi-User Preference Learning | v0.8.0 | MUPL Framework |
| Cross-Home Sync v0.2 | v0.6.0 | Haushaltuebergreifende Sync |
| Collective Intelligence v0.2 | v0.6.1 | Erste Federated Features |
| Security P0 Fixes | v0.12.x | Kritische Sicherheitsfixes |
| Architecture Merge | v0.8.7 / v0.13.4 | HACS + Core vereinheitlicht |
| Config Flow Modularization | v0.13.5 | config_flow.py -> 6 Module |
| API Pydantic Validation | v0.8.8 | Schema-Validierung |

### Release-Versionen

| Version | Codename | Highlights |
|---------|----------|------------|
| **v1.0.0** | First Full Release | Feature-Parity beider Repos, vollstaendige Test-Coverage, stabile API, Dokumentation komplett, Port 8909 finalisiert |
| **v1.1.0** | Styx Identity + Unified Dashboard | Styx als benannte Identitaet, einheitliches Dashboard-Design, Character System v1.0, SOUL.md als Persoenlichkeitsquelle |
| **v1.2.0** | Qualitaetsoffensive | Echtes Health-Monitoring, XSS-Schutz, Input Validation (Pydantic), Resilience-Patterns (Circuit Breaker, Retry), Error Isolation pro Modul |
| **v1.3.0** | Module Control + Automation Creator | Module Control API (active/learning/off), Automation Creator via Supervisor REST API, Automation Manager Dashboard, SQLite-Persistenz fuer Modulzustaende |
| **v2.0.0** | Native Lovelace + Conversation Agent | styx-mood-card, styx-brain-card, styx-habitus-card als native Lovelace Cards, StyxConversationAgent in HA Assist Pipeline, WebSocket Real-time Updates |
| **v2.1.0** | Explainability + Multi-User Profiles | Explainability Engine mit Brain Graph Causal Chain Traversal, natuerlichsprachliche Erklaerungen via LLM, Confidence-Transparenz, Multi-User Profile Switching |
| **v2.2.0** | Predictive Intelligence | Arrival Prediction aus Person-Entity Historie, Energy Price Optimization (Tibber/aWATTar), Zeitreihen-Forecasting (Moving Average + Time-of-Day), Pre-Heating/Pre-Lighting Vorschlaege |
| **v3.0.0** | Federated Learning + A/B Testing | Federated Learning mit Differential Privacy, Cross-Home Gradient Sharing, A/B Testing fuer Automationen mit Auto-Promotion, Pattern Library aus Collective Learning |

---

## 20. Dokumentationsstruktur

Dieses Dokument (`VISION.md`) ist die **Single Source of Truth**.

### Aktive Dokumente

| Dokument | Repo | Zweck |
|----------|------|-------|
| `VISION.md` | Core (primaer) + HACS (Symlink) | Dieses Dokument |
| `CHANGELOG.md` | Beide (je eigenes) | Release-Historie |
| `SOUL.md` | Core | Styx Persoenlichkeit + Werte |
| `IDENTITY.md` | Core | Styx Identitaetsdefinition |
| `HEARTBEAT.md` | Core | Live Decision Matrix |
| `HANDBUCH.md` | Core | Benutzerhandbuch (deutsch) |
| `docs/API.md` | Core | API-Referenz |
| `docs/USER_MANUAL.md` | HACS | Benutzerhandbuch |
| `docs/DEVELOPER_GUIDE.md` | HACS | Entwicklerhandbuch |
| `docs/SETUP_GUIDE.md` | HACS | Installationsanleitung |
| `docs/MUPL_DESIGN.md` | HACS | MUPL-Spezifikation |

### Archivierte Dokumente

Die folgenden Dokumente sind durch `VISION.md` ersetzt und nur noch historisch relevant:

- `PILOTSUITE_VISION.md` (beide Repos) -> ersetzt durch Kapitel 4-5
- `HABITUS_PHILOSOPHY.md` (beide Repos) -> ersetzt durch Kapitel 4
- `ARCHITECTURE_CONCEPT.md` -> ersetzt durch Kapitel 5
- `BLUEPRINT_CoPilot_Addon_v0.1.md` -> ersetzt durch Kapitel 2-3
- `MODULE_INVENTORY.md` (beide Repos) -> ersetzt durch Kapitel 6
- `INDEX.md` (beide Repos) -> ersetzt durch dieses Dokument
- `IMPLEMENTATION_TODO.md` -> ersetzt durch Kapitel 19
- `PROJECT_PLAN.md` -> ersetzt durch Kapitel 19
- `START_HERE.md` -> ersetzt durch dieses Dokument
- `BOOTSTRAP.md` -> ersetzt durch dieses Dokument

---

## 21. Praxisdialoge (Styx-Persoenlichkeit)

So kommuniziert Styx mit dem User:

1. **Konflikt ohne Aufloesung:** "Mehrere Signale sprechen fuer X und Y. Was moechtest du?"
2. **Vorschlag mit Gegenargumenten:** "Ich wuerde X vorschlagen, weil Y. Dagegen spricht Z."
3. **Bewusstes Ablehnen:** "Soll ich mir merken, dass das oft nicht passt?"
4. **Rueckblick:** "Warum hast du gestern nichts vorgeschlagen?" -> Mood war niedrig
5. **Systemzustand:** "Aktuell ist Entspannung moderat, Fokus niedrig..."
6. **Erklaerung:** "Der Vorschlag basiert auf 23 Beobachtungen in den letzten 30 Tagen..."
7. **Vorhersage:** "Max kommt voraussichtlich um 17:45 - soll ich vorheizen?"

**Persoenlichkeit** (aus SOUL.md):
- Genuinely helpful, nicht performatively helpful
- Hat Meinungen, darf widersprechen
- Resourceful bevor er fragt
- Behandelt Zugang zum Zuhause mit Respekt
- Erklaert seine Entscheidungen transparent

---

*Dieses Dokument wird bei jedem Release aktualisiert. Bei Widerspruechen zwischen diesem Dokument und Code gilt der Code.*
