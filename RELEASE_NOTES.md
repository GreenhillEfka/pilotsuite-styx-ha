# Release Notes v8.9.0 (2026-02-25)

**Version:** 8.9.0
**Date:** 2026-02-25
**Tag:** `v8.9.0`
**Branch:** main (HA/HACS konform)
**Hassfest:** ✅ compliant

## Release Features
- feat: Habitus zone form now supports role-based selectors:
  - `brightness`, `noise`, `humidity`, `co2`, `temperature`, `heating`, `camera`, `media`.
- feat: area-driven auto-suggestions now prefill standard role buckets, not only generic optional entities.
- fix: seed adapter ignores internal `ai_home_copilot_*seed*` helper entities to prevent self-generated Repairs spam.
- fix: noisy `CoPilot/PilotSuite Seed:*` titles without detected target entities are filtered before candidate creation.
- docs: cloud fallback model default in user manual updated to `qwen3.5:cloud`.
- chore: manifest versions aligned to `8.9.0`.

## HA/HACS Conformance
- manifest.json: v8.9.0
- domain Feld vorhanden
- HACS structure: OK
- hassfest: ✅ compliant

## Testing
```bash
# Syntax validation
python3 -m py_compile \
  custom_components/ai_home_copilot/__init__.py \
  custom_components/ai_home_copilot/config_zones_flow.py \
  custom_components/ai_home_copilot/seed_adapter.py \
  custom_components/ai_home_copilot/config_options_flow.py \
  custom_components/ai_home_copilot/config_schema_builders.py
```

---

**PilotSuite Styx HA v8.9.0**
