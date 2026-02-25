# Release Notes v8.9.1 (2026-02-25)

**Version:** 8.9.1  
**Date:** 2026-02-25  
**Tag:** `v8.9.1`  
**Branch:** main (HA/HACS konform)

## Highlights
- repairs: automatische Bereinigung alter Seed-Noise-Reparaturmeldungen (`CoPilot Seed: on/5/17/...`) beim Setup.
- repairs: interne Seed-Quellen (`ai_home_copilot_*seed*`) werden auch nach Upgrade nicht mehr als UI-Restproblem stehen gelassen.
- branding: Integration liefert jetzt aktive Brand-Assets unter `custom_components/ai_home_copilot/brands/` (`icon.png`, `logo.png`).
- i18n: Reparaturtitel von `CoPilot Seed` auf `PilotSuite suggestion` / `PilotSuite Vorschlag` umgestellt.
- docs: Installations-/Setup-Anleitungen auf aktuelle HA/Core-Architektur (`:8909`) und Release-Line aktualisiert.

## Version Sync
- `custom_components/ai_home_copilot/manifest.json`: `8.9.1`
- `manifest.json` (Repo): `8.9.1`

## Validation
```bash
cd pilotsuite-styx-ha
pytest -q tests/test_repairs_cleanup.py tests/test_seed_adapter.py
```

---

**PilotSuite Styx HA v8.9.1**
