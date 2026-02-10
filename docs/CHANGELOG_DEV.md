# CHANGELOG_DEV (WIP)

Dieses Dokument listet **Work-in-progress** Änderungen, die noch **nicht** als Release getaggt sind.

- Stable Releases stehen in `CHANGELOG.md` (Tags `vX.Y.Z`).
- Dieser Dev-Log ist bewusst kurz: 1–3 Bulletpoints pro Thema.

## Unreleased (development)

### Candidate: v0.3.2-rc.1 (Tag System v0.1 HA Integration)
**Status:** Release-ready for approval (code-complete, compile-clean, integration tests scaffolding ready).

#### Added
- **Tag System Service (`tag_sync.py`):** Pulls canonical tag registry + assignments from Core.
  - `async_pull_tag_system_snapshot()`: Fetches `/api/v1/tag-system/tags` and `/assignments`, imports canonical tags, replaces assignment snapshot, materializes labels.
  - Respects tag materialization policy: `confirmed` tags → HA labels, `pending`/`learned`/`candidate` → skipped unless explicitly confirmed.
  - Stores tags/assignments/metadata in HA `.storage` for diffing and history tracking.

- **Tag Registry Store (HA-side `tag_registry.py`):**
  - Local tag registry mirroring Core canonical tags (title, icon, color, display names).
  - Assignment snapshot tracking (subject_kind:subject_id → tag_ids).
  - User-alias support: discovers existing HA labels as `user.*` read-only mirrors.
  - Labeling API adapters for entity/device/area registries (defensive signature compatibility for multiple HA versions).

- **Label Materialization (`async_sync_labels_now()`):**
  - Ensures HA labels exist for confirmed tags (creates with icon/color if available).
  - Applies labels to supported subjects (entity/device/area).
  - Imports and preserves existing HA labels as read-only `user.*` aliases.
  - Defensive error handling for older HA versions lacking label support.

#### Tests
- Unit tests: `test_tag_utils.py` (7 tests for tag logic, user-tag detection, materialization policy).
- Integration test scaffolding: `test_tag_sync_integration.py` (mock-based roundtrip validation, ready for pytest runner).
- Compilation: `python3 -m compileall custom_components/ai_home_copilot` ✓.

#### Security
- No external API calls except to Core (validated token-based auth inherited from integration config).
- Labels are materialized locally; no Habitus data or learning artifacts leave Home Assistant.

#### Breaking Changes
- None (new module).

#### Notes
- Full HA integration tests require pytest + Home Assistant test framework (deferred to CI phase).
- Pairs with Core v0.4.0-rc.1 or later.

### In Arbeit
- Repairs/Blueprints: governance-first Apply-Flow (confirm-first) + Transaction-Log (WIP)
- dev_surface: UI Buttons + PilotSuite toggle (WIP integriert)
- diagnostics_contract: contract-shaped Diagnostics + Support-Bundle (WIP integriert) 
