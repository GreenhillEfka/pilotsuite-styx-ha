# PilotSuite HA Integration - TODOs

## Priorität 1 - Kritisch

### Legacy Code Cleanup
| Legacy File | Current Version | Action |
|-------------|-----------------|--------|
| `forwarder.py` | `forwarder_n3.py` | Entfernen |
| `habitus_zones_entities.py` | `habitus_zones_entities_v2.py` | Entfernen |
| `media_context.py` | `media_context_v2.py` | Entfernen |
| `habitus_zones_store.py` | `habitus_zones_store_v2.py` | Prüfen |
| `button_safety.py` | `button_safety_backup.py` | Entfernen |

### Large File Refactoring
| File | Lines | Suggested Split |
|------|-------|-----------------|
| `config_flow.py` | 1260 | wizard_steps.py, options_handler.py |
| `brain_graph_panel.py` | 947 | graph_builder.py, viz_renderer.py |
| `forwarder_n3.py` | 772 | event_processor.py, rate_limiter.py |
| `habitus_dashboard_cards.py` | 728 | card_factory.py, validators.py |

---

## Priorität 2 - Features

### User Hints Automation
- **Datei**: `custom_components/ai_home_copilot/core/user_hints/service.py`
- **Zeile**: ~206
- **TODO**: Create automation in Home Assistant
- **Status**: Stub

### MUPL Integration
- **Status**: ✅ Implementiert in v0.15.1
- **Ref**: vector_client.py nutzt MUPL

---

## Priorität 3 - Testing

### Test Suite Remediation
- **Issue**: 24 test failures, 25 errors
- **Betroffene Tests**:
  - `test_habitus_dashboard_cards.py`
  - `test_brain_graph_panel.py`
  - `test_mood_module.py`
- **Action**: Fix test code vs implementation mismatches

---

## Priorität 4 - Nice to Have

### Vector Store Sync
- **Status**: Implementiert
- **TODO**: Testing und Optimierung

---

*Last Updated: 2026-02-18*
