# Habituszonen (Habitus Zones)

## Motivation
Home Assistant installations often grow into an entity “wirrwarr”. Habituszonen are a user-defined, curated layer that:
- selects a **small set of relevant entities** per zone,
- makes the system **slimmer, explainable, and maintainable**,
- provides a stable foundation for **UX dashboards**, analytics, and later suggestions.

Think: **"my real rooms as I live in them"** (habitus), not necessarily HA Areas/Devices.

## Principles
- **Local-first / privacy-first:** zones and selections live locally.
- **Governance-first:** CoPilot may *suggest* assignments/tags; it must not silently rewrite HA metadata.
- **Safe defaults:** if no zones are configured, nothing changes.

## Data model (proposal)
A Habituszone contains:
- `id` (stable key): e.g. `wohnbereich`
- `name` (display): e.g. "Wohnbereich"
- `entity_ids` (explicit allowlist)
- optional `tags` / `labels` (if HA Labels are available) used as inclusion rules
- optional `kinds` to structure UX panels:
  - `presence` (motion/presence)
  - `climate` (temp/humidity)
  - `light` (brightness/lights)
  - `media` (sonos/spotify/tv)
  - `energy` (power meters)

## Configuration UX (incremental)
### Phase 1 (fast, robust)
- A dashboard-editable text entity per zone OR a single JSON/YAML text config entity.
- Buttons:
  - "validate zones" (check entity existence)
  - "reload zones"

### Phase 2 (nice UX)
- Options flow / config flow wizard:
  - create zone
  - add/remove entities (multi-select)
  - set minimal "required" entity types (optional)

### Phase 3 (labels/tags integration)
- If HA Labels exist: allow zone inclusion via labels.
- CoPilot may suggest labels via Repairs (confirm-gated):
  - "Add label room:wohnbereich to these entities"

## Runtime usage
Once zones exist, other modules consume zones as their primary scope:
- MediaContext: per-zone music vs tv signals
- Mood: per-zone mood proxy + house mood aggregation
- Habitus miner: routines per zone
- Suggestions: only use zone-curated entities

## UX dashboards (PilotSuite)
Habituszonen enable generating a per-zone dashboard view:
- key sensors (temp/humidity/occupancy)
- trends (history graphs)
- media controls
- activity summary (time occupied)

**Recommended:** generate YAML files locally and let user import (governance-first).

## Open questions (for implementation)
- Does your HA version support Labels? (If not, we keep everything internal.)
- How strict should "minimum required" be? (Warn vs block.)
- Should zones map to HA Areas by default, or be independent by default?
