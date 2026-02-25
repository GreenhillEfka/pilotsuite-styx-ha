# Release Notes v8.4.1 (2026-02-25)

**Version:** 8.4.1  
**Date:** 2026-02-25  
**Tag:** `v8.4.1`  
**Branch:** main (HA/HACS konform)  
**Hassfest:** ✅ compliant

## Release Features
- chore: Version sync with Core `v8.4.1` (paired deployment clarity)
- no functional HA delta compared to `v8.4.0`
- feat: entity profile runtime select (UI dropdown for Core model/provider)
- fix: knowledge_graph guard for KeyError safety
- fix: guard all hass.data access against KeyError
- fix: inspector_sensor key path fix
- feat: Brain Graph + Habitus Rules sensors
- feat: Core API integration improvements
- feat: dashboard improvements
- feat: Per-module options submenu
- feat: Core module control API
- Pytest: 608 passed

## HA/HACS Conformance
- manifest.json: v8.4.1
- domain Feld vorhanden
- HACS structure: OK
- hassfest: ✅ compliant

## Testing
```bash
# Run tests
pytest -q tests/test_*.py
# 608 passed, 1 skipped
```

---

**PilotSuite Styx HA v8.4.1** 🧠🏠  
**Release Iteration Maschine — v8.4.1** 🦝🔧🌙
