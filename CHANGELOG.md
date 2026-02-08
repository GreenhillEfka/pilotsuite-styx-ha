# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-02-08
### Added
- Governance-Kern: **Candidates Store** (persistenter Lifecycle: new/offered/deferred/accepted/dismissed, bounded, anti-nagging).
- **Dev Surface v0.1**: Diagnostics-Snapshot (devlogs excerpt + error digest), Core-Ping + Debug-Toggle (30m) + Clear Digest (Buttons, optional in PilotSuite).
- **Diagnostics Contract v0.1** (privacy-first, bounded): HA diagnostics payload contract-shaped.
- **Tag Registry v0.1** (minimal): Tag-Registry Store + Services + Sync-Button (HA Labels materialisieren; learned/candidate nur nach Bestätigung).
- **Graph→Candidates Bridge v0.1**: Buttons zum Preview/Offer von Graph-Kandidaten (Core Endpoint erforderlich).
- **Repairs→Blueprint Apply v0.1**: confirm-first Flow, installiert shipped Blueprint (A→B safe) und kann daraus eine Automation erstellen; TX-Log (bounded) für Audit.

### Notes
- Einige Features (Graph→Candidates) benötigen ein passendes Core-Update (siehe Core Release Notes).
- HACS Update erfordert Home Assistant Neustart.

## [0.2.21] - 2026-02-08
### Changed
- PilotSuite: Safety-Backup Buttons werden standardmäßig nicht im Dashboard gezeigt (Option in den Integration-Settings), damit Updates/Neustarts nicht versehentlich durch laufende Backups blockiert werden.

## [0.2.20] - 2026-02-08
### Added
- Events forwarder: optionale **persistente Queue** (unsent Events über HA-Restarts behalten), bounded + drop-oldest.
- Forwarder-Status zeigt persistente Queue-Länge + Drop-Zähler.

### Fixed
- Forwarder-Reliability: bei POST-Fehlern wird der Batch wieder in die Queue gelegt (geht nicht verloren).

## [0.2.19] - 2026-02-08
### Added
- Core Graph: neuer Button "fetch core graph state" (zeigt `/api/v1/graph/state` als Notification), um Brain-Graph Feeding leicht zu verifizieren.

## [0.2.18] - 2026-02-08
### Fixed
- PilotSuite: Safety-Backup Buttons haben jetzt stabile Entity-IDs (behebt "Entität nicht gefunden" Warnungen im Dashboard).


## [0.2.17] - 2026-02-08
### Added
- Safety Backup ("Safety Point"): neue Buttons zum Starten eines HA-Backups (bevor Updates/Experimente laufen) + Statusanzeige.
  - Nutzt bevorzugt `backup.create_automatic` (HA OS/supervised), fallback `backup.create`.

## [0.2.16] - 2026-02-08
### Added
- Events forwarder: optional forwarding of `call_service` events (privacy-first; only when targets match Habitus zone entities; strict domain allowlist).
- Events forwarder: best-effort event idempotency (event `id` = `event_type:context.id` when available) + configurable in-memory TTL.

### Changed
- Events forwarder (state_changed): allowlist state attributes (lights: brightness/color_temp/hs_color; media_player: volume_level). All other state attributes remain stripped.

## [0.2.15] - 2026-02-08
### Fixed
- HA errors digest: zeigt jetzt vollständige Log-Entries inkl. multiline Tracebacks (statt nur "Traceback…" Zeilen) und fokussiert auf ai_home_copilot-relevante Fehler.

## [0.2.14] - 2026-02-08
### Improved
- Habitus-Dashboard UX (Deutsch): weniger redundante Überschriften, mehr Messwert-Graphen (Helligkeit/Temperatur/Luftfeuchte/CO₂/Lärm/Luftdruck), Motion zeigt „letzte Änderung“.
- Licht: Sammelschalter (Header-Toggle) + „alle umschalten“-Button.
- Optional: Habitus-Zonen Durchschnitts-Sensoren (Temperatur Ø / Luftfeuchte Ø), wenn >2 Quellen in der Zone vorhanden sind.
- Duplikate in „Weitere Entitäten“ reduziert (keine Doppelanzeigen bei gemischter `entity_ids` + `entities` Konfiguration).
- PilotSuite (Deutsch): Quicklinks, Generate-only Fokus (Download bleibt optional), Dev/Fehler-Buttons gebündelt.
- PilotSuite: optionaler Block „Systemressourcen“ (CPU/RAM/Load/Disk), falls entsprechende Sensoren existieren.

## [0.2.13] - 2026-02-08
### Fixed
- Events forwarder queue bug: events were not enqueued when the queue was empty (prevented any POST to Core).
- Removed Habitus zones bulk TextEntity from the `text` platform (HA state length limit caused errors). Bulk edit remains in OptionsFlow.
- Config snapshot export/publish moved to executor (avoids blocking I/O in event loop warnings).

## [0.2.12] - 2026-02-08
### Added
- Habitus zones: optional categorized `entities:` mapping (named signals like brightness/heating/humidity/co2/cover/lock/door/window/media).

### Changed
- Habitus zones wizard now stores `entities` roles (motion/lights/other) for better UX.
- Habitus zones dashboard generator uses named sections (Helligkeit, Heizung, Luftfeuchte, Schloss, Tür/Fenster, Rollo, Media/Lautstärke, CO₂, …).

## [0.2.11] - 2026-02-08
### Fixed
- Events forwarder reliability: schedule tasks strictly on the event loop and record send status (sending/sent/error/cancelled).

## [0.2.10] - 2026-02-08
### Changed
- Forwarder status now shows: last seen event + queue length (helps debug why events are not reaching Core).

## [0.2.9] - 2026-02-08
### Fixed
- HA 2026.x thread-safety: Core API v1 status sensor updates are now scheduled on the event loop (prevents async_write_ha_state warnings/crash risk).

### Added
- Forwarder status button: shows subscribed entity count + last send/error.

## [0.2.8] - 2026-02-08
### Added
- Ops: HA error digest (manual button + optional auto-digest every N seconds).
- Dashboards: keep a stable "latest" filename on generate/publish, while still writing timestamped archives.

## [0.2.7] - 2026-02-08
### Fixed
- Events forwarder thread-safety: avoid calling `hass.async_create_task` outside the event loop (prevents HA warnings/crash risk).

## [0.2.6] - 2026-02-08
### Added
- Habitus zones bulk editor (OptionsFlow): paste YAML/JSON to create/update zones quickly.
- Core events fetch button: shows last 20 `/api/v1/events` items in a persistent notification.
- PilotSuite dashboard generator (governance-first): generate + download a multi-view YAML dashboard.

### Fixed
- Event forwarder now stores zone_ids + old/new state inside event attributes so Core keeps the data.

## [0.2.5] - 2026-02-08
### Fixed
- OptionsFlow menu labels missing in HA (adds `options.*` translation section for EN/DE).

## [0.2.4] - 2026-02-08
### Fixed
- German UI: Options/fields now show proper labels (adds `translations/de.json`).
- Integration branding: adds `custom_components/ai_home_copilot/icon.png` + `logo.png` (fixes “icon not available”).

## [0.2.3] - 2026-02-08
### Added
- CI: basic syntax + JSON validation on push/PR.

### Changed
- Declutter: advanced config entities and dev/demo buttons are now disabled by default (can be enabled in HA entity registry).

## [0.2.2] - 2026-02-07
### Added
- Local config snapshot export (generate + download link). Tokens are redacted by default.
- Snapshot import via OptionsFlow (Backup/restore) with confirmation + automatic reload.

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
