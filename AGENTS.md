# Repository Guidelines

## Project Structure & Module Organization
This repository contains the Home Assistant integration for PilotSuite Styx.

- Core integration code: `custom_components/ai_home_copilot/`
- Entity/platform modules: `custom_components/ai_home_copilot/*.py`
- Runtime/modules: `custom_components/ai_home_copilot/core/modules/`
- Translations: `custom_components/ai_home_copilot/translations/`
- Tests: `tests/` and `custom_components/ai_home_copilot/tests/`
- Docs: `docs/`, project notes in root (`VISION.md`, `PROJECT_STATUS.md`)

This repo is tightly coupled with `pilotsuite-styx-core`; keep API contracts and versioning aligned across both.

## Build, Test, and Development Commands
- Full test suite: `pytest -q`
- Focused config/zone tests: `pytest -q tests/test_config_zones_flow.py tests/test_config_options_flow_merge.py`
- Focused identity/migration tests: `pytest -q tests/test_device_identity.py tests/test_connection_config_migration.py`

Run targeted tests while iterating, then run full suite before pushing.

## Coding Style & Naming Conventions
- Python only; 4-space indentation.
- Use type hints for modified/new public functions.
- Naming: `snake_case` (functions/variables), `PascalCase` (classes), `UPPER_CASE` (constants).
- Preserve backwards compatibility for config keys and entity unique IDs.
- Prefer small, explicit functions over broad utility blobs.

## Testing Guidelines
- Framework: `pytest`.
- File naming: `test_*.py`; test names should describe expected behavior.
- Add a regression test for every bug fix (config flows, migration, API compatibility, dashboard generation).
- Keep tests deterministic and local (no hard network dependency).

## Commit & Pull Request Guidelines
- Commit messages follow a light “conventional commits” pattern used in this repo:
  `feat: ...`, `fix: ...`, `chore: ...`, and release commits like `v10.1.3: ...`.
- One logical change per commit.
- PR/release notes should include:
  - problem and user-visible impact
  - touched modules/files
  - test evidence (`N passed`)
  - manifest/changelog updates when version changes

## Security & Configuration Tips
- Never commit real tokens, secrets, or private IP credentials.
- Keep auth behavior compatible with both `Authorization: Bearer` and `X-Auth-Token`.
- Validate failover behavior when Core is unreachable or partially available.
