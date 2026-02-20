# Lovelace dashboard view (recommended)

Goal: show everything needed to operate PilotSuite in one place.

## What to add
Create a new dashboard (or a new view tab) and add an **Entities** card with:

- `binary_sensor.ai_home_copilot_online`
- `sensor.ai_home_copilot_version`
- `button.ai_home_copilot_analyze_logs`
- `button.ai_home_copilot_rollback_last_fix`
- `button.ai_home_copilot_generate_ha_overview`
- `button.ai_home_copilot_download_ha_overview`

Optional (recommended): add the HACS update entity for this repository (name varies), e.g.
- `update.ai_home_copilot` / `update.hacs_*` (search for `update.*` containing "CoPilot")

## YAML example
```yaml
type: entities
title: PilotSuite
show_header_toggle: false
entities:
  - entity: binary_sensor.ai_home_copilot_online
  - entity: sensor.ai_home_copilot_version
  - type: divider
  - entity: button.ai_home_copilot_analyze_logs
  - entity: button.ai_home_copilot_rollback_last_fix
  - type: divider
  - entity: button.ai_home_copilot_generate_ha_overview
  - entity: button.ai_home_copilot_download_ha_overview
```

Notes:
- We do **not** auto-create dashboards from the integration (governance-first).
- Config (host/port/token) is kept in the integration options UI.
