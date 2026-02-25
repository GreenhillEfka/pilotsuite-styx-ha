# Release Notes v8.6.0 (2026-02-25)

**Version:** 8.6.0  
**Date:** 2026-02-25  
**Tag:** `v8.6.0`  
**Branch:** main (HA/HACS konform)  
**Hassfest:** ✅ compliant

## Release Features
- feat: generated Habitus dashboards now include camera entities as dedicated sections and live `picture-entity` cards
- feat: habitus key-signal history/logbook includes camera traces for better zone observability
- chore: version alignment across HA manifests to `8.6.0`
- Pytest (targeted): 33 passed

## HA/HACS Conformance
- manifest.json: v8.6.0
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

**PilotSuite Styx HA v8.6.0**
