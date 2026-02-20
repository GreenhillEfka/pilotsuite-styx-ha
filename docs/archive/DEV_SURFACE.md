# Dev surface (observability)

Goal: make development safe and fast without breaking the core principles.

## What we use

### 1) Lovelace "Mini" / PilotSuite (always works)
- Use dashboard entities/buttons as the stable control surface.
- Keep a dedicated "Dev" section with:
  - online/version
  - devlog push test/latest
  - devlogs fetch (shows last items inside HA)
  - analyze logs
  - reload

### 2) HA error digest (local)
- Optional operator tool: read and filter the last lines of `/config/home-assistant.log` and show only relevant errors/warnings as a persistent notification.
- Supports:
  - Manual button: `fetch HA errors`
  - Auto-digest (opt-in): every N seconds (default 300)

### 3) DevLogs pipeline (HA → Core)
- Browser access to `/devlogs` may show `unauthorized` when `auth_token` is set.
- The recommended operator workflow is:
  1) press `devlog push test`
  2) press `devlogs fetch`
  3) review the persistent notification

See: `docs/DEVLOGS.md`

### 3) Home Assistant Diagnostics (download)
This integration provides a HA-native diagnostics download (sanitized).
- Settings → Devices & services → AI Home CoPilot → … → **Download diagnostics**

Diagnostics must never include tokens.
