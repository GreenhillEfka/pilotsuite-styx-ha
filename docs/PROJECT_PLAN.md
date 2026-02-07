# AI Home CoPilot – Project Plan (Canvas + Kanban)

## 0) Project Canvas (1 page)
**Mission**
Turn Home Assistant usage patterns into *governed*, *privacy-first* automation suggestions that users can accept via Repairs + Blueprints.

**Non‑negotiables**
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
- ✅ HACS repo + releases/tags (v0.1.0, v0.1.1)
- ✅ Webhook push + watchdog fallback
- ✅ Governance UX: Repairs + safe blueprint shipped
- ✅ Error analysis + reversible fixer (log scan + Repairs fix + rollback)

### NEXT (make suggestions real)
**N1 – Candidate lifecycle + UX polish (HA side)**
- ⏳ Candidate states: add `defer` (with “offer again after X days”)
- ⏳ Better Repairs fix flow text + link to Blueprint UI
- ⏳ Store minimal evidence payload (support/confidence/lift) and show it in Repairs text

**N2 – Core API v1 minimal**
- ⏳ `POST /api/v1/ingest/events` (batch)
- ⏳ Habitus miner A→B (Δt window, debounce, support/confidence/lift)
- ⏳ `GET /api/v1/habitus/candidates`
- ⏳ `POST /api/v1/habitus/candidates/{id}/accept|dismiss|defer`

**N3 – HA → Core event forwarder**
- ⏳ Allowlist which HA events/entities we forward
- ⏳ Token-protected calls, rate limits, and redaction rules

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
- This file should be the single “source of truth” overview.
- Detailed specs live in `docs/` (API draft, concept v0.2, model v0.1).
