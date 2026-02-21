# PilotSuite — Projekt-Statusbericht & Roadmap

> **Zentrale Projektanalyse** — Aktualisiert 2026-02-21
> Core v4.3.0 | Integration v4.3.0
> Gilt fuer beide Repos: `pilotsuite-styx-core` (Core) + `pilotsuite-styx-ha` (HACS)

---

## Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Gesamtbewertung](#2-gesamtbewertung)
3. [Kritische Fehler (Sofort beheben)](#3-kritische-fehler-sofort-beheben)
4. [Wichtige Probleme (Vor Release beheben)](#4-wichtige-probleme-vor-release-beheben)
5. [Modul-fuer-Modul Bewertung](#5-modul-fuer-modul-bewertung)
6. [Home Assistant Kompatibilitaet](#6-home-assistant-kompatibilitaet)
7. [Wettbewerbsvergleich & State of the Art](#7-wettbewerbsvergleich--state-of-the-art)
8. [Was fehlt fuer v1.0](#8-was-fehlt-fuer-v10)
9. [Roadmap](#9-roadmap)
10. [Aktionsplan](#10-aktionsplan)

---

## 1. Executive Summary

PilotSuite (ehemals AI Home CoPilot) ist ein **einzigartiges Open-Source-Projekt** — es gibt kein vergleichbares System, das Pattern Learning, Privacy-First, Governance und Multi-User-Support in einer lokalen HA-Integration vereint.

**Status v4.3.0:** Alle P1-Meilensteine (P1.1-P1.5) sind abgeschlossen. Race Conditions gefixt, Brain Graph Pruning, History Backfill, MUPL Role API, Delegation API, Mood Persistence und API Docs implementiert. CI/HACS/Hassfest durchgaengig gruen.

| Metrik | Core Add-on | HACS Integration |
|--------|-------------|------------------|
| Code Quality | 9/10 | 9/10 |
| Security | 9/10 | 9/10 |
| HA-Kompatibilitaet | 9.5/10 | 9.5/10 |
| Test Coverage | 7/10 | 7/10 |
| Architektur | 9/10 | 9/10 |
| Feature-Vollstaendigkeit | 9/10 | 9/10 |
| **Gesamt** | **8.8/10** | **8.8/10** |
| **Deployment Ready** | **JA** | **JA** |

**Geschaetzter Aufwand bis v1.0:** 1-2 Wochen (button_debug Refactoring, Test Coverage, LLM-Integration)

**Release-Historie seit v4.0.0:**

| Version | Datum | Highlights |
|---------|-------|------------|
| v4.0.0 | 2026-02-20 | Repo-Rename, Branding, qwen3:4b Standard |
| v4.0.1 | 2026-02-20 | Version-Fix, Branding-Cleanup, Add-on Store Fix |
| v4.1.0 | 2026-02-20 | Race Conditions Fix (Core: threading.Lock/RLock, HA: asyncio.Lock) |
| v4.2.0 | 2026-02-20 | Brain Graph Pruning (Core), History Backfill (HA), OpenAPI Spec |
| v4.2.1 | 2026-02-20 | Hassfest + Config Flow Fix (manifest.json homeassistant key) |
| v4.3.0 | 2026-02-21 | MUPL Role API + Delegation (Core), Mood Persistence (HA) |

**Abgeschlossene Meilensteine:**
- P0.3 Error-Isolation: ✅ (runtime.py, both repos)
- P1.1 Mood Engine API: ✅ (Core `/api/v1/mood/*`)
- P1.2 Race Conditions: ✅ v4.1.0 (threading.Lock, asyncio.Lock, SQLite WAL, RLock)
- P1.3 Extended User Roles: ✅ v4.3.0 (MUPL Role API — Device Manager, Everyday User, Restricted User)
- P1.4 Delegation Workflows: ✅ v4.3.0 (delegate/revoke/list API mit Expiry + Audit)
- P1.5 API Documentation: ✅ v4.2.0 (OpenAPI Spec)
- Brain Graph Pruning: ✅ v4.2.0 (Daemon-Thread, konfigurierbar)
- History Backfill: ✅ v4.2.0 (HA Recorder → Core, einmalig)
- Mood Persistence: ✅ v4.3.0 (HA Storage API, 24h TTL Cache)
- Hassfest/CI: ✅ v4.2.1 (manifest.json Fix)

---

## 2. Gesamtbewertung

### Staerken
- Einzigartige Architektur (Normative Kette, Neuronen, Moods, Brain Graph)
- 100% lokal, Privacy-first — marktdifferenzierend
- Governance-first — kein anderes Open-Source-Projekt hat dies formalisiert
- Error-Isolation implemented (try/except in runtime.py)
- Mood Engine API vollständig (Orchestration, Force, Status)
- 80+ Sensoren, 15+ Dashboard Cards
- Core Add-on Integration mit HACS
- Token-Auth korrekt implementiert (validate_token mit flask_request Instanz)

### Schwächen
- button_debug.py ist unübersichtlich (821 Zeilen, 44 functions) → Refactoring geplant
- Kein echtes ML-Training (nur Association Rules) → Impact: von HA Core 2026.x überholt
- Port-Konflikt war nicht dokumentiert (jetzt in v0.9.1-alpha.2 korrigiert)
- HabitusZone Integration war nicht aktiviert (jetzt in v0.14.1-alpha.3 aktiviert)

---

## 3. Kritische Fehler (Sofort beheben)

### CRITICAL-1: Token-Auth Bug (Core) -- **BEREITS GEFIXT** ✅

**Status:** Bereits in v0.9.0-alpha.1 behoben durch Commit `d8be957` und `bf0c11f`

**Beschreibung:** `require_token()` übergab Klasse statt Instanz → Auth-Bypass möglich  
**Datei:** `copilot_core/api/security.py`  
**Fix:** `validate_token(flask_request)` statt `validate_token(Request)`  
**Status:** ✅ Verifiziert – Code ist korrekt implementiert

### CRITICAL-2: Doppelte Entity Unique-IDs (HACS) -- **BEREITS GEFIXT** ✅

**Status:** BEHOBEN in v0.14.0-alpha.1

**Beschreibung:** Doppelte `unique_id`-Eintraege in button_debug.py und button_system.py  
**Dateien:** `button_debug.py`, `button_system.py`  
**Fix:** Doppelte IDs entfernt, kanonische Quelle ist `button_debug.py`  
**Status:** ✅ Verifiziert

---

## 4. Wichtige Probleme (Vor Release beheben)

### P1.2: Race Conditions Fix — ✅ ERLEDIGT (v4.1.0)
**Datei Core:** `brain_graph/service.py`, `brain_graph/store.py`, `candidates/store.py`, `ingest/event_processor.py`
**Datei HA:** `events_forwarder.py`
**Fix:** threading.Lock/RLock (Core), asyncio.Lock (HA), SQLite WAL+Pragmas

### P1.3: Extended User Roles (MUPL) — ✅ ERLEDIGT (v4.3.0)
**Datei:** `api/v1/user_preferences.py`
**Fix:** REST-Endpoints fuer Role Inference (GET /user/<id>/role, GET /user/roles), RBAC Device Access Check

### P1.4: Enhanced Delegation Workflows — ✅ ERLEDIGT (v4.3.0)
**Datei:** `api/v1/user_preferences.py`, `storage/user_preferences.py`
**Fix:** delegate/revoke/list API mit Expiry-Support, generische _load_extra/_save_extra Persistenz
**Offen:** Conflict Resolution UI (Frontend-Seite)

### P1.5: API Documentation — ✅ ERLEDIGT (v4.2.0)
**Datei:** `docs/openapi.yaml`
**Fix:** OpenAPI Spec fuer alle Endpoints

### Verbleibend vor v1.0:
- **button_debug.py Refactoring** — 821 Zeilen aufteilen
- **Test Coverage** — von 7/10 auf 8+/10
- **Conflict Resolution UI** — Frontend fuer Delegation-Konflikte

---

## 5. Modul-fuer-Modul Bewertung

### Core Add-on

| Modul | Status | Bewertung | Notizen |
|-------|--------|-----------|---------|
| **runtime.py** | ✅ | 9/10 | Error-Isolation mit try/except implementiert |
| **security.py** | ✅ | 9/10 | Token-Auth korrekt (validate_token(flask_request)) |
| **mood.py** | ✅ | 8/10 | API Endpoints /zones/{name}/orchestrate implementiert |
| **mood/orchestrator.py** | ✅ | 9/10 | Mood Engine vollständig implementiert |
| **neurons/manager.py** | ✅ | 9/10 | Energy + UniFi Neurons integriert |
| **candidates/store.py** | ✅ | 9/10 | RLock + Backup (.bak) implementiert (v4.1.0) |
| **brain_graph/store.py** | ✅ | 9/10 | Write-Lock, WAL, Pruning-Daemon (v4.1.0+v4.2.0) |
| **user_preferences.py** | ✅ | 9/10 | Role API + Delegation + Extra-Storage (v4.3.0) |

### HACS Integration

| Modul | Status | Bewertung | Notizen |
|-------|--------|-----------|---------|
| **runtime.py** | ✅ | 9/10 | Error-Isolation mit try/except implementiert |
| **mood_module.py** | ✅ | 8/10 | v0.2 vollständig, Core API Integration (simuliert) |
| **events_forwarder.py** | ✅ | 9/10 | asyncio.Lock (v4.1.0), Race Condition behoben |
| **mood_store.py** | ✅ | 9/10 | HA Storage API Cache, 24h TTL (v4.3.0) |
| **mood_context_module.py** | ✅ | 9/10 | Pre-Load + Persist + Fallback (v4.3.0) |
| **history_backfill.py** | ✅ | 8/10 | Einmalige 24h Recorder-Sync (v4.2.0) |
| **button_debug.py** | ⚠️ | 5/10 | 821 Zeilen, 44 functions – Refactoring nötig |
| **entity.py** | ✅ | 9/10 | CopilotBaseEntity korrekt implementiert |

---

## 6. Home Assistant Kompatibilitaet

| Feature | Status | Kompatibilität |
|---------|--------|----------------|
| HACS Integration | ✅ | v0.14.1-alpha.1 |
| Add-on Manifest | ✅ | v0.9.1-alpha.1 |
| Config Flow | ✅ | OptionsFlow implementiert |
| Entity Registry | ✅ | eindeutige unique_ids |
| Services | ✅ | mood_orchestrate_zone, mood_orchestrate_all |
| Dashboard Cards | ✅ | Brain Graph, Mood, Neurons Cards |

---

## 7. Wettbewerbsvergleich & State of the Art

### HA Core 2026.x
- **Lokale KI:** Whisper/Piper, Ollama Integration
- **Local-first:** Same principle – CoPilot ist konkurrenzfähig
- **LLM-Integration:** HA Core nutzt zunehmend LLMs für Automation Suggestions

### CoPilot USP (Unique Selling Proposition)
- **100% lokal:** Keine Cloud, keine externen API-Calls
- **Governance-first:** Vorschläge vor Aktionen, Human-in-the-Loop
- **Pattern Learning:** Habitus – Verhaltensmuster erkennen
- **Multi-User Support:** MUPL mit Differential Privacy

### CoPilot Lücken
- **Kein echtes ML:** Nur Association Rules (nicht Neural Networks)
- **LLM-Integration:** Fehlt – HA Core nutzt zunehmend LLMs
- **Performance:** Brain Graph Queries langsam bei >1000 Nodes

---

## 8. Was fehlt fuer v1.0

### ~~P1.2: Race Conditions Fix~~ ✅ ERLEDIGT (v4.1.0)
### ~~P1.3: Extended User Roles~~ ✅ ERLEDIGT (v4.3.0)
### ~~P1.4: Enhanced Delegation Workflows~~ ✅ ERLEDIGT (v4.3.0)
### ~~P1.5: API Documentation~~ ✅ ERLEDIGT (v4.2.0)

### Verbleibend:

### R1: button_debug.py Refactoring (4-6h)
- 821 Zeilen aufteilen auf logische Module
- Entity-Registrierung vereinfachen

### R2: Test Coverage (1-2 Tage)
- Unit Tests fuer neue Endpoints (Role, Delegation)
- Integration Tests fuer Mood Persistence
- Ziel: >80% Coverage

### R3: Conflict Resolution UI (1 Tag)
- Frontend-Seite fuer Delegation-Konflikte
- Preference Input Workflows

### P2.1: LLM-Integration (2-3 Wochen)
- Ollama Integration
- Local LLM fuer Automation Suggestions
- Brain Graph + LLM Kombination

---

## 9. Roadmap

### Abgeschlossen
| Release | Task | Status |
|---------|------|--------|
| v4.0.0 | Repo-Rename, Branding, qwen3:4b | ✅ Done |
| v4.0.1 | Version-Fix, Branding-Cleanup | ✅ Done |
| v4.1.0 | P1.2 Race Conditions Fix (Core + HA) | ✅ Done |
| v4.2.0 | Brain Graph Pruning + History Backfill + OpenAPI | ✅ Done |
| v4.2.1 | Hassfest + Config Flow Fix | ✅ Done |
| v4.3.0 | MUPL Role API + Delegation + Mood Persistence | ✅ Done |

### Naechster Sprint
| Task | Prioritaet | Status |
|------|------------|--------|
| button_debug.py Refactoring (R1) | Hoch | ⏳ Pending |
| Test Coverage >80% (R2) | Hoch | ⏳ Pending |
| Conflict Resolution UI (R3) | Mittel | ⏳ Pending |

### Q2 2026 Roadmap
| Woche | Fokus | Ziel |
|-------|-------|------|
| KW9 | R1 + R2 | Refactoring + Tests |
| KW10 | R3 + P2.1 Start | Conflict UI + LLM-Vorbereitung |
| KW11-12 | P2.1 LLM Integration | Ollama Core Integration |
| KW13 | v1.0 Release | Stable Release |

---

## 10. Aktionsplan

### Sofort (Naechster Sprint)

1. **button_debug.py Refactoring (R1)** — 821 Zeilen aufteilen auf logische Module
2. **Test Coverage (R2)** — Unit Tests fuer Role/Delegation/Mood Endpoints, Ziel >80%
3. **Conflict Resolution UI (R3)** — Frontend fuer Delegation-Konflikte

### Naechste Woche

4. **LLM Integration (P2.1)** — Ollama Core Integration vorbereiten
5. **README.md Sync** — Beide Repos auf aktuellen Stand bringen

### Monat 2

6. **LLM Integration** — Ollama + Brain Graph Kombination
7. **v1.0 Release** — Stable Release

---

## SWOT-Analyse

| | Positiv | Negativ |
|---|---------|---------|
| **Intern** | **Staerken:** Einzigartige Architektur, Privacy-first, Governance, 80+ Sensoren, Error-Isolation implementiert, 100% lokal | **Schwaechen:** button_debug.py unuebersichtlich (821 Zeilen), kein echtes ML (nur Association Rules), Einzelentwickler |
| **Extern** | **Chancen:** Marktluecke (offen+lokal+lernend), LLM-Revolution, DSGVO/AI-Act, Matter/Thread, HA Core 2026.x nutzt lokale KI | **Risiken:** Google/Amazon Privacy-Features, HA Core AI, Komplexitaet, Nachhaltigkeit, keine echte LLM-Integration |

---

## Fazit

> **PilotSuite ist das einzige Open-Source-System, das Verhaltensmuster im Smart Home automatisch erkennt, erklaert und vorschlaegt — 100% lokal, mit formalem Governance-Modell, Error-Isolation und ohne jemals eigenmaechtig zu handeln.**

Das Konzept ist **dem State of the Art voraus** in den Bereichen Governance, Erklaerbarkeit und Privacy. Alle P1-Meilensteine sind abgeschlossen — es fehlen noch **Refactoring, Tests und LLM-Integration** fuer ein stabiles v1.0 Release.

Die groessten Gaps zum State of the Art (LLM-Integration, echtes ML) sind fuer Q2 2026 realistisch adressierbar.

---

*Dieser Bericht wird bei jedem Release aktualisiert. Bei Fragen: siehe VISION.md als Single Source of Truth fuer Architektur und Konzepte.*
