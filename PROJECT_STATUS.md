# PilotSuite — Projekt-Statusbericht & Roadmap

> **Zentrale Projektanalyse** — Aktualisiert 2026-02-17 17:15
> Core v0.9.1-alpha.3 | Integration v0.14.1-alpha.3
> Gilt fuer beide Repos: Home-Assistant-Copilot (Core) + ai-home-copilot-ha (HACS)

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

**Status Alpha Release:** Das System befindet sich in der Alpha-Phase (v0.9.1-alpha.3 / v0.14.1-alpha.3). Alle kritischen Fixes wurden adressiert (Token-Auth, Port-Fix, Error-Isolation, Zone-Integration), Mood Engine API implementiert, HabitusZone Integration aktiviert.

| Metrik | Core Add-on | HACS Integration |
|--------|-------------|------------------|
| Code Quality | 8/10 | 8.5/10 |
| Security | 9/10 | 9/10 |
| HA-Kompatibilitaet | 9/10 | 9/10 |
| Test Coverage | 7/10 | 7/10 |
| Architektur | 9/10 | 9/10 |
| Feature-Vollstaendigkeit | 8.5/10 | 8.5/10 |
| **Gesamt** | **8.5/10** | **8.5/10** |
| **Deployment Ready** | **JA (mit Roadmap)** | **JA (mit Roadmap)** |

**Geschaetzter Aufwand bis v1.0:** 2-3 Wochen fokussierte Entwicklung (P1.3-P1.5)

**Status Update 2026-02-17 17:15:**
- P0.3 Error-Isolation: ✅ Implemented in both repos (runtime.py)
- P1.1 Mood Engine API: ✅ Core Add-on `/api/v1/mood/*` endpoints implemented
- Token-Auth Bug: ✅ Already fixed in v0.9.0-alpha.1 (commit d8be957)
- Port-Konflikt: ✅ Fixed (8099 → 8909) in v0.9.1-alpha.2 / v0.14.1-alpha.2
- HabitusZone Integration: ✅ Aktiviert (use_habitus_zones=True) in v0.14.1-alpha.3
- CHANGELOG.md: ✅ Updated for v0.9.1-alpha.3 / v0.14.1-alpha.3
- PROJECT_STATUS.md: ✅ Updated fuer v0.9.1-alpha.3 / v0.14.1-alpha.3

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

### P1.2: Race Conditions Fix
**Status:** Geplant für nächsten Sprint  
**Datei:** `custom_components/ai_home_copilot/core/modules/events_forwarder.py`  
**Problem:** Thread-safety in Events Forwarder  
**Lösung:** asyncio.Lock für shared state access  
**Aufwand:** 2-4h

### P1.3: Extended User Roles (MUPL)
**Status:** Geplant für nächsten Sprint  
**Datei:** `copilot_core/neurons/mupl.py`  
**Problem:** User Role Binding unvollständig  
**Lösung:** Device Manager, Everyday User, Restricted User Rollen implementieren  
**Aufwand:** 2-3 Tage

### P1.4: Enhanced Delegation Workflows
**Status:** Geplant für nächsten Sprint  
**Problem:** Conflict Resolution UI fehlt  
**Lösung:** Preference Input Workflows, Schedule Automation  
**Aufwand:** 1-2 Tage

### P1.5: API Documentation
**Status:** Geplant für nächsten Sprint  
**Problem:** OpenAPI Spec fehlt  
**Lösung:** OpenAPI Spec für alle Endpoints, API Versioning  
**Aufwand:** 1 Tag

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
| **candidates/store.py** | ⚠️ | 7/10 | Backup fehlt (P1.2) |
| **brain_graph/store.py** | ⚠️ | 7/10 | Pruning zeitbasiert fehlt (P1.2) |

### HACS Integration

| Modul | Status | Bewertung | Notizen |
|-------|--------|-----------|---------|
| **runtime.py** | ✅ | 9/10 | Error-Isolation mit try/except implementiert |
| **mood_module.py** | ✅ | 8/10 | v0.2 vollständig, Core API Integration (simuliert) |
| **events_forwarder.py** | ⚠️ | 7/10 | Race conditions, try/finally für flush logic |
| **button_debug.py** | ⚠️ | 5/10 | 821 Zeilen, 44 functions – Refactoring nötig |
| **entity.py** | ✅ | 9/10 | CopilotBaseEntity korrekt implementiert |

---

## 6. Home Assistant Kompatibilitaet

| Feature | Status | Kompatibilität |
|---------|--------|----------------|
| HACS Integration | ✅ | v0.14.1-alpha.3 |
| Add-on Manifest | ✅ | v0.9.1-alpha.3 |
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

### P1.2: Race Conditions Fix (2-4h)
- Events Forwarder Thread-safety
- Brain Graph Locking
- SQLite WAL Mode

### P1.3: Extended User Roles (2-3 Tage)
- Device Manager Role
- Everyday User Role
- Restricted User Role

### P1.4: Enhanced Delegation Workflows (1-2 Tage)
- Preference Input Workflows
- Conflict Resolution UI

### P1.5: API Documentation (1 Tag)
- OpenAPI Spec für alle Endpoints
- API Versioning Policy

### P2.1: LLM-Integration (2-3 Wochen)
- Ollama Integration
- Local LLM für Automation Suggestions
- Brain Graph + LLM Kombination

---

## 9. Roadmap

### Aktueller Sprint (Woche 1)
| Tag | Task | Status |
|-----|------|--------|
| Di | Token-Auth Fix | ✅ Done |
| Di | Port 8909 | ✅ Done |
| Di | Error-Isolation | ✅ Done (Core + HACS runtime.py) |
| Di | Mood Engine API Endpoints | ✅ Done (zone orchestration) |
| Di | Commit & Push | ✅ Done (bd99fe5, d235766, aad1d2e, c2c9388, 7c02931) |
| Mi | Race Conditions Audit | ✅ Done (P1.2 Start) |
| Do | P0 Abschluss Review | ✅ Done |
| Fr | P1.2 Start (Race Conditions) | ✅ Done |
| Fr | Port-Konflikt Fix | ✅ Done (v0.9.1-alpha.2 / v0.14.1-alpha.2) |
| Fr | HabitusZone Integration | ✅ Done (v0.14.1-alpha.3) |

### Nächste Sprint (Woche 2)
| Tag | Task | Status |
|-----|------|--------|
| Mo | P1.2 Race Conditions Fix | ⏳ Pending |
| Di | P1.2 Race Conditions Fix | ⏳ Pending |
| Mi | P1.3 Extended User Roles | ⏳ Pending |
| Do | P1.3 Extended User Roles | ⏳ Pending |
| Fr | P1.4 Enhanced Delegation | ⏳ Pending |

### Q2 2026 Roadmap
| Woche | Fokus | Ziel |
|-------|-------|------|
| Woche 3 | P1.4 + P1.5 | Delegation Workflows + API Docs |
| Woche 4 | P2.1 LLM Integration | Ollama Core Integration |
| Woche 5 | Testing | Full Test Suite >80% Coverage |
| Woche 6 | v1.0 Release | Stable Release |

---

## 10. Aktionsplan

### Sofort (Diese Woche)

1. **Race Conditions Fix (P1.2)** — Events Forwarder Thread-safety
2. **Extended User Roles (P1.3)** — Device Manager, Everyday User, Restricted User
3. **Enhanced Delegation Workflows (P1.4)** — Preference Input, Conflict Resolution

### Diese Woche

4. **button_debug.py Refactoring** — 821 Zeilen aufteilen auf mehrere Files
5. **Brain Graph Pruning** — zeitbasiertes Pruning implementieren
6. **History-Fetch** — HA Recorder API anbinden

### Naechste Woche

7. **Mood State Persistence** — HA Storage API fuer Mood Data
8. **API Documentation** — OpenAPI Spec fuer alle Endpoints
9. **README.md Sync** — Core Repo mit HACS syncen (PilotSuite Umbenennung)

### Monat 2

10. **LLM Integration** — Ollama Core Integration
11. **Full Test Suite** — Coverage >80%
12. **v1.0 Release** — Stable Release

---

## SWOT-Analyse

| | Positiv | Negativ |
|---|---------|---------|
| **Intern** | **Staerken:** Einzigartige Architektur, Privacy-first, Governance, 80+ Sensoren, Error-Isolation implementiert, 100% lokal | **Schwaechen:** button_debug.py unuebersichtlich (821 Zeilen), kein echtes ML (nur Association Rules), Einzelentwickler |
| **Extern** | **Chancen:** Marktluecke (offen+lokal+lernend), LLM-Revolution, DSGVO/AI-Act, Matter/Thread, HA Core 2026.x nutzt lokale KI | **Risiken:** Google/Amazon Privacy-Features, HA Core AI, Komplexitaet, Nachhaltigkeit, keine echte LLM-Integration |

---

## Fazit

> **PilotSuite ist das einzige Open-Source-System, das Verhaltensmuster im Smart Home automatisch erkennt, erklaert und vorschlaegt — 100% lokal, mit formalem Governance-Modell, Error-Isolation und ohne jemals eigenmaechtig zu handeln.**

Das Konzept ist **dem State of the Art voraus** in den Bereichen Governance, Erklaerbarkeit und Privacy. Die Implementation braucht aber noch **2-3 Wochen kritische Arbeit** fuer P1.3-P1.5 bevor ein stabiles v1.0 Release moeglich ist.

Die groessten Gaps zum State of the Art (LLM-Integration, echtes ML) sind fuer Q2 2026 realistisch adressierbar.

---

*Dieser Bericht wird bei jedem Release aktualisiert. Bei Fragen: siehe VISION.md als Single Source of Truth fuer Architektur und Konzepte.*
