# PilotSuite - Unified Vision & Architecture

> **Single Source of Truth** for the entire PilotSuite project.
> Both repos (Core Add-on + HACS Integration) reference this document.
> Last Updated: 2026-02-19 | Core v3.1.0 | Integration v3.0.0

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
| **Governance-first** | 3-Tier Autonomie (active/learning/off) | Auto-Apply nur wenn BEIDE Module aktiv (doppelte Sicherheit) |
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
- Autonomie nur bei doppelter Sicherheit (beide Module aktiv)
- Unsicherheit/Konflikt reduziert Handlungsspielraum

### 3-Tier Autonomie-Modell (v3.1.0)

| Modus | Datensammlung | Vorschlaege | Ausfuehrung | Use Case |
|-------|--------------|-------------|-------------|----------|
| **active** | Ja | Ja | AUTO (wenn Ziel auch active) | Vertrauenswuerdige Module |
| **learning** | Ja | Ja (zur Genehmigung) | NUR nach User-Bestaetigung | Neue/unbekannte Module |
| **off** | Nein | Nein | Nein | Deaktiviert |

**Doppelte Sicherheit:** `should_auto_apply(source, target)` prueft ob BEIDE Module aktiv sind.
Wenn nur eines aktiv und das andere learning: Vorschlag wird erzeugt, aber zur manuellen
Uebernahme vorgelegt.

### Rollenmodell

| Rolle | Verhalten | Standard |
|-------|-----------|----------|
| **CoPilot/Berater** | Schlaegt vor + begruendet | **Default** (learning mode) |
| **Agent** | Handelt autonom wenn beide Module aktiv | active + active |
| **Autopilot** | Uebernimmt komplett (kuenftig) | Explizit, alle Module aktiv |
| **Nutzer** | Entscheidet final | Immer (learning mode) |

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

1. **Beobachten, nicht annehmen** - Lernt aus tatsaechlichem Verhalten
2. **Vorschlagen, nicht handeln** - Proposes automations, never executes without permission
3. **Kontinuierlich lernen** - Passt sich Lifestyle-Aenderungen an
4. **Privacy respektieren** - Alles lokal, opt-in, loeschbar

### Muster und Confidence

| Mustertyp | Beispiel | Ergebnis |
|-----------|----------|----------|
| **Zeitbasiert** | Licht an um 7:00 Werktags | Morgenroutine-Vorschlag |
| **Trigger-basiert** | Bewegung -> Licht an | Anwesenheits-Automatisierung |
| **Sequenz** | Tuer auf -> Flur-Licht -> Thermostat | Ankunftsroutine |
| **Kontextuell** | Filmabend -> Licht dimmen | Aktivitaetsbasierte Szene |

`Confidence = (Support x Consistency x Recency) / Complexity` -- Werte >0.7 erzeugen aktive Vorschlaege, <0.5 nur informativ.

### Feedback-Loop

Akzeptiert -> aehnliche boosten | Modifiziert -> Parameter anpassen | Abgelehnt -> Gewicht reduzieren

---

## 5. Architektur: Zwei Projekte

### Repo-Uebersicht

| Repo | Rolle | Version | Port |
|------|-------|---------|------|
| **Home-Assistant-Copilot** | Core Add-on (Backend) | v3.0.0 | 8909 |
| **ai-home-copilot-ha** | HACS Integration (Frontend) | v3.0.0 | - (verbindet sich zum Core) |

Warum zwei Repos: HACS-Anforderung (eigenstaendiges Repo), unabhaengige Skalierung, Headless-Betrieb moeglich, bekanntes Muster (ESPHome, Node-RED).

### Systemarchitektur

```
+---------------------------------------------------------------+
| Home Assistant                                                 |
|  +----------------------------------------------------------+ |
|  | HACS Integration v3.0.0                                   | |
|  | 25 Core-Module | 80+ Sensoren | 20+ Dashboard Cards      | |
|  | 3 Native Lovelace: styx-mood-card, styx-brain-card,       | |
|  |                    styx-habitus-card                       | |
|  | StyxConversationAgent (HA Assist Pipeline)                 | |
|  +-------------------+--+------------------------------------+ |
|           REST API --+  +-- WebSocket (real-time)              |
|                      v                                         |
|  +----------------------------------------------------------+ |
|  | Core Add-on v3.0.0 - Port 8909                            | |
|  | Brain Graph | Habitus Miner | Mood Engine | Candidates    | |
|  | Tag System  | Vector Store  | Knowledge G | Collective    | |
|  | Neurons 14+ | Search API    | Weather API | Performance   | |
|  | Module Ctrl | Automat.Creator| Explain Eng| Predict Intel | |
|  | A/B Testing | Federated Learn|            |               | |
|  | 40+ API-Blueprints | 30+ Packages | SQLite + JSONL       | |
|  +----------------------------------------------------------+ |
+---------------------------------------------------------------+
```

### Datenfluss

```
HA Event Bus -> EventsForwarder (batched, PII-redacted)
  -> POST /api/v1/events -> Core
     +-> Event Store (JSONL) | Brain Graph | Knowledge Graph
     +-> Habitus Miner -> Predictive Intelligence
         -> Candidate Generator (confidence scoring)
            -> GET /api/v1/candidates <- CandidatePollerModule (5min)
               -> HA Repairs System -> User: Accept/Modify/Reject
                  -> Automation Creator -> POST supervisor/core/api/config/automation/config
                     -> Echte HA-Automatisierung + Automation Manager
```

---

## 6. Neuronales System

### Neuronen (Core Add-on, 14+ Module)

| Neuron | Aspekt | Neuron | Aspekt |
|--------|--------|--------|--------|
| `presence` | Anwesenheit | `camera` | Kameras |
| `mood` | Stimmung (Comfort/Joy/Frugality) | `context` | Tageszeit, Saison |
| `energy` | PV-Forecast, Kosten, Grid | `state` | Entity-State-Tracking |
| `weather` | Bedingungen + Empfehlungen | `calendar` | Termine + Zeitfenster |
| `unifi` | WAN-Qualitaet, Latenz | `cognitive` | Aktivitaetskomplexitaet |
| `media` | Player-Status, Inhalte | `time_pattern` | Tages-/Wochenzyklen |

Plus `base.py` (abstrakte Klasse) und `manager.py` (NeuronManager/Orchestrierung).

### Sensoren (HACS Integration, 80+)

`mood_sensor`, `presence_sensors`, `activity_sensors`, `energy_sensors`/`energy_insights`, `neurons_14` (14+ Basis-Neuronen), `neuron_dashboard`, `anomaly_alert`, `predictive_automation`, `environment_sensors`, `calendar_sensors`, `cognitive_sensors`, `media_sensors`, `habit_learning_v2`, `time_sensors`, `voice_context`.

---

## 7. Zone & Tag System

**Hierarchie:** Floor (EG/OG/UG) -> Area (Wohnbereich/Schlafbereich) -> Room (Wohnzimmer/Kueche/Bad)

**Tags:** `aicp.<kategorie>.<name>` -- Kategorien: `kind` (light, sensor), `role` (safety_critical, morning), `state` (needs_repair, low_battery), `place` (auto-erstellt bei Zone).

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
| PII-Redaktion + SHA256 Hashing | Implementiert |
| Bounded Storage (alle Stores) | Implementiert |
| Source Allowlisting + Rate Limiting | Implementiert |
| Idempotency-Key Deduplication | Implementiert |
| `exec()` -> `ast.parse()` (Security Fix) | Implementiert |
| XSS-Schutz + CSRF Protection + CSP Headers | Implementiert |
| Input Validation (Pydantic) | Implementiert |
| Differential Privacy (Federated Learning) | Implementiert |

**Safety-First:** Sicherheitsrelevante Aktionen immer Manual Mode. Destructive Actions erst fragen. Secrets nie in Logs. Updates mit Governance-Event + Persistent Notification.

---

## 10. Module Control System

Feingranulare Steuerung jedes PilotSuite-Moduls ueber API und Dashboard.

| Zustand | Bedeutung | Verhalten |
|---------|-----------|-----------|
| **active** | Modul vollstaendig aktiv | Daten sammeln + Vorschlaege erzeugen |
| **learning** | Beobachtungsmodus | Daten sammeln, aber KEINE Vorschlaege |
| **off** | Modul deaktiviert | Kein Datensammeln, kein Processing |

### API

```
POST /api/v1/modules/{id}/configure   # Body: { "state": "active"|"learning"|"off" }
GET  /api/v1/modules                  # Alle Module
GET  /api/v1/modules/{id}             # Einzelnes Modul
GET  /api/v1/modules/{id}/status      # Status-Details
```

**Persistenz:** SQLite (`/data/module_states.db`), ueberleben Neustarts. Dashboard-Toggle synchronisiert mit Backend-Zustand. Jede Aenderung erzeugt ein Governance-Event.

---

## 11. Automation Creator

Akzeptierte Vorschlaege werden zu echten Home Assistant Automatisierungen via Supervisor REST API (`POST http://supervisor/core/api/config/automation/config`).

### Template Mapping

| Mustertyp | HA Trigger | HA Action |
|-----------|------------|-----------|
| **Zeitbasiert** | `trigger: time` + Wochentag-Condition | `service: light.turn_on` etc. |
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

**Automation Manager:** Dashboard-Seite mit Status-Anzeige (aktiv/pausiert/fehlerhaft), Performance-Metriken, Ein-Klick Deaktivierung und Loeschung.

---

## 12. Native Lovelace Cards

| Karte | Custom Element | Funktion |
|-------|---------------|----------|
| **styx-mood-card** | `<styx-mood-card>` | Echtzeit-Stimmung mit 3D-Visualisierung (Comfort/Joy/Frugality) |
| **styx-brain-card** | `<styx-brain-card>` | Interaktiver Brain Graph mit Zoom, Filter und Node-Details |
| **styx-habitus-card** | `<styx-habitus-card>` | Pattern-Uebersicht mit Confidence-Bars und Trend-Anzeige |

Custom Elements registriert fuer HACS. Echtzeit-Updates via WebSocket. Responsive (Desktop + Mobile). Dark/Light Theme Support. Konfiguration ueber YAML oder Visual Editor.

```yaml
type: custom:styx-mood-card
entity: sensor.styx_mood
show_history: true
animation: true
```

---

## 13. HA Conversation Agent

`StyxConversationAgent` erweitert `AbstractConversationAgent` und ist nativ in der HA Assist Pipeline verfuegbar.

```
User Spracheingabe -> HA Assist (STT -> Intent -> Conversation Agent)
  -> StyxConversationAgent.async_process()
  -> POST Core:8909/v1/chat/completions -> Ollama -> Response + Tool-Aufruf -> HA Action
```

- **Nativ in HA:** Erscheint als Conversation Agent in der Assist-Konfiguration
- **Kontextanreicherung:** Mood, Neuronen, Haushalt wird ins System-Prompt injiziert
- **Tool-Calling:** 9+ HA-Tools (Licht, Klima, Szenen) ueber `qwen3:4b`
- **Conversation Memory:** SQLite-basiertes Langzeitgedaechtnis
- **Offline:** 100% lokal, keine externen API-Calls

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
GET /api/v1/explain/suggestions/{id}    # Vorschlag erklaeren
GET /api/v1/explain/neurons/{neuron_id} # Neuron-Bewertung erklaeren
GET /api/v1/explain/mood/current        # Aktuelle Stimmung erklaeren
GET /api/v1/explain/patterns/{id}       # Pattern erklaeren
```

### Brain Graph Causal Chain

Trigger-Event -> Brain Graph Edge Traversal (Kausalitaetskette) -> Pattern Match (Habitus Miner) -> Natuerlichsprachliche Erklaerung via LLM.

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

Confidence-Scores in allen Vorschlaegen sichtbar. Brain Graph Gewichte zeigen Verbindungsstaerke. LLM generiert menschenlesbare Zusammenfassung.

---

## 15. Predictive Intelligence

Vorausschauende Intelligenz auf Basis historischer Daten - ohne Cloud, ohne externe APIs.

### Arrival Prediction

Person-Entity Historie -> Zeitreihen-Analyse (Moving Average + Time-of-Day Weights) -> Ankunftsvorhersage -> Pre-Heating/Pre-Lighting Vorschlag.

### Energy Price Optimization

| Datenquelle | Integration | Funktion |
|-------------|-------------|----------|
| **Tibber** | Tibber HA Integration | Stundenbasierte Strompreise |
| **aWATTar** | aWATTar HA Integration | Day-Ahead Preise |
| **PV-Forecast** | Forecast.Solar | Eigenproduktion vorhersagen |

Strompreis-Forecast + PV-Forecast + Verbrauchsmuster = optimaler Zeitpunkt fuer energieintensive Geraete.

### Zeitreihen-Forecasting

Moving Average + Time-of-Day + Day-of-Week Gewichtung. Lookback konfigurierbar (Standard: 30 Tage). Vorhersagefenster 1-24 Stunden. Anwendungen: Temperatur, Energieverbrauch, Anwesenheit, Aktivitaetsmuster.

### API

```
GET  /api/v1/predict/arrival/{person_id}    # Ankunftsvorhersage
GET  /api/v1/predict/energy/optimal-time    # Optimaler Zeitpunkt
GET  /api/v1/predict/forecast/{entity_id}   # Zeitreihen-Forecast
POST /api/v1/predict/configure              # Konfiguration
```

---

## 16. Collective Intelligence

Freiwilliges, datenschutzkonformes Lernen ueber Haushaltsgrenzen hinweg.

### Federated Learning mit Differential Privacy

Lokales Modell trainieren -> Gradient + Differential Privacy (Epsilon aus Config) -> Verschluesselter Upload (nur Gradienten, keine Rohdaten) -> Federated Averaging -> Verbessertes Modell zurueck.

- Epsilon konfigurierbar (`config.collective.epsilon`, Default: 1.0)
- Gaussian Noise auf Gradienten vor Upload
- Verschluesselung in Transit (TLS 1.3)
- Opt-in pro Kategorie (Energie, Komfort, Anwesenheit), jederzeit widerrufbar

### A/B Testing fuer Automationen

| Feature | Beschreibung |
|---------|-------------|
| **Split-Testing** | Zwei Varianten einer Automation parallel testen |
| **Metriken** | Energieverbrauch, User-Zufriedenheit, Ausfuehrungshaeufigkeit |
| **Auto-Promotion** | Bessere Variante wird nach Testphase automatisch Standard |
| **Testdauer** | Konfigurierbar (Standard: 14 Tage, min. 20 Ausfuehrungen/Variante) |

### Pattern Library

Erprobte Muster aus Federated Learning als Library. Patterns mit hoher Cross-Home Confidence priorisiert. Kein automatisches Anwenden - immer Governance-first.

### API

```
GET  /api/v1/collective/status              # Federated Status
POST /api/v1/collective/opt-in              # Teilnahme aktivieren
POST /api/v1/collective/opt-out             # Teilnahme beenden
GET  /api/v1/collective/patterns            # Pattern Library
GET  /api/v1/collective/ab-tests            # Alle A/B Tests
POST /api/v1/collective/ab-tests/create     # Neuen Test erstellen
GET  /api/v1/collective/ab-tests/{id}/results  # Testergebnisse
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
| Foundation | v0.4.x | Grundarchitektur, Flask, erste Neuronen |
| Suggestions E2E | v0.5.x | Kompletter Vorschlags-Workflow |
| Mood Ranking | v0.5.7 | Mood-basierte Priorisierung |
| SystemHealth/UniFi/Energy | v0.4.9-v0.4.13 | Hardware-Neuronen |
| Modular Runtime | v0.5.4 | Plugin-faehige Architektur |
| Candidate Lifecycle | v0.5.0-v0.5.2 | Governance-Workflow |
| Core API v1 | v0.4.3-v0.4.5 | REST API Grundgeruest |
| Event Forwarder | v0.5.x | HA -> Core Event-Bridge |
| Brain Graph | v0.6.x | Graph Store + Patterns |
| Integration Bridge | v0.5.0-v0.5.2 | Bidirektionale Kommunikation |
| Tag System v0.2 | v0.4.14 | Tag-basierte Organisation |
| Habitus Zones v2 | v0.4.15 | Zonenbasiertes Mining |
| Character System | v0.12.x | Styx Persoenlichkeit |
| Interactive Brain Graph | v0.8.x | Visuelle Graph-Exploration |
| MUPL | v0.8.0 | Multi-User Preference Learning |
| Cross-Home + Collective | v0.6.0-v0.6.1 | Federated Features |
| Security P0 + Architecture Merge | v0.8.7-v0.12.x | Sicherheit + Vereinheitlichung |
| Config Flow + Pydantic | v0.8.8-v0.13.5 | Modularisierung + Validation |

### Release-Versionen

| Version | Codename | Highlights |
|---------|----------|------------|
| **v1.0.0** | First Full Release | Feature-Parity, Test-Coverage, stabile API, Port 8909 |
| **v1.1.0** | Styx Identity | Styx als Identitaet, Unified Dashboard, SOUL.md |
| **v1.2.0** | Qualitaetsoffensive | Health-Monitoring, XSS, Pydantic, Circuit Breaker, Error Isolation |
| **v1.3.0** | Module Control | Module Control API, Automation Creator, Automation Manager |
| **v2.0.0** | Native Lovelace | styx-mood/brain/habitus-card, StyxConversationAgent, WebSocket |
| **v2.1.0** | Explainability | Causal Chain Traversal, LLM-Erklaerungen, Multi-User Profiles |
| **v2.2.0** | Predictive Intel | Arrival Prediction, Energy Optimization (Tibber/aWATTar) |
| **v3.0.0** | Federated Learning | Differential Privacy, A/B Testing, Pattern Library |

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

Durch `VISION.md` ersetzt: `PILOTSUITE_VISION.md`, `HABITUS_PHILOSOPHY.md`, `ARCHITECTURE_CONCEPT.md`, `BLUEPRINT_CoPilot_Addon_v0.1.md`, `MODULE_INVENTORY.md`, `INDEX.md`, `IMPLEMENTATION_TODO.md`, `PROJECT_PLAN.md`, `START_HERE.md`, `BOOTSTRAP.md`.

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

**Persoenlichkeit** (aus SOUL.md): Genuinely helpful, hat Meinungen und darf widersprechen, resourceful bevor er fragt, behandelt Zugang zum Zuhause mit Respekt, erklaert seine Entscheidungen transparent.

---

*Dieses Dokument wird bei jedem Release aktualisiert. Bei Widerspruechen zwischen diesem Dokument und Code gilt der Code.*
