# Release Notes v8.5.0 (2026-02-25)

**Version:** 8.5.0  
**Date:** 2026-02-25  
**Tag:** `v8.5.0`  
**Branch:** main (HA/HACS konform)  
**Hassfest:** ✅ compliant

## Release Features
- fix: camera forwarding has a legacy-safe sync wrapper, avoiding `coroutine was never awaited` warnings from old call paths
- fix: performance memory warnings are less noisy (default threshold `3072 MB`, alert only after 3 consecutive breaches)
- test: dedicated regressions for camera legacy wrapper + performance streak behavior
- chore: version alignment across HA manifests to `8.5.0`
- Pytest (targeted): 25 passed

## HA/HACS Conformance
- manifest.json: v8.5.0
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

**PilotSuite Styx HA v8.5.0**
