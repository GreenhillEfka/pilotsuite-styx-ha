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
