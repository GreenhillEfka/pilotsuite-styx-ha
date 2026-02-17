# PilotSuite Master Projektplan

> **Neustart-resistent** — Stand: 2026-02-17 14:01  
> Aktueller Task: P0/#3 Error-Isolation (wartet auf User-Update)

---

## 🎯 Projekt-Übersicht

**Repos:**
- Core Add-on: `/config/.openclaw/workspace/ha-copilot-repo` (v0.9.0-alpha.1)
- HA Integration: `/config/.openclaw/workspace/ai_home_copilot_hacs_repo` (v0.14.0-alpha.1)

**Port:** 8909 (korrigiert von 8099 wegen HA-Konflikten)

---

## 🔴 P0 — Sicherheit & Stabilität (Diese Woche)

| # | Task | Status | Commit | Aufwand | Blocker |
|---|------|--------|--------|---------|---------|
| 1 | ~~Token-Auth Fix~~ | ✅ **DONE** | `bf0c11f` | 30 min | — |
| 2 | ~~Port 8099→8909~~ | ✅ **DONE** | `bf0c11f` | 15 min | — |
| 3 | **Error-Isolation** | 🔄 **NEXT** | — | 2-4h | User-Update |
| 4 | Race Conditions fixen | ⏳ Pending | — | 2-4h | — |

**P0/#3 Error-Isolation Details:**
- **Problem:** Keine Isolation im Modul-Setup → ein Modul-Crash killt alles
- **Lösung:** Try-except Wrapper in `core/runtime.py` + Modul-Health-Check
- **Dateien:** `copilot_core/core/runtime.py`
- **Impact:** HIGH

---

## 🟡 P1 — Core Features (Nächster Sprint)

| # | Task | Status | Aufwand | Impact |
|---|------|--------|---------|--------|
| 5 | Mood Engine vervollständigen | ⏳ Pending | 1-2d | HIGH |
| 6 | Extended User Roles (MUPL) | ⏳ Pending | 4-6h | HIGH |
| 7 | ANN Energy Prediction | ⏳ Pending | 2-3d | HIGH |
| 8 | CHANGELOG aktualisieren | ⏳ Pending | 30 min | MED |

---

## 🟢 P2 — Zukunft (Q2-Q3)

| # | Task | Status | Aufwand | Impact |
|---|------|--------|---------|--------|
| 9 | MCP Integration | ⏳ Planned | 1-2d | Future-proof |
| 10 | UWB Sensor Support | ⏳ Planned | 2-3d | Innovation |
| 11 | DRL Energy Optimization | ⏳ Planned | 3-5d | HIGH |
| 12 | Semantic Ontologies | ⏳ Planned | 2-3d | MED |

---

## 📊 Aktueller Status

**Letzte Aktivität:** 2026-02-17 11:36 — Token-Auth + Port Fix committed & gepusht

**Nächste Aktion:** Error-Isolation implementieren (nach User-Update)

**Offene Fragen:**
- Soll Error-Isolation auch für die HACS-Integration gelten?
- Priorisierung von P1-Features?

---

## 🔗 Referenzen

- **Tageslog:** `memory/2026-02-17.md`
- **Research:** `notes/research/research_2026-02-17.md`
- **Changelog Core:** `ha-copilot-repo/CHANGELOG.md`
- **Changelog HACS:** `ai_home_copilot_hacs_repo/CHANGELOG.md`

---

*Automatisch aktualisiert bei jedem Neustart*
