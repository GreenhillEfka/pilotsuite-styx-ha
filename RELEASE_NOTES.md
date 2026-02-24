# Release Notes v8.0.0 (2026-02-24)

**Version:** 8.0.0  
**Date:** 2026-02-24  
**Tag:** `v8.0.0`  
**Branch:** main (direct release)  
**HA hassfest:** ✓ compliant

## Major Release Features
- Scene Pattern Extraction (v7.11.1)
- Routine Pattern Extraction (v7.11.1)
- Dashboard API endpoints (/dashboard/health, /dashboard/brain-summary)
- SearXNG auto-integration in llm_provider.py
- Direct Web Search API (/api/v1/llm/search, /api/v1/llm/status)
- Anomaly Detector Fixes (bool type + last true anomaly)
- Extend routine pattern extraction with scene grouping
- Pytest: 608 tests passing

## HA/HACS Conformance
- manifest.json: v8.0.0
- HACS structure: OK
- hassfest: ✓ compliant

## Testing
```bash
# Run tests
pytest -q tests/test_*.py
```

---

**PilotSuite Styx HA v8.0.0** 🧠🏠  
**Groky Dev Check — Final Release Build v8.0.0** 🦝🔧🌙
