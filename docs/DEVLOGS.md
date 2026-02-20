# DevLogs (HA → Core) — Debug pipeline

DevLogs exist to make development and troubleshooting practical **without** copying raw Home Assistant logs around.

## Principles
- **Opt‑in**: disabled by default.
- **Sanitized**: redact obvious secrets; keep payload small.
- **Deduplicated**: identical snippets are not resent.
- **Best‑effort**: failure to push must never break the integration.

## What is pushed
- Only **small traceback blocks** that reference `ai_home_copilot`.
- Example kinds:
  - `devlog_test`
  - `ha_log_snippet`

## Where it goes
- Core endpoint (default): `POST /api/v1/dev/logs`
- Core can expose:
  - `GET /api/v1/dev/logs?limit=10`

## Security notes
- Core may require a shared token (`X-Auth-Token`).
- Do not expose the Core LAN port publicly.

## Controls
- Options:
  - `devlog_push_enabled`
  - `devlog_push_interval_seconds`
  - `devlog_push_path`
  - `devlog_push_max_lines`
  - `devlog_push_max_chars`
- Buttons:
  - "devlog push test"
  - "devlog push latest"
  - "devlogs fetch" (shows last items inside HA)
