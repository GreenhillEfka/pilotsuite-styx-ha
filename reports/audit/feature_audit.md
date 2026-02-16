# Feature Audit - AI Home CoPilot
Generiert: Mon Feb 16 12:02:37 CET 2026

## 1. MODULE IM ADD-ON
| Modul | Dateien |
|-------|---------|
| api | 30 |
| brain_graph | 9 |
| candidates | 3 |
| collective_intelligence | 8 |
| data | 0 |
| dev_surface | 4 |
| energy | 3 |
| habitus | 4 |
| habitus_miner | 6 |
| ingest | 3 |
| knowledge_graph | 6 |
| log_fixer_tx | 4 |
| mood | 7 |
| neurons | 12 |
| sharing | 2 |
| storage | 4 |
| synapses | 3 |
| system_health | 3 |
| tagging | 5 |
| tags | 4 |
| unifi | 3 |
| vector_store | 3 |

## 2. MODULE IN DER INTEGRATION (hacs_repo)
| Kategorie | Dateien |
|-----------|---------|
| button*.py | 15 |
| sensor*.py | 1 |
| *_dashboard*.py | 17 |
| *_entities*.py | 20 |
| *_store*.py | 11 |

## 3. API-ENDPUNKTE IM ADD-ON
| Endpunkt | Datei |
|----------|-------|

## 4. PORTS IN BEIDEN
| Datei | Port |
|-------|------|
ai_home_copilot_hacs_repo/custom_components/ai_home_copilot/dashboard_cards/energy/energy_distribution_card.py:92:    max_power = 5000  # Default max (5 kW)
ai_home_copilot_hacs_repo/custom_components/ai_home_copilot/const.py:79:DEFAULT_PORT = 8909
addons/copilot_core/rootfs/usr/src/app/copilot_core/ingest/event_store.py:8:    COPILOT_EVENT_STORE_MAX   – max events in memory ring (default: 5000)
addons/copilot_core/rootfs/usr/src/app/copilot_core/ingest/event_store.py:24:_DEFAULT_MAX_EVENTS = 5000
addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/graph_ops.py:20:    lru_max: int = 5000
