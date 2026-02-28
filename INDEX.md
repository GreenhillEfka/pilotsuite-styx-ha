# PilotSuite HA Index

Quick orientation for the Home Assistant integration repository (`pilotsuite-styx-ha`).

## Current Baseline

- Version: `11.2.0`
- Domain: `ai_home_copilot`
- Product name/UI: `PilotSuite - Styx`
- Companion backend: `pilotsuite-styx-core` (Core API default port `8909`)

## Main Paths

- Integration code: `custom_components/ai_home_copilot/`
- Runtime modules: `custom_components/ai_home_copilot/core/modules/`
- Config/Options flows: `custom_components/ai_home_copilot/config_flow.py`, `custom_components/ai_home_copilot/config_options_flow.py`
- Habitus zone management: `custom_components/ai_home_copilot/config_zones_flow.py`
- Auto-setup: `custom_components/ai_home_copilot/auto_setup.py`
- Entity classifier: `custom_components/ai_home_copilot/entity_classifier.py`
- Panel setup: `custom_components/ai_home_copilot/panel_setup.py`
- Tests: `tests/` and `custom_components/ai_home_copilot/tests/`
- Docs: `docs/`, plus root files (`VISION.md`, `PROJECT_STATUS.md`, `CHANGELOG.md`)

## Key Features

- Zero-config onboarding + Auto-Setup from HA areas
- ML-style entity classifier (4-signal pipeline)
- Sidebar dashboard panel (Core ingress iframe)
- 39 modules in 4 tiers (T0-T3)
- 115+ entities, 94+ sensors
- NeuronTagResolver with bilingual patterns
- Habitus Zones v2 with area-based suggestions
- Candidate governance via Repairs
- Stable single-device identity (`styx_hub`) with legacy migration
- Seed/noise suppression and operational diagnostics

## Stats

- 579+ tests
- 325+ Python files
- 39 modules (4 tiers: T0-T3)
- 115+ entities, 94+ sensors

## Integration Focus (React-first)

- Core React dashboard is the primary UI for status, module control, chat, and Habitus operations.
- Legacy YAML dashboards remain optional compatibility mode.
- Zone creation/editing is selector-based (including role fields like brightness, humidity, CO2, heating, camera, media).
- Runtime includes module orchestration, candidate governance via Repairs, and bidirectional Core communication.

## Release/Docs

- Release notes: `RELEASE_NOTES.md`
- Changelog: `CHANGELOG.md`, `custom_components/ai_home_copilot/CHANGELOG.md`
- Handbuch: `HANDBUCH.md`
- Projektplan: `PROJEKTPLAN.md`
- Strukturplan: `STRUKTURPLAN.md`
- Setup guides: `SETUP.md`, `docs/INSTALLATION.md`, `docs/USER_MANUAL.md`
- Vision: `VISION.md`

## Release Chain

Current release: v11.2.0
