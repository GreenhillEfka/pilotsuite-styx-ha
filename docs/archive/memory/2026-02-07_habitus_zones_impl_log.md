# Worklog — 2026-02-07 — Habitus zones (Phase 1)

## Goal
Implement Habitus zones as a user-curated, local-first selection layer for entities, independent of HA Areas.

## Implemented (Phase 1)
- Store: `ai_home_copilot.habitus_zones` (HA storage), keyed by config entry id.
- Text entity: `AI Home CoPilot habitus zones (json)`
  - Value is JSON list of zones: `[{id,name,entity_ids:[...]}]`
  - On set: validates/normalizes and saves; shows persistent notification.
- Button: `AI Home CoPilot validate habitus zones`
  - Checks referenced entity_ids exist (best-effort via current states) and reports missing.
- Sensor: `AI Home CoPilot habitus zones count`
  - Updates via dispatcher signal on save.

## Notes
- Safe default: no zones configured => empty list.
- No HA metadata changes (areas/labels) are performed.
- No dashboards are generated yet; this is just the configuration + validation substrate.

## Next
- Phase 2: nicer wizard UI (options/config flow) + optional per-zone dashboard generator (YAML) with user import.
- Connect zones into MediaContext/Mood/Habitus modules as the preferred scope.
