# Release Notes v8.4.2 (2026-02-25)

**Version:** 8.4.2  
**Date:** 2026-02-25  
**Tag:** `v8.4.2`  
**Branch:** main (HA/HACS konform)  
**Hassfest:** ✅ compliant

## Release Features
- fix: low-signal Seed-Reparaturen unterdrueckt (`on/off`, Zahlen-only, zu kurze payloads)
- fix: state-basierter Seed-Fallback nur noch fuer wirklich inhaltliche Texte aktiv
- fix: Performance-Warnschwelle fuer RAM auf `2048 MB` angehoben
- chore: Manifest-/Versionsinfos vereinheitlicht (keine widerspruechlichen Versionsanzeigen)
- Pytest (targeted): 33 passed

## HA/HACS Conformance
- manifest.json: v8.4.2
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

**PilotSuite Styx HA v8.4.2**
