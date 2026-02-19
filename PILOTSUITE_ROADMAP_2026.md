# PilotSuite Roadmap 2026 -- Vollstaendiger Projektplan

> Erstellt: 2026-02-17 | Aktualisiert: 2026-02-19
> Aktuell: Core v1.2.0 | Integration v1.2.0
> Ziel: v3.0.0 -- Kollektive Intelligenz

---

## Uebersicht

| Phase | Version | Fokus | Status |
|-------|---------|-------|--------|
| Foundation | v1.0.0 | First Full Release | DONE |
| Identity | v1.1.0 | Styx + Dashboard | DONE |
| Quality | v1.2.0 | Resilienz + Transparenz | DONE |
| Control | v1.3.0 | Module Control + Automationen | IN PROGRESS |
| Native HA | v2.0.0 | Lovelace Cards + Conversation Agent | PLANNED |
| Explainability | v2.1.0 | Erklaerbarkeit + Multi-User | PLANNED |
| Prediction | v2.2.0 | Vorhersage + Energie | PLANNED |
| Collective | v3.0.0 | Federated Learning + A/B Testing | PLANNED |

### Versionsschema

- **Major** (v1 -> v2 -> v3): Architektur-Aenderungen, Breaking Changes
- **Minor** (v1.0 -> v1.1 -> v1.2): Feature-Releases, rueckwaertskompatibel
- **Patch** (v1.2.0 -> v1.2.1): Bugfixes, Security Patches

---

## Abgeschlossene Releases

### v1.0.0 -- First Full Release (2026-02-19)

Der Sprung von Alpha (v0.15.2 / v0.9.9) direkt zu v1.0.0. Alle Grundlagen stehen,
das System laeuft stabil als Home Assistant Add-on mit HACS Integration.

**Core Features:**
- Zero Config Setup -- Add-on installieren, fertig
- 50+ Dashboard Cards (Flask-served HTML/JS)
- 23 Core Module (Brain Graph, Habitus Miner, Mood Engine, Neurons, etc.)
- 80+ Sensors via HACS Integration
- Event Ingest Pipeline mit Deduplication und Batching
- Candidate Management mit Governance-Workflow
- Ollama gebundelt im Docker Container (lfm2.5-thinking Default-Modell)
- OpenAI-kompatible API unter `/v1/chat/completions` und `/v1/models`
- Telegram Bot mit Server-Side Tool-Calling
- Conversation Memory (SQLite lifelong learning)

**Infrastruktur:**
- Tag System v0.2 fuer Entity-Klassifikation
- `extended_openai_conversation_pilot` Integration
- Bearer Token Auth (leerer Token = offener Zugang fuer Ersteinrichtung)
- Waitress WSGI Server auf Port 8909
- `/data/` Persistenz (HA Add-on Mount)

**Dateien (Kernstruktur):**
- `copilot_core/core_setup.py` -- init_services + register_blueprints
- `copilot_core/api/v1/blueprint.py` -- Blueprint-Registry
- `copilot_core/brain_graph/` -- Graph Store + Service
- `copilot_core/habitus_miner/` -- Pattern-Discovery
- `copilot_core/mood/` -- 3D-Scoring (Comfort, Joy, Frugality)
- `copilot_core/neurons/` -- 12+ Bewertungs-Neuronen
- `copilot_core/candidates/` -- Candidate Store + API
- `copilot_core/telegram/` -- Telegram Bot (long-polling)
- `copilot_core/conversation_memory.py` -- SQLite Memory Store

---

### v1.1.0 -- Styx (2026-02-19)

Identitaet und visuelles Erlebnis. Das System heisst jetzt **Styx** und bekommt
ein einheitliches Dashboard mit Brain-Visualisierung.

**Features:**
- Styx Identity -- Name, Persona, konsistente Ansprache
- Unified Dashboard: Brain + Chat + History in einer Ansicht
- Module Pipeline Visualisierung (Event -> Brain -> Habitus -> Candidate)
- Domain-Colored Brain Graph (SVG mit Farben pro Entity-Domain)
- Suggestion Bar fuer schnellen Zugriff auf aktive Vorschlaege
- Chat-Interface direkt im Dashboard (OpenAI-kompatibel)

**Dashboard-Architektur:**
- Single-Page App in `dashboard.html` (Flask-served)
- Fetch-basierte API-Aufrufe gegen `/api/v1/*`
- Brain Graph SVG-Rendering mit D3.js-inspirierten Layouts
- Responsive Design fuer Desktop und Tablet

**Dateien:**
- `copilot_core/templates/dashboard.html` (UPDATED)
- `copilot_core/api/v1/dashboard.py` (UPDATED)
- `copilot_core/brain_graph/svg_renderer.py` (UPDATED)
- `IDENTITY.md` (NEW) -- Styx Persona Definition
- `SOUL.md` (NEW) -- Styx Verhaltensrichtlinien

---

### v1.2.0 -- Qualitaetsoffensive (2026-02-19)

Schluss mit Fake-Daten und stillen Fehlern. Jedes Modul liefert echte Health-Daten,
das Dashboard zeigt nur was wirklich laeuft.

**Features:**
- Echte Modul-Health Checks -- 11 APIs parallel abgefragt
- XSS-Schutz im Dashboard (Content Security Policy, Input Sanitization)
- `Promise.allSettled` statt `Promise.all` -- ein kaputter Endpoint killt nicht alles
- Keine Fake-Daten mehr -- wenn ein Modul nicht antwortet, steht "Offline"
- Pipeline-Status mit Tooltips (Hover zeigt letzte Response-Time + Fehler)
- Resiliente Error-States -- Graceful Degradation auf allen Ebenen
- HTTP Error Codes korrekt (404 statt 500 bei fehlenden Ressourcen)

**Technische Details:**
- Health-Endpoint pro Modul: `GET /api/v1/{module}/health`
- Parallel Fetch mit AbortController (5s Timeout pro Modul)
- Dashboard zeigt gruene/gelbe/rote Indikatoren basierend auf echtem Status
- Error Boundary Pattern im Frontend (fehlgeschlagene Cards bleiben stehen)

**Dateien:**
- `copilot_core/system_health/` (UPDATED -- echte Health Checks)
- `copilot_core/templates/dashboard.html` (UPDATED -- resilientes JS)
- `copilot_core/api/v1/blueprint.py` (UPDATED -- Health Endpoints)
- `copilot_core/api/security.py` (UPDATED -- XSS Headers)

---

## v1.3.0 -- Module Control + Automationen (In Progress)

Nutzer koennen Module steuern und akzeptierte Vorschlaege werden zu echten
Home Assistant Automationen. Der Kreis schliesst sich.

### Module Control API

Jedes der 23 Module bekommt drei Zustaende:

| Zustand | Verhalten | Datensammlung |
|---------|-----------|---------------|
| `active` | Beobachtet und handelt, erstellt Suggestions | Ja |
| `learning` | Beobachtet nur, erstellt keine Suggestions | Ja |
| `off` | Komplett deaktiviert | Nein |

**Endpoints:**
- `GET /api/v1/modules` -- Liste aller Module mit Status
- `GET /api/v1/modules/{id}` -- Einzelnes Modul mit Details
- `POST /api/v1/modules/{id}/configure` -- Zustand aendern
- `GET /api/v1/modules/{id}/stats` -- Laufzeit-Statistiken

**Persistenz:**
- SQLite-Datenbank unter `/data/module_states.db`
- Schema: `module_id TEXT PRIMARY KEY, state TEXT, updated_at TIMESTAMP`
- Wird beim Start geladen, Default-Zustand: `active`

### Automation Creator

Akzeptierte Suggestions (Candidate Status = `accepted`) werden echte
Home Assistant Automationen. Kein Copy-Paste mehr.

**Ablauf:**
1. Nutzer akzeptiert Suggestion im Dashboard oder via API
2. Automation Creator mapped Suggestion auf HA-Automation Template
3. Supervisor REST API: `POST /config/automation/config/{id}`
4. Automation erscheint in HA unter Einstellungen -> Automationen
5. Automation Manager im Dashboard zeigt erstellte Automationen

**Template-Mapping:**

| Suggestion-Typ | HA Automation Trigger | Beispiel |
|----------------|----------------------|----------|
| Zeitbasiert | `platform: time` | "Licht um 22:00 dimmen" |
| Zustandsbasiert | `platform: state` | "Heizung aus wenn Fenster offen" |
| Entity-Aktion | `platform: device` | "Rolladen bei Sonnenuntergang" |
| Kombination | `platform: template` | "Licht + Heizung bei Ankunft" |

### Dashboard Updates

- Module-Tab mit Toggle-Switches (active / learning / off)
- Toggles steuern echtes Backend via `POST /api/v1/modules/{id}/configure`
- Automation-Tab zeigt erstellte Automationen mit Status
- Automation-Logs (letzte 50 Ausfuehrungen pro Automation)

### Dateien

| Datei | Aktion | Beschreibung |
|-------|--------|-------------|
| `copilot_core/module_registry.py` | NEW | Module State Management + SQLite |
| `copilot_core/api/v1/module_control.py` | NEW | REST API fuer Module Control |
| `copilot_core/automation_creator.py` | NEW | Suggestion -> HA Automation Mapper |
| `copilot_core/api/v1/automation_api.py` | NEW | REST API fuer Automationen |
| `copilot_core/templates/dashboard.html` | UPDATED | Module Toggles + Automation Tab |
| `copilot_core/core_setup.py` | UPDATED | Neue Services registrieren |

---

## v2.0.0 -- Native HA Integration (Planned)

Der grosse Architektur-Sprung: Styx wird nativ in Home Assistant sichtbar.
Eigene Lovelace Cards, eigener Conversation Agent, WebSocket-Updates.

### Native Lovelace Cards

Drei Custom Cards fuer das HA Dashboard (nicht unser eigenes):

| Card | Funktion | Groesse |
|------|----------|---------|
| `styx-mood-card` | Aktuelle Stimmung als 3D-Visualisierung | 2x2 |
| `styx-brain-card` | Brain Graph Mini-Ansicht mit Top-Nodes | 3x2 |
| `styx-habitus-card` | Aktive Patterns + Suggestions | 2x3 |

**Technologie:**
- Custom Elements (Web Components) via HACS Frontend
- Lit Framework fuer reaktive UI
- WebSocket-Subscription fuer Echtzeit-Updates
- Kompatibel mit HA Themes (Dark/Light)

### HA Conversation Agent

Styx wird als nativer Conversation Agent in Home Assistant verfuegbar:

```python
class StyxConversationAgent(AbstractConversationAgent):
    """Styx als HA Conversation Agent."""

    async def async_process(self, user_input):
        # Proxy zu Core /v1/chat/completions
        # Context Injection (Mood, Neurons, Household)
        # Tool Execution via HA Service Calls
        ...
```

- Direkt nutzbar in HA Assist Pipeline
- Kann als Default-Agent gesetzt werden
- Wake Word: "Hey Styx" (ueber HA Voice Pipeline)
- Kontext-Injektion: Mood, aktive Patterns, Household-Status

### WebSocket Server

Echtzeit-Updates fuer Dashboard und Lovelace Cards:

- `ws://host:8909/ws` -- WebSocket Endpoint
- Events: `brain.update`, `mood.change`, `suggestion.new`, `module.health`
- Heartbeat alle 30s
- Auto-Reconnect im Client

### Dateien

| Datei | Repo | Aktion |
|-------|------|--------|
| `www/styx-mood-card.js` | HACS | NEW |
| `www/styx-brain-card.js` | HACS | NEW |
| `www/styx-habitus-card.js` | HACS | NEW |
| `custom_components/ai_home_copilot/conversation.py` | HACS | NEW |
| `copilot_core/websocket_server.py` | Core | NEW |
| `copilot_core/ws_events.py` | Core | NEW |

---

## v2.1.0 -- Erklaerbarkeit + Multi-User (Planned)

Styx erklaert seine Entscheidungen und lernt individuelle Praeferenzen
pro Haushaltsmitglied.

### Explainability Engine

Jede Suggestion bekommt eine nachvollziehbare Erklaerung:

**Endpoint:** `GET /api/v1/suggestions/{id}/explain`

**Response-Struktur:**
```json
{
  "suggestion_id": "abc-123",
  "explanation": "Basierend auf 14 Beobachtungen in den letzten 7 Tagen...",
  "causal_chain": [
    {"event": "motion.kitchen", "time": "18:30", "weight": 0.8},
    {"event": "light.kitchen_on", "time": "18:31", "weight": 0.9}
  ],
  "confidence": 0.87,
  "patterns_used": ["evening_kitchen_routine"],
  "neuron_scores": {"presence": 0.9, "time_context": 0.8, "energy": 0.6}
}
```

- Brain Graph kausale Kette: Welche Nodes und Edges fuehrten zur Suggestion?
- LLM-generierte natuerlichsprachige Erklaerung (via Ollama)
- Confidence-Score sichtbar im Dashboard und in Lovelace Cards
- "Warum?"-Button bei jeder Suggestion

### Multi-User Profiles

Verschiedene Haushaltsmitglieder, verschiedene Praeferenzen:

- HA Person-Entity -> User-Profil Mapping
- Pro-Nutzer Praeferenzvektor (Temperatur, Licht, Musik, etc.)
- Nutzerspezifische Suggestions (nicht jeder braucht die gleichen Vorschlaege)
- Praeferenz-Lernen aus Accept/Dismiss-Verhalten pro User
- Konflikt-Resolution bei widerspruechlichen Praeferenzen

**Beispiel:**
- Person A mag es kuehl (20 Grad) -- Person B mag es warm (23 Grad)
- Styx lernt: Wenn A allein zuhause -> 20 Grad, wenn B allein -> 23 Grad
- Beide zuhause -> Kompromiss 21.5 Grad (oder letzte akzeptierte Einstellung)

### Dateien

| Datei | Aktion | Beschreibung |
|-------|--------|-------------|
| `copilot_core/explainability.py` | NEW | Erklaerungslogik + Kausalketten |
| `copilot_core/api/v1/explain.py` | NEW | REST API fuer Erklaerungen |
| `copilot_core/user_profiles.py` | NEW | Multi-User Praeferenzen |
| `copilot_core/api/v1/user_profiles_api.py` | NEW | REST API fuer User Profile |
| `copilot_core/templates/dashboard.html` | UPDATED | Warum-Button + User-Switcher |

---

## v2.2.0 -- Praediktive Intelligenz (Planned)

Styx reagiert nicht mehr nur -- Styx sagt voraus. Ankunftszeiten,
Energiepreise, proaktive Optimierung.

### Ankunftsprognose

- Gleitender Durchschnitt der letzten 14 Tage pro Wochentag
- Tageszeit-Gewichtung (Morgens praeziser als Abends)
- Confidence-Interval basierend auf Varianz
- Input: HA Person Tracker (GPS, Zone-Events)
- Output: "Person A kommt voraussichtlich um 17:42 (+/- 8 Min)"

### Energiepreis-Optimierung

- Tibber API Integration (Stundenwerte, naechster Tag ab 13:00)
- aWATTar API als Alternative (Deutschland/Oesterreich)
- Geraete-Profiling: Welches Geraet braucht wie viel kWh?
- Optimale Startzeit berechnen fuer verschiebbare Lasten

**Beispiel:**
> "Styx verschiebt Waschmaschine auf 02:30 -- Strompreis 40% guenstiger als jetzt"

### Proaktive Vorschlaege

Styx handelt bevor der Nutzer fragt:

| Trigger | Aktion | Vorlauf |
|---------|--------|---------|
| Ankunft in 15 Min | Heizung hochfahren | 15 Min |
| Strompreis steigt ab 17:00 | Geschirrspueler jetzt starten | 2h |
| Regen in 30 Min | Dachfenster schliessen | 30 Min |
| Schlafenszeit naht | Lichter dimmen, Rolladen runter | 20 Min |

### Time-Series Forecasting

Bewusst ohne ML-Framework. Leichtgewichtige Verfahren:

- Exponential Smoothing (bereits im Mood-Engine erprobt)
- Saisonale Zerlegung (Wochentag + Tageszeit)
- Einfache lineare Regression fuer Trends
- Alles in reinem Python -- kein TensorFlow, kein PyTorch

### Dateien

| Datei | Aktion | Beschreibung |
|-------|--------|-------------|
| `copilot_core/prediction/forecaster.py` | NEW | Ankunftsprognose |
| `copilot_core/prediction/energy_optimizer.py` | NEW | Tarifoptimierung |
| `copilot_core/prediction/proactive.py` | NEW | Proaktive Suggestion Engine |
| `copilot_core/prediction/api.py` | NEW | REST Endpoints |
| `copilot_core/prediction/__init__.py` | NEW | Package Init |

---

## v3.0.0 -- Kollektive Intelligenz (Planned)

Das Endziel: Styx-Instanzen lernen voneinander. Opt-in, datenschutzkonform,
mathematisch abgesichert.

### Federated Learning

Kein Haushalt teilt Rohdaten. Nur Modell-Gradienten werden aggregiert:

- **Differential Privacy**: Laplace-Mechanismus mit konfigurierbarem Epsilon
- **Aggregation**: FedAvg (Federated Averaging) ueber teilnehmende Instanzen
- **Transport**: HTTPS REST API zwischen Styx-Instanzen (Opt-in)
- **Mindestanzahl**: Aggregation erst ab 5 teilnehmenden Instanzen
- **Validierung**: Gradient Clipping gegen Poisoning Attacks

**Ablauf:**
1. Lokales Training auf Haushaltsdaten
2. Gradienten + Noise (Differential Privacy) berechnen
3. An Aggregation Server senden (kann jede Instanz sein)
4. Aggregiertes Modell-Update empfangen
5. Lokales Modell aktualisieren

### A/B Testing fuer Automationen

Styx testet zwei Varianten einer Automation und waehlt die bessere:

| Parameter | Wert |
|-----------|------|
| Varianten | 2 (A und B) |
| Messzeitraum | Mindestens 14 Tage |
| Metriken | Akzeptanzrate, Energieverbrauch, Nutzerzufriedenheit |
| Signifikanzniveau | 95% (p < 0.05) |
| Auto-Promote | Gewinner wird nach Signifikanz automatisch aktiv |
| Fallback | Bei keiner Signifikanz bleibt Status Quo |

**Beispiel:**
- Variante A: Heizung 30 Min vor Ankunft hochfahren
- Variante B: Heizung 15 Min vor Ankunft hochfahren
- Messung: Temperatur bei Ankunft, Energieverbrauch, Nutzer-Feedback
- Ergebnis nach 3 Wochen: B spart 18% Energie bei gleicher Zufriedenheit -> B gewinnt

### Pattern-Bibliothek

Kollektiv gelernte Muster als Vorlagen fuer neue Installationen:

- **Kategorien**: Energie, Komfort, Sicherheit, Schlaf, Morgenroutine
- **Qualitaet**: Nur Patterns mit >80% Akzeptanzrate ueber 10+ Haushalte
- **Opt-in Sharing**: Explizite Zustimmung pro Pattern
- **Anonymisierung**: Keine Entity-IDs, nur abstrakte Muster
- **Import**: Neue Styx-Instanz kann aus Bibliothek starten

### Dateien

| Datei | Aktion | Beschreibung |
|-------|--------|-------------|
| `copilot_core/collective_intelligence/federated_learner.py` | UPDATED | FedAvg + Diff. Privacy |
| `copilot_core/collective_intelligence/ab_testing.py` | NEW | A/B Test Framework |
| `copilot_core/collective_intelligence/pattern_library.py` | NEW | Pattern Sharing |
| `copilot_core/collective_intelligence/aggregation_server.py` | NEW | Gradient Aggregation |
| `copilot_core/collective_intelligence/privacy.py` | NEW | Laplace-Mechanismus |
| `copilot_core/api/v1/collective.py` | UPDATED | REST Endpoints |

---

## Priorisierungsmatrix

| Feature | Relevanz | Aufwand | Impact | Version |
|---------|----------|---------|--------|---------|
| Module Control API | Hoch | M (2-3 Tage) | Hoch | v1.3.0 |
| Automation Creator | Hoch | M (3-4 Tage) | Sehr Hoch | v1.3.0 |
| Dashboard Toggles | Mittel | S (1 Tag) | Mittel | v1.3.0 |
| Lovelace Cards | Hoch | L (5-7 Tage) | Sehr Hoch | v2.0.0 |
| Conversation Agent | Sehr Hoch | M (3-4 Tage) | Sehr Hoch | v2.0.0 |
| WebSocket Server | Mittel | M (2-3 Tage) | Hoch | v2.0.0 |
| Explainability Engine | Hoch | M (3-4 Tage) | Hoch | v2.1.0 |
| Multi-User Profiles | Mittel | M (3-4 Tage) | Hoch | v2.1.0 |
| Ankunftsprognose | Mittel | S (2 Tage) | Mittel | v2.2.0 |
| Energiepreis-Optimierung | Hoch | M (3-4 Tage) | Sehr Hoch | v2.2.0 |
| Proaktive Vorschlaege | Hoch | M (3-4 Tage) | Sehr Hoch | v2.2.0 |
| Federated Learning | Mittel | XL (7-10 Tage) | Hoch | v3.0.0 |
| A/B Testing | Mittel | L (4-5 Tage) | Hoch | v3.0.0 |
| Pattern-Bibliothek | Niedrig | M (3-4 Tage) | Mittel | v3.0.0 |

**Legende Aufwand:** S = 1-2 Tage | M = 2-4 Tage | L = 4-7 Tage | XL = 7+ Tage

---

## Release-Prozess

Fuer jede Version gilt der gleiche Ablauf:

### 1. Vorbereitung

- Feature Branch erstellen: `claude/feature-v{version}`
- Alle Features implementieren und lokal testen
- Code Review (manuell oder via AI-Assistent)

### 2. Version Bumps

Vier Dateien muessen aktualisiert werden:

| Datei | Feld | Beispiel |
|-------|------|---------|
| `addons/copilot_core/config.yaml` | `version:` | `1.3.0` |
| `copilot_core/main.py` | `__version__` | `"1.3.0"` |
| `custom_components/ai_home_copilot/manifest.json` | `"version":` | `"1.3.0"` |
| `addons/copilot_core/rootfs/usr/src/app/start_dual.sh` | `VERSION=` | `"1.3.0"` |

### 3. Dokumentation

- `CHANGELOG.md` aktualisieren (neuer Abschnitt oben)
- `PROJECT_STATUS.md` aktualisieren
- Diese Roadmap aktualisieren (Status-Spalte)

### 4. Release

1. Code implementieren und testen
2. Version Bumps in allen vier Dateien
3. CHANGELOG aktualisieren
4. Commit: `release: v{version} -- {Kurzbeschreibung}`
5. Push to Branch
6. PR erstellen + Review + Merge
7. GitHub Release erstellen mit Tag `v{version}`
8. Release Notes aus CHANGELOG uebernehmen

### 5. Post-Release

- HACS Repository aktualisieren (falls HACS-aenderungen)
- Community benachrichtigen (falls oeffentlich)
- Naechste Version in Roadmap auf IN PROGRESS setzen

---

## Technische Leitlinien

### Architektur-Prinzipien

| Prinzip | Beschreibung |
|---------|-------------|
| Kein ML-Framework | Reines Python, keine TensorFlow/PyTorch Abhaengigkeit |
| SQLite fuer alles | Persistenz immer via SQLite unter `/data/` |
| Thread-safe Singletons | `threading.Lock()` mit Double-Checked Locking |
| Graceful Degradation | Jedes Modul darf ausfallen ohne das System zu stoppen |
| Flask Blueprints | Jeder Bereich ein eigener Blueprint mit eigenem Prefix |
| Services-Dict | Alle Services in `app.config["COPILOT_SERVICES"]` |

### Modell-Strategie

| Anwendung | Modell | Grund |
|-----------|--------|-------|
| General Chat | lfm2.5-thinking (Liquid AI) | Klein (731MB), gut genug |
| Tool Calling | qwen3:4b | lfm2.5-thinking unterstuetzt kein Tool Calling |
| Erklaerungen | lfm2.5-thinking | Natuerliche Sprache, kein Tool Calling noetig |
| Forecasting | Kein LLM | Statistische Methoden reichen |

### API-Design

- Alle neuen Endpoints unter `/api/v1/`
- JSON Request/Response
- HTTP Status Codes korrekt verwenden (201 Created, 404 Not Found, etc.)
- Bearer Token Auth via `Authorization` Header
- Rate Limiting pro Endpoint konfigurierbar

---

## Meilensteine und Zeitplan

| Meilenstein | Zieltermin | Abhaengigkeiten |
|-------------|-----------|-----------------|
| v1.3.0 Release | Maerz 2026 | Keine |
| v2.0.0 Release | April 2026 | v1.3.0 (stabile Module API) |
| v2.1.0 Release | Mai 2026 | v2.0.0 (Conversation Agent) |
| v2.2.0 Release | Juni 2026 | v2.0.0 (WebSocket fuer Echtzeit) |
| v3.0.0 Release | Q3/Q4 2026 | v2.2.0 (Prediction als Basis) |

---

## Offene Entscheidungen

| Frage | Optionen | Entscheidung bis |
|-------|----------|-----------------|
| Lovelace Card Framework | Lit vs. Preact vs. Vanilla | v2.0.0 Start |
| Aggregation Server Hosting | Self-hosted vs. Cloud | v3.0.0 Start |
| Energy API Provider | Tibber vs. aWATTar vs. Beide | v2.2.0 Start |
| WebSocket Library | Flask-SocketIO vs. websockets | v2.0.0 Start |
| Pattern-Bibliothek Backend | GitHub Repo vs. eigener Server | v3.0.0 Start |

---

*Letzte Aktualisierung: 2026-02-19*
*Maintainer: PilotSuite Team*
