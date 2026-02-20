# Operations (reload vs restart)

## Code updates (via HACS)
When you update the integration version via HACS, **Home Assistant must restart** to load the new Python code.

A config-entry **reload** does **not** reload changed Python modules.

## Runtime changes (no restart)
These changes should work with a **reload** of the config entry:
- Changing PilotSuite options (seed sensors, limiter, allow/block domains)
- Re-registering webhook / seed listeners

## Recommended controls
- Use the built-in HA UI: *Settings → Devices & services → PilotSuite → Reload*
- Or use the CoPilot button (if enabled): `button.ai_home_copilot_reload_config_entry`

## Why we keep this conservative
- Governance-first: avoid doing restarts automatically.
- Stability: reload is safer for small config changes.
