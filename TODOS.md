# PilotSuite TODOs - Complete List

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

### Push Notifications
- **Datei**: `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/notifications.py`
- **Zeile**: ~207
- **TODO**: Implement actual push notification sending
- **Status**: HA notify fallback vorhanden

---

## Priorität 2 - Features

### Tests für Core Add-on schreiben
- **Status**: Tests vorhanden aber nicht vollständig
- **TODO**: Test-Coverage erhöhen
- **Ref**: HA Integration hat 24 Test-Fehler

### MCP Phase 2
- **Roadmap**: `docs/MCP_ROADMAP.md`
- **TODO**: Calendar, Weather, Energy Integration
- **Phase 1**: ✅ Core HA Tools (MVP) - DONE
- **Phase 2**: ⏳ Erweiterte Tools

---

## Priorität 3 - Technical Debt

### Legacy Code Cleanup (aus NEXT_IMPROVEMENTS.md)
| Legacy File | Current Version | Action |
|-------------|-----------------|--------|
| `forwarder.py` | `forwarder_n3.py` | Entfernen |
| `habitus_zones_entities.py` | `habitus_zones_entities_v2.py` | Entfernen |
| `media_context.py` | `media_context_v2.py` | Entfernen |
| `habitus_zones_store.py` | `habitus_zones_store_v2.py` | Prüfen |

### Large File Refactoring
| File | Lines | Suggested Split |
|------|-------|-----------------|
| `config_flow.py` | 1260 | wizard_steps.py, options_handler.py |
| `brain_graph_panel.py` | 947 | graph_builder.py, viz_renderer.py |
| `forwarder_n3.py` | 772 | event_processor.py, rate_limiter.py |

### Test Suite Remediation
- 24 Test-Fehler in HA Integration
- Betrifft: habitus_dashboard_cards, brain_graph_panel, mood_module

---

## Priorität 4 - Nice to Have

### Connection Pooling
- **Riskant**: SQLite threading issues
- **Status**: Nicht implementiert

### Debug Mode v0.8.0
- **Status**: Dev Surface vorhanden, kann erweitert werden

---

*Last Updated: 2026-02-18 20:40*
