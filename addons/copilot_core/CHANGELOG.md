# Add-on Changelog – AI Home CoPilot Core (MVP)

This file exists so Home Assistant can show an add-on changelog.
For full history, see the repository-level `CHANGELOG.md`.

## 0.2.3
- Logs the listening port on startup.
- `/health` includes the effective port.
- Respects add-on `log_level` option.

## 0.2.2
- Default port changed from 8099 to 8909.

## 0.2.1
- Fix startup crash (DevLogs used current_app at import time).
