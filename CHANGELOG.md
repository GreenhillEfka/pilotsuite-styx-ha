# CHANGELOG

## v10.1.4 (2026-02-27) — DASHBOARD + CONTEXT PIPELINE FIXES

### Added
- Button: **PilotSuite reload dashboards** (Lovelace YAML/resources reload trigger).
- HA → Core Forwarding: Waste collections + Birthdays list are now pushed to Core so the Core Haushalt UI can render real data.

### Changed
- Zero-config defaults hardened:
  - Entity profile defaults to `full` (instead of `core`).
  - Events forwarder defaults to enabled.
  - Legacy YAML dashboards default to enabled (generation + wiring on first run).
- Habitus-Zonen YAML: If no zones exist yet, a starter view with instructions is generated (no more blank dashboard).

### Fixed
- Calendar sensor: repaired coordinator reference + service call handling for `calendar.get_events`.
- CI: Production Guard now fetches tags reliably (`fetch-tags: true`) for scheduled tag checks.

## v10.1.3 (2026-02-26) — COMPAT GUARDRAILS

### Added
- Core/HA Versionschutz: Major/Minor Mismatch wird als Repairs-Hinweis angezeigt (Update-Anleitung im Issue).

### Fixed
- Contract-Test fuer Habitus Dashboard Cards Endpoint-Pfad (`/api/v1/habitus/dashboard_cards`).

## v10.1.2 (2026-02-26) — HA DOCS COMPLIANCE

### Changed
- HA Best Practice: `single_config_entry` im Integration-Manifest aktiviert (verhindert multiple Config-Entries/Duplikate).

## v10.1.1 (2026-02-26) — VERSION SYNC + DOCS

### Fixed
- Versionen/Metadaten konsolidiert (Repo `manifest.json` + Integration `manifest.json` + Status/Doku).

## v10.1.0 (2026-02-26) — COORDINATOR COMPLETE + SENSOR FIXES

### Fixed
- Sensor-Datenpfade bereinigt, fehlende Sensoren ergänzt, Coordinator-Flow vervollständigt.

## v10.0.1 (2026-02-26) — OVERRIDE MODES + MUSIKWOLKE + HABITUS CONTROLS

### Added
- Override-Mode Sensoren.

### Changed
- Musikwolke Dashboard + Habitus Controls erweitert.

## v10.0.0 (2026-02-26) — MODULE SYSTEM + ZONE AUTOMATION

### Added
- Modul-System-Konsolidierung + Zone-Automation Grundlage (HA-Seite).

## v9.1.0 (2026-02-26) — HA API INTEGRATION + DEVICE DISCOVERY + LABELS

### Added
- **EntityDiscoveryModule v2**: Now collects devices (manufacturer, model, sw_version) + HA labels + floor info from all registries.
  - Area resolution: entity → device → area (per HA API docs: area_id is NOT in REST /api/states).
  - Domain-specific extras: media_player sources, climate HVAC modes, light color modes, cover positions.
  - Auto-tags zone suggestions from Core response.
- **Entity Tags v2**: New tag types: `area_*` (HA area tags), `ha_label_*` (synced from HA native labels).
  - `async_auto_tag_by_area()` — bridges HA areas with PilotSuite tags.
  - `async_sync_ha_labels()` — imports HA native labels as PilotSuite tags.
  - Enhanced LLM context with tag type markers ([auto:zone], [auto:area], [ha:label]).
- **ha_discovery.py v2**: Comprehensive HA export script using REST + WebSocket API.
  - WebSocket: `config/entity_registry/list`, `config/device_registry/list`, `config/area_registry/list`, `config/floor_registry/list`, `config/label_registry/list`.
  - 18 role patterns (DE+EN), 14 zone keywords, entity-device enrichment.

### Changed
- **EntityDiscoveryModule**: Bumped to v2.0.0. Now pushes devices alongside entities+areas. Sync methods are synchronous (no unnecessary async).
- **EntityTagsModule**: Bumped to v0.3.0. Added zone colors for keller, esszimmer, waschkueche, dachboden.
- **Version**: `manifest.json` → `9.1.0`. Paired with Core `v9.1.0`.

## v9.0.0 (2026-02-26) — ARCHITECTURE OVERHAUL + EVENTBUS + TAG SYSTEM

### Added
- **EventBus Architecture**: Thread-safe pub/sub EventBus for inter-module communication (topics: `zone.*`, `mood.*`, `neuron.*`, `candidate.*`, `graph.*`, `event.*`).
- **Bidirectional Zone Sync**: New `ZoneSyncModule` with hash-based dedup, syncs zones via `/api/v1/habitus/zones/sync` (fallback to legacy endpoint).
- **Automation Adoption Module**: `AutomationAdoptionModule` converts Core suggestions into HA automations (`adopt_suggestion`, `dismiss_suggestion` services).
- **Coordinator Module**: Dedicated `CoordinatorModule` for coordinator lifecycle management (extracted from legacy).
- **Habitus Zone Dashboard Card**: Comprehensive Lovelace card generator with zone overview, mood gauges (comfort/joy/frugality), entity lists, news/warnings, household quick actions.
- **Zone Auto-Tagging**: `EntityTagsModule.async_auto_tag_zone_entities()` — automatic zone + Styx tagging when entities are assigned to Habitus zones.
- **Entity Search API**: Searchable entity dropdown data from Core via `/api/v1/entities/search`, `/domains`, `/by-area`.

### Changed
- **Zone Sync**: `config_zones_flow.py` now tries new API first (`/api/v1/habitus/zones/sync`), falls back to legacy.
- **Module Registry**: 3 new modules registered in `__init__.py`: `coordinator_module`, `automation_adoption`, `zone_sync`.
- **Tag System**: Dual-layer tags (manual + automatic zone/Styx tags) with role-based colors per zone.

### Version
- `manifest.json` → `9.0.0`
- Paired with Core `v9.0.0`.

## v8.12.1 (2026-02-26)
- compat(core): paired with Core `v8.12.1` Habitus recommendation apply endpoint (`/api/v1/hub/habitus/management/apply_zone`).
- compat(core): HomeKit auto-sync metadata now returned on zone lifecycle/bootstrap responses and consumed in dashboard flow.
- chore(version): integration + repo manifest aligned to `8.12.1`.

## v8.12.0 (2026-02-26)
- compat(core): paired with Core `v8.12.0` multi-room Habitus recommendation payload (`room_ids`, `room_candidates`) and improved bootstrap flow.
- ux(habitus): React dashboard now consumes richer recommendation data for room-aware zone prefill and edit flow.
- compat(homekit): HomeKit zone cards now surface explicit connectivity state (`zone_present`) from Core API.
- chore(version): integration + repo manifest aligned to `8.12.0`.

## v8.11.0 (2026-02-25)
- compat(core): paired with Core `v8.11.0` system observability endpoints (`/api/v1/system/*`) for dashboard health/resource/sensor views.
- chore(version): integration + repo manifest aligned to `8.11.0`.
- docs: setup/install guides updated to reference the new system overview flow.

## v8.10.0 (2026-02-25)
- fix(homekit): HomeKit bridge module now imports `async_get_clientsession` correctly, so setup-info sync from Core (`/api/v1/homekit/all-zones-info`) works reliably.
- compat(core): paired with Core `v8.10.0` HomeKit zone server API and Habitus dashboard HomeKit management panel.
- chore(version): integration + repo manifest aligned to `8.10.0`.

## v8.9.1 (2026-02-25)
- fix(repairs): startup cleanup now removes stale low-signal `seed_suggestion` issues (e.g. `CoPilot Seed: on/5/17`) from older releases.
- fix(repairs): stale internal seed-source issues (`sensor/number/text.ai_home_copilot_*seed*`) are now auto-pruned.
- feat(branding): integration brand assets are now shipped in `custom_components/ai_home_copilot/brands/` (`icon.png`, `logo.png`) for consistent HA icon rendering.
- chore(i18n): seed issue title changed from `CoPilot Seed` to `PilotSuite suggestion` / `PilotSuite Vorschlag`.
- docs: setup/install docs refreshed for current `8909` architecture and paired HA/Core release line.
- test: new stale-seed cleanup regression tests (`tests/test_repairs_cleanup.py`).

## v8.9.0 (2026-02-25)
- feat(zones): Habitus zone create/edit flow expanded with role-based selectors:
  - `brightness_entity_ids`, `noise_entity_ids`, `humidity_entity_ids`, `co2_entity_ids`
  - `temperature_entity_ids`, `heating_entity_ids`, `camera_entity_ids`, `media_entity_ids`
- feat(zones): area-based auto-suggestions now prefill standard role buckets (Motion/Licht + Klima/CO2/Laerm/Helligkeit/Kamera/Media).
- fix(seed): internal `ai_home_copilot_*seed*` helper entities are now ignored by seed adapter to prevent self-generated Repairs spam.
- fix(seed): noisy seed-style titles without detected entities (`CoPilot/PilotSuite Seed:*`) are filtered out before issue creation.
- docs: cloud model default in user manual updated to `qwen3.5:cloud` for Ollama Cloud alignment.
- test: zone flow helper tests updated for role-selector schema.

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
