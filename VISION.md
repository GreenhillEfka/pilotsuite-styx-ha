# PilotSuite Styx - Vision (2026-02-22)

This document is the active vision baseline for the dual-repo system:
- Core add-on repo: `pilotsuite-styx-core`
- HACS integration repo: `pilotsuite-styx-ha`

Version baseline:
- Core add-on: `7.7.8`
- HA integration: `7.7.8`
- Core API port: `8909`

## Mission
Build a local-first AI co-pilot for Home Assistant that learns household patterns, explains recommendations, and never bypasses user governance.

## Non-negotiable principles
- Local-first: no cloud dependency for core operation.
- Privacy-first: redaction, bounded storage, explicit retention.
- Governance-first: recommendation before action, user remains decider.
- Safety defaults: fail safe under uncertainty, degraded mode over crash.
- Explainability: every recommendation has traceable evidence.

## Normative loop
`HA states -> Neuron context -> Mood/Intent weighting -> Pattern mining -> Candidate -> User decision -> Feedback`

Rules:
- No direct state-to-action shortcut in default mode.
- High-risk classes remain manual unless explicitly elevated.
- Feedback (accept/defer/dismiss) is part of the learning loop.

## Dual-repo contract
- `pilotsuite-styx-core`: backend runtime, event ingest, graph, mining, candidate lifecycle, LLM/memory, health APIs.
- `pilotsuite-styx-ha`: Home Assistant-facing runtime, entities/cards/config-flow, events forwarder, repairs/governance UX, decision sync.

Separation is intentional for HA ecosystem compatibility and release independence.

## Communication architecture
Forward path (HA -> Core):
- HA events -> N3 forwarder envelope -> `POST /api/v1/events` -> EventProcessor -> BrainGraph -> Habitus.

Return path (Core -> HA):
- Candidate API -> HA Candidate Poller -> Repairs issue/workflow -> user decision -> `PUT /api/v1/candidates/:id`.

Realtime path:
- Core webhook push -> HA coordinator merge -> entity refresh.

## Module intent map
Core subsystems:
- Ingest and event store: reliable intake with idempotency.
- Brain graph: decayed relationship model and graph queries.
- Habitus mining: pattern extraction with quality thresholds.
- Candidate store: governed lifecycle and feedback memory.
- Mood and neuron services: contextual weighting and suppression logic.
- Vector/memory/knowledge: semantic recall and explainability context.
- Hub engines: advanced domain-specific orchestration surfaces.

HA integration runtime modules (31 active) are grouped as:
- Core plumbing: `legacy`, `events_forwarder`, `candidate_poller`, `history_backfill`, `dev_surface`.
- Intelligence/context: `habitus_miner`, `brain_graph_sync`, `mood`, `mood_context`, `ml_context`, `knowledge_graph_sync`.
- Domain context: `energy_context`, `weather_context`, `media_zones`, `network`, `camera_context`.
- User/governance: `character_module`, `entity_tags`, `quick_search`, `voice_context`, `ops_runbook`.
- Home operations: `home_alerts`, `waste_reminder`, `birthday_reminder`, `person_tracking`, `scene_module`, `calendar_module`, `homekit_bridge`, `frigate_bridge`, `unifi_module`, `performance_scaling`.

## Configurability goals
- Zero-config first run works out of the box.
- Advanced mode exposes host/port/token, zones, tags, module toggles, thresholds.
- Runtime behavior is adjustable without manual file edits.
- Operational diagnostics are available from HA UI and API endpoints.

## UX vision (dashboard + controls)
State-of-the-art UX for this project means:
- Clear system posture: health, readiness, and confidence visible at all times.
- Progressive disclosure: simple default, deep diagnostics on demand.
- Fast feedback loop: user decisions reflected immediately in UI state.
- Explainable recommendations: evidence and risk level visible before action.
- Mobile-safe layouts and low-friction controls for critical flows.

Current implementation direction:
- Ingress dashboard with Brain/Mood/Module views.
- Lovelace card resources for mood/neurons/habitus surfaces.
- Repairs-based governance workflow for controlled application of candidates.

## Production readiness definition
A release is production-ready only if all are true:
- Critical path tests pass (forward path + return path + auth + status).
- Runtime fallback behavior works outside ideal HA container paths.
- CI fails on real regressions (no masked failures).
- Versioning/changelogs/docs are synchronized across both repos.

## Continuous hardening loop
Both repos run a scheduled `production-guard` workflow every 15 minutes to validate critical paths continuously.

Purpose:
- detect regressions early,
- keep dual-repo contract healthy,
- provide a stable base for iterative feature work.

## Beyond 7.7.x
- Deeper explainability and policy controls per risk class.
- Stronger cross-module contract tests and mutation-based hardening.
- UX refinement for recommendation triage and large-home scalability.
