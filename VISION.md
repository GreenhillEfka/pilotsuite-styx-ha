# AI Home CoPilot - Unified Vision & Architecture

> **Single Source of Truth** for the entire AI Home CoPilot project.
> Both repos (Core Add-on + HACS Integration) reference this document.
> Last Updated: 2026-02-16 | Core v0.8.7 | Integration v0.13.4

---

## 1. Was ist AI Home CoPilot?

Ein **privacy-first, lokaler KI-Assistent** für Home Assistant, der die Muster deines Zuhauses lernt und intelligente Automatisierungen vorschlägt. Alle Daten bleiben lokal. Kein Cloud-Dependency. Der Mensch entscheidet immer.

**In einem Satz:**
> Erklärendes, begrenztes, dialogisches Entscheidungssystem - bewertet (Neuronen), bündelt Bedeutung (Moods), berechnet Relevanz (Synapsen), erzeugt Vorschläge, erhält Freigaben, lässt Home Assistant ausführen.

---

## 2. Philosophie: Die 4 Grundprinzipien

| Prinzip | Bedeutung | Konsequenz |
|---------|-----------|------------|
| **Local-first** | Alles läuft lokal, keine Cloud | Kein externer API-Call, kein Log-Shipping |
| **Privacy-first** | PII-Redaktion, bounded Storage | Max 2KB Metadata/Node, Context-ID auf 12 Zeichen gekürzt |
| **Governance-first** | Vorschläge vor Aktionen | Human-in-the-Loop, kein stilles Automatisieren |
| **Safe Defaults** | Begrenzte Speicher, opt-in Persistenz | Max 500 Nodes, 1500 Edges, optional JSONL |

---

## 3. Die Normative Kette (unverletzbar)

```
States → Neuronen → Moods → Synapsen → Vorschläge → Dialog/Freigabe → HA-Aktion
```

**Regeln:**
- Kein direkter Sprung State → Mood (Neuronen sind zwingende Zwischenschicht)
- Mood kennt keine Sensoren/Geräte - nur Bedeutung
- Vorschläge werden NIE ohne explizite Freigabe ausgeführt
- Unsicherheit/Konflikt reduziert Handlungsspielraum

### Rollenmodell

| Rolle | Verhalten | Standard |
|-------|-----------|----------|
| **CoPilot/Berater** | Schlägt vor + begründet | **Default** |
| **Agent** | Handelt autonom, NUR nach Freigabe | Opt-in pro Scope |
| **Autopilot** | Übernimmt komplett, NUR wenn aktiviert | Explizit |
| **Nutzer** | Entscheidet final | Immer |

### Risikoklassen

| Klasse | Beispiele | Policy |
|--------|-----------|--------|
| **Sicherheit** | Türen, Alarm, Heizung | Immer Manual Mode |
| **Privatsphäre** | Kameras, Mikrofone | Lokale Auswertung bevorzugen |
| **Komfort** | Licht, Musik, Klima | Assisted nach Opt-in |
| **Info** | Status, Wetter, Kalender | Sofort (read-only) |

---

## 4. Das Lernende Zuhause (Habitus)

**Habitus** (lat. "Zustand") ist die Pattern-Discovery-Engine. Sie beobachtet Verhaltensmuster und schlägt passende Automatisierungen vor.

### Kernprinzipien

1. **Beobachten, nicht annehmen** - Lernt aus tatsächlichem Verhalten, nicht aus Regeln
2. **Vorschlagen, nicht handeln** - Proposes automations, never executes without permission
3. **Kontinuierlich lernen** - Passt sich Lifestyle-Änderungen an
4. **Privacy respektieren** - Alles lokal, opt-in, löschbar

### Was Habitus entdeckt

| Mustertyp | Beispiel | Ergebnis |
|-----------|----------|----------|
| **Zeitbasiert** | Licht an um 7:00 Werktags | Morgenroutine-Vorschlag |
| **Trigger-basiert** | Bewegung → Licht an | Anwesenheits-Automatisierung |
| **Sequenz** | Tür auf → Flur-Licht → Thermostat | Ankunftsroutine |
| **Kontextuell** | Filmabend → Licht dimmen | Aktivitätsbasierte Szene |

### Confidence-System

```
Confidence = (Support × Consistency × Recency) / Complexity
```

| Confidence | Bedeutung | Aktion |
|------------|-----------|--------|
| 0.9+ | Sehr starkes Muster | Hohe Empfehlung |
| 0.7-0.9 | Starkes Muster | Guter Vorschlag |
| 0.5-0.7 | Moderates Muster | Test empfohlen |
| <0.5 | Schwaches Muster | Nur informativ |

### Feedback-Loop

```
Vorschlag angezeigt → User Feedback → Lernen
   ├── Akzeptiert → Ähnliche boosten
   ├── Modifiziert → Parameter anpassen
   └── Abgelehnt → Gewicht reduzieren
```

---

## 5. Architektur: Zwei Projekte

### Warum zwei Repos?

1. **HACS-Anforderung**: HA-Integration muss eigenständiges HACS-Repo sein
2. **Unabhängige Skalierung**: Backend und Frontend separat entwickelbar
3. **Flexibilität**: Headless-Betrieb möglich (Core ohne Frontend)
4. **Bekanntes Muster**: ESPHome, Node-RED, etc. nutzen dasselbe Pattern

### Repo-Übersicht

| Repo | Rolle | Version | Port |
|------|-------|---------|------|
| **Home-Assistant-Copilot** | Core Add-on (Backend) | v0.8.7 | 8099 |
| **ai-home-copilot-ha** | HACS Integration (Frontend) | v0.13.4 | - (verbindet sich zum Core) |

### Systemarchitektur

```
┌────────────────────────────────────────────────────────────────┐
│                      Home Assistant                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         HACS Integration (ai_home_copilot)               │  │
│  │                                                           │  │
│  │  22 Core-Module    80+ Sensoren   15+ Dashboard Cards    │  │
│  │  ┌─────────────┐  ┌───────────┐  ┌──────────────────┐   │  │
│  │  │ Forwarder   │  │ Mood      │  │ Brain Graph      │   │  │
│  │  │ Habitus     │  │ Presence  │  │ Mood Card        │   │  │
│  │  │ Candidates  │  │ Activity  │  │ Neurons Card     │   │  │
│  │  │ Brain Sync  │  │ Energy    │  │ Habitus Card     │   │  │
│  │  │ Mood Context│  │ Neurons14 │  │                  │   │  │
│  │  │ Media       │  │ ...       │  │                  │   │  │
│  │  │ Energy      │  │           │  │                  │   │  │
│  │  │ Weather     │  │           │  │                  │   │  │
│  │  │ UniFi       │  │           │  │                  │   │  │
│  │  │ ML Context  │  │           │  │                  │   │  │
│  │  │ MUPL        │  │           │  │                  │   │  │
│  │  │ ...         │  │           │  │                  │   │  │
│  │  └─────────────┘  └───────────┘  └──────────────────┘   │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                              │ HTTP REST API (Token-Auth)       │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Core Add-on (copilot_core) - Port 8099           │  │
│  │                                                           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │  │
│  │  │ Brain    │ │ Habitus  │ │ Mood     │ │ Candidates │  │  │
│  │  │ Graph    │ │ Miner    │ │ Engine   │ │ Generator  │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │  │
│  │  │ Tag      │ │ Vector   │ │ Knowledge│ │ Collective │  │  │
│  │  │ System   │ │ Store    │ │ Graph    │ │ Intel.     │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │  │
│  │  │ Neurons  │ │ Search   │ │ Weather  │ │ Performance│  │  │
│  │  │ (12)     │ │ API      │ │ API      │ │ Monitor    │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │  │
│  │                                                           │  │
│  │  37 API-Blueprints | 23 Module-Packages | SQLite + JSONL │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### Datenfluss

```
1. HA Event Bus
      │
      ▼
2. EventsForwarder (batched, rate-limited, PII-redacted)
      │
      ▼
3. POST /api/v1/events → Core
      │
      ├──▶ Event Store (JSONL, bounded)
      ├──▶ Brain Graph (Nodes + Edges, exponential decay)
      ├──▶ Knowledge Graph (SQLite/Neo4j)
      └──▶ Habitus Miner (A→B Pattern Mining)
               │
               ▼
4. Candidate Generator (confidence scoring)
      │
      ▼
5. GET /api/v1/candidates ← CandidatePollerModule (5min)
      │
      ▼
6. HA Repairs System (Vorschlag anzeigen)
      │
      ▼
7. User: Akzeptieren / Modifizieren / Ablehnen
      │
      ▼
8. Blueprint Import → HA-Automatisierung erstellt
```

---

## 6. Neuronales System

### Neuronen (Core Add-on)

12 Neuron-Module bewerten jeweils einen Aspekt des Zuhauses:

| Neuron | Aspekt | Bewertung |
|--------|--------|-----------|
| `presence.py` | Anwesenheit | Wer ist wo? |
| `mood.py` | Stimmung | Comfort/Joy/Frugality |
| `energy.py` | Energie | PV-Forecast, Kosten, Grid |
| `weather.py` | Wetter | Bedingungen + Empfehlungen |
| `unifi.py` | Netzwerk | WAN-Qualität, Latenz |
| `camera.py` | Kameras | Status + Presence |
| `context.py` | Kontext | Tageszeit, Saison |
| `state.py` | Zustände | Entity-State-Tracking |
| `base.py` | Basis | Abstrakte Neuron-Klasse |
| `manager.py` | Orchestrierung | NeuronManager |

### Sensoren (HACS Integration)

80+ Sensoren machen Neuron-Daten in HA sichtbar (17 Sensor-Module + Inspector):

| Sensor | Funktion |
|--------|----------|
| `mood_sensor` | Mood-Entity für HA |
| `presence_sensors` | Anwesenheitserkennung |
| `activity_sensors` | Aktivitätserkennung |
| `energy_sensors` / `energy_insights` | Energieüberwachung |
| `neurons_14` | 14+ Basis-Neuronen (Time, Calendar, Cognitive, etc.) |
| `neuron_dashboard` | Dashboard-Integration |
| `anomaly_alert` | Anomalie-Erkennung |
| `predictive_automation` | Prädiktive Vorschläge |
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
  └── Area (Wohnbereich, Schlafbereich)
        └── Room (Wohnzimmer, Küche, Bad)
```

### Tag-Konvention

```
aicp.<kategorie>.<name>
```

| Kategorie | Beispiele |
|-----------|-----------|
| `kind` | `aicp.kind.light`, `aicp.kind.sensor` |
| `role` | `aicp.role.safety_critical`, `aicp.role.morning` |
| `state` | `aicp.state.needs_repair`, `aicp.state.low_battery` |
| `place` | `aicp.place.wohnzimmer` (auto-erstellt bei Zone) |

### Integration

```
Zone erstellen → Tag aicp.place.{zone} automatisch erstellen
Entity mit Tag → automatisch in Zone eingeordnet
Brain Graph verlinkt: Tag ↔ Zone ↔ Entity (bidirektional)
```

---

## 8. Multi-User Preference Learning (MUPL)

| Phase | Funktion | Status |
|-------|----------|--------|
| **User Detection** | Wer ist zu Hause? (person.*, device_tracker.*) | Implementiert |
| **Action Attribution** | Wer hat was gemacht? (context.user_id) | Implementiert |
| **Preference Learning** | Was mag wer? (Exponential Smoothing) | Implementiert |
| **Multi-User Aggregation** | Konsens/Priority/Konflikt bei mehreren Usern | Implementiert |

**Privacy:** Opt-in, 90 Tage Retention, lokal in HA Storage, User kann eigene Daten löschen.

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
| `exec()` → `ast.parse()` (Security Fix) | Implementiert |
| SHA256 Hashing | Implementiert |

**Safety-First Checklist:**
- Sicherheitsrelevante Aktionen (Türen, Alarm): IMMER Manual Mode
- Destructive Actions: Erst fragen, dann handeln
- Secrets: Nie in Logs, immer in Config/Env
- Updates: Governance-Event mit Persistent Notification

---

## 10. API-Übersicht (Core Add-on)

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
| **User Preferences** | `/api/v1/user/*` | Preferences, Mood |
| **Collective Intel.** | `/api/v1/collective/*` | Federated Learning |
| **Dev Logs** | `/api/v1/dev/logs` | Debug Pipeline |

---

## 11. Codebase-Metriken

| Metrik | Core Add-on | HACS Integration |
|--------|-------------|------------------|
| Python-Dateien | 180 | 234 |
| Test-Dateien | 53 | 48 |
| API-Blueprints | 37 | - |
| Module-Packages | 23 | 22 Core-Module (inkl. CharacterModule) |
| Sensoren | - | 80+ (inkl. Inspector) |
| Dashboard Cards | - | 15+ |
| Neuronen | 12 | 14+ (via neurons_14.py) |

---

## 12. Completed Milestones

| Milestone | Version | Status |
|-----------|---------|--------|
| M0: Foundation | v0.4.x | Done |
| M1: Suggestions E2E | v0.5.x | Done |
| M2: Mood Ranking | v0.5.7 | Done |
| M3: SystemHealth/UniFi/Energy Neurons | v0.4.9-v0.4.13 | Done |
| N0: Modular Runtime | v0.5.4 | Done |
| N1: Candidate Lifecycle + UX | v0.5.0-v0.5.2 | Done |
| N2: Core API v1 | v0.4.3-v0.4.5 | Done |
| N3: HA → Core Event Forwarder | v0.5.x | Done |
| N4: Brain Graph | v0.6.x | Done |
| N5: Core ↔ HA Integration Bridge | v0.5.0-v0.5.2 | Done |
| Tag System v0.2 | v0.4.14 | Done |
| Habitus Zones v2 | v0.4.15 | Done |
| Character System v0.1 | v0.12.x | Done |
| Interactive Brain Graph Panel | v0.8.x | Done |
| Multi-User Preference Learning | v0.8.0 | Done |
| Cross-Home Sync v0.2 | v0.6.0 | Done |
| Collective Intelligence v0.2 | v0.6.1 | Done |
| Security P0 Fixes | v0.12.x | Done |
| Architecture Merge (HACS + Core) | v0.8.7 / v0.13.4 | Done |

---

## 13. Roadmap

### Nächste Schritte (Q1 2026)

| Priorität | Aufgabe | Status |
|-----------|---------|--------|
| P1 | Test Suite Remediation (24 failing tests fixen) | Offen |
| P1 | Legacy v1 Files aufräumen (forwarder.py, media_context.py, etc.) | Teilweise |
| P2 | config_flow.py refactoring (1260 → mehrere Dateien) | Offen |
| P2 | Pydantic-Validation für API Endpoints | Offen |
| P2 | Port-Konfiguration vereinheitlichen (8099 vs 8909) | **Erledigt** |

### Zukunft (Q2+ 2026)

| Feature | Beschreibung |
|---------|-------------|
| ML Training Pipeline | Advanced Pattern Recognition |
| Predictive Suggestions | Bedürfnisse vorhersagen |
| Natural Language | Automatisierungen in Klartext beschreiben |
| v1.0 Release | Feature-Parity, full test coverage |

---

## 14. Dokumentationsstruktur

Dieses Dokument (`VISION.md`) ist die **Single Source of Truth**.

### Aktive Dokumente

| Dokument | Repo | Zweck |
|----------|------|-------|
| `VISION.md` | Core (primär) + HACS (Symlink) | Dieses Dokument |
| `CHANGELOG.md` | Beide (je eigenes) | Release-Historie |
| `docs/API.md` | Core | API-Referenz |
| `docs/USER_MANUAL.md` | HACS | Benutzerhandbuch |
| `docs/DEVELOPER_GUIDE.md` | HACS | Entwicklerhandbuch |
| `docs/SETUP_GUIDE.md` | HACS | Installationsanleitung |
| `docs/MUPL_DESIGN.md` | HACS | MUPL-Spezifikation |
| `HEARTBEAT.md` | Core | Live Decision Matrix |

### Archivierte Dokumente

Die folgenden Dokumente sind durch `VISION.md` ersetzt und nur noch historisch relevant:

- `PILOTSUITE_VISION.md` (beide Repos) → ersetzt durch Kapitel 4-5
- `HABITUS_PHILOSOPHY.md` (beide Repos) → ersetzt durch Kapitel 4
- `ARCHITECTURE_CONCEPT.md` → ersetzt durch Kapitel 5
- `BLUEPRINT_CoPilot_Addon_v0.1.md` → ersetzt durch Kapitel 2-3
- `MODULE_INVENTORY.md` (beide Repos) → ersetzt durch Kapitel 6
- `INDEX.md` (beide Repos) → ersetzt durch dieses Dokument
- `IMPLEMENTATION_TODO.md` → ersetzt durch Kapitel 13
- `PROJECT_PLAN.md` → ersetzt durch Kapitel 12-13
- `START_HERE.md` → ersetzt durch dieses Dokument
- `BOOTSTRAP.md` → ersetzt durch dieses Dokument

---

## 15. Praxisdialoge (CoPilot-Persönlichkeit)

So kommuniziert der CoPilot mit dem User:

1. **Konflikt ohne Auflösung:** "Mehrere Signale sprechen für X und Y. Was möchtest du?"
2. **Vorschlag mit Gegenargumenten:** "Ich würde X vorschlagen, weil Y. Dagegen spricht Z."
3. **Bewusstes Ablehnen:** "Soll ich mir merken, dass das oft nicht passt?"
4. **Rückblick:** "Warum hast du gestern nichts vorgeschlagen?" → Mood war niedrig
5. **Systemzustand:** "Aktuell ist Entspannung moderat, Fokus niedrig..."

**Persönlichkeit** (aus SOUL.md):
- Genuinely helpful, nicht performatively helpful
- Hat Meinungen, darf widersprechen
- Resourceful bevor er fragt
- Behandelt Zugang zum Zuhause mit Respekt

---

*Dieses Dokument wird bei jedem Release aktualisiert. Bei Widersprüchen zwischen diesem Dokument und Code gilt der Code.*
