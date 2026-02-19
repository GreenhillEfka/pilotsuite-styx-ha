# MEMORY.md - Long-Term Memory

## Design-Entscheidungen (wichtig!)

### Habitus Philosophy: Das lernende Zuhause
**Kernidee (2026-02-15):**
- Ein Smart Home ist nur so schlau wie sein Nutzer – aber es kann lernen
- **HabitusZones** = Brücke zwischen statischen Regeln und individuellen Mustern
- **Tags** = Semantik (Bedeutung), **Zones** = Kontext
- **Vorschläge, nicht Automatik** – Nutzer entscheidet immer

**Tag → Zone Integration:**
- `aicp.place.X` → Entity automatisch zu `HabitusZone("X")` hinzufügen
- `aicp.role.safety_critical` → Immer Bestätigung erforderlich
- Zone-basiertes Mining für präzise Muster

**Philosophie-Dokument:** `/docs/HABITUS_PHILOSOPHY.md`

---

### Habitus Zones: Manuelle Entity-Auswahl bei Installation
**Entscheidung vom 2026-02-15:**
- Entities für Habitus Zones werden **manuell während der Installation ausgewählt**
- Wenn ein Habitus-Bereich hinzugefügt wird, wählt der User die relevanten Entities aus
- **Nur diese manuell ausgewählten Entities** werden für die Auswertung im PilotSystem herangezogen
- Das macht das System zu Beginn **übersichtlicher** und vermeidet Rauschen durch nicht-relevante Entities

**Aktuelles Beispiel:**
- Aktuell ist nur **Wohnbereich** als Habitus-Zone für die Entwicklung definiert
- Weitere Zones können später ergänzt werden, aber jede Zone beginnt mit manuellem Entity-Set

**Begründung:**
1. **Übersichtlichkeit** - nur relevante Entities pro Zone
2. **Privacy-First** - keine automatisierte Entity-Erkennung die falsch liegen kann
3. **User-Kontrolle** - User entscheidet was relevant ist
4. **Entwicklungsimplizität** - klares, bekanntes Set für Tests

---

## System Status (Stand 2026-02-15)

### Dashboard & Orchestrierung
- **ReactBoard**: http://<PRIVATE-IP>:48099/__openclaw__/ReactBoard/ ✅
- **Release Script**: `/config/.openclaw/workspace/scripts/release_system.sh`
- **Commands**: `status|sync|commit|push|release|dashboard|full`

### CLI Orchestrierung
- **Claude Code**: 2.1.42 ✅ - GitHub Sync, Release Koordination
- **Gemini CLI**: 0.28.2 ✅ - Architektur-Reviews (1M Context)
- **Codex CLI**: 0.101.0 ✅ - Code Reviews, Security Scans

### Release Workflow
```bash
# Full Release
./scripts/release_system.sh release v0.X.X

# Dashboard Update
./scripts/release_system.sh dashboard

# Full Sync
./scripts/release_system.sh full
```

---

### Zone Conflict Resolution (2026-02-16)
**Architektur-Entscheidung:**
- Bei überlappenden Zones (Entity in mehreren aktiven Zones) wird automatisch konfliktgelöst
- **Strategien (in Priorität):**
  1. `HIERARCHY` - Spezifischere Zone (room > area > floor) gewinnt
  2. `PRIORITY` - Höhere Priorität gewinnt
  3. `USER_PROMPT` - Event feuern, User entscheidet
  4. `MERGE` - Entities zusammenführen
  5. `FIRST_WINS` - Erste aktive Zone gewinnt
- **Default:** `HIERARCHY` - Child-Zones überschreiben Parent-Zones
- **Implementation:** `ZoneConflictResolver` in `habitus_zones_store_v2.py`

**State Machine:**
- Zone States: `idle` → `active` → `transitioning` → `idle`
- States persistiert via HA Storage API
- Events: `SIGNAL_HABITUS_ZONE_STATE_CHANGED`, `SIGNAL_HABITUS_ZONE_CONFLICT`

---

## AI Home CoPilot Projekt (Stand 2026-02-16 02:50)

### Versionen (aktuell)
- **HA Integration**: v0.13.2 - Brain Graph Panel v0.8, Cross-Home Sync, Collective Intelligence ✅
- **Core Add-on**: v0.8.3 - Brain Graph Panel API, Cross-Home Sync API, Collective Intelligence API ✅
- **Neurons implementiert**: SystemHealth, UniFi, Energy
- **Features komplett**: Tag System v0.2, Habitus Zones v2 (+ Conflict Resolution), Mood Context, Brain Graph v0.8, Debug Mode, MUPL

### Sync Status (2026-02-16)
- HA Integration: Clean, synced with origin ✅
- Core Add-on: Clean, synced with origin ✅

### Autopilot Task Queue
1. ~~Interactive Brain Graph Panel v0.7.6~~ ✅ RELEASED (2026-02-15)
2. ~~Multi-User Preference Learning v0.8.0~~ ✅ RELEASED (2026-02-15)
3. Performance Optimization ⏳ (next)

### Repos
- HA Integration: `/config/.openclaw/workspace/ai_home_copilot_hacs_repo`
- Core Add-on: `/config/.openclaw/workspace/ha-copilot-repo`

## LERNEN (2026-02-14)
- **NICHT openclaw.json ändern ohne explizite Erlaubnis**
- User hat eigene funktionierende Konfiguration mit `ollamam2/glm-5:cloud`
- Meine "Reparaturen" haben die Config kaputt gemacht
- Immer ERST fragen, DANN vorschlagen
- Testen bevor Änderungen vorgeschlagen werden
- **NIE wieder nachfragen was schon dokumentiert ist - LESEN!**

## LERNEN (2026-02-15)
- **NIEMALS Module löschen ohne Import-Check!** (mood/ war KEIN Duplikat – enthielt Service/Engine/API)
- **tagging/ ist KEIN Duplikat von tags/** - beide Module werden benötigt!
  - `tagging/` = Persistence Layer (TagAssignmentStore, Validierung)
  - `tags/` = Integration Layer (HabitusZone, API)
- **Autopilot-Fehler in v0.4.25/v0.4.26** - mood/ und tagging/ fälschlich gelöscht
- **🚨 2026-02-15 17:24: collective_intelligence/ (+1954 lines) GELÖSCHT!** Wiederhergestellt aus Commit 15fdc45. Pattern wiederholt sich! Working-Directory-Löschungen ohne Commit-Bezug sind gefährlich.
- **Autopilot-Modell-Auswahl funktioniert**: qwen3-coder-next:cloud für Coding-Tasks via Remote-Ollama (http://<OLLAMA-HOST>:11434)
- **Debug Mode v0.8.0**: Kleiner Scope, sicher, hoher User-Value - gute Autopilot-Aufgabe
- **Core Add-on API-Blueprint Pattern**: Blueprint in `copilot_core/api/v1/` erstellen und in `blueprint.py` registrieren
- HA Pipeline Agent ist zur **Beobachtung**, nicht zum Schalten
- Der CoPilot schlägt vor, User entscheidet – immer
- **React Board NICHT anfassen** – vorherige Reparatur-Versuche haben die Config zerstört
- VOLLSTÄNDIGE DOKU: `/config/.openclaw/workspace/docs/PILOTSUITE_VISION.md`
- **🚨 AUTOPILOT DARF NICHT AUTONOM RELEASEN!** (v0.4.25 Disaster: mood/ fälschlich gelöscht)
- **NIEMALS Module löschen ohne Import-Check!** (mood/ war KEIN Duplikat – enthielt Service/Engine/API)

## RELEASE-STRATEGIE (2026-02-15)
- **Automatisch** wenn:
  - Code frei geprüft (Tests grün, Review ok)
  - Home Assistant Docs konform (https://www.home-assistant.io/docs/)
  - CHANGELOG aktualisiert
- **Manuell** bei:
  - Breaking Changes
  - Security-relevanten Änderungen
  - User explizit "Nein" oder "Warten"

## URSPRÜNGLICHER PLAN (AI_HOME_COPILOT_CONCEPT.md)

### Rollenmodell
| Rolle | Verhalten |
|-------|-----------|
| **Agent** | Handelt autonom (nur nach Freigabe) |
| **Autopilot** | Übernimmt komplett (explizit aktiviert) |
| **Berater/CoPilot** | Schlägt vor + begründet |
| **Nutzer** | Entscheidet final |

### Neuronales Modell (Logische Kette)
```
State (objektiv) → Neuron (bewertet Aspekt) → Mood (aggregiert Bedeutung) → Entscheidung
```

**Wichtig:**
- Kein direkter Sprung State → Mood
- Neuronen sind zwingende Zwischenschicht
- Mood kennt keine Sensoren/Geräte - nur Bedeutung

### Mood-Diagnose
- "Warum keine Vorschläge?" → Mood niedrig
- "Warum viele Vorschläge?" → Mood konkurrierend
- "Warum falsche Richtung?" → Falsche Gewichtung
- **Mood ist Debug-Ebene, nicht Werkzeug**

### Praxisdialoge (Beispiele)
1. **Konflikt ohne Auflösung**: "Mehrere Signale sprechen für X und Y. Was möchtest du?"
2. **Vorschlag mit Gegenargumenten**: "Ich würde X vorschlagen, weil Y. Dagegenspricht Z."
3. **Bewusstes Ablehnen**: "Soll ich mir merken, dass das oft nicht passt?"
4. **Rückblick**: "Warum hast du gestern nichts vorgeschlagen?"
5. **Systemzustand**: "Aktuell ist Entspannung moderat, Fokus niedrig..."

### Stakeholder-Matrix
| Aktion | User | CoPilot | System |
|--------|------|---------|--------|
| Vorschlagen | ✔ | ✔ | ✖ |
| Erklären | ✔ | ✔ | ✔ |
| Handeln | ✔ | ⛔/✔* | ✔ |
| Lernen | ✔ | ⛔ | ⛔ |

### Risikoklassen
- **Sicherheit**: Türen/Alarm/Heizung = immer Manual Mode
- **Privatsphäre**: Lokale Auswertung bevorzugen
- **Komplexitätsbremse**: Synapsen-Limits

## Preferences / Operating Principles
- **Sicherheit zuerst.** Bei unklaren oder potenziell riskanten Aktionen lieber nachfragen und konservativ handeln.
- **Enable-by-default Policy:** Neue Funktionen/Entities **standardmäßig aktivieren**, außer sie sind **riskant** (State-Change, destruktiv, oder External Egress) → dann vorher explizit bestätigen lassen.
- **Stetig professioneller werden.** Arbeitsweise iterativ verbessern (Playbooks/Checklisten), Fehler/Erkenntnisse dokumentieren.
- **Kontinuität:** Wichtige gemeinsam erarbeitete Setups/Entscheidungen dauerhaft festhalten (Konfig-Pfade, Geräte/Entity-IDs, Trigger/Workflows).

## Smart Home (Home Assistant)
- Aktionen, die etwas schalten/ändern: **erst bestätigen lassen** („Ja“), Read-only geht sofort.
- Bei Gruppen (z.B. Lichter): **immer Mitglieder/Segmente identifizieren und einzeln setzen**; Gruppen-State kann verzögert sein.
- Zielbild (langfristig): Smart Home soll kontextsensitiv werden (äußere Einflüsse → Verhalten), dabei **stufenweise Autonomie** mit Sicherheits-/Freigabe-Levels.

## Vision & Image Models (Stand 2026-02)

**Dokumentation:** `/config/.openclaw/workspace/VISION_MODELS.md`

### Vor jeder Vision/Bild-Aufgabe:
1. **DOKU LESEN** → `VISION_MODELS.md` konsultieren
2. **Use Case identifizieren** → Passendes Modell wählen
3. **Bei unbekannten Modellen** → Web-Suche nach aktuellen Benchmarks

### Top Vision Models 2026:
| Use Case | Best Model |
|----------|------------|
| Complex Scenes | Gemini 3 Pro |
| Document/OCR | Qwen2.5-VL, Gemma 3 |
| Edge/IoT | Pixtral |
| Video | Qwen2.5-VL |
| Fallback | GPT-5.2, Claude Opus 4.5 |

### Top Image Generation:
| Use Case | Best Model |
|----------|------------|
| Quality | DALL-E 3 |
| Creative | Midjourney v6 |
| Open/Local | Flux, Stable Diffusion 3 |

---

## Fallbacks

### Web-Suche
- **Perplexity API** (primär): ✅ Funktioniert via `pplx` Scripts
  - `/config/.openclaw/workspace/scripts/pplx "query"` - schnell
  - `/config/.openclaw/workspace/scripts/pplx-deep "query"` - balanced
  - `/config/.openclaw/workspace/scripts/pplx-reasoning "query"` - tief
- **Ollama Cloud**: ⚠️ Funktioniert, aber veraltete Daten (Training Cutoff ~2024)
  - `/config/.openclaw/workspace/scripts/ollama-websearch "query"`
  - Nutzt Tool-Calling + Perplexity als Such-Backend
- **Brave API** (web_search Tool): ❌ Token-Header Problem
- **DuckDuckGo HTML**: ❌ Keine zuverlässigen Ergebnisse

---

## Integrationen (Stand 2026-02)
- Telegram Bot: `@HomeClaw1_Bot` (DM-Pairing).
- **Perplexity** direkt via API (`PERPLEXITY_API_KEY` gesetzt):
  - `/config/.openclaw/workspace/scripts/pplx "query"` → `sonar` (schnell)
  - `/config/.openclaw/workspace/scripts/pplx-deep "query"` → `sonar-pro` (balanced)
  - `/config/.openclaw/workspace/scripts/pplx-reasoning "query"` → `sonar-reasoning-pro` (deep)
  - **⚠️ IMMER Perplexity API direkt, NIEMALS via OpenRouter!**
  - Backend-Config (intern in Perplexity): `openrouter/arcee-ai/trinity-large-preview:free + fallbacks`
  - Fallback: `web_search` Tool (Brave Search API) - ⚠️ aktuell Token-Header Problem

## Coding Agents (Stand 2026-02-13)
- **Codex CLI** (`codex`): ✅ Funktioniert
  - Config: `~/.codex/config.toml` (provider=openai, model=gpt-4o)
  - Login: `printenv OPENAI_API_KEY | codex login --with-api-key`
  - Nutzung: `codex exec "Prompt"` (PTY empfohlen)
- **Claude Code** (`claude`): ✅ Funktioniert (v2.1.41)
  - Pfad: `/usr/local/bin/claude` (Symlink zu ~/.local/bin/claude)
  - Nutzung: `claude -p "Prompt"` (PTY empfohlen)
- **Gemini CLI** (`gemini`): ✅ Funktioniert (v0.28.2)
  - Pfad: `/config/.node_global/bin/gemini`
  - Auth: OAuth (Google Account) in `~/.gemini/`
  - Nutzung: `gemini -p "Prompt"` (Headless) oder interaktiv
  - Skill: `gemini-expert` in `/config/.openclaw/workspace/skills/`
  - Features: 1M Token Context, Google Search Grounding, MCP Support
  - Update: `npm install -g @google/gemini-cli@latest`

## Ollama Models (Stand 2026-02-14 21:30)
### Server:
- **Remote**: `http://<OLLAMA-HOST>:11434` ✅ PRIMARY
- **Lokal**: `http://localhost:11434` (Fallback)

### Hauptmodelle (Ollama Cloud):
| Modell | Zweck | Context | Status |
|--------|-------|---------|--------|
| **qwen3-coder-next:cloud** | Coding/Reasoning | 256k | ✅ Best Coding |
| **glm-5:cloud** | Primary - Reasoning | 198k | ✅ Primary |
| **minimax-m2.5:cloud** | Productivity | 200k | ✅ Long Context |
| **kimi-k2.5:cloud** | Vision/Bilder | 131k | ✅ Vision |
| **deepseek-r1:latest** | Reasoning | 131k | ✅ Local Fallback |
| **codellama:latest** | Coding Backup | 16k | ✅ Backup |

### Model-Auswahl für Cron Jobs:
| Task | Modell | Grund |
|------|--------|-------|
| Coding/Implementierung | qwen3-coder-next:cloud | 256k, 80B, Tool-fähig |
| Architektur/Design | qwen3-coder-next:cloud | 256k, Best Reasoning |
| Koordination | minimax-m2.5:cloud | 200k Context |
| Vision/Dashboard | kimi-k2.5:cloud | Vision-fähig |
| Schnelle Tasks | glm-5:cloud | 198k, schnell |

### Priority Chain:
```
qwen3-coder-next:cloud (Coding/Reasoning) → glm-5:cloud (Primary) → minimax-m2.5:cloud (200k) → deepseek-r1:latest (Local)
```

### Spezial:
- **Bilder**: kimi-k2.5:cloud (Vision-Modell)
- **TTS**: OpenAI (bereits konfiguriert)
- **Neue Modelle**: Per API pullen: `curl -X POST http://<OLLAMA-HOST>:11434/api/pull -d '{"name": "modell:tag"}'`

### Konfiguration:
- **CLI**: `./bin/openclaw-cli status|test|models`
- **Config**: `config/models.sh`
- **Env**: `OLLAMA_HOST=http://<OLLAMA-HOST>:11434`

### Usage:
```bash
# Status
export OLLAMA_HOST="http://<OLLAMA-HOST>:11434" && ./bin/openclaw-cli status

# Test
./bin/openclaw-cli test

# API call direkt
curl -s "http://<OLLAMA-HOST>:11434/api/generate" \
  -d '{"model": "glm-5:cloud", "prompt": "Hi", "stream": false}'
```
# Status check
./bin/openclaw-cli status

# Test models
./bin/openclaw-cli test

# Ollama direkt
curl http://localhost:11434/api/generate \
  -d '{"model": "glm-5:cloud", "prompt": "Hi"}'
```

---

## Home Assistant Integration (2026-02-17)

### HA API Zugriff
**Nabu Casa URL:** `https://<REDACTED>.ui.nabu.casa`

**Longlife Token:** (aus .openclaw/openclaw.json HOMEASSISTANT_TOKEN)
```
<REDACTED - HA Long-Lived Access Token>
```

**Verfügbare Lichter:**
- `light.deckenlicht` - Deckenlicht (links + rechts) ✅
- `light.retrolampe` - Retrolampe (muss über HA App gesteuert werden)

### Aktions-Pattern (FUNKTIONIEREND!)
```bash
# Licht ausschalten
curl -X POST "HA_URL/api/services/light/turn_off" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"entity_id": "light.deckenlicht"}'

# Licht einschalten mit Helligkeit
curl -X POST "HA_URL/api/services/light/turn_on" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"entity_id": "light.deckenlicht", "brightness_pct": 69}
```

**Tested & Working (2026-02-17 18:33):**
- Deckenlicht ausgeschaltet ✅
- Deckenlicht auf 69% eingeschaltet ✅

**Status:** HA Integration vollständig aktiv - alle Lichter steuerbar!
