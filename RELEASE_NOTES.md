# Release Notes v8.11.0 (2026-02-25)

**Version:** 8.11.0  
**Date:** 2026-02-25  
**Tag:** `v8.11.0`  
**Branch:** main (HA/HACS konform)

## Highlights
- core pairing: abgestimmt auf Core `v8.11.0` (System-Overview APIs fuer Dashboard Health/Resources/Sensorstatus).
- docs: Setup-/Installationsdoku auf `8.11.0` und neues System-Overview-Konzept aktualisiert.
- version sync: Manifeste auf `8.11.0` vereinheitlicht.

## Version Sync
- `custom_components/ai_home_copilot/manifest.json`: `8.11.0`
- `manifest.json` (Repo): `8.11.0`

## Validation
```bash
cd pilotsuite-styx-ha
python3 -m py_compile custom_components/ai_home_copilot/core/modules/homekit_bridge.py
pytest -q tests/test_repairs_cleanup.py tests/test_seed_adapter.py tests/test_config_zones_flow.py
```

---

**PilotSuite Styx HA v8.11.0**
