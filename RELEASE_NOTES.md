# Release Notes v8.8.0 (2026-02-25)

**Version:** 8.8.0  
**Date:** 2026-02-25  
**Tag:** `v8.8.0`  
**Branch:** main (HA/HACS konform)  
**Hassfest:** ✅ compliant

## Release Features
- feat: Habitus options flow switched to React-first dashboard mode (`dashboard_info` menu entry).
- feat: Legacy YAML dashboard generation/refresh in setup is now opt-in (disabled by default).
- chore: updated strings + tests for the new dashboard menu concept.
- chore: version alignment across HA manifests to `8.8.0`.
- validation: `python3 -m py_compile` passed for changed HA modules.

## HA/HACS Conformance
- manifest.json: v8.8.0
- domain Feld vorhanden
- HACS structure: OK
- hassfest: ✅ compliant

## Testing
```bash
# Syntax validation
python3 -m py_compile \
  custom_components/ai_home_copilot/__init__.py \
  custom_components/ai_home_copilot/config_options_flow.py \
  custom_components/ai_home_copilot/config_schema_builders.py
```

---

**PilotSuite Styx HA v8.8.0**
