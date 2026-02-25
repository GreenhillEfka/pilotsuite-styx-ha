# Release Notes v8.7.0 (2026-02-25)

**Version:** 8.7.0  
**Date:** 2026-02-25  
**Tag:** `v8.7.0`  
**Branch:** main (HA/HACS konform)  
**Hassfest:** ✅ compliant

## Release Features
- feat: Coordinator integrates Core RAG status (`/api/v1/rag/status`) into shared state payload
- feat: New sensor `sensor.ai_home_copilot_rag_pipeline` for RAG observability in HA
- fix: `sensor.py` now initializes `_LOGGER` correctly (prevents hidden runtime exceptions in dynamic sensor refresh paths)
- fix: `performance_scaling` now auto-tunes memory thresholds + hysteresis to reduce repetitive warning spam on large setups
- chore: version alignment across HA manifests to `8.7.0`
- validation: `python3 -m py_compile` passed for all changed HA modules

## HA/HACS Conformance
- manifest.json: v8.7.0
- domain Feld vorhanden
- HACS structure: OK
- hassfest: ✅ compliant

## Testing
```bash
# Syntax validation
python3 -m py_compile \
  custom_components/ai_home_copilot/sensor.py \
  custom_components/ai_home_copilot/coordinator.py \
  custom_components/ai_home_copilot/core/modules/performance_scaling.py \
  custom_components/ai_home_copilot/sensors/rag_status_sensor.py
```

---

**PilotSuite Styx HA v8.7.0**
