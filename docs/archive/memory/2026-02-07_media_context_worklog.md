# Worklog — 2026-02-07 — MediaContext v0.1

## Goal
Implement MediaContext v0.1 as read-only signals (Music vs TV/Other) without breaking core stability.

## Done
- Implemented event-driven MediaContext coordinator watching configured media_player entities.
- Added config keys (music players CSV + TV players CSV) with safe defaults (empty).
- Exposed dashboard-editable text entities for both CSV lists.
- Added sensors/binary_sensors for:
  - music_active, tv_active
  - music_now_playing, tv_source
  - primary areas
  - active counts
- Wired setup/unload into the existing legacy module flow.
- Updated Options UI labels (strings.json) and config_flow normalization.
- Tagged + released integration v0.1.17.

## Notes / Caveats
- Music active is conservative: only `state == playing`.
- TV active is pragmatic: any state not in (off/standby/unavailable/unknown).
- `/devlogs` browser endpoint remains protected when core auth_token is set; devlogs fetch in HA is the recommended verification path.

## User actions to validate
1) Update integration to v0.1.17 via HACS + restart HA.
2) Set:
   - AI Home CoPilot media music players (csv): spotify + sonos
   - AI Home CoPilot media TV players (csv): smarttv + apple tv
3) Play music / turn on TV; verify new sensors in HA.
