# PilotSuite - Implementation Roadmap v1.0

## Priorisierung nach Triple Agent Review

### 🔴 P0 - KRITISCH (Security)
| # | Task | Status | Aufwand |
|---|------|--------|---------|
| 1 | Auth Bypass Fix (security.py) | ⏳ | 15 min |
| 2 | Command Injection Fix (ops_runbook.py) | ⏳ | 10 min |
| 3 | Rate Limiting hinzufügen | ⏳ | 20 min |
| 4 | Input Validation Core API | ⏳ | 30 min |

### 🟡 P1 - HOCH
| # | Task | Status | Aufwand |
|---|------|--------|---------|
| 5 | SHA1 → BLAKE2 | ⏳ | 10 min |
| 6 | Dashboard Auto-Import | ⏳ | 20 min |
| 7 | ML Training Pipeline aktivieren | ⏳ | 30 min |
| 8 | Brain Graph Cache Limit | ⏳ | 10 min |

### 🟢 P2 - MEDIUM
| # | Task | Status | Aufwand |
|---|------|--------|---------|
| 9 | Character → Mood Integration | ⏳ | 20 min |
| 10 | User Hints → Core API | ⏳ | 20 min |
| 11 | Zone Management UI | ⏳ | 30 min |
| 12 | Button Consolidation | ⏳ | 30 min |

### 🔵 P3 - LOW
| # | Task | Status | Aufwand |
|---|------|--------|---------|
| 13 | Legacy v1 Code entfernen | ⏳ | 20 min |
| 14 | Missing Dashboard Cards | ⏳ | 20 min |
| 15 | Neuron Smoothing Tuning | ⏳ | 10 min |

---

## Zeitplan (5-Minuten Sprints)

```
Sprint 1 (5min):   P0-1 Auth Bypass
Sprint 2 (5min):   P0-2 Command Injection  
Sprint 3 (5min):   P0-3 Rate Limiting Setup
Sprint 4 (5min):   P1-5 SHA1 → BLAKE2
Sprint 5 (5min):   P1-6 Dashboard Auto-Import
Sprint 6 (5min):   P1-7 ML Pipeline
Sprint 7 (5min):   P1-8 Cache Limit
Sprint 8 (5min):   P2-9 Character Integration
Sprint 9 (5min):   P2-10 User Hints Integration
Sprint 10 (5min):  P2-11 Zone UI
Sprint 11 (5min):  P2-12 Button Consolidation
Sprint 12 (5min):  P3-13 Legacy Cleanup
Sprint 13 (5min):  P3-14 Dashboard Cards
Sprint 14 (5min):  P3-15 Smoothing Tuning
```

---

## Success Metrics (10/10 Ziel)

| Kategorie | Ziel | Metrik |
|-----------|------|--------|
| Security | 10/10 | Keine P0 Issues |
| Architecture | 10/10 | Saubere Module |
| Innovation | 10/10 | Neuronales System |
| UX | 10/10 | Setup Wizard + Dashboard |
| Performance | 10/10 | Cache + Async |
| Code Quality | 10/10 | Type Hints + Exceptions |

---

## Checkpoints

- [ ] Sprint 1-3: Security P0 complete
- [ ] Sprint 4-8: P1 + Brain Graph optimization
- [ ] Sprint 9-12: UX Improvements
- [ ] Sprint 13-15: Polish & Cleanup
- [ ] **v1.0 Release**
