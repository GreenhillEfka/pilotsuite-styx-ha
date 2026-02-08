# Start here — Home Assistant CoPilot (Core add-on)

This repository ships the **Copilot Core** Home Assistant add-on.

## Principles
- Local-first by default
- Privacy-first
- Governance-first (suggestions before actions)
- Safe defaults (bounded stores, optional persistence)

## Quick ops checks

### Default port
- Default Core port: **8909**

### Verify the Core is reachable
From your LAN browser:
- `http://<HA_IP>:8909/health`
- `http://<HA_IP>:8909/version`

Tip: If `homeassistant.local` does not resolve reliably, use the HA IP.

### Logs
On startup, the Core logs a line like:
- `Copilot Core vX.Y.Z listening on http://0.0.0.0:8909`

## Docs
- Ethics & Governance: `docs/ETHICS_GOVERNANCE.md`
- Changelog: `CHANGELOG.md`
- Add-on changelog (HA UI): `addons/copilot_core/CHANGELOG.md`

If a guiding principle blocks a clearly better solution, we revisit it explicitly (issue + rationale + safeguards + doc update).
