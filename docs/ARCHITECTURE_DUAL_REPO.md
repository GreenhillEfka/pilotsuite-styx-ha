# PilotSuite Styx — Dual-Repo Architektur (Gesamtkonzept)

> Version: 11.1 | Stand: 2026-02-27

---

## 1. Warum zwei Repos?

PilotSuite besteht aus zwei getrennt versionierten Repositories, die **gemeinsam** ein vollstaendiges KI-SmartHome-System bilden:

```
┌─────────────────────────────────────┐     ┌─────────────────────────────────────┐
│  pilotsuite-styx-ha (HACS)          │     │  pilotsuite-styx-core (Add-on)      │
│  "Die Sinne + Haende"               │     │  "Das Gehirn + Stimme"              │
│                                     │     │                                     │
│  - Liest HA-States (4520+ Entities) │     │  - Ollama LLM (qwen3:0.6b/4b)      │
│  - Erstellt Sensoren/Entities       │     │  - Brain Graph (500 Nodes)          │
│  - Dashboard-Generierung (YAML)     │     │  - Habitus Mining (A→B Patterns)    │
│  - Config Flow (UI)                 │     │  - 14 Evaluations-Neuronen          │
│  - Webhook-Empfaenger               │     │  - Event Processing Pipeline        │
│  - Event-Forwarder (N3 Batching)    │     │  - Mood Engine (3D Scoring)         │
│  - Conversation Agent (Proxy)       │     │  - Vector Store + RAG               │
│  - Self-Healing (Repair Issues)     │     │  - Candidate Store (Governance)     │
│  - Suggestion Panel (UI)            │     │  - 17 Hub Engines                   │
│  - Live Mood (lokaler Fallback)     │     │  - Webhook-Pusher → HA              │
│  - Zone Bootstrap + Auto-Setup      │     │  - Telegram Bot                     │
│  - 36+ Module in 4 Tiers            │     │  - MCP Server + SearXNG             │
│                                     │     │  - OpenAI-kompatibler Endpoint      │
│  Python: HA asyncio Framework       │     │  Flask+Waitress, Port 8909          │
│  Kein eigener Server moeglich       │     │  Docker-Container (HA Add-on)       │
└──────────────┬──────────────────────┘     └──────────────┬──────────────────────┘
               │           REST API + Webhooks             │
               └───────────────────────────────────────────┘
```

**Technischer Grund:** HA Custom Integrations laufen _innerhalb_ des HA-Prozesses — sie koennen Sensoren erstellen, Events lauschen und Webhooks empfangen, aber keinen eigenen HTTP-Server, keine langlebigen Prozesse und kein Ollama hosten. Das Core Add-on laeuft als eigenstaendiger Docker-Container und kann all das.

---

## 2. Verantwortungsteilung

### Was kann NUR die HA-Integration?

| Faehigkeit | Grund |
|------------|-------|
| HA-States lesen/schreiben | Direkter Zugriff auf `hass.states` |
| Entities/Sensoren erstellen | HA Platform Setup |
| Config Flow (Setup-UI) | HA ConfigFlow Framework |
| HA Repair Issues erstellen | `issue_registry` API |
| HA Events lauschen/feuern | `hass.bus` |
| Lovelace Dashboard wiring | HA Frontend API |
| Device Registry / Area Registry | HA Registry APIs |

### Was kann NUR der Core?

| Faehigkeit | Grund |
|------------|-------|
| Ollama LLM hosten | Eigener Prozess (Port 11435 intern) |
| Langlebige Background-Loops | Neuronen-Evaluation alle 60s |
| Brain Graph persistent halten | In-Memory + SQLite mit Decay |
| RAG/Embeddings berechnen | Vector Store + Bag-of-Words |
| Pattern Mining (vollstaendig) | Habitus: Association Rules aus tausenden Events |
| Tool Calling (LLM) | Server-side Tool-Execution-Loop |
| Telegram Bot | Eigener Server-Prozess |
| SearXNG Web-Suche | Externer Service-Aufruf |
| Adaptive Lighting Loop | Circadianer Rhythmus-Loop |
| Zone Automation Controller | Koordiniert Presence+Brightness+Mood+Media |

### Was koennen beide (komplementaer)?

| Faehigkeit | HA-Integration | Core |
|------------|---------------|------|
| Mood berechnen | LiveMoodEngine (lokal, Fallback) | MoodService (voll, 3D mit Smoothing) |
| Zonen verwalten | ZoneStore V2 + Auto-Setup | HabitusZoneEngine + Zone-Mining |
| Suggestions verarbeiten | SuggestionPanel (UI) + SuggestionLoader | CandidateStore + ProactiveEngine |
| Automationen analysieren | AutomationAnalyzer (lokal) | AutomationTemplateEngine |
| Pattern erkennen | Einfache lokale Analyse | Association Rule Mining (komplex) |

---

## 3. Kommunikationsarchitektur

### 3.1 HA → Core (REST API)

Die HA-Integration nutzt `CopilotApiClient` (aiohttp) mit Multi-URL-Failover:

| Endpoint | Methode | Modul | Zweck |
|----------|---------|-------|-------|
| `/api/v1/events` | POST | EventsForwarder | Batched HA Events (N3 Envelope) |
| `/v1/chat/completions` | POST | Conversation | LLM Chat (OpenAI-kompatibel) |
| `/api/v1/neurons/mood` | GET | Coordinator | Mood-Zustand abfragen |
| `/api/v1/neurons` | GET | Coordinator | Alle 14 Neuronen-States |
| `/api/v1/neurons/evaluate` | POST | Coordinator | Neural Pipeline mit HA-Kontext |
| `/api/v1/candidates` | GET | CandidatePoller | Vorschlaege abholen (5min) |
| `/api/v1/candidates/{id}` | PUT | Repairs | Feedback zurueckmelden |
| `/api/v1/graph/state` | GET/POST | BrainGraphSync | Entity-Graph synchronisieren |
| `/api/v1/habitus/rules` | GET | Coordinator | Entdeckte Muster |
| `/api/v1/habitus/zones/sync` | POST | ZoneBootstrap | Zonen-Konfiguration synchronisieren |
| `/api/v1/kg/*` | GET/POST | KnowledgeGraph | Knowledge Graph Sync |
| `/api/v1/vector/*` | POST | VectorClient | Embeddings + RAG |
| `/api/v1/weather/*` | GET | WeatherContext | Wetter-Daten |
| `/api/v1/modules/*` | GET/POST | Coordinator | Modul-Lifecycle-Control |
| `/api/v1/zone-automation/*` | POST | AutomationEngine | Zonen-Regeln evaluieren |
| `/api/v1/user/*` | GET/POST | UserPreference | Nutzer-Praeferenzen |
| `/health` | GET | Coordinator | Health Check (120s Polling) |
| `/version` | GET | Coordinator | Core-Version |
| `/api/v1/capabilities` | GET | Coordinator | Feature-Flags |

**Authentifizierung:** `Authorization: Bearer <token>` + `X-Auth-Token: <token>` (Legacy)

**Failover:** Primary → HA internal_url → HA external_url → homeassistant.local → localhost → 127.0.0.1

### 3.2 Core → HA (Webhook Push)

Der Core pusht Echtzeit-Updates an die HA-Integration:

| Event-Typ | Payload | Aktion in HA |
|-----------|---------|-------------|
| `mood_changed` | `{mood, confidence, dimensions}` | Merge in `coordinator.data["mood"]` |
| `neuron_update` | `{neurons: {...}}` | Merge in `coordinator.data["neurons"]` |
| `suggestion_new` | `{suggestion data}` | Fire Event `ai_home_copilot_suggestion_received` |
| `proactive_suggestion` | `{suggestion data}` | Fire Event `ai_home_copilot_proactive_suggestion` |
| `status` | `{online, version}` | Update `coordinator.data["ok"]` |

### 3.3 Hybrid-Modus

```
Primaer:   Core → Webhook Push → HA (Echtzeit, <100ms)
Fallback:  HA → REST Polling → Core (alle 120 Sekunden)
```

Der Coordinator fusioniert beide Datenstroeme. Bei Webhook-Ausfall uebernimmt Polling automatisch.

---

## 4. Datenfluss (End-to-End)

### 4.1 Event-Pipeline

```
1. HA State Change (z.B. light.wohnzimmer → on)
   │
   ▼
2. EventsForwarder (HA)
   │ Batched (50 Events), PII-redacted, Idempotent
   │
   ▼
3. POST /api/v1/events ──▶ Core Event Store
   │
   ├──▶ Brain Graph Update (Nodes + Edges)
   ├──▶ Habitus Mining (A→B Patterns)
   └──▶ Neuronen-Evaluation (60s Loop)
        │
        ├──▶ Mood Scoring (Comfort/Joy/Frugality)
        └──▶ Candidate Generation (Vorschlaege)
             │
             ├── Webhook Push → HA (mood_changed, suggestion_new)
             └── REST Polling ← HA (GET /api/v1/candidates)
```

### 4.2 Chat-Pipeline

```
User spricht mit Styx (HA Conversation Agent)
   │
   ▼
conversation.py (HA)
   │ 1. System-Prompt bauen (lokal):
   │    - Live Mood, Zonen, Personen, Wetter
   │    - Top-3 Vorschlaege, Automations-Analyse
   │    (max 2000 Zeichen)
   │
   ▼
   │ 2. POST /v1/chat/completions ──▶ Core LLM Provider
   │                                      │
   │                                      ├─ Ollama (lokal, Port 11435)
   │                                      │  qwen3:0.6b (400MB) oder qwen3:4b (2.5GB)
   │                                      │
   │                                      ├─ Cloud Fallback (optional)
   │                                      │
   │                                      └─ Tool Calling (8+ Tools):
   │                                         - execute_ha_tool (HA Services steuern)
   │                                         - execute_create_automation
   │                                         - execute_web_search (SearXNG)
   │                                         - execute_play_zone (Sonos)
   │                                         - execute_waste_status
   │                                         - execute_get_news / get_warnings
   │                                         └─ ...
   ▼
Antwort zurueck an User (mit Kontext + Tool-Ergebnissen)
```

**Ohne Core = kein LLM = kein Chat.** Ollama laeuft im Core-Container.

### 4.3 Suggestion-Pipeline

```
Quellen:                                              Ziel:
┌─────────────────────────┐
│ 1. initial_suggestions  │ (lokal, einmalig)
│    .json                │──┐
└─────────────────────────┘  │
┌─────────────────────────┐  │
│ 2. AutomationAnalyzer   │  │    ┌──────────────┐    ┌──────────────────┐
│    (lokal, HA Event)    │──┼──▶ │ Suggestion   │──▶ │ SuggestionPanel  │
└─────────────────────────┘  │    │ Loader (T1)  │    │ (WebSocket UI)   │
┌─────────────────────────┐  │    └──────────────┘    └────────┬─────────┘
│ 3. Core Webhook         │  │                                 │
│    (proactive_suggestion│──┤                                 ▼
└─────────────────────────┘  │                          Accept / Reject
┌─────────────────────────┐  │                                 │
│ 4. Core Polling         │  │                                 ▼
│    (suggestion_received)│──┘                          MUPL Feedback
└─────────────────────────┘                             (Preference Learning)
```

Quellen 1+2 funktionieren ohne Core. Quellen 3+4 liefern die **intelligenten** Vorschlaege (aus Brain Graph + Neuronen + Pattern Mining).

### 4.4 Governance-Pipeline

```
Core erkennt Muster → Candidate Store (pending)
     │
     ▼
CandidatePoller (HA, 5min) → GET /api/v1/candidates
     │
     ▼
HA Repairs UI / SuggestionPanel (Nutzer sieht Vorschlag)
     │
     ▼
Nutzer: Akzeptieren / Verschieben / Ablehnen
     │
     ▼
PUT /api/v1/candidates/{id} → Feedback an Core
     │
     ▼
Brain Graph lernt aus Entscheidung
```

**Kein Vorschlag wird automatisch umgesetzt.** Jeder Vorschlag braucht explizite Nutzer-Zustimmung.

---

## 5. Modul-Architektur (HA-Integration)

### 4-Tier System

```
TIER 0 — KERNEL (6 Module, kein Opt-Out)
  legacy, coordinator_module, performance_scaling,
  events_forwarder, entity_tags, brain_graph_sync

TIER 1 — BRAIN (12 Module, wenn Core erreichbar)
  knowledge_graph_sync, habitus_miner, candidate_poller,
  mood, mood_context, zone_sync, history_backfill,
  entity_discovery, scene_module, person_tracking,
  automation_adoption, suggestion_loader

TIER 2 — KONTEXT (7 Module, wenn relevante Entities vorhanden)
  energy_context, weather_context, media_zones,
  camera_context, network, ml_context, voice_context

TIER 3 — ERWEITERUNGEN (12 Module, explizit aktivieren)
  homekit_bridge, frigate_bridge, calendar_module,
  home_alerts, character_module, waste_reminder,
  birthday_reminder, automation_analyzer, dev_surface,
  ops_runbook, unifi_module, quick_search
```

Boot-Reihenfolge: T0 → T1 → T2 → T3. Fehler in einzelnen Modulen werden gefangen — andere Module starten trotzdem.

---

## 6. Service-Architektur (Core Add-on)

### 45+ Backend-Services

Alle Services werden in `core_setup.init_services()` initialisiert:

| Service | Funktion |
|---------|----------|
| **BrainGraphStore** | In-Memory Graph mit Decay, Pruning, SQLite |
| **HabitusMiner** | Association Rule Mining, Zone-basiert |
| **MoodService** | 3D-Scoring mit Exponential Smoothing |
| **CandidateStore** | Governance-Workflow (pending→offered→accepted) |
| **NeuronManager** | 14 Evaluations-Neuronen (60s Loop) |
| **EventProcessor** | Event→Graph Pipeline + Habitus-Feeding |
| **LLMProvider** | Ollama (lokal) + Cloud Fallback |
| **VectorStore** | Bag-of-Words Embeddings + Similarity |
| **RAGService** | Dokument-Indexierung + Retrieval |
| **ConversationMemory** | Lifelong Learning (SQLite) |
| **WebhookPusher** | Mood/Suggestions → HA Push |
| **ProactiveContextEngine** | Presence+Mood→Suggestions |
| **ZoneAutomationController** | Multi-Signal Zone Rules |
| **MediaZoneManager** | Sonos Zone-Following |
| **OverrideModesService** | Party/Vacation/Sleep/Eco/Guest |
| **TelegramBot** | Server-side Tool-Execution |
| **WebSearchService** | NINA + DWD + DuckDuckGo |
| **17 Hub Engines** | Anomaly, Energy, Light, Presence, etc. |

### Neural Pipeline

```
HA Events → Event Ingest → Brain Graph → Habitus Miner → Candidates
                              │               │
                          Neurons          Patterns
                              │               │
                          Mood Engine    Vorschlaege → HA Repairs UI
```

---

## 7. Parallel-Entwicklung

### Versionierung

Beide Repos werden **zusammen** versioniert und released:

```
HA v11.1.0  ←→  Core v11.1.0   (Paired Release)
```

Major/Minor-Mismatch wird dem Nutzer als HA Repair Issue angezeigt.

### Release-Prozess

1. Feature in **beiden** Repos implementieren (wenn beidseitig relevant)
2. Tests in beiden Repos ausfuehren
3. Version in beiden `manifest.json` bumpen
4. Git Tag + GitHub Release in beiden Repos
5. HACS erkennt neues Release automatisch

### Kompatibilitaetsregeln

| Regel | Beschreibung |
|-------|-------------|
| **API-Stabilitaet** | Endpoint-Pfade und Payloads nur additiv aendern |
| **Fallback** | HA muss auch bei Core-Ausfall starten koennen |
| **Graceful Degradation** | Fehlende Core-Features → leere Sensoren, kein Crash |
| **Token-Format** | Bearer + X-Auth-Token parallel unterstuetzen |
| **Webhook-Format** | Event-Typen nur additiv erweitern |

---

## 8. Ohne Core — was geht, was nicht?

### Funktioniert ohne Core

- HA-Integration startet und laeuft (Coordinator zeigt `ok: false`)
- Live Mood Engine (lokaler Fallback aus Entity-States)
- Dashboard-Generierung (rein lokal aus Zonen-Config)
- Automation Analyzer (lokale Analyse der HA-Automationen)
- Self-Healing Repair Issues (lokal)
- Zero-Config Auto-Setup (Zonen + Entity Classifier)
- Alle Config Flows und Options Flows
- SuggestionLoader (Quellen 1+2: JSON + Analyzer)

### Braucht Core

- **LLM/Chat** (Ollama laeuft im Core-Container)
- **Brain Graph** (persistenter Graph-Store)
- **Pattern Mining** (Habitus: Association Rules)
- **Neuronen-Evaluation** (14 Neuronen alle 60s)
- **RAG/Embeddings** (Vector Store)
- **Proaktive Vorschlaege** (ProactiveContextEngine)
- **Tool Calling** (LLM steuert HA-Services)
- **Telegram Bot** (Server-Prozess)
- **Zone Automation** (Multi-Signal Controller)
- **Override Modes** (Party/Vacation/Sleep)
- **Intelligente Suggestions** (Quellen 3+4)

---

## 9. Grundprinzipien

| Prinzip | Bedeutung |
|---------|-----------|
| **Local-first** | Alles lokal, keine Cloud-Abhaengigkeit |
| **Privacy-first** | PII-Redaktion, bounded Storage, opt-in |
| **Governance-first** | Vorschlaege vor Aktionen, Human-in-the-Loop |
| **Safe Defaults** | Sicherheitsrelevante Aktionen immer Manual Mode |
| **Hand-in-Hand** | Beide Repos parallel entwickeln und releasen |
| **Graceful Degradation** | HA funktioniert auch bei Core-Ausfall (eingeschraenkt) |

---

*Dieses Dokument beschreibt die Gesamtarchitektur der PilotSuite Styx Plattform ueber beide Repositories.*
