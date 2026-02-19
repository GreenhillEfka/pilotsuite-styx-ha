# Changelog - PilotSuite Core Add-on

## [3.2.0] - 2026-02-19

### Müllabfuhr + Geburtstags-Erinnerungen (Server-Side)

- **WasteCollectionService**: Server-seitiger Waste-Kontext für LLM + Dashboard
  - REST API: `POST /api/v1/waste/event`, `POST /api/v1/waste/collections`,
    `GET /api/v1/waste/status`, `POST /api/v1/waste/remind`
  - TTS-Delivery via Supervisor API
  - LLM-Kontext-Injection (Müllabfuhr-Status im System-Prompt)
- **BirthdayService**: Server-seitiger Geburtstags-Kontext
  - REST API: `POST /api/v1/birthday/update`, `GET /api/v1/birthday/status`,
    `POST /api/v1/birthday/remind`
  - TTS + Persistent Notification Delivery
  - LLM-Kontext (Styx weiß wer Geburtstag hat)
- **LLM Tools**: `pilotsuite.waste_status` + `pilotsuite.birthday_status` (19 Tools total)
- **Dashboard**: Müllabfuhr-Panel + Geburtstags-Panel auf Modules-Page
- **Module Health**: Waste + Birthday Status in Module-Grid
- Version auf 3.2.0

## [3.1.1] - 2026-02-19

### Frontend-Backend Integration Fix

#### CRITICAL Fixes
- **Dashboard Graph Stats**: Korrektes Parsing der `/api/v1/graph/stats`
  Response (`gr.nodes` statt `gr.stats.nodes`)
- **Dashboard Mood Endpoint**: `/api/v1/mood` statt `/api/v1/mood/state`,
  `mr.moods` statt `mr.zones`
- **Dashboard Media Zones**: `mzr.zones` statt `Object.keys(mzr)`
- **Module Control Routing**: Blueprint url_prefix auf `/api/v1/modules`
  korrigiert (war `/modules`)

#### Zone-Entry Event Forwarding
- **ZoneDetector Integration**: HACS ZoneDetector erkennt jetzt Zonen-Wechsel
  und forwarded `POST /api/v1/media/proactive/zone-entry` an Core Addon
- **Musikwolke Auto-Update**: Proactive zone-entry Endpoint aktualisiert
  automatisch aktive Musikwolke-Sessions (Audio folgt Person)
- ZoneDetector in `__init__.py` verdrahtet (Setup + Unload)

#### Dashboard Erweiterungen
- **Media Zonen Panel**: Zeigt Zone-Player-Zuordnung + aktive Musikwolke Sessions
- **Web & News Panel**: Info ueber DuckDuckGo-Suche, RSS News, NINA/DWD
- **API Endpoints Tabelle**: Aktualisiert mit Media Zones, Musikwolke, Proaktiv
- Autonomie-Tooltips aktualisiert (Auto-Apply bei beiden Modulen aktiv)
- Musikwolke-Session-Count in Module Health Details

#### Mood Event Processor
- Mood Service wird jetzt automatisch aus Event-Pipeline gespeist
  (media_player State Changes → MoodService.update_from_media_context)

#### Config
- `web_search` Section in addon config.json (ags_code, news_sources)
- config.json Version → 3.1.0

Dateien: `module_control.py`, `media_zones.py`, `core_setup.py`,
`config.json`, `dashboard.html`, `zone_detector.py` (HACS), `__init__.py` (HACS)

## [3.1.0] - 2026-02-19

### Autonomie + Web-Intelligenz + Musikwolke

#### Autonomie-faehiges Modul-System (3-Tier)
- **active**: Vorschlaege werden AUTOMATISCH umgesetzt — nur wenn BEIDE
  beteiligten Module (Quelle + Ziel) aktiv sind (doppelte Sicherheit)
- **learning**: Beobachtungsmodus — Daten sammeln + Vorschlaege zur
  MANUELLEN Uebernahme erzeugen (User muss accept/reject)
- **off**: Modul deaktiviert (keine Datensammlung, kein Output)
- Neue API-Methoden: `should_auto_apply()`, `should_suggest()`,
  `get_suggestion_mode()` in ModuleRegistry

#### Web-Suche & Nachrichten fuer Styx
- **DuckDuckGo-Suche**: Styx kann das Web durchsuchen (kein API-Key noetig)
  Nutzer: "Recherchier mal die besten Zigbee-Sensoren 2026"
- **News-Aggregation**: Aktuelle Nachrichten von Tagesschau + Spiegel
  via RSS, mit 15-Min-Cache
- **Regionale Warnungen**: NINA/BBK Zivilschutz + DWD Wetterwarnungen
  mit AGS-Regionalfilter. Warnungen fliessen in den LLM-Kontext ein
- Neue LLM Tools: `pilotsuite.web_search`, `pilotsuite.get_news`,
  `pilotsuite.get_warnings`

#### Musikwolke + Media Zonen
- **MediaZoneManager**: Media-Player den Habituszonen zuordnen (SQLite),
  Playback-Steuerung pro Zone (play/pause/volume)
- **Musikwolke**: Smart Audio Follow — Musik folgt dem User durch die Raeume.
  Start/Stop via Chat ("Musikwolke starten") oder REST API
- **Proaktive Vorschlaege**: Kontext-basierte Suggestions bei Raum-Eintritt
  (z.B. "Du bist im Wohnzimmer, soll Netflix auf AppleTV starten?")
  mit Cooldown, Quiet Hours, Dismiss-Tracking
- Neue LLM Tools: `pilotsuite.play_zone`, `pilotsuite.musikwolke`
- REST API: 16 Endpoints unter `/api/v1/media/*`

#### Modul-Umbenennung
- `unifi_context` -> `network` (generisch, nutzt UniFi API wenn vorhanden)
- `media_context` -> `media_zones` (Musikwolke + Zonen-Player)
- `event_forwarder` -> `Event Bridge`
- `user_preferences` -> `Nutzer-Profile` (Multi-User + Autonomie)
- Neue Module: `proactive` (Kontext-Vorschlaege), `web_search` (News + Recherche)

#### Sharing-Modul Fix
- Blueprint-Registrierung nachgezogen (war nicht in core_setup.py verdrahtet)

#### Dashboard v3.1
- 17 Module (von 15), neue Autonomie-Tooltips auf Modul-Toggles
- Media-Zonen Health-Check in der Module-Seite
- Warnung-Context wird in LLM-System-Prompt injiziert

Dateien: `module_registry.py`, `web_search.py`, `media_zone_manager.py`,
`proactive_engine.py`, `api/v1/media_zones.py`, `mcp_tools.py`,
`api/v1/conversation.py`, `core_setup.py`, `dashboard.html`, `main.py`

## [3.0.1] - 2026-02-19

### Natural Language Automation Creation -- End-to-End Pipeline Fix

- **Neues LLM Tool `pilotsuite.create_automation`**: Der LLM kann jetzt echte
  HA-Automationen erstellen wenn der User z.B. sagt "Wenn die Kaffeemaschine
  einschaltet, soll die Kaffeemuehle sich synchronisieren". Der LLM parsed die
  natuerliche Sprache in strukturierte Trigger/Action-Daten und erstellt die
  Automation via Supervisor API.
- **Neues LLM Tool `pilotsuite.list_automations`**: Erstellte Automationen auflisten.
- **UserHintsService komplett**: `accept_suggestion()` und `reject_suggestion()`
  implementiert mit AutomationCreator-Bridge. Akzeptierte Suggestions erstellen
  jetzt echte HA-Automationen.
- **HintData Model**: `to_dict()` und `to_automation()` Methoden hinzugefuegt.
- **AutomationCreator erweitert**: Akzeptiert jetzt auch strukturierte
  Trigger/Action-Dicts (nicht nur Regex-parsbare Strings).
- **System Prompt aktualisiert**: LLM weiss jetzt ueber seine
  Automations-Erstellungs-Faehigkeit.

Dateien: `mcp_tools.py`, `api/v1/conversation.py`, `api/v1/service.py`,
`api/v1/models.py`, `api/v1/user_hints.py`, `automation_creator.py`

## [3.0.0] - 2026-02-19

### Kollektive Intelligenz — Cross-Home Learning

- **Federated Learning**: Pattern-Austausch zwischen Homes mit Differential Privacy
  (Laplace-Mechanismus, konfigurierbares Epsilon)
- **A/B Testing fuer Automationen**: Zwei Varianten testen, Outcome messen (Override-Rate),
  Chi-Squared Signifikanztest, Auto-Promote Winner bei p<0.05
- **Pattern Library**: Kollektiv gelernte Muster mit gewichteter Confidence-Aggregation
  ueber mehrere Homes, opt-in Sharing

Dateien: `ab_testing.py`, `collective_intelligence/pattern_library.py`

## [2.2.0] - 2026-02-19

### Praediktive Intelligenz — Vorhersage + Energieoptimierung

- **Ankunftsprognose**: `ArrivalForecaster` nutzt zeitgewichteten Durchschnitt der
  letzten 90 Tage (Wochentag + Uhrzeit), SQLite-Persistenz, kein ML-Framework
- **Energiepreis-Optimierung**: `EnergyOptimizer` findet guenstigstes Zeitfenster,
  unterstuetzt Tibber/aWATTar API oder manuelle Preistabelle
- **Geraete-Verschiebung**: "Styx verschiebt Waschmaschine auf 02:30 (34ct gespart)"
- **REST API**: `/api/v1/predict/arrival/{person}`, `/api/v1/predict/energy/*`

Dateien: `prediction/__init__.py`, `prediction/forecaster.py`, `prediction/energy_optimizer.py`,
`prediction/api.py`

## [2.1.0] - 2026-02-19

### Erklaerbarkeit + Multi-User — Warum schlaegt Styx das vor?

- **Explainability Engine**: Brain Graph Traversal (BFS, max Tiefe 5) findet kausale
  Ketten fuer Vorschlaege, Template-basierte natuerlichsprachige Erklaerung,
  Confidence-Berechnung aus Edge-Gewichten
- **Multi-User Profiles**: Pro HA-Person-Entity eigenes Profil mit Praeferenzvektor,
  Suggestion-History, Feedback-Tracking (accept/reject), SQLite-Persistenz
- **REST API**: `/api/v1/explain/suggestion/{id}`, `/api/v1/explain/pattern/{id}`

Dateien: `explainability.py`, `api/v1/explain.py`, `user_profiles.py`

## [2.0.0] - 2026-02-19

### Native HA Integration — Lovelace Cards + Conversation Agent

- **3 Native Lovelace Cards** (HACS Integration):
  - `styx-brain-card`: Brain Graph Visualisierung mit Force-Directed Layout
  - `styx-mood-card`: Mood-Gauges (Comfort/Joy/Frugality) mit Kreis-Grafik
  - `styx-habitus-card`: Top-5 Pattern-Liste mit Confidence-Badges
- **HA Conversation Agent**: `StyxConversationAgent` nativ in HA Assist Pipeline,
  Proxy zu Core `/v1/chat/completions`, DE + EN

Dateien: `www/styx-brain-card.js`, `www/styx-mood-card.js`, `www/styx-habitus-card.js`,
`conversation.py` (HACS)

## [1.3.0] - 2026-02-19

### Module Control + Automationen — Toggles mit echter Wirkung

- **Module Control API**: `POST /api/v1/modules/{id}/configure` setzt Modul-Zustand
  (active/learning/off) im Backend, SQLite-Persistenz in `/data/module_states.db`
  - active: Modul laeuft normal, beobachtet und erzeugt Vorschlaege
  - learning: Modul beobachtet, erstellt aber keine Suggestions
  - off: Modul deaktiviert, keine Datensammlung
- **Dashboard-Toggle ruft API**: `toggleModule()` sendet jetzt POST an Backend,
  Fallback auf localStorage wenn API nicht erreichbar
- **Automation Creator**: Akzeptierte Vorschlaege erzeugen echte HA-Automationen
  via Supervisor REST API (`POST /config/automation/config`), Template-Mapping
  (Zeit-Trigger, State-Trigger, Entity-Aktionen)
- **Automationen-Liste**: Neue Sektion im Modules-Tab zeigt erstellte Automationen

Dateien: `module_registry.py`, `api/v1/module_control.py`, `automation_creator.py`,
`api/v1/automation_api.py`, `dashboard.html` (updated)

## [1.2.0] - 2026-02-19

### Qualitaetsoffensive — Volle Transparenz, Maximale Resilienz

#### Dashboard v3 — Kein Dummy-Code mehr
- **Echte Modul-Health**: `fetchModuleHealth()` laedt Status aus 11 APIs parallel
  (Brain Graph Stats, Habitus Health, Mood State, Neurons, Memory, Energy, Weather,
  UniFi, Telegram, Capabilities) — alle Module zeigen echten Zustand (active/learning/off)
- **Modul-Override mit Persistenz**: Nutzer-Toggles (active/learning/off) werden in
  `localStorage` gespeichert und bei jedem Reload wiederhergestellt; Override-Indikator
  sichtbar wenn Nutzer-Status von API-Status abweicht
- **Echte Pipeline-Status**: Pipeline-Pills auf der Styx-Seite zeigen tatsaechlichen
  Modul-Status mit Hover-Tooltip (Detail-Info aus API), nicht mehr hardcoded 'active'
- **Neue Pipe-Klassen**: `pipe-error` (rot) und `pipe-unknown` (gedimmt) fuer Fehler-
  und Unbekanntzustaende sichtbar in der Pipeline-Leiste
- **XSS-Schutz**: `escapeHtml()` helper — alle API-Daten werden vor innerHTML-Rendering
  escaped (Chat-Antworten, Vorschlaege, Zonen, Modell-Namen, SVG-Labels, alles)
- **Resiliente Fehler-States**: Status-Pill zeigt "API offline" (rot) wenn Core nicht
  erreichbar; LLM-Settings zeigt klare Fehlermeldung statt Loading-Spinner; alle Seiten
  zeigen "Erneut versuchen" Button bei Ladefehler
- **Kein Fake-Chart-Data**: Trend-Charts zeigen "Nicht genug Daten" Hinweis wenn weniger
  als 2 echte Datenpunkte vorhanden — kein Sine-Wave-Dummy mehr
- **Promise.allSettled ueberall**: Suggestion Inbox und Settings nutzen `allSettled`
  statt `all` — ein fehlschlagender API-Aufruf bricht nicht alles ab
- **MCP-Status echt**: MCP Server Status kommt aus `/api/v1/capabilities` (nicht mehr
  immer-gruen hardcoded); Capabilities-Features werden in Settings angezeigt
- **Hint-Consequent-Parsing**: Hints mit Format "X -> Y" werden korrekt in
  Antecedent/Consequent aufgeteilt; nicht mehr immer leer
- **loadPage() try-catch**: Alle Seiten-Loader sind in resilientem Wrapper —
  unerwartete Fehler zeigen "Erneut versuchen" UI statt stiller Fehler
- **Suggestion Inbox**: 3 Quellen (Habitus Rules, Brain Graph Candidates, Hints),
  Accept/Reject mit Backend-Integration, Batch-Pipeline, Brain-Edge-Animation
- **Dead Code entfernt**: Nutzloses `c.querySelector('.loading')||null` entfernt

## [1.1.0] - 2026-02-19

### Styx — Die Verbindung beider Welten

- **Styx Identity**: Configurable assistant name (`ASSISTANT_NAME` env var, config field)
- **Unified Dashboard**: Brain Graph + Chat + History on one page, 5-page navigation
- **Module Pipeline**: 15 modules with status indicators (active/learning/off)
- **Domain-Colored Brain Graph**: 16 HA domain colors, SVG glow filter, auto-legend
- **Canvas Trend Charts**: Habitus and Mood 24h gradient-fill mini charts
- **Suggestion Bar**: Top suggestions from Habitus rules, clickable into chat
- **Fix**: start_with_ollama.sh default model → qwen3:4b

---

## [0.9.7-alpha.1] - 2026-02-18

### Bugfix
- **Logging**: `print()` → `logger.warning()` in transaction_log.py
- **Ollama Conversation**: Bereinigung undefinierter Funktionsreferenzen

---

## [0.9.6-alpha.1] - 2026-02-18

### Features
- **Dev Surface Enhanced**: Performance-Metriken in SystemHealth
  - Cache-Hits/Misses/Evictions
  - Batch-Mode Status
  - Pending Invalidations
  - duration_ms Tracking für Operationen
- **MCP Tools**: Vollständig integriert (249 Zeilen)
  - HA Service Calls
  - Entity State Queries
  - History Data
  - Scene Activation

### Performance
- **Batch-Mode für Brain Graph Updates**
  - Event-Processor nutzt Batch-Verarbeitung
  - Cache-Invalidierung wird bis zum Batch-Ende verzögert
  - ~10-50x weniger Cache-Invalidierungen bei vielen Events
- **Optimiertes Pruning** (4 Table Scans → 2)
  - JOIN-basierte Node/Edge Limitierung in einem Durchgang
  - Deterministic Pruning (alle 100 Operationen)

---

## [0.9.4-alpha.1] - 2026-02-18

### Performance
- **Batch-Mode für Brain Graph Updates**
  - Event-Processor nutzt jetzt Batch-Verarbeitung
  - Cache-Invalidierung wird bis zum Batch-Ende verzögert
  - ~10-50x weniger Cache-Invalidierungen bei vielen Events
  - Deutlich verbesserte Performance bei hohem Event-Aufkommen
- **Optimiertes Pruning** (4 Table Scans → 2)
  - JOIN-basierte Node/Edge Limitierung in einem Durchgang
  - Deterministic Pruning (statt random)
- **Pruning-Trigger**: Alle 100 Operationen statt zufällig

### Bugfix
- **Ollama Conversation Endpoint**: Bereinigung undefinierter Funktionsreferenzen

---

## [0.9.1-alpha.9] - 2026-02-17

### Removed
- **OpenAI Chat Completions API entfernt**
  -/openai_chat.py gelöscht
  - Blueprint Registration entfernt
  - OpenAI API config entfernt

**Hintergrund:** Nutzt HA integrierte Chatfunktion statt OpenClaw Assistant

---

## [0.9.1-alpha.8] - 2026-02-17