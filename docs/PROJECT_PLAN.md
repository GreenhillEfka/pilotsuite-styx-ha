# AI Home CoPilot - Project Plan (Canvas + Kanban)

## 0) Project Canvas (1 page)
**Mission**
Turn Home Assistant usage patterns into *governed*, *privacy-first* automation suggestions that users can accept via Repairs + Blueprints.

**Non-negotiables**
- Privacy-first: no log shipping; no personal defaults in repo; tokens never logged.
- Governance-first: no silent automation creation; every change requires explicit confirmation.
- Prefer push/event driven; polling only as fallback (watchdog).

**Main building blocks**
- **HA Integration (`ai_home_copilot`)**: connectivity, webhook receiver, UX (Repairs), blueprints, safe actions.
- **Copilot Core Add-on**: ingest events, mine habits, generate candidates, scoring/ranking.
- **Suggestion pipeline**: Habitus → Candidate → Repairs → Blueprint import/create → User confirm.

**Success criteria (MVP+)**
- Stable install/update/rollback (HACS tags/releases).
- HA shows online/version + can run a safe test action.
- Candidates can be offered + accepted/dismissed with audit trail.
- At least one end-to-end habit mined into a candidate.

---

## 1) Kanban (work in slices)
Legend: ✅ done / 🟡 in progress / ⏳ next / 💡 later

### NOW (stabilize + operability)
- ✅ HACS repo + releases/tags
- ✅ Webhook push + watchdog fallback
- ✅ Governance UX: Repairs + safe blueprint shipped
- ✅ Error analysis + reversible fixer (log scan + Repairs fix + rollback)
- ✅ DevLogs debug pipeline (opt-in push + in-HA fetch) to keep development observable
- ✅ Modular runtime skeleton (legacy wrapper) to enable 20+ modules without breaking behavior
- ✅ Service registration extraction (`services_setup.py`) — `__init__.py` 300→60 lines (v0.5.4)

### NEXT (make suggestions real)
**N0 - Stable module foundation (HA side)**
- ✅ Release the modular runtime skeleton (legacy wrapper) as a no-behavior-change update (v0.5.4)
- ✅ Add `media_players_csv` config + **MediaContext v0.1 (read-only)** to provide reliable signals (Spotify/Sonos) for Mood/Habitus/Entertain (v0.5.5)

**N1 – Candidate lifecycle + UX polish (HA side)** ✅
- ✅ Candidate states: add `defer` (with "offer again after X days")
- ✅ Better Repairs fix flow text + link to Blueprint UI (v0.4.9)
- ✅ Store minimal evidence payload (support/confidence/lift) and show it in Repairs text (v0.4.8)

**N2 - Core API v1 minimal** ✅
- ✅ `POST /api/v1/events` (batch) — v0.4.3 Core
- ✅ `GET /api/v1/events` (debug window / support tooling) — v0.4.3 Core
- ✅ Candidate store endpoints (for HA UX + future ranking) — v0.4.4 Core
- ✅ Habitus miner A→B (Δt window, debounce, support/confidence/lift) — v0.4.5 Core

**N3 - HA → Core event forwarder**
- ✅ Capabilities ping (`GET /api/v1/capabilities`) and clear "Core supports v1?" status
- ✅ Allowlist which HA entities we forward (default: Habitus zones; optional: MediaContext lists)
- ✅ Token-protected calls, rate limits, and redaction rules
- ✅ Heartbeat monitoring for Core health (60s interval, configurable)
- ✅ Enhanced zone inference for person/device_tracker entities
- ✅ Privacy-first redaction (GPS, tokens, PII) per Alpha Worker N3 spec

**N4 - Brain Graph (Dev surface)**
- ✅ Co-activity graph (neurons + synapses) generated from forwarded events
- ✅ Multi-source zone inference with confidence weighting
- ✅ Enhanced intentional action tracking (service calls 2x salience)
- ✅ Spatial intent chains and trigger inference using HA context
- ✅ `/api/v1/graph/patterns` endpoint for automation hints
- ✅ Privacy-first bounded storage (max 500 nodes, 1500 edges)
- ✅ First view: static SVG + summary table (HA-friendly, low maintenance)
- 💡 Later: interactive graph panel (optional)

**N5 - Core ↔ HA Integration Bridge**
- ✅ CandidatePollerModule: HA polls Core `/api/v1/candidates?state=pending` every 5 min (v0.5.0)
- ✅ Auto-offer via Repairs with evidence display + pre-populated Blueprint inputs (v0.5.0)
- ✅ Bidirectional state sync: offered/accepted/dismissed states sent back to Core (v0.5.0)
- ✅ Decision sync-back: accept/dismiss/defer synced to Core via PUT (v0.5.1)
- ✅ Habitus trigger: `ai_home_copilot.trigger_mining` service calls `POST /api/v1/habitus/mine` on-demand (v0.5.2)
- ✅ Pipeline Health sensor: `sensor.ai_home_copilot_pipeline_health` consolidates Core component status (v0.5.2)

### LATER (expansion modules)
- 💡 Mood vector v0.1 (comfort/frugality/joy) and ranking
- 💡 SystemHealth neuron (Zigbee/Z-Wave/Mesh, recorder, slow updates)
- 💡 UniFi neuron (WAN loss/jitter, client roams, baselines)
- 💡 Energy neuron (anomalies, load shifting, explainability)

---

## 2) Dependency map (so connections stay obvious)
1. **Core candidates** depend on: event ingest + habit miner.
2. **HA suggestions UX** depends on: candidates list + lifecycle.
3. **Rollbackable fixes** depend on: transaction store.
4. **Mood ranking** depends on: candidate evidence + basic metadata.

---

## 3) Issue taxonomy (recommended)
If we track work in GitHub:
- Labels: `epic`, `core`, `ha-integration`, `ux`, `security`, `privacy`, `governance`, `bug`, `docs`
- Milestones:
  - `M0 Foundation` (done)
  - `M1 Suggestions E2E` (NEXT)
  - `M2 Mood ranking` (LATER)
  - `M3 SystemHealth/UniFi/Energy` (LATER)

---

## 4) Where this lives
- This file should be the single "source of truth" overview.
- Detailed specs live in `docs/` (API draft, concept v0.2, model v0.1).
