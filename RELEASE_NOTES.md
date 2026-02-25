# Release Notes v8.1.1 (2026-02-25)

**Version:** 8.1.1  
**Date:** 2026-02-25  
**Tag:** `v8.1.1`  
**Branch:** main (HA/HACS konform)  
**Hassfest:** ✅ compliant

## Release Features
- RFC-Phase 2 Core Tools implementiert
- Scene Automation Skills (create_scene_from_behavior, list_scenes)
- Multi-Zone Audio Control (group_zones, ungroup_zones)
- Security & Access (door_status, lock_door, unlock_door)
- Maintenance & Diagnostics (system_health, restart_service)
- Calendar & Scheduling (upcoming_events, optimal_time)
- Weather-Based Automation (weather_trigger)
- MCP-compatible API mit input schemas
- Pytest: 608 passed

## HA/HACS Conformance
- manifest.json: v8.1.1
- domain Feld hinzugefügt (falsches `domains` war das Problem!)
- HACS structure: OK
- hassfest: ✅ compliant

## Testing
```bash
# Run tests
pytest -q tests/test_*.py
```

---

**PilotSuite Styx HA v8.1.1** 🧠🏠  
**Release Iteration Maschine — v8.1.1** 🦝🔧🌙

