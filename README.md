# PilotSuite -- Core Add-on

[![Release](https://img.shields.io/github/v/release/GreenhillEfka/Home-Assistant-Copilot)](https://github.com/GreenhillEfka/Home-Assistant-Copilot/releases)

**PilotSuite Core** (ehemals AI Home CoPilot) -- ein **privacy-first, lokaler KI-Assistent** fuer Home Assistant. Lernt die Muster deines Zuhauses, schlaegt intelligente Automatisierungen vor -- und handelt nur mit deiner Zustimmung. Alle Daten bleiben lokal.

> Erklaerend, begrenzt, dialogisch: bewertet (Neuronen), buendelt Bedeutung (Moods), berechnet Relevanz (Synapsen), erzeugt Vorschlaege, erhaelt Freigaben, laesst Home Assistant ausfuehren.

## Architektur

Dieses Repo ist das **PilotSuite Backend (Core Add-on)** -- es laeuft als Home Assistant Add-on auf Port **8909**.

Die dazugehoerige **HACS-Integration** (Frontend, Sensoren, Dashboard Cards) ist ein separates Repo:
[PilotSuite HACS Integration](https://github.com/GreenhillEfka/ai-home-copilot-ha)

```
Home Assistant
+-- HACS Integration (ai_home_copilot)      <-- Frontend, 80+ Sensoren, 15+ Cards
|     HTTP REST API (Token-Auth)
|     v
+-- Core Add-on (copilot_core) Port 8909    <-- Backend, Brain, Habitus, Mood Engine
```

## Installation

### 1. Core Add-on installieren

1. Home Assistant → **Settings** → **Add-ons** → **Add-on Store**
2. Menü (⋮) → **Repositories** → diese URL hinzufügen:
   ```
   https://github.com/GreenhillEfka/Home-Assistant-Copilot
   ```
3. **AI Home CoPilot Core** installieren und starten
4. Das Add-on läuft auf Port **8909**

### 2. HACS Integration installieren

Siehe: [ai-home-copilot-ha](https://github.com/GreenhillEfka/ai-home-copilot-ha#installation)

## Features

### Neuronales System (12+ Neuronen)
Bewertet jeden Aspekt deines Zuhauses: Anwesenheit, Stimmung, Energie, Wetter, Netzwerk, Kameras, Kontext, Zustaende u.v.m.

### Habitus — Das Lernende Zuhause
Pattern-Discovery-Engine: beobachtet Verhaltensmuster und schlägt passende Automatisierungen vor. Confidence-Scoring, Feedback-Loop, zeitbasierte/trigger-basierte/sequenzielle/kontextuelle Muster.

### Brain Graph
State-Tracking mit Nodes + Edges, exponential Decay, Snapshots, Pattern-Erkennung.

### Mood Engine
Mood-Bewertung (Comfort, Joy, Frugality), Ranking und Kontext-Integration.

### Multi-User Preference Learning (MUPL)
Erkennt wer zu Hause ist, attributiert Aktionen, lernt individuelle Präferenzen, löst Multi-User-Konflikte.

### Sicherheit
Token-Auth, PII-Redaktion, Bounded Storage, Rate Limiting, Idempotency-Key Deduplication, Source Allowlisting.

## API-Übersicht (Port 8909)

| Modul | Endpoints | Beschreibung |
|-------|-----------|-------------|
| **Basis** | `/health`, `/version`, `/api/v1/status`, `/api/v1/capabilities` | System Info |
| **Events** | `/api/v1/events` | Event Ingest + Query |
| **Brain Graph** | `/api/v1/graph/*` | State, Snapshot, Stats, Prune, Patterns |
| **Habitus** | `/api/v1/habitus/*` | Status, Rules, Mine, Dashboard Cards |
| **Candidates** | `/api/v1/candidates/*` | CRUD + Stats + Cleanup |
| **Mood** | `/api/v1/mood/*` | Mood Query + Update |
| **Tags** | `/api/v1/tag-system/*` | Tags, Assignments |
| **Neurons** | `/api/v1/neurons/*` | Neuron State |
| **Search** | `/api/v1/search/*` | Entity Search + Index |
| **Knowledge Graph** | `/api/v1/kg/*` | Nodes, Edges, Query |
| **Vector Store** | `/api/v1/vector/*` | Store, Search, Stats |
| **Weather** | `/api/v1/weather/*` | Wetterdaten |
| **Energy** | `/api/v1/energy/*` | Energiemonitoring |
| **Notifications** | `/api/v1/notifications/*` | Push System |
| **Performance** | `/api/v1/performance/*` | Cache, Pool, Metrics |

37 API-Blueprints | 23 Module-Packages | 180 Python-Dateien | 521+ Tests

## Die 4 Grundprinzipien

| Prinzip | Bedeutung |
|---------|-----------|
| **Local-first** | Alles läuft lokal, keine Cloud, kein externer API-Call |
| **Privacy-first** | PII-Redaktion, bounded Storage, max 2KB Metadata/Node |
| **Governance-first** | Vorschläge vor Aktionen, Human-in-the-Loop |
| **Safe Defaults** | Max 500 Nodes, 1500 Edges, opt-in Persistenz |

## Updates

- **Stable:** GitHub Releases/Tags (empfohlen)
- **Dev:** opt-in Branch-Builds

Keine stillen Updates. Updates werden als Governance-Events protokolliert.

## Dokumentation

- **[VISION.md](VISION.md)** -- Single Source of Truth (Architektur, Roadmap, alle Details)
- **[CHANGELOG.md](CHANGELOG.md)** -- Release-Historie
- **[HANDBUCH.md](HANDBUCH.md)** -- Installations- und Benutzerhandbuch (deutsch)
- **[PROJEKTSTRUKTUR.md](PROJEKTSTRUKTUR.md)** -- Moduluebersicht und Verzeichnisstruktur
- **[CLAUDE.md](CLAUDE.md)** -- Projektkontext fuer KI-Assistenten

## Lizenz

Dieses Projekt ist privat. Alle Rechte vorbehalten.
