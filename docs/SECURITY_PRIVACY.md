# Security & Privacy

## Threat model (practical)
- Your Home Assistant instance contains sensitive household information.
- Any feature that exports data (logs, timelines, device lists) must be treated as sensitive.

## Defaults
- Privacy-first defaults: no IPs/entity IDs shipped.
- No silent automations.
- DevLogs pipeline is disabled by default.

## Tokens / keys
- Keep tokens out of logs, reports, and entity state.
- Prefer storing secrets in:
  - Config entry data (integration)
  - Supervisor add-on options (core)

## Network
- Prefer local LAN access.
- Avoid exposing the Core port to the Internet.

## Reporting
- Reports are generated locally.
- Publishing a report to `/local/…` is an explicit button action.

## Core v1: Events forwarder (opt-in)
If enabled, the integration can forward a **privacy-first allowlist** of events to Copilot-Core.

- `state_changed`: only for entities included in Habitus zones.
  - Only forwards the state change + a tiny allowlist of state attributes:
    - `light`: `brightness`, `color_temp`, `hs_color`
    - `media_player`: `volume_level`
- `call_service` (optional): forwards intent-like service calls **only when** they target Habitus zone entities.
  - Service data is stripped (only the domain/service name and the targeted entity_ids are kept).
- Event `id` uses `event_type:context.id` when available to support best-effort idempotency.
- Optional: **persistent forwarder queue** (disabled by default):
  - Stores unsent forwarder events in Home Assistant's local `.storage/` (per config entry).
  - Bounded queue with **drop-oldest** policy.
  - Persisted in a rate-limited manner (flush interval) to avoid blocking the event loop.
