# AI Home CoPilot (Home Assistant custom integration)

Custom integration domain: `ai_home_copilot`.

Privacy-first:
- No personal data (IPs, tokens) is shipped as defaults.
- The integration never creates automations silently (governance-first).

## Install (recommended): HACS (works with private repos)
1. Install HACS (if not already installed).
2. HACS → **Integrations** → menu (⋮) → **Custom repositories**.
3. Add this repository as type **Integration**.
   - If the repository is private, make sure HACS has a GitHub token with access.
4. Install the integration from HACS.
5. Restart Home Assistant.

### Update / Rollback
HACS creates an `update.*` entity for the repository.

- Update: use the UI or call `update.install`.
- Rollback: call `update.install` with `version` set to a Git tag (recommended) or commit SHA.

## Setup
Settings → Devices & services → Add integration → **AI Home CoPilot**

Config fields:
- Host (default: `homeassistant.local`) — set to your HA host LAN IP/hostname if needed
- Port (default: `8909`)
- API token (optional)
- Test light (optional) for the demo toggle button

Entities created:
- `binary_sensor.ai_home_copilot_online`
- `sensor.ai_home_copilot_version`
- `button.ai_home_copilot_toggle_light`

## Included blueprint
A safe A→B automation blueprint is shipped with the integration and will be installed (if missing) to:
`/config/blueprints/automation/ai_home_copilot/a_to_b_safe.yaml`

It does **not** create an automation automatically.
