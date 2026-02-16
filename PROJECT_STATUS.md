# AI Home CoPilot — Projekt-Statusbericht & Roadmap

> **Zentrale Projektanalyse** — Erstellt 2026-02-16
> Core v0.8.8 | Integration v0.13.5
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

AI Home CoPilot ist ein **einzigartiges Open-Source-Projekt** — es gibt kein vergleichbares System, das Pattern Learning, Privacy-First, Governance und Multi-User-Support in einer lokalen HA-Integration vereint.

**Aber:** Das System ist **nicht deployment-ready**. Es gibt kritische Security-Bugs (gebrochene Token-Auth), architektonische Schwaechen (fehlende Error Isolation), und HACS-Blocker (doppelte Entity-IDs).

| Metrik | Core Add-on | HACS Integration |
|--------|-------------|------------------|
| Code Quality | 6.5/10 | 7/10 |
| Security | 2/10 (KRITISCH) | 7/10 |
| HA-Kompatibilitaet | 7/10 | 6/10 (Entity-ID-Blocker) |
| Test Coverage | 6/10 | 6/10 |
| Architektur | 8/10 | 8/10 |
| Feature-Vollstaendigkeit | 7/10 | 8/10 |
| **Gesamt** | **6/10** | **7/10** |
| **Deployment Ready** | **NEIN** | **NEIN** |

**Geschaetzter Aufwand bis v1.0:** 4-6 Wochen fokussierte Entwicklung

---

## 2. Gesamtbewertung

### Staerken
- Einzigartige Architektur (Normative Kette, Neuronen, Moods, Brain Graph)
- 100% lokal, Privacy-first — marktdifferenzierend
- Governance-first — kein anderes Open-Source-Projekt hat dies formalisiert
- Umfangreiche Sensorik (80+ Sensoren) und Dashboard-Integration
- Dual-Repo-Architektur ermoeglicht Flexibilitaet
- 521+ Tests im Core, 346+ in HACS
- Ausgereiftes Event-Forwarding mit Rate Limiting, Dedup, PII-Redaktion

### Schwaechen
- Gebrochene Token-Authentifizierung im Core (Security-Bypass)
- Doppelte Entity-IDs in der HACS-Integration (HACS-Rejection)
- Keine Error-Isolation im Modul-System (ein Modul-Crash killt alles)
- Mood Engine unvollstaendig implementiert
- Kein echtes ML-Training (nur Association Rules)
- History-Fetch nicht implementiert (nur Event-Buffer)
- Race Conditions in Events Forwarder und Brain Graph

---

## 3. Kritische Fehler (Sofort beheben)

### CRITICAL-1: Gebrochene Token-Authentifizierung (Core)

**Datei:** `copilot_core/api/security.py:84`

```python
# BUG: Request ist eine Klasse, keine Instanz!
def require_token(f):
    def decorated_function(*args, **kwargs):
        if not validate_token(Request):  # <-- Uebergibt Klasse statt request-Instanz
            return jsonify(...)
        return f(*args, **kwargs)
```

**Zusaetzlich:** In `events_ingest.py:66` und `tag_system.py` wird `require_token(request)` als Funktion aufgerufen statt als Decorator. `require_token()` gibt immer eine Funktion zurueck (truthy) → **Auth-Bypass**.

**Impact:** Alle geschuetzten Endpoints sind ungeschuetzt. Security-Bypass moeglich.
**Fix-Aufwand:** 30 Minuten

### CRITICAL-2: Doppelte Entity Unique-IDs (HACS)

**Dateien:** `button_debug.py`, `button_devlog.py`, `button_graph.py`, `button_safety.py`, `button_other.py`

9+ Button-Entities haben identische `unique_id` ueber mehrere Dateien:
- `ai_home_copilot_analyze_logs` in `button_debug.py` UND `button_other.py`
- `ai_home_copilot_publish_brain_graph_viz` in `button_graph.py` UND `button_debug.py`
- `ai_home_copilot_rollback_last_fix` in `button_safety.py` UND `button_debug.py`
- u.v.m.

**Impact:** HA weigert sich Entities zu erstellen. HACS-Distribution blockiert.
**Fix-Aufwand:** 2-4 Stunden (Refactoring)

### CRITICAL-3: Keine Error-Isolation im Modul-Setup (HACS)

**Datei:** `core/runtime.py`

```python
async def async_setup_entry(self, entry, modules):
    for name in modules:
        mod = self.registry.create(name)
        await mod.async_setup_entry(ctx)  # <-- Kein try/except!
```

**Impact:** Wenn EIN Modul beim Setup fehlschlaegt, crasht die GESAMTE Integration.
**Fix-Aufwand:** 15 Minuten

### CRITICAL-4: Race Condition in Events Forwarder (HACS)

**Datei:** `core/modules/events_forwarder.py:224`

```python
st.flushing = True
# ... await HTTP-Request (kann fehlschlagen)
st.flushing = False  # <-- Wird nie erreicht bei Exception → Deadlock
```

**Impact:** Nach einem fehlgeschlagenen HTTP-Request wird `flushing` nie zurueckgesetzt → Event-Pipeline blockiert permanent.
**Fix-Aufwand:** 5 Minuten (try/finally)

---

## 4. Wichtige Probleme (Vor Release beheben)

### Core Add-on

| # | Problem | Datei | Aufwand |
|---|---------|-------|---------|
| I-1 | Brain Graph: Keine Transaction-Isolation (SQLite Race Conditions) | `brain_graph/store.py` | 2h |
| I-2 | Brain Graph: Non-deterministic Pruning (random statt time-based) | `brain_graph/service.py:98` | 1h |
| I-3 | Habitus Miner: Zone-Filtering unvollstaendig | `habitus_miner/mining.py:72` | 1h |
| I-4 | Mood Engine: Scoring-Logik unvollstaendig | `mood/engine.py:100-150` | 2h |
| I-5 | Event Processor: Kein Rollback bei Partial Failure | `ingest/event_processor.py:37` | 2h |
| I-6 | CandidateStore: Silentes Verwerfen bei Korruption | `candidates/store.py:94` | 1h |
| I-7 | Fehlende Config-Validation (max_nodes=0 moeglich) | `core_setup.py:73` | 1h |

### HACS Integration

| # | Problem | Datei | Aufwand |
|---|---------|-------|---------|
| I-8 | Background Tasks nicht supervised (Memory Leaks) | Mehrere Module | 4h |
| I-9 | Sensor unique_id Coverage unklar (77+ Klassen) | `sensors/*.py` | 3h |
| I-10 | Code-Duplikation in Button-Modulen | `button_debug.py` (821 Zeilen) | 4h |
| I-11 | Deprecated v1 Code noch aktiv | `habitus_zones_store.py` | 2h |
| I-12 | Dashboard Cards nicht registriert | `dashboard_cards/` | 2h |
| I-13 | Fehlende Error-Handling in `__init__.py` | `__init__.py:214-262` | 1h |
| I-14 | Idempotency-Dict waechst unbegrenzt | `events_forwarder.py:205` | 1h |

---

## 5. Modul-fuer-Modul Bewertung

### Core Add-on Module

| Modul | Score | Status | Naechster Schritt |
|-------|-------|--------|-------------------|
| **Brain Graph** | 8/10 | Funktional, Race Conditions | Transaction Isolation hinzufuegen |
| **Habitus Miner** | 7/10 | Funktional, Zone-Filtering lueckenhaft | Zone-Validation, konfigurierbare Thresholds |
| **Mood Engine** | 5/10 | Unvollstaendig | Scoring-Logik fertigstellen |
| **Candidates** | 8/10 | Solide | Backup bei Korruption |
| **Neurons** | 6/10 | Funktional, globaler State | Dependency Injection |
| **Event Processing** | 7/10 | Funktional, kein Rollback | Transaction-Support |
| **API Security** | 2/10 | GEBROCHEN | Sofort fixen |
| **Knowledge Graph** | 7/10 | Funktional | Mehr Query-Operationen |
| **Vector Store** | 7/10 | Funktional | ML-Integration |
| **Tag System** | 8/10 | Solide | - |
| **Search** | 7/10 | Funktional | Fuzzy Search |

### HACS Integration Module (22 Core-Module)

| Modul | Score | Status | Naechster Schritt |
|-------|-------|--------|-------------------|
| **Events Forwarder** | 8/10 | Feature-reich, Race Condition | try/finally Fix |
| **Habitus Miner** | 7/10 | Funktional | History-Fetch implementieren |
| **Candidate Poller** | 8/10 | Solide | - |
| **Brain Graph Sync** | 7/10 | Funktional, Task-Cleanup pruefen | Task-Supervision |
| **Mood Module** | 7/10 | Funktional | Tiefere Core-Integration |
| **Mood Context** | 7/10 | Funktional | - |
| **Media Context** | 7/10 | Funktional | - |
| **Energy Context** | 6/10 | Basis | Scheduling-Algorithmen |
| **Weather Context** | 7/10 | Funktional | - |
| **UniFi Module** | 7/10 | Funktional | - |
| **ML Context** | 5/10 | Basis, kein echtes ML | TFLite/ONNX Integration |
| **Knowledge Graph Sync** | 7/10 | Funktional, Task-Cleanup fehlt | Task-Supervision |
| **Voice Context** | 6/10 | Basis | HA Assist Integration |
| **Character Module** | 7/10 | Funktional | LLM-Integration |
| **Quick Search** | 8/10 | Solide | - |
| **Home Alerts** | 7/10 | Funktional | - |
| **Camera Context** | 6/10 | Basis | Frigate-Integration |
| **Dev Surface** | 7/10 | Debugging-Tools | - |
| **Legacy** | 5/10 | Abwaertskompatibilitaet | Entfernen wenn moeglich |
| **Performance Scaling** | 6/10 | Basis | Auto-Scaling |
| **Ops Runbook** | 6/10 | Basis | - |

---

## 6. Home Assistant Kompatibilitaet

### Manifest.json: OK
- domain, version, config_flow, dependencies, iot_class — alles korrekt
- Semantic Versioning — korrekt

### Config Flow: OK (nach Refactoring)
- Modulare Struktur (6 Dateien) — gut
- Translations (EN + DE) — vorhanden
- Options Flow — implementiert

### HACS Compliance: BLOCKIERT
- hacs.json — vorhanden
- README — aktualisiert
- **BLOCKER:** Doppelte Entity-IDs muessen behoben werden

### Platform Registration: TEILWEISE
- sensor, binary_sensor, button, text, number, select — registriert
- **Fehlend:** switch-Platform (manche Toggle-Buttons waeren besser als Switches)

### Sensor-Qualitaet: PRUEFUNG NOETIG
- 89 Sensor-Instanziierungen, 82+ Klassen
- Basis-Entity nutzt CoordinatorEntity korrekt
- unique_id Coverage muss auditiert werden

---

## 7. Wettbewerbsvergleich & State of the Art

### Marktpositionierung

```
                    Lernfaehigkeit
                         |
           Google Nest   |   Amazon Alexa
           (Cloud+ML)    |   (Cloud+ML)
                         |
    ─────────────────────┼─────────────────────
    Geschlossen          |              Offen
                         |
           Apple Home    |   ★ AI Home CoPilot
           (lokal,       |   (lokal, lernend,
            begrenzt)    |    offen, governance)
                         |
                    Statisch
```

**AI Home CoPilot besetzt den einzigen leeren Quadranten: offen + lernfaehig + lokal.**

### Feature-Vergleich mit Kommerziellen Systemen

| Feature | CoPilot | Google Nest | Amazon Alexa | Apple Home | SmartThings |
|---------|---------|-------------|--------------|------------|-------------|
| Pattern Learning | Ja (Habitus) | Ja | Ja (Hunches) | Minimal | Ja |
| 100% Lokal | **Ja** | Nein | Nein | Teilweise | Nein |
| Human-in-the-Loop | **Ja (Kern)** | Nein | Teilweise | Nein | Nein |
| Multi-User | Ja (MUPL) | Ja | Ja | Ja | Teilweise |
| Mood/Stimmung | **Ja (3D)** | Nein | Nein | Nein | Nein |
| Knowledge Graph | **Ja** | Intern | Intern | Nein | Nein |
| Erklaerbarkeit | **Ja (Brain Graph)** | Minimal | Minimal | Nein | Minimal |
| Offene API | **Ja (37 Endpoints)** | Eingeschraenkt | Eingeschraenkt | Sehr eingeschraenkt | Ja |
| Datensouveraenitaet | **100% User** | Google | Amazon | Apple | Samsung |

### Vergleich mit HA-Oekosystem

**Kein vergleichbares Open-Source-Projekt** vereint:
- Automatische Mustererkennung aus Verhalten
- Vorschlagssystem mit Governance
- Multi-User-Praeferenzlernen
- Neuronales Bewertungssystem + Knowledge Graph
- 100% lokal

### Alleinstellungsmerkmale (USP)

1. **Normative Kette** (States → Neuronen → Moods → Synapsen → Vorschlaege) — formalisierte Entscheidungskette
2. **Mood Engine** (Comfort/Joy/Frugality) — multidimensionale Stimmungsbewertung
3. **Brain Graph mit Decay** — visueller, zeitlich zerfallender Zustandsgraph
4. **Risikoklassen** (Sicherheit → Komfort → Info) — formalisierte Autonomie-Abstufung
5. **Ethics & Governance als Kernprinzip** — dokumentiert und implementiert

### Technologie-Luecken zum State of the Art

| Bereich | State of the Art | CoPilot Status | Prioritaet |
|---------|-----------------|----------------|------------|
| **LLM-Integration** | Lokale LLMs (Ollama, llama.cpp) | Fehlt | HOCH |
| **On-Device ML** | TFLite, ONNX, Coral TPU | Minimal | HOCH |
| **Sprachsteuerung** | HA Assist + Whisper/Piper | Voice-Sensor vorhanden | MITTEL |
| **Energieoptimierung** | LSTM-Prognosen, Load Shifting | Basis-Neuron | MITTEL |
| **Anomalie-Erkennung** | Isolation Forest, Autoencoder | Basis-Sensor | MITTEL |
| **Reinforcement Learning** | State of the Art fuer Steuerung | Nicht implementiert | MITTEL |

---

## 8. Was fehlt fuer v1.0

### Must-Have (Release Blocker)

- [ ] Token-Authentifizierung fixen (Core)
- [ ] Doppelte Entity-IDs entfernen (HACS)
- [ ] Error-Isolation im Modul-System (HACS)
- [ ] Race Condition in Events Forwarder (HACS)
- [ ] Brain Graph Transaction-Isolation (Core)
- [ ] Mood Engine Scoring fertigstellen (Core)
- [ ] Sensor unique_id Audit (HACS)
- [ ] Button-Module konsolidieren (HACS)
- [ ] Background Task Supervision (HACS)
- [ ] Config Validation (Core)
- [ ] History-Fetch implementieren (HACS Habitus Miner)
- [ ] Deprecated v1 Code entfernen (HACS)

### Should-Have (v1.0 Qualitaet)

- [ ] Security Test Suite (Core)
- [ ] Auth-Tests fuer alle geschuetzten Endpoints
- [ ] Brain Graph Pruning zeitbasiert machen
- [ ] CandidateStore Backup/Recovery
- [ ] Idempotency-Dict TTL Cleanup
- [ ] Dashboard Cards dokumentieren oder auto-registrieren
- [ ] switch-Platform hinzufuegen
- [ ] HACS Pre-Validation bestehen

### Nice-to-Have (v1.0+)

- [ ] Lokale LLM-Integration (Ollama)
- [ ] TFLite/ONNX ML-Inference
- [ ] HA Assist Voice-Integration
- [ ] Energieoptimierung mit Scheduling
- [ ] Reinforcement Learning fuer Steuerung
- [ ] Community-Dokumentation (Contributing Guide)

---

## 9. Roadmap

### Phase 1: Critical Fixes (Woche 1-2)

**Ziel:** Deployment-Ready machen

| Aufgabe | Repo | Aufwand | Prioritaet |
|---------|------|---------|------------|
| Token-Auth fixen | Core | 30min | P0 |
| Auth-Decorator korrekt verwenden | Core | 30min | P0 |
| Auth-Tests schreiben | Core | 2h | P0 |
| Doppelte Entity-IDs entfernen | HACS | 4h | P0 |
| Error-Isolation in runtime.py | HACS | 15min | P0 |
| Events Forwarder Race Condition | HACS | 5min | P0 |
| Brain Graph Transactions | Core | 2h | P1 |
| Mood Engine fertigstellen | Core | 2h | P1 |
| Config Validation | Core | 1h | P1 |

### Phase 2: Stability & Quality (Woche 3-4)

**Ziel:** Produktionsqualitaet erreichen

| Aufgabe | Repo | Aufwand | Prioritaet |
|---------|------|---------|------------|
| Sensor unique_id Audit | HACS | 3h | P1 |
| Button-Module konsolidieren | HACS | 4h | P1 |
| Background Task Supervision | HACS | 4h | P1 |
| Deprecated v1 Code entfernen | HACS | 2h | P1 |
| History-Fetch implementieren | HACS | 4h | P1 |
| Brain Graph Pruning zeitbasiert | Core | 1h | P2 |
| CandidateStore Backup | Core | 1h | P2 |
| Idempotency Cleanup | HACS | 1h | P2 |
| Security Test Suite | Core | 4h | P2 |

### Phase 3: v1.0 Release (Woche 5-6)

**Ziel:** Erste stabile Version veroeffentlichen

| Aufgabe | Repo | Aufwand | Prioritaet |
|---------|------|---------|------------|
| HACS Pre-Validation | HACS | 2h | P1 |
| Dashboard Cards registrieren | HACS | 2h | P2 |
| switch-Platform | HACS | 2h | P2 |
| Full Test Suite Green | Beide | 4h | P1 |
| Release Notes | Beide | 2h | P1 |
| Version 1.0.0 Tag | Beide | 1h | P1 |

### Phase 4: Next-Gen Features (Q2 2026)

| Feature | Aufwand | Impact |
|---------|---------|--------|
| Lokale LLM-Integration (Ollama) | 2 Wochen | Sehr hoch |
| TFLite/ONNX ML-Inference | 2 Wochen | Hoch |
| HA Assist Voice-Integration | 1 Woche | Hoch |
| Energieoptimierung mit Scheduling | 2 Wochen | Hoch |
| LSTM/Transformer Zeitreihen | 3 Wochen | Hoch |

### Phase 5: Zukunft (Q3+ 2026)

| Feature | Beschreibung |
|---------|-------------|
| Reinforcement Learning | Adaptive Steuerung statt Rules |
| Differential Privacy verbessern | Collective Intelligence haerten |
| Digital Twin | Simulationsumgebung fuer Automationen |
| Multi-Agent RL | Autonome Agenten pro Raum |
| Graph Neural Networks | Brain Graph mit ML verbinden |
| Community + HACS Default | In den HACS Default-Store kommen |

---

## 10. Aktionsplan

### Sofort (Diese Woche)

1. **Core `security.py` fixen** — `Request` → `request` (Flask-Instanz)
2. **`events_ingest.py` + `tag_system.py` fixen** — `validate_token(request)` statt `require_token(request)`
3. **HACS `runtime.py` fixen** — try/except um Modul-Setup
4. **HACS `events_forwarder.py` fixen** — try/finally um Flush-Logic
5. **Tests schreiben fuer Auth-Fixes**

### Diese Woche

6. **Entity-ID-Audit** — Alle doppelten unique_ids finden und fixen
7. **Sensor unique_id Audit** — Alle 82+ Sensor-Klassen pruefen
8. **button_debug.py aufloesen** — Duplikate entfernen, eine Quelle der Wahrheit

### Naechste Woche

9. **Brain Graph Transactions** — SQLite WAL-Mode + explizite Transaktionen
10. **Mood Engine fertigstellen** — Scoring-Algorithmus implementieren
11. **History-Fetch** — HA Recorder API anbinden fuer Habitus Miner
12. **Background Tasks** — Task-Registry mit Cancel-on-Unload

### Monat 2

13. **HACS Pre-Validation bestehen**
14. **v1.0.0 Release vorbereiten**
15. **LLM-Integration evaluieren** (Ollama + Brain Graph)

---

## SWOT-Analyse

| | Positiv | Negativ |
|---|---------|---------|
| **Intern** | **Staerken:** Einzigartige Architektur, Privacy-first, Governance, 80+ Sensoren, Ethik als Kernprinzip | **Schwaechen:** Security-Bugs, fehlende Error-Isolation, kein echtes ML, Einzelentwickler |
| **Extern** | **Chancen:** Marktluecke (offen+lokal+lernend), LLM-Revolution, DSGVO/AI-Act, Matter/Thread | **Risiken:** Google/Amazon Privacy-Features, HA Core AI, Komplexitaet, Nachhaltigkeit |

---

## Fazit

> **AI Home CoPilot ist das einzige Open-Source-System, das Verhaltensmuster im Smart Home automatisch erkennt, erklaert und vorschlaegt — 100% lokal, mit formalem Governance-Modell und ohne jemals eigenmaechtig zu handeln.**

Das Konzept ist **dem State of the Art voraus** in den Bereichen Governance, Erklaerbarkeit und Privacy. Die Implementation braucht aber noch **4-6 Wochen kritische Arbeit** bevor ein stabiles v1.0 Release moeglich ist. Die groessten Gaps zum State of the Art (LLM-Integration, echtes ML) sind fuer Q2 2026 realistisch adressierbar.

---

*Dieser Bericht wird bei jedem Release aktualisiert. Bei Fragen: siehe VISION.md als Single Source of Truth fuer Architektur und Konzepte.*
