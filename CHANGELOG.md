# CHANGELOG

## v8.8.0 (2026-02-25)
- feat(flow): Habitus options flow switched to React-first dashboard concept (`dashboard_info` in menu, legacy YAML actions no longer default path).
- feat(core-alignment): legacy YAML dashboard auto-generation/auto-refresh is now opt-in (`legacy_yaml_dashboards` / `PILOTSUITE_LEGACY_YAML_DASHBOARDS`).
- feat(strings): updated options strings for React-first dashboard mode.
- test: updated habitus dashboard config-flow expectations for the new menu concept.
- chore(version): align integration + repo manifest to `8.8.0`.

## v8.7.0 (2026-02-25)
- feat(sensor): new `PilotSuite RAG Pipeline` sensor (`sensor.ai_home_copilot_rag_pipeline`) wired into coordinator data.
- feat(coordinator): HA now fetches Core RAG status via `/api/v1/rag/status` and exposes it in coordinator payload.
- fix(sensor): added missing logger initialization in `sensor.py` (prevented silent exceptions in dynamic context sensor refresh paths).
- fix(perf): performance scaling now auto-tunes memory threshold to sane host/container limits and adds hysteresis (`trigger +96MB`, clear at `92%`) to prevent repetitive warning spam.
- chore(version): align integration + repo manifest to `8.7.0`.
- validation: `python3 -m py_compile` on all changed HA integration modules passed.

## v8.6.0 (2026-02-25)
- feat(habitus-dashboard): camera entities are now rendered explicitly in generated Habitus dashboards (entities + live `picture-entity` cards)
- feat(habitus-dashboard): zone overview signal stack now includes camera signals in key history/logbook tracks
- chore(version): align integration + repo manifest to `8.6.0`
- targeted tests: 33 passed (`habitus_dashboard_generation`, `habitus_zones_dashboard`, `camera_context_module`, `performance_scaling`)

## v8.5.0 (2026-02-25)
- fix(camera): `CameraContextModule` now keeps a legacy-safe sync wrapper for `_forward_to_brain`, preventing `coroutine ... was never awaited` warnings from old sync callsites
- test(camera): added regression test for direct legacy `_forward_to_brain(...)` invocation path
- fix(perf): raised default memory alert threshold to `3072 MB` and added sustained-breach logic (3 consecutive checks) to suppress restart spike noise
- test(perf): added alert streak regression test for memory-high warnings
- chore: version alignment to `8.5.0` in both integration manifest and repo `manifest.json`

## v8.4.2 (2026-02-25)
- fix: seed adapter now filters low-signal values (`on/off`, numeric-only) to prevent noisy `CoPilot Seed:*` repair spam
- fix: state fallback in seed adapter is now stricter (only meaningful text payloads become seed candidates)
- fix: performance scaling default memory alert threshold raised to `2048 MB` to reduce false-positive warnings on normal HA hosts
- chore: align manifest metadata/versioning (`custom_components/.../manifest.json`, repo `manifest.json`) to avoid inconsistent update/version display

## v8.4.1 (2026-02-25)
- chore: sync HA integration version with Core `v8.4.1` line
- no functional HA code changes; compatibility release for paired install tracking

## v8.4.0 (2026-02-25)
- feat: entity profile runtime select
- fix: knowledge_graph guard for KeyError
- Pytest: 608 passed

## v8.3.0 (2026-02-25)
- fix: guard all hass.data access against KeyError
- fix: inspector_sensor key path
- Pytest: 608 passed

## v8.2.0 (2026-02-25)
- feat: Brain Graph + Habitus Rules sensors
- feat: Core API integration
- feat: dashboard improvements
- Pytest: 608 passed

## v8.1.2 (2026-02-25)
- feat: Per-module options submenu
- feat: Core module control API
- Pytest: 608 passed

## v8.1.1 (2026-02-25)
- RFC-Phase 2 Core Tools implementiert
- Scene Automation Skills (create_scene_from_behavior, list_scenes)
- Multi-Zone Audio Control (group_zones, ungroup_zones)
- Security & Access (door_status, lock_door, unlock_door)
- Maintenance & Diagnostics (system_health, restart_service)
- Calendar & Scheduling (upcoming_events, optimal_time)
- Weather-Based Automation (weather_trigger)
- MCP-compatible API mit input schemas
- Pytest: 608 passed

## v8.1.0 (2026-02-25)
- HACS Release Pipeline (v8.1.0)
- HA Dashboard API Endpoints (v7.11.0)
- LLM Provider Fallback (v7.11.0)
- SearXNG Auto-Integration (v7.11.1)
- Direct Web Search API Endpoints
- HASSFest Fix (domain Feld in manifest.json)
- Pytest: 608 passed

## v8.0.0 (2026-02-24)

## v7.9.3 (2026-02-24)
- fix(anomaly_detector): ensure is_anomaly returns Python bool type
- fix(anomaly_detector): correct last_anomaly timestamp and features to reflect last true anomaly
- fix(manifest): bump ai_home_copilot to v7.9.3 and root manifest to v7.9.3
- tests: all 608 tests passing

## v7.9.1 (2026-02-24)
- fix(anomaly_detector): correct last_anomaly to latest true anomaly, wrap is_anomaly in bool() for type consistency
- feat(habit_predictor): extend routine pattern extraction with scene grouping
- Tagged test-p0-202602240915

## v7.8.11-dev (2026-02-24)
- Synced with core fixes
- Tagged test-p0-202602240530
- Updated RELEASE_NOTES for P0 fixes
- Tagged test-p0-202602240620
- Tagged test-p0-202602240640
- Tagged test-p0-202602240650
- Tagged test-p0-202602240710
- Tagged test-p0-202602240730
- Tagged test-p0-202602240740
- Tagged test-p0-202602240750
- Tagged test-p0-202602240840
- Pytest: 2 failures, 606 passed (ha)
