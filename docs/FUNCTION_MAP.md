# PilotSuite Core - Complete Function Map

Version: 0.9.9 | Date: 2026-02-18

## Architecture Overview

```
Home Assistant ←→ HACS Integration (v0.15.2) ←→ Core Addon (v0.9.9)
                  ai_home_copilot                 copilot_core
                  22 modules, 80+ sensors          Flask + Waitress
                  15+ dashboard cards              37+ API endpoints
                                                   Ollama LLM (bundled)
```

### Neural Pipeline Flow
```
HA Events → EventProcessor → BrainGraph → HabitusMiner → Candidates → Repairs UI
                                ↓               ↓              ↓
                          NeuronManager → MoodEngine → Suggestions → Webhook
```

---

## API Endpoints (80+)

### Core Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Service index |
| GET | `/health` | No | Health check |
| GET | `/version` | No | Version info |

### Brain Graph (`/api/v1/graph/`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/graph/state` | Yes | Graph state with caching |
| GET | `/api/v1/graph/stats` | Yes | Graph statistics |
| GET | `/api/v1/graph/patterns` | Yes | Inferred patterns |
| GET | `/api/v1/graph/snapshot.svg` | Yes | SVG visualization |
| GET | `/api/v1/graph/nodes` | Yes | List nodes (paginated) |
| POST | `/api/v1/graph/prune` | Yes | Trigger graph pruning |
| POST | `/api/v1/graph/cache/clear` | Yes | Clear response cache |

### Candidates (`/api/v1/candidates/`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/candidates` | Yes | List candidates (filtered) |
| POST | `/api/v1/candidates` | Yes | Create candidate |
| GET | `/api/v1/candidates/{id}` | Yes | Get specific candidate |
| PUT | `/api/v1/candidates/{id}` | Yes | Update state (accept/dismiss/defer) |
| GET | `/api/v1/candidates/stats` | Yes | Storage statistics |

### Mood Engine (`/api/v1/mood/`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/mood` | Yes | All zone moods |
| GET | `/api/v1/mood/{zone_id}` | Yes | Zone mood snapshot |
| GET | `/api/v1/mood/summary` | Yes | Aggregated mood stats |
| POST | `/api/v1/mood/update-media` | Yes | Update from media context |
| POST | `/api/v1/mood/update-habitus` | Yes | Update from habitus |
| GET | `/api/v1/mood/{zone}/suppress-energy-saving` | Yes | Check suppression |

### Habitus Miner (`/api/v1/habitus/`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/habitus/mine` | Yes | Trigger pattern mining |
| GET | `/api/v1/habitus/stats` | Yes | Mining statistics |
| GET | `/api/v1/habitus/patterns` | Yes | Recent patterns |
| GET | `/api/v1/habitus/zones` | Yes | Zone information |
| GET | `/api/v1/habitus/health` | Yes | Health check |

### Neurons (`/api/v1/neurons/`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/neurons/` | Yes | List all neurons |
| GET | `/api/v1/neurons/{id}` | Yes | Get neuron state |
| POST | `/api/v1/neurons/evaluate` | Yes | Run full pipeline |
| POST | `/api/v1/neurons/update` | Yes | Update neuron state |

### Energy (`/api/v1/energy/`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/energy` | Yes | Energy snapshot |
| GET | `/api/v1/energy/anomalies` | Yes | Anomaly detection |
| GET | `/api/v1/energy/shifting` | Yes | Load shifting opportunities |

### UniFi Network (`/api/v1/unifi/`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/unifi` | Yes | Network snapshot |
| GET | `/api/v1/unifi/clients` | Yes | Connected clients |
| GET | `/api/v1/unifi/roaming-events` | Yes | Roaming history |
| GET | `/api/v1/unifi/anomalies` | Yes | Network anomalies |

### System Health (`/api/v1/system_health/`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/system_health` | Yes | Full system health |
| GET | `/api/v1/system_health/zigbee` | Yes | Zigbee mesh |
| GET | `/api/v1/system_health/zwave` | Yes | Z-Wave mesh |
| GET | `/api/v1/system_health/recorder` | Yes | DB health |
| GET | `/api/v1/system_health/updates` | Yes | Update status |

### Tags (`/api/v1/tags/`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/tags` | Yes | List tags |
| POST | `/api/v1/tags` | Yes | Create tag |
| GET | `/api/v1/tags/{id}` | Yes | Get tag |
| GET | `/api/v1/assignments` | Yes | List assignments |
| POST | `/api/v1/assignments` | Yes | Create assignment |
| DELETE | `/api/v1/assignments/{id}` | Yes | Delete assignment |

### Events (`/api/v1/events/`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/events` | Yes | Ingest event batch |
| GET | `/api/v1/events` | Yes | Query events |
| GET | `/api/v1/events/stats` | Yes | Event statistics |

### Conversation / LLM (`/chat/*` and `/v1/*`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/chat/completions` | Yes | **OpenAI-compatible** chat (for extended_openai_conversation) |
| GET | `/v1/models` | No | OpenAI-compatible model list (for integration validation) |
| GET | `/v1/models/{id}` | No | Get model details |
| POST | `/chat/completions` | Yes | Legacy chat endpoint |
| GET | `/chat/status` | No | LLM availability & config |
| GET | `/chat/characters` | No | Character presets list |
| GET | `/chat/tools` | Yes | MCP tools list |
| GET | `/chat/models/recommended` | No | Recommended Ollama models |

---

## Service Classes

### BrainGraphService
**Location:** `copilot_core/brain_graph/service.py`
- `touch_node(node_id, delta, ...)` - Update node score
- `upsert_edge(from_id, to_id, ...)` - Add/update edge
- `get_neighborhood(center, hops)` - Query graph
- `get_stats()` - Node/edge counts
- `prune_now()` - Remove expired data
- `process_ha_event(event_data)` - Process HA event
- `infer_patterns()` - Pattern discovery

### MoodService
**Location:** `copilot_core/mood/service.py`
- `get_zone_mood(zone_id)` - Zone mood snapshot (comfort/frugality/joy)
- `get_all_zone_moods()` - All zones
- `update_from_media_context(snapshot)` - Media signal
- `update_from_habitus(context)` - Habitus signal
- `should_suppress_energy_saving(zone_id)` - Joy > 0.6 suppression
- `get_suggestion_relevance_multiplier(zone_id, type)` - Mood-weighted relevance
- `get_summary()` - Cross-zone averages

### NeuronManager
**Location:** `copilot_core/neurons/manager.py`
- `configure_from_ha(ha_states, config)` - Setup neurons
- `update_states(new_states)` - Feed HA state changes
- `evaluate()` - Run full pipeline → NeuralPipelineResult
- `set_household(profile)` - Family-aware suggestions
- `add_neuron(type, name, neuron)` - Register neuron

**Pipeline:** Context → State → Mood → Suggestions
- **Context Neurons (4):** Presence, TimeOfDay, LightLevel, Weather
- **State Neurons (6):** EnergyLevel, StressIndex, RoutineStability, SleepDebt, AttentionLoad, ComfortIndex
- **Mood Neurons (8):** Relax, Focus, Active, Sleep, Away, Alert, Social, Recovery
- **Energy Neurons (3):** PVForecast, EnergyCost, GridOptimization
- **UniFi Neurons (1):** UniFiContext

### HabitusService
**Location:** `copilot_core/habitus/service.py`
- `mine_and_create_candidates(lookback_hours, force, zone)` - Mine patterns
- `get_pattern_stats()` - Mining statistics
- `list_recent_patterns(limit)` - Recent patterns

### CandidateStore
**Location:** `copilot_core/candidates/store.py`
- `add_candidate(candidate)` - Create
- `get_candidate(id)` - Retrieve
- `list_candidates(state, ...)` - Query with filters
- `update_state(id, new_state)` - State transition (accept/dismiss/defer)

### HouseholdProfile
**Location:** `copilot_core/household.py`
- `from_config(config)` - Create from options.json
- `get_adults()` / `get_children()` - Filter by age
- `is_child_present(entity_ids)` - Check child presence
- `is_only_children_home(entity_ids)` - Safety check
- `earliest_bedtime(entity_ids)` - Bedtime calculation
- `presence_summary(entity_ids)` - Context for NeuronManager

### WebhookPusher
**Location:** `copilot_core/webhook_pusher.py`
- `push_mood_changed(mood, confidence)` - Fire-and-forget
- `push_neuron_update(neuron_data)` - Neuron state
- `push_suggestion(suggestion)` - New suggestion

### TagRegistry
**Location:** `copilot_core/tags/__init__.py`
- `create_tag(facet, metadata)` - Create tag
- `assign_tag(subject_id, tag_id)` - Assignment
- `list_tags(facet)` - Query
- `get_subject_tags(subject_id)` - Subject tags

---

## Character Presets

| ID | Name | Icon | Description |
|----|------|------|-------------|
| `copilot` | CoPilot | mdi:brain | Main assistant - suggests automations |
| `butler` | Butler | mdi:account-tie | Formal, anticipates needs |
| `energy_manager` | Energiemanager | mdi:lightning-bolt | Energy efficiency focus |
| `security_guard` | Sicherheitswache | mdi:shield-home | Security-focused, warns about anomalies |
| `friendly` | Freundlicher Assistent | mdi:emoticon-happy | Casual, warm, conversational |
| `minimal` | Minimal | mdi:text-short | Short, direct, efficient |

---

## Recommended Ollama Models

| Model | Size | Best For |
|-------|------|----------|
| `lfm2.5-thinking` (default) | 731 MB | Ultra-light reasoning, simple HA control |
| `qwen3:4b` | 2.5 GB | Best balance for tool calling + HA |
| `llama3.2:3b` | 2 GB | Native tool calling, fast |
| `mistral:7b` | 4 GB | Proven reliability, HA community standard |
| `fixt/home-3b-v3` | 2 GB | Purpose-built for HA (97% accuracy) |

---

## HACS Integration Modules (22+)

| Module | File | Purpose |
|--------|------|---------|
| EventsForwarder | events_forwarder.py | Event batching & forwarding to core |
| HabitusMiner | habitus_miner.py | Pattern discovery & zone management |
| BrainGraphSync | brain_graph_sync.py | Brain graph synchronization |
| CandidatePoller | candidate_poller.py | Core bridge polling |
| MoodModule | mood_module.py | Mood inference & state |
| MoodContext | mood_context_module.py | Mood aggregation |
| MediaContext | media_context_module.py | Media player tracking |
| EnergyContext | energy_context_module.py | Energy monitoring |
| WeatherContext | weather_context_module.py | Weather integration |
| UniFiModule | unifi_module.py | UniFi network monitoring |
| UniFiContext | unifi_context_module.py | UniFi context enrichment |
| CameraContext | camera_context_module.py | Camera motion/presence |
| VoiceContext | voice_context.py | Voice assistant context |
| QuickSearch | quick_search.py | Local entity search |
| KnowledgeGraphSync | knowledge_graph_sync.py | Knowledge graph sync |
| MLContext | ml_context_module.py | ML feature extraction |
| CharacterModule | character_module.py | CoPilot personality |
| HomeAlerts | home_alerts_module.py | Critical alerts |
| UserPreference | user_preference_module.py | User preferences |
| DevSurface | dev_surface.py | Debug surface |
| OpsRunbook | ops_runbook.py | Operations runbook |
| Legacy | legacy.py | Legacy support |

---

## Dashboard Cards (15+)

| Card | File | Description |
|------|------|-------------|
| Energy Distribution | energy_distribution_card.py | Energy usage breakdown |
| Mesh Network Health | mesh_monitoring_card.py | Zigbee/Z-Wave health |
| Mobile Dashboard | mobile_responsive_dashboard.py | Responsive grid layout |
| Interactive Dashboard | interactive_dashboard.py | Neuron detail + filters |
| Zone Context | zone_context_card.py | Zone context data |
| Media Context | media_context_card.py | Media player context |
| User Together | user_together_card.py | Multi-user status |
| Home Alerts | home_alerts_card.py | Alert display |
| User Hints | user_hints_card.py | User hint cards |
| Weather/Calendar | weather_calendar_cards.py | Weather + calendar |
| Overview | overview_dashboard.py | System overview |
| Presence/Activity | presence_activity_cards.py | Presence tracking |
| Brain Graph Panel | brain_graph_panel.py | D3.js visualization |
| Mood Dashboard | mood_dashboard.py | Mood state display |
| Habitus Dashboard | habitus_dashboard_cards.py | Pattern display |

---

## Sensors (80+)

Categories: Presence (6), Voice (5), Energy (8), Media (6), Activity (7),
Habit Learning (3), Environment (6), Neuron Dashboard (3), Mood (3),
Cognitive (6), Time (6), Anomaly (2), Energy Insights (2), Calendar (3),
Predictive (2), Inspector (1), Core Neurons (16)

---

## Integration: extended_openai_conversation Setup

1. Install addon (Ollama is bundled)
2. In HA: Settings > Devices & Services > Add Integration > Extended OpenAI Conversation
3. Configure:
   - **API Key:** Your `auth_token` from addon config (or any non-empty string if unconfigured)
   - **Base URL:** `http://<addon-host>:8099/v1`
4. Options:
   - **Chat Model:** `lfm2.5-thinking` (or any installed model)
   - **Max Tokens:** 1024+
   - **Temperature:** 0.3-0.5
5. Expose entities in Settings > Voice Assistants > Expose tab
