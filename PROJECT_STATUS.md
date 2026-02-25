# PilotSuite - Production Status (2026-02-25)

Scope: dual-repo production audit (`pilotsuite-styx-core` + `pilotsuite-styx-ha`).

Release baseline for this status:
- Core add-on target: `8.9.0`
- HA integration target: `8.9.0`

## Executive summary
System is release-ready with validated critical communication loops and continuous guardrails.

Validated for current baseline:
- Main CI green in both repositories.
- HACS validation and add-on validation green on latest main commits.
- Production guard workflows active (15-minute cadence).

Additional hardening completed:
- Single-instance config flow guard to prevent duplicate devices/config entries.
- Stable primary device identity (`styx_hub`) with legacy alias mapping.
- Selector-first setup/options flow for entity selection (reduced free-text errors).
- Zone creation flow repaired and now supports async area-based entity suggestions.
- Agent auto-config now triggers Core self-heal on failed/degraded startup checks and exposes manual `repair_agent` service.
- Conversation API timeout in HA bridge increased to `90s` (avoids false timeouts on local 4B models).
- Sensor communication path unified to coordinator failover endpoint + centralized auth headers.
- Backward-compatible token normalization (`auth_token` -> `token`) in coordinator startup.

## What was audited
- Vision consistency (design intent vs runtime behavior).
- Module purpose and lifecycle for runtime-loaded modules.
- Forward path: HA events to Core ingest and graph/mining pipeline.
- Return path: candidate polling, repairs decisions, sync-back to Core.
- Configurability and runtime fallbacks.
- Dashboard/UX posture for operational clarity.

## Evidence-based verification
- Syntax checks (`py_compile`) pass for both repos.
- Core critical APIs validated by tests:
  - status/auth/events/full-flow/e2e pipeline.
- HA critical integrations validated by tests:
  - forwarder envelope behavior, candidate poller, repairs workflow, API compat.
- New full-flow integration test in HA validates:
  - N3 privacy-safe event envelope creation.
  - Candidate payload conversion for Repairs.
  - Accept/defer decision sync to Core candidate endpoint.

## Module implementation status
Core:
- Service initialization: resilient (`try/except` isolation in `core_setup.py`).
- Brain graph + habitus + candidates + mood + neurons: active and test-covered.
- Runtime persistence fallbacks for non-writable `/data`: implemented for key stores.

HA integration:
- Runtime module registry and lifecycle orchestration: active.
- 31 runtime modules loaded by default integration setup.
- Repairs-based governance loop and Core sync-back: active.

## Configurability posture
- Zero-config path exists for fast onboarding.
- Advanced options cover host/port/token, zones, features, and tuning knobs.
- Production safety options present through module gating + decision workflows.

## UX posture (state of the art criteria)
Current implementation meets project-level operational UX criteria:
- clear health/status visibility,
- recommendation inbox with explicit decisions,
- explainable recommendation data exposure,
- dashboard/card surfaces for mood/neurons/habitus,
- mobile-safe responsive behavior in ingress dashboard.

## Remaining known risks
- Full live HA runtime behavior still depends on environment-specific entities/devices.
- Scheduled production guards are quality loops, not autonomous feature development.

## Continuous hardening setup
Added in both repos:
- `.github/workflows/production-guard.yml`
- Trigger cadence: every 15 minutes (`cron: "*/15 * * * *"`)
- Purpose: fast detection of regressions on critical paths.

## Release gate
Production release is permitted when all of the following hold:
- local critical tests green,
- main CI green,
- production-guard workflow green,
- versions/changelogs/docs synchronized across both repos.
