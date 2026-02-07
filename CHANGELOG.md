# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
