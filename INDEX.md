# PilotSuite HA Index

Quick orientation for the Home Assistant integration repository (`pilotsuite-styx-ha`).

## Current Baseline

- Version: `9.0.0`
- Domain: `ai_home_copilot` (kept for backward compatibility)
- Product name/UI: `PilotSuite - Styx`
- Companion backend: `pilotsuite-styx-core` (Core API default port `8909`)

## Main Paths

- Integration code: `custom_components/ai_home_copilot/`
- Runtime modules: `custom_components/ai_home_copilot/core/modules/`
- Config/Options flows: `custom_components/ai_home_copilot/config_flow.py`, `custom_components/ai_home_copilot/config_options_flow.py`
- Habitus zone management: `custom_components/ai_home_copilot/config_zones_flow.py`
- Tests: `tests/` and `custom_components/ai_home_copilot/tests/`
- Docs: `docs/`, plus root files (`VISION.md`, `PROJECT_STATUS.md`, `CHANGELOG.md`)

## Integration Focus (React-first)

- Core React dashboard is the primary UI for status, module control, chat, and Habitus operations.
- Legacy YAML dashboards remain optional compatibility mode.
- Zone creation/editing is selector-based (including role fields like brightness, humidity, CO2, heating, camera, media).
- Runtime includes module orchestration, candidate governance via Repairs, and bidirectional Core communication.

## Key Features

- Zero-config onboarding + connection normalization
- Stable single-device identity (`styx_hub`) with legacy migration
- Module runtime loader (31 modules)
- Candidate poller + Repairs decision sync-back
- Habitus zones v2 with area-based suggestions and role mapping
- Seed/noise suppression and operational diagnostics

## Release/Docs

- Release notes: `RELEASE_NOTES.md`
- Changelog: `CHANGELOG.md`, `custom_components/ai_home_copilot/CHANGELOG.md`
- Setup guides: `SETUP.md`, `docs/INSTALLATION.md`, `docs/USER_MANUAL.md`
- Vision: `VISION.md`
