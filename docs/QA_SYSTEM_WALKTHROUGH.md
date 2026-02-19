# PilotSuite — Vollstaendige Q&A: System-Durchleuchtung

> **Version:** v3.8.0 | **Stand:** 2026-02-19
> Gilt fuer beide Repos: Home-Assistant-Copilot (Core) + ai-home-copilot-ha (HACS)

---

## Architektur-Uebersicht

```
+-----------------------------------------------------+
|  HACS Integration (ai-home-copilot-ha)              |
|  - 33 Module, 94+ Sensoren                          |
|  - Laeuft IN Home Assistant                          |
|  - Daten-Sammlung, Event-Weiterleitung, UI           |
+--------------------+--------------------------------+
                     |  HTTP  (events / candidates / context)
+--------------------v--------------------------------+
|  Core Add-on (Home-Assistant-Copilot)               |
|  - Flask + Waitress, Port 8909                      |
|  - LLM, RAG, Brain Graph, Autonomie-Engine          |
|  - SQLite-Datenbanken unter /data/                  |
+-----------------------------------------------------+
```

---

## Startup-Sequenz

### HACS Integration (HA Boot)

1. `__init__.py` -> `async_setup_entry()` aufgerufen
2. `_get_runtime()` baut Modul-Registry auf — jede der 33 Modul-Klassen wird registriert, einzeln try/except (kein Single-Point-of-Failure)
3. Module werden parallel ueber `asyncio.gather()` mit `async_setup_entry()` gestartet
4. HA State-Listener werden registriert (state_changed events)
5. `coordinator.async_refresh()` — initialer Datenabruf

### Core Add-on (Docker Container)

1. `main.py` -> Flask App via Waitress auf Port 8909
2. `core_setup.init_services(config)` — Services in `app.config["COPILOT_SERVICES"]` gespeichert:
   - SQLite-Datenbanken geoeffnet (WAL-Mode + busy_timeout=5000)
   - VectorStore initialisiert (`/data/vector_store.db`)
   - ConversationMemory initialisiert (`/data/conversation_memory.db`)
   - MoodService initialisiert (`/data/mood_history.db`) — laedt letzte Mood-Snapshots
   - BrainGraph geladen (aus JSON-Persist, max 500 Nodes)
   - Neuron-Pipeline aktiviert
   - ProactiveEngine gestartet

---

## Modul-Durchleuchtung

### 1. EventsForwarder — Der Daten-Highway

**Wann aktiv:** Ab HA-Start, kontinuierlich.

**Was passiert:**
- Registriert `state_changed` Listener fuer alle HA-Entities
- Events werden gefiltert, dedupliziert (idempotency key = entity_id + state + timestamp)
- Token-Bucket Rate Limiter verhindert Flood bei schnell wechselnden States
- Events in Batch-Queue (max 500 Items) gesammelt
- `_flush_now()` sendet Batch zu Core `/api/v1/events`

**Persistenz:** SQLite Store: Event-Queue + Drop-Count + Idempotency-Cache

**Zweck erfuellt?** Ja. Core bekommt alle relevanten HA-Zustandsaenderungen in Echtzeit.

---

### 2. BrainGraphSync + KnowledgeGraphSync — Das Weltmodell

**Wann aktiv:** Nach EventsForwarder-Setup; reagiert auf Activity/Calendar-Neurons.

**Was passiert:**
- Entity-States werden als Nodes + Edges in den Brain Graph geschrieben
- Node-Typen: entity, area, person, zone, scene
- Edges: semantische Beziehungen (located_in, controlled_by, used_together_with)
- Exponential Decay: wenig genutzte Nodes verlieren Score, werden bei Ueberschreitung gepruned

**Persistenz (Core):** Brain Graph als JSON (`/data/brain_graph.json`)

**Zum Lernen verwendet:** Grundlage fuer Habitus Mining und Neuron-Scoring.

---

### 3. HabitusMiner — Pattern Mining

**Wann aktiv:** Event-getriggert + periodisch konfigurierbar.

**Was passiert (HACS-Seite):**
- Event-Buffer (deque, max 1000) sammelt Aktionen mit Timestamps
- Zone-Affinity Map: welche Entities in welcher Zone
- Buffer wird alle 5 Minuten persistent gespeichert (HA Storage)

**Was passiert (Core-Seite):**
- Association Rule Mining: A->B Regeln
- Support: wie oft kommt A+B zusammen vor
- Confidence: wenn A, wie oft dann B
- Lift: Verbesserung gegenueber Zufall
- Regeln werden zu Kandidaten wenn Schwellwerte ueberschritten (z.B. confidence > 0.7)

**Persistenz:**
- HACS: Event-Buffer + Discovered Rules in HA Storage (survives Restart)
- Core: Mining-Ergebnisse in `/data/candidates.json`

**Zweck erfuellt?** Ja — das ist der Kern-Lernprozess. System entdeckt echte Nutzungsmuster ohne explizites Training.

---

### 4. CandidatePoller — Bruecke zur Nutzer-Entscheidung

**Wann aktiv:** Periodisch (default: alle 15 Minuten, Backoff bei Fehlern).

**Was passiert:**
1. Pollt Core `/api/v1/candidates?state=pending`
2. Offene Kandidaten -> HA Repairs UI (Issue mit Titel + Beschreibung)
3. User sieht: "Styx schlaegt vor: Wenn Wohnzimmer Licht > 30min, dimmen auf 50%"
4. User: Accept / Dismiss

**Was bei Bestaetigung passiert:**
1. CandidatePoller sendet `POST /api/v1/candidates/{id}` mit `state: "accepted"`
2. Core `automation_creator.py` baut HA Automation Blueprint
3. Blueprint wird ueber HA REST API angelegt
4. **Automation ist sofort aktiv in HA**
5. Pattern-Confidence wird erhoeht, wird in VectorStore eingebettet
6. UserPreferenceModule lernt die bestaetigte Aktion

**Was bei Ablehnung passiert:**
- Kandidat -> `dismissed`, wird nicht erneut angeboten
- Character Module lernt: dieser Typ Vorschlag ist unerwuenscht

**Zweck erfuellt?** Ja — Automation wird tatsaechlich in HA erstellt, nicht nur vorgeschlagen.

---

### 5. ProactiveEngine (Core) — Kontextuelle Hinweise

**Wann aktiv:** Bei Zone-Wechsel, konfigurierbare Cooldown + Quiet Hours.

**Was passiert:**
- Person betritt Zone -> Neuron-Scores + Mood + Brain Graph abgefragt
- Passende Suggestions aus Pattern-Store gefiltert (Character-Preset beachtet)
- `max_per_hour` Limit, Quiet Hours respektiert (konfigurierbar 22:00-08:00)
- Ausgabe ueber Telegram, TTS oder HA Notification

---

### 6. ConversationMemory (Core) — Lebenslanges Gedaechtnis

**Wo:** `/data/conversation_memory.db` (SQLite, WAL-Mode)

**Was gespeichert wird:**
- Alle Nachrichten (User + Assistant) mit Timestamp
- Automatisch extrahierte Praeferenzen mit Confidence-Score (0.0-1.0)
- z.B. "Nutzer bevorzugt Wohnzimmer-Licht 40% abends"

**Wie es beim Lernen genutzt wird:**
1. Neue Konversation startet
2. `search_similar_sync(user_query, VectorStore)` holt aehnliche Praeferenzen
3. Als System-Context in LLM-Prompt injiziert
4. LLM antwortet praeferenzbewusst

**Persistenz:** Permanent. Survives Neustarts, Updates. Max 10.000 Eintraege (FIFO).

---

### 7. VectorStore — Semantische Suche

**Wo:** `/data/vector_store.db` (SQLite)

**Methode:** Bag-of-Words Embeddings (kein Transformer — laeuft auf Raspberry Pi)

**Was eingebettet wird:**
- Praeferenzen aus ConversationMemory
- Akzeptierte Kandidaten (Pattern-Text)
- Entity-Beschreibungen
- User Hints

**Abruf:** `search_similar_sync(query_text, top_k=5, threshold=0.3)` bei jedem LLM-Call.

---

### 8. MoodService + Mood Engine — Stimmungsmodell

**Wann aktiv:** Permanent; Event-getriggert.

**3D Mood-Scoring:**
- Comfort (Temperatur, Luftfeuchtigkeit, Licht-Qualitaet)
- Joy (Musik an, Aktivitaet, soziale Praesenz)
- Frugality (Energie-Verbrauch vs Baseline, Solar-Ertrag)

**Verwendung:**
- Character Module gewichtet Suggestions basierend auf Mood
- Bei niedrigem Comfort -> Klima-Suggestion priorisiert
- Mood ist Teil des LLM-Prompts ("aktuell ruhiger Abend-Modus")

**Persistenz:** SQLite `/data/mood_history.db` — 30 Tage Rolling History, Snapshot alle 60s pro Zone. Letzter Mood wird bei Restart wiederhergestellt.

---

### 9. HomeAlertsModule — Kritische Ueberwachung

**Wann aktiv:** Periodischer Scan (alle 5 Minuten) + Echtzeit-Events.

**Was ueberwacht wird:**
- Batterie < 20% aller Sensoren
- Klimaabweichung (Soll vs Ist > 2 Grad)
- Praesenz-Aenderungen
- System-Errors (Offline-Entities)

**Alert-Schweregrade:** low / medium / high / critical

**Health Score:** 0-100, aggregiert aus Alert-Anzahl und Schwere.

**Persistenz:** HA Storage — Acknowledged Alert IDs + taegliche Alert-History (30 Tage). Bestaetigte Alerts bleiben nach Restart bestaetig.

---

### 10. UserPreferenceModule — Explizites Praeferenz-Lernen

**Wann aktiv:** Event-getriggert; nach jeder Konversation.

**Was gespeichert wird:**
- Explizit genannte Praeferenzen ("Ich mag es morgens hell")
- Implizite Muster (wiederholte Aktionen)
- Confidence Score pro Praeferenz (steigt bei Bestaetigung)

**Persistenz:** HA Storage (`.storage/ai_home_copilot.user_preferences`)

**Abruf:** Beim Aufbau des LLM-System-Prompts; hoechste Confidence-Items bevorzugt.

---

### 11. CharacterModule — Persoenlichkeit & Suggestion-Filter

| Preset | Charakter | Suggestions/Std | Auto-Execute |
|--------|-----------|-----------------|--------------|
| minimal | Stummer Assistent | 0 | Nein |
| assistant | Nuetzlich, diskret | 2 | Nein |
| companion | Gespraechig, warm | 4 | Nein |
| guardian | Sicherheitsfokus | 3 | Ja (nur Security) |
| efficiency | Energie-Optimierer | 5 | Ja |
| relaxed | Entspannt, selten | 1 | Nein |

**Persistenz:** HA Storage — Preset survives Restart.

---

### 12. Neuron-Pipeline — Das Bewusstsein

12 spezialisierte Bewertungs-Neuronen:

| Neuron | Bewertet | Output |
|--------|----------|--------|
| PresenceNeuron | Wer ist wo | Presence-Score pro Zone |
| EnergyNeuron | Stromverbrauch vs Baseline | Frugality-Score |
| WeatherNeuron | Aussentemperatur, Solar | Context-Tags |
| ActivityNeuron | Bewegung, Zeitpunkt | Activity-Level |
| CalendarLoadNeuron | Termine heute/morgen | Load-Score |
| ClimateNeuron | Heizung Ist vs Soll | Comfort-Score |
| MediaNeuron | Musik/TV aktiv | Entertainment-Flag |
| SecurityNeuron | Tueren, Fenster, Alarm | Security-Score |
| NetworkNeuron | WAN-Qualitaet, AP-Status | Network-Health |
| SleepNeuron | Schlafenszeit-Muster | Rest-Mode Flag |
| ArrivalNeuron | Heim-Ankunft erkannt | Arrival-Sequence trigger |
| DepartureNeuron | Verlassen erkannt | Departure-Sequence trigger |

---

## Gesamtfluss: Vom Muster zur Automation

```
Tag 1-7: Nutzer dimmt Wohnzimmer-Licht taeglich um 20:00 auf 40%
            |
EventsForwarder: State-Change -> Core /api/v1/events
            |
BrainGraph: Node "light.wohnzimmer" + Edge "dimmed_by_user" erhoeht
            |
HabitusMiner: Regel "time=20:00 -> light.wohnzimmer.brightness=40, confidence=0.82"
            |
Kandidat erstellt: pending in /data/candidates.json
            |
CandidatePoller: HA Repairs Issue erstellt
"Styx schlaegt vor: Taeglich um 20:00 Wohnzimmer auf 40% dimmen"
            |
Nutzer klickt "Uebernehmen"
            |
Core automation_creator.py: HA Automation Blueprint erstellt
            |
Automation ist aktiv — ab jetzt automatisch
            |
UserPreferenceModule: Confidence fuer "Abend-Dimming" +0.2
VectorStore: Praeferenz eingebettet fuer kuenftige RAG-Abfragen
ConversationMemory: Entscheidung gespeichert
```

---

## Wissens-Persistenz Uebersicht

| Was | Wo | Survives Restart |
|-----|----|-----------------|
| Konversationshistorie | `/data/conversation_memory.db` | Ja |
| Praeferenzen (extrahiert) | `/data/conversation_memory.db` | Ja |
| Einbettungen/RAG | `/data/vector_store.db` | Ja |
| Brain Graph | `/data/brain_graph.json` | Ja |
| Kandidaten | `/data/candidates.json` | Ja |
| Mood History | `/data/mood_history.db` | Ja |
| Character-Preset | HA Storage | Ja |
| Entity-Tags | HA Storage | Ja |
| User-Praeferenzen | HA Storage | Ja |
| Event-Queue (HACS) | HA Storage (SQLite) | Ja |
| Alert Acknowledgments | HA Storage | Ja |
| Alert History (30 Tage) | HA Storage | Ja |
| Habitus Event Buffer | HA Storage | Ja |
| Habitus Discovered Rules | HA Storage | Ja |

---

## Kernfragen — Direkte Antworten

### Q: Ist das System nur weil es installiert ist schon lernfaehig?

**A: Ja — ab dem Moment der Installation beginnt das Lernen.**

1. **EventsForwarder** sammelt sofort alle state_changed Events und leitet sie an Core weiter
2. **BrainGraph** baut ab dem ersten Event das Weltmodell auf (Nodes + Edges)
3. **ConversationMemory** speichert jede Chat-Nachricht und extrahiert Praeferenzen
4. **HabitusMiner** fuellt den Event-Buffer und kann jederzeit Mining triggern
5. **HomeAlerts** ueberwacht sofort Batterie, Klima und Systemzustand

Was **nicht** automatisch passiert:
- Mining muss initial manuell getriggert werden (Service Call `habitus_mine_rules`) oder `auto_mining_enabled` auf `true` setzen
- Vorschlaege werden nur im Learning-Modus angeboten (Standard)
- Automationen werden nur nach expliziter Bestaetigung erstellt

Das System ist also ab Installation **lern-bereit** — es sammelt Daten, baut Kontext auf, und wartet auf den ersten Mining-Trigger oder Konversation.

### Q: Werden bestaetigte Vorschlaege tatsaechlich umgesetzt?

**A: Ja.** `automation_creator.py` ruft `POST /api/services/automation` via Supervisor REST API auf. Die Automation ist nach Bestaetigung sofort in HA aktiv und erscheint im Automation-Editor.

### Q: Wird nachhaltig Wissen gespeichert?

**A: Ja — in drei Schichten:**
1. **Explizit:** Praeferenzen in `conversation_memory.db`
2. **Implizit:** Muster in `vector_store.db` + `candidates.json`
3. **Strukturell:** Beziehungen in `brain_graph.json`

Plus seit v3.8.0:
4. **Mood History:** 30-Tage Mood-Verlauf in `mood_history.db`
5. **Alert History:** Taegliche Alert-Aggregate in HA Storage
6. **Mining Buffer:** Event-Buffer persisted in HA Storage

Nichts davon wird bei Update/Neustart geloescht.

### Q: Wie greift das System beim Lernen darauf zu?

**A: RAG bei jedem LLM-Call.** `search_similar_sync(user_query)` holt die top-5 aehnlichsten Erinnerungen aus dem VectorStore und injiziert sie als System-Context. Fuer Suggestions: Habitus Miner nutzt Brain Graph + Mining-Regeln; Character Module filtert passende; ProactiveEngine liefert sie zur richtigen Zeit.

### Q: Was passiert nach dem Abruf?

**A:** Erinnerungen fliessen als zusaetzlicher Kontext in den LLM-Prompt ein. Das Modell "weiss" damit was der Nutzer frueher bestaetig hat und passt Ton/Inhalt an. Das ist kein Fine-Tuning, sondern In-Context Learning bei jedem Request neu.

### Q: Wann werden Module aktiv?

| Trigger | Module |
|---------|--------|
| HA Boot | Alle (parallel async_setup_entry) |
| state_changed Event | EventsForwarder, BrainGraphSync, HomeAlerts, CameraContext |
| Zeitplan | WasteReminder, BirthdayReminder, HabitusMiner, CandidatePoller |
| Zone-Eintritt | ProactiveEngine, MoodContext, ArrivalNeuron |
| LLM Request | VectorStore RAG, ConversationMemory, Character |
| User-Aktion (HA UI) | CandidatePoller (Accept/Dismiss callback) |

---

## Sicherheit (v3.7.1+)

- **Defense-in-Depth Auth:** Globale `@app.before_request` Middleware + Blueprint-Level `@bp.before_request` auf allen 19+ API-Blueprints
- **Token-Auth:** X-Auth-Token Header oder Bearer Token (OpenAI-SDK kompatibel)
- **Timing-Safe:** hmac.compare_digest fuer Token-Vergleich
- **Rate Limiting:** Per-Endpoint konfigurierbar via Environment Variables
- **Circuit Breaker:** ha_supervisor (5 fails/30s), ollama (3 fails/60s)
