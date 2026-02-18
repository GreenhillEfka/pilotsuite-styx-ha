# PilotSuite TODOs - Open Issues

## Priorität 1 - Kritisch

### Scene Pattern Extraction
- **Datei**: `addons/copilot_core/rootfs/usr/src/app/copilot_core/brain_graph/bridge.py`
- **Zeile**: ~296
- **TODO**: Implement multi-node pattern extraction for scenes
- **Status**: Stub (leere Liste returned)

### Routine Pattern Extraction  
- **Datei**: `addons/copilot_core/rootfs/usr/src/app/copilot_core/brain_graph/bridge.py`
- **Zeile**: ~306
- **TODO**: Implement time-based pattern extraction for routines
- **Status**: Stub (leere Liste returned)

---

## Priorität 2 - Features

### Tests für Core Add-on
- **Datei**: `addons/copilot_core/rootfs/usr/src/app/tests/`
- **Status**: Tests vorhanden aber nicht vollständig
- **TODO**: Test-Coverage erhöhen

### MCP Phase 2
- **Roadmap**: `docs/MCP_ROADMAP.md`
- **TODO**: Calendar, Weather, Energy Integration
- **Phase 1**: ✅ Core HA Tools (MVP) - DONE
- **Phase 2**: ⏳ Erweiterte Tools

### Push Notifications
- **Datei**: `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/notifications.py`
- **Zeile**: ~207
- **TODO**: Implement actual push notification sending
- **Status**: HA notify fallback vorhanden

---

## Priorität 3 - Nice to Have

### Connection Pooling
- **Riskant**: SQLite threading issues
- **Status**: Nicht implementiert

### Debug Mode v0.8.0
- **Status**: Dev Surface vorhanden, kann erweitert werden

---

*Last Updated: 2026-02-18*
