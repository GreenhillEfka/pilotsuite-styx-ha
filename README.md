# AI Home CoPilot (custom integration)

This folder contains a Home Assistant custom integration: `ai_home_copilot`.

## Install
Copy `custom_components/ai_home_copilot` into your HA `/config/custom_components/`.

Example:
- `/config/custom_components/ai_home_copilot/__init__.py`
- ...

Then restart Home Assistant.

## Setup
Settings → Devices & services → Add integration → **AI Home CoPilot**

Config fields:
- Host (default: `homeassistant.local`) — set to your HA host LAN IP/hostname if needed
- Port (default: `8909`)
- API token (optional)
- Light entity_id for test button (optional)

Entities created:
- `binary_sensor.ai_home_copilot_online`
- `sensor.ai_home_copilot_version`
- `button.ai_home_copilot_toggle_light`
