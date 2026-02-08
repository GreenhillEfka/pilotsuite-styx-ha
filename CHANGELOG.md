# Changelog

All notable changes to this repository are documented here.

This repository contains a Home Assistant Add-on repository (Copilot Core) and related scaffolding.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [copilot_core-v0.2.3] - 2026-02-08
### Added
- Startup log line includes the listening port.
- `/health` includes the effective port (for ops/debug).

### Changed
- Core respects add-on `log_level` option (basic Python logging setup).

## [copilot_core-v0.2.2] - 2026-02-08
### Changed
- Default port changed from 8099 to 8909 (ingress + exposed port).

## [copilot_core-v0.2.1] - 2026-02-08
### Fixed
- Startup crash in v0.2.0: DevLogs module accessed `current_app` at import time ("Working outside of application context").

## [copilot_core-v0.1.2] - 2026-02-07
### Added
- `/devlogs` HTML view for ingested DevLogs.

## [copilot_core-v0.1.1] - 2026-02-07
### Added
- `POST/GET /api/v1/dev/logs` endpoint.
- Shared token auth via add-on option `auth_token`.
