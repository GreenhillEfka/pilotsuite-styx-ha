# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-02-07
### Added
- Core API v1 capabilities: sensor `AI Home CoPilot core API v1` (shows supported/not_supported/unauthorized) + button to fetch capabilities now.
- Capabilities ping on startup (best-effort, read-only; old cores return 404).
- HA → Core Events forwarder (opt-in): forwards state changes for Habitus zone entities to Core `/api/v1/events` in small batches.

### Changed
- Candidate lifecycle: added `defer` (“remind me later”) option in Repairs flows.

## [0.2.0] - 2026-02-07
### Added / Included (foundation bundle)
- Stable connectivity entities: online + core version.
- Webhook push mode + optional watchdog polling fallback.
- Governance UX: Repairs + shipped safe A→B blueprint (no silent automations).
- Log analysis + reversible fixer (disable broken custom integration via rename + rollback).
- Overview report generator + publish/download flow.
- Seeds adapter (optional) + limiter + allow/block domains.
- Dev surface:
  - DevLogs push (opt-in) + in-HA fetch
  - HA Diagnostics download (sanitized)
- MediaContext v0.1 (read-only): music vs TV/other signals (Spotify/Sonos/TV).
- Habitus zones v0.1:
  - UX wizard (create/edit/delete) with required motion/presence + lights
  - validate button + zones count
  - dashboard YAML generator + publish/download
- Modular runtime skeleton (legacy wrapper) to enable 20+ modules without breaking behavior.

### Notes
- Safe defaults: no personal IPs/entity_ids shipped; secrets are not exposed via entities.
- HACS updates require a Home Assistant restart.

## [0.1.19] - 2026-02-07
### Added
- Habitus zones (UX): Options wizard (create/edit/delete) with required motion/presence + lights.
- Habitus dashboard generator: create + publish YAML dashboard views per zone.

### Changed
- Habitus zones store now enforces the minimum requirements on save.

## [0.1.18] - 2026-02-07
### Added
- Dev surface documentation and HA Diagnostics support (sanitized).

## [0.1.17] - 2026-02-07
### Added
- MediaContext v0.1 (read-only): music vs TV/other signals.
- Config via dashboard-editable text entities (CSV lists of media players).

## [0.1.15] - 2026-02-07
### Added
- Documentation pack: operations, dashboard, privacy/governance, DevLogs, release checklist.

### Changed
- Manifest now links to the real documentation/issue tracker.

## [0.1.14] - 2026-02-07
### Added
- Button to fetch last DevLogs items from the Core and show them in a persistent notification.

## [0.1.13] - 2026-02-07
### Fixed
- Accept full URL pasted into the host field (avoid malformed `http://http://...`).

## [0.1.12] - 2026-02-07
### Added
- DevLogs manual buttons: push test + push latest.
- Option labels for DevLogs settings.

## [0.1.11] - 2026-02-07
### Added
- Opt-in DevLogs push: sanitized HA log snippets are sent to the Core endpoint.

## [0.1.10] - 2026-02-07
### Fixed
- Options flow 500 on HA 2026.x (OptionsFlow `config_entry` became read-only).

## [0.1.9] - 2026-02-07
### Added
- Dashboard-editable config entities (`text.*` / `number.*`) to reduce reliance on Options UI.

## [0.1.4] - 2026-02-07
### Added
- Overview report generator + publish/download flow.

## [0.1.0] - 2026-02-07
### Added
- Initial HACS integration scaffold (online/version entities + safe test button).
