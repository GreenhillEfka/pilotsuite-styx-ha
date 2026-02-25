# Release Notes v8.1.0 (2026-02-25)

**Version:** 8.1.0  
**Date:** 2026-02-25  
**Tag:** `v8.1.0`  
**Branch:** main (HA/HACS konform)  
**Hassfest:** ✅ compliant

## Release Features
- HACS Release Pipeline (v8.1.0)
- HA Dashboard API Endpoints (v7.11.0)
- LLM Provider Fallback (v7.11.0)
- SearXNG Auto-Integration (v7.11.1)
- Direct Web Search API Endpoints
- HASSFest Fix (domain Feld in manifest.json)
- Pytest: 608 tests passing

## HA/HACS Conformance
- manifest.json: v8.1.0
- domain Feld hinzugefügt (falsches `domains` war das Problem!)
- HACS structure: OK
- hassfest: ✅ compliant

## Testing
```bash
# Run tests
pytest -q tests/test_*.py
```

---

**PilotSuite Styx HA v8.1.0** 🧠🏠  
**Release Iteration Maschine — v8.1.0** 🦝🔧🌙
