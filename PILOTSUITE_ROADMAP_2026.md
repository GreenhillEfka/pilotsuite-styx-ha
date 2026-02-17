# PilotSuite Roadmap 2026 - Vollständiger Projektplan

> Erstellt: 2026-02-17
> Ziel: v1.0 Release in Q2 2026
> Status: Alpha v0.9.0-alpha.1 / v0.14.0-alpha.1

---

## 🎯 Übersicht

| Phase | Zeitraum | Fokus | Ziel |
|-------|----------|-------|------|
| **P0 - Critical** | Feb 2026 | Security & Stability | Production-ready Security |
| **P1 - Foundation** | Mär 2026 | Core Features | v0.15.x Beta |
| **P2 - Enhancement** | Apr 2026 | ML & Intelligence | v0.16.x |
| **P3 - Polish** | Mai 2026 | UX & Performance | v0.17.x |
| **P4 - Release** | Jun 2026 | v1.0 | Stable Release |

---

## 🔴 P0 - Critical Fixes (Diese Woche)

### P0.1 ✅ Token-Auth Fix (ERLEDIGT)
- [x] `@require_token` Decorator korrekt implementieren
- [x] `events_ingest.py` migriert
- [x] `tag_system.py` migriert
- [x] `main.py` migriert
- [x] Python Syntax validiert

### P0.2 Port-Korrektur 8099→8909 (ERLEDIGT)
- [x] Dockerfile angepasst
- [x] config.json aktualisiert
- [x] main.py angepasst

### P0.3 Error-Isolation (ERLEDIGT ✅)
- [x] `core/runtime.py` Modul-Setup absichern
- [x] Try/except Wrapper für jedes Modul (already implemented)
- [x] Graceful degradation bei Modul-Crashes
- [x] Logging für Modul-Fehler (`_LOGGER.exception`)
- **Status:** Beide Repos (Core + HACS) ✅
- **Note:** HACS `runtime.py` (lines 40-50) hat bereits try/except mit `_LOGGER.exception`

### P0.4 Commit & Push (ERLEDIGT ✅)
- [x] P0.3 Error-Isolation commiten
- [x] P1.1 Mood Engine API endpoints hinzugefügt
- [x] Tag v0.9.1-alpha.1 erstellen
- [x] Push zu origin/main
- **Commit:** `bd99fe5` - "feat(mood): add zone orchestration endpoints + error isolation"

---

## 🟡 P1 - Foundation (März 2026)

### P1.1 Mood Engine Completion (TEILWEISE ERLEDIGT ✅)
- [x] Mood-Berechnung vervollständigen (Engine + Scoring)
- [x] API Endpoints für Zone Orchestration (`/zones/{name}/orchestrate`)
- [x] Mood ↔ Neuron Integration (MoodEngine + NeuronManager)
- [ ] Mood-State Persistence implementieren (HA Storage API)
- [ ] Mood-Transition Events (Event Dispatcher)
- **Status:** Core Add-on API fertig, HACS Module ready für Integration
- **Aufwand:** ~4h (geplant: 1-2 Tage)

### P1.2 Race Conditions Fix
- [ ] Events Forwarder Thread-safety
- [ ] Brain Graph Locking
- [ ] SQLite WAL Mode
- **Aufwand:** 2-4h

### P1.3 Extended User Roles (MUPL)
- [ ] Device Manager Role
- [ ] Everyday User Role
- [ ] Restricted User Role
- [ ] Role-Based Access Control (RBAC)
- **Aufwand:** 2-3 Tage

### P1.4 Enhanced Delegation Workflows
- [ ] Preference Input Workflows
- [ ] Conflict Resolution UI
- [ ] Schedule Automation
- **Aufwand:** 1-2 Tage

### P1.5 API Documentation
- [ ] OpenAPI Spec für alle Endpoints
- [ ] API Versioning
- [ ] Breaking Changes Policy
- **Aufwand:** 1 Tag

---

## 🟢 P2 - Enhancement (April 2026)

### P2.1 ANN Energy Prediction
- [ ] TensorFlow/PyTorch Integration
- [ ] Modell-Training Pipeline
- [ ] Prediction API
- [ ] Evaluation Metrics
- **Aufwand:** 5-7 Tage
- **Impact:** Hoch (8-16% Energieeinsparung)

### P2.2 MCP Integration (Model Context Protocol)
- [ ] MCP Server Implementierung
- [ ] Tool Discovery
- [ ] Context Injection
- [ ] Plugin Architecture
- **Aufwand:** 3-4 Tage
- **Impact:** Hoch (Ecosystem-Kompatibilität)

### P2.3 UWB Sensor Integration
- [ ] UWB Anchor Discovery
- [ ] Indoor Positioning
- [ ] Zone-Precise Localization
- [ ] Human Activity Recognition (HAR)
- **Aufwand:** 4-5 Tage

### P2.4 Semantic Ontologies
- [ ] Ontology-Engine
- [ ] Fuzzy Personas
- [ ] Rule Reasoning
- [ ] Context Inference
- **Aufwand:** 3-4 Tage

---

## 🔵 P3 - Polish (Mai 2026)

### P3.1 Performance Optimization
- [ ] QueryCache Tuning
- [ ] Connection Pool Optimization
- [ ] Async Operations
- [ ] Memory Profiling
- **Aufwand:** 2-3 Tage

### P3.2 Dashboard Improvements
- [ ] Brain Graph Visualization v2
- [ ] Real-time Updates
- [ ] Mobile Optimization
- [ ] Custom Themes
- **Aufwand:** 3-4 Tage

### P3.3 Testing & Coverage
- [ ] Unit Test Coverage >80%
- [ ] Integration Tests
- [ ] E2E Tests
- [ ] Performance Tests
- **Aufwand:** 3-5 Tage

### P3.4 Documentation
- [ ] User Manual (DE/EN)
- [ ] Developer Docs
- [ ] API Docs
- [ ] Deployment Guide
- **Aufwand:** 2-3 Tage

---

## 🟣 P4 - Release (Juni 2026)

### P4.1 v1.0 Release Preparation
- [ ] Feature Freeze
- [ ] Bugfix Sprint
- [ ] Security Audit
- [ ] Performance Benchmarks

### P4.2 Release
- [ ] Tag v1.0.0
- [ ] Release Notes
- [ ] Migration Guide
- [ ] Community Announcement

---

## 📊 Priorisierung Matrix

| Feature | Relevanz | Aufwand | Impact | Priorität |
|---------|----------|---------|--------|-----------|
| Token-Auth Fix | ⭐⭐⭐⭐⭐ | S | Critical | P0 ✅ |
| Port 8909 | ⭐⭐⭐⭐⭐ | S | Critical | P0 ✅ |
| Error-Isolation | ⭐⭐⭐⭐ | M | High | P0 |
| Mood Engine | ⭐⭐⭐⭐ | M | Med | P1 |
| ANN Energy | ⭐⭐⭐⭐ | L | High | P2 |
| MCP Integration | ⭐⭐⭐⭐ | M | High | P2 |
| User Roles | ⭐⭐⭐⭐ | M | High | P1 |
| UWB Sensors | ⭐⭐⭐ | L | Med | P2 |
| Semantic Ontologies | ⭐⭐⭐ | M | Med | P2 |
| DRL Optimization | ⭐⭐⭐ | L | High | P3 |
| Grid Integration | ⭐⭐ | L | Low | P4 |

---

## 🔄 Iterativer Ablauf

### Jede Iteration:
1. **Auswahl** nächster Task(s) aus aktueller Phase
2. **Implementation** mit Sub-Agent (Clowdya)
3. **Review** - Syntax-Check, Tests, Code-Review
4. **Commit** mit Deskriptiver Message
5. **Update** Roadmap Status
6. **Report** an User

### Wöchentlicher Rhythmus:
- **Montag:** Roadmap Review, Task-Auswahl
- **Di-Do:** Implementation (iterativ)
- **Freitag:** Integration, Tests, Commit
- **Wochenende:** Deployment-Testing

---

## 🎯 Aktueller Sprint (Woche 1)

**Fokus:** P0 Critical Fixes + P1.1 Mood Engine + P1.2 Start + Port-Konflikt + HabitusZone + HA Standard

| Tag | Task | Status |
|-----|------|--------|
| Di | Token-Auth Fix | ✅ Done |
| Di | Port 8099 | ✅ Done (HA Add-on Standard) |
| Di | Error-Isolation | ✅ Done (Core + HACS runtime.py) |
| Di | Mood Engine API Endpoints | ✅ Done (zone orchestration) |
| Di | Commit & Push | ✅ Done (bd99fe5, d235766, aad1d2e, c2c9388, 7c02931, 59648dd, ee54067) |
| Mi | Race Conditions Audit | ✅ Done (P1.2 Start) |
| Do | P0 Abschluss Review | ✅ Done |
| Fr | P1.2 Start (Race Conditions) | ✅ Done |
| Fr | Port-Konflikt Fix | ✅ Done (v0.9.1-alpha.4 - HA Add-on Standard 8099) |
| Fr | HabitusZone Integration | ✅ Done (v0.14.1-alpha.3) |

---

*Letzte Aktualisierung: 2026-02-17 17:25*
