# Changelog

All notable changes to AI Home CoPilot will be documented in this file.

## [0.9.6] - 2026-02-16

### Added
- **Cross-Home Sync Module** (`cross_home_sync.py`):
  - Multi-home entity sharing via Core Add-on API
  - Peer discovery for other CoPilot homes on network
  - Entity share/unshare with permission control (read/read_write)
  - State change sync to remote homes
  - Conflict resolution (local_wins, remote_wins, merge)
  - Shared entity registry with sync status tracking
  - Tests: 9 unit tests

---

## [0.9.5] - 2026-02-16

### Added
- **Collective Intelligence Module** (`collective_intelligence.py`):
  - Federated Learning support for distributed pattern sharing
  - Differential privacy with configurable epsilon (privacy-first)
  - Support for multiple model types: habit, anomaly, preference, energy
  - Pattern contribution threshold to ensure quality
  - Aggregated intelligence from multiple homes
  - Local model registration and versioning
  - Pattern expiration and cleanup
  - Tests: 11 unit tests

### Fixed
- **test_repairs_workflow.py**: Fix mock configuration for hass.data

---

## [0.9.4] - 2026-02-15

### Added
- **Quick Search Module** (`core/modules/quick_search.py`):
  - Entity Search: Search all HA entities by name, state, domain
  - Automation Search: Search automations by name, trigger, action
  - Service Search: Search available services by domain, service name
  - Quick Actions: Direct access to commonly used entities/services
  - Services: `ai_home_copilot.search_entities`, `ai_home_copilot.search_automations`, `ai_home_copilot.search_services`, `ai_home_copilot.quick_action`

- **Voice Context Module** (`core/modules/voice_context.py`):
  - Voice Command Parser: Parse voice commands into structured actions
  - TTS Output: Text-to-speech via HA TTS services
  - Voice State Tracking: Track voice assistant states
  - Command Templates: Predefined command patterns (German/English)
  - Supported commands: Light on/off, Climate control, Media control, Scene activation, Automation trigger, Status queries
  - Services: `ai_home_copilot.parse_command`, `ai_home_copilot.speak`, `ai_home_copilot.execute_command`, `ai_home_copilot.get_voice_state`

- **Calendar Integration** (existing: `calendar_context.py`):
  - Calendar Events → Neurons integration
  - calendar.load neuron (CalendarLoadSensor)
  - Termine-basiertes Context (Meeting detection, Focus/Social/Relax keywords)
  - Mood-Weight Berechnung aus Kalender

- **Mobile Dashboard** (existing: `mobile_dashboard_cards.py`):
  - Responsive Cards für mobile Geräte
  - Touch-friendly UI mit min 44px Tap-Targets
  - Quick Actions Card, Mood Status Card, Entity Quick Access Card
  - Notification Badge Card, Calendar Today Card, Quick Search Card

---

## [0.9.3] - 2026-02-15

### Added
- **Predictive Automation Sensors** (`sensors/predictive_automation.py`):
  - `predictive_automation_sensor`: Shows ML-based automation suggestion count
  - `predictive_automation_details_sensor`: Shows detailed suggestions with pattern, confidence, lift, support
  - Integration with `repairs_enhanced.py` for enhanced UX

- **Anomaly Alert Sensors** (`sensors/anomaly_alert.py`):
  - `anomaly_alert_sensor`: Real-time anomaly detection status (healthy/active/idle)
  - `alert_history_sensor`: Shows recent anomaly history with timestamps and scores
  - Integration with `AnomalyDetector` from `ml/patterns/anomaly_detector.py`

- **Energy Insights Sensors** (`sensors/energy_insights.py`):
  - `energy_insight_sensor`: Shows total energy consumption (kWh) with device breakdown
  - `energy_recommendation_sensor`: Shows active energy optimization recommendations
  - Integration with `EnergyOptimizer` from `ml/patterns/energy_optimizer.py`

- **Habit Learning v2 Sensors** (`sensors/habit_learning_v2.py`):
  - `habit_learning_sensor`: Shows number of learned habit patterns
  - `habit_prediction_sensor`: Shows habit predictions with confidence scores
  - `sequence_prediction_sensor`: Shows device sequence predictions (cross-device correlation)
  - Integration with `HabitPredictor` from `ml/patterns/habit_predictor.py`

### Services
- `predictive_automation_suggest_automation`: Suggest automation based on ML patterns
- `anomaly_alert_check_and_alert`: Check for anomalies and send alerts
- `anomaly_alert_clear_history`: Clear anomaly history
- `energy_insights_get`: Get energy insights and recommendations
- `habit_learning_learn`: Learn new habit pattern through observation
- `habit_learning_predict`: Predict future events or sequences

### Features
- Unified ML context via `MLContext` module
- All sensors integrate with existing ML subsystems
- Push notifications via HA system notifications
- Dashboard cards via existing `habitus_dashboard_cards.py`

### Configuration
- Enable via `ml_enabled: true` in config entry options
- Auto-sync of entity states to ML context every 60 seconds

---

## [0.8.16] - 2026-02-15

### Added
- **Knowledge Graph Integration** (`api/knowledge_graph.py`):
  - Full async client for Core Add-on Knowledge Graph API
  - Node operations: create, list, get by ID/type
  - Edge operations: create, list, relationships
  - Query operations: structural, causal, contextual, temporal queries
  - Pattern import from Habitus mining

- **Knowledge Graph Sync Module** (`core/modules/knowledge_graph_sync.py`):
  - Auto-syncs HA entities to Knowledge Graph
  - Creates BELONGS_TO edges for entity→area relationships
  - Creates HAS_CAPABILITY edges for entity features
  - Creates HAS_TAG edges from tag registry
  - Creates RELATES_TO_MOOD edges from neural system
  - Periodic full sync (configurable interval)
  - Real-time state change tracking

- **Knowledge Graph Sensors** (`knowledge_graph_entities.py`):
  - Knowledge Graph Stats sensor (node/edge counts)
  - Knowledge Graph Nodes sensor
  - Knowledge Graph Edges sensor
  - Sync Status sensor
  - Last Sync timestamp sensor

### Features
- Entities automatically added to graph when discovered
- Zone/Tag/Mood relationships synced in real-time
- Query related entities for suggestion context
- Foundation for Pattern-to-Entity mapping

### Configuration
- `knowledge_graph_enabled`: Enable/disable sync (default: true)
- `knowledge_graph_sync_interval`: Full sync interval in seconds (default: 3600)

### Technical
- All modules pass py_compile validation
- Async-safe client with error handling
- Module registry integration for runtime access

## [0.8.15] - 2026-02-15

### Added
- **Suggestion Panel** (`suggestion_panel.py`): Dedicated UI for AI Home CoPilot suggestions
  - Timeline view of pending suggestions
  - Accept/Reject/Snooze actions via service calls
  - Confidence indicator and "Why?" explanations
  - Zone and Mood context display
  - Priority-based sorting (High/Medium/Low)
  - WebSocket API for real-time updates

- **Mood Dashboard** (`mood_dashboard.py`): Visualisierung der aktuellen Stimmung
  - MoodSensor with icon, color, and German name
  - MoodHistorySensor for tracking mood changes
  - MoodExplanationSensor with "Warum?" explanations
  - Lovelace card config generator
  - Top contributing factors display

- **Calendar Context Neuron** (`calendar_context.py`): Kalender-basierter Kontext
  - Meeting detection (now/soon)
  - Weekend/holiday detection
  - Vacation mode detection
  - Mood weight computation based on calendar events
  - Conflict detection
  - Keyword-based categorization (focus, social, relax, alert)

### Enhanced
- Extended `const.py` with new configuration options
- Added sensor entities: ZoneOccupancySensor, UserPresenceSensor, UserPreferenceSensor, SuggestionQueueSensor
- Added calendar context integration to sensor setup

### Technical
- All modules pass py_compile validation
- WebSocket API with proper error handling
- Async storage for suggestion persistence

## [0.8.14] - 2026-02-15

### Added
- Enhanced Repairs UX with zone and mood context
- Risk visualization for suggestions

## [0.8.0] - 2026-02-15

### Added
- Multi-User Preference Learning (MUPL) v0.8.0
- User-spezifische Mood-Gewichtung
- Debug Mode v0.8.0

## [0.4.33] - 2026-02-14

### Added
- Neuronen-System: Context, State, Mood, Weather, Presence, Energy, Camera
- Habitus Zones: Zone-basierte Muster-Erkennung
- Tag System v0.2
- Brain Graph
## [0.9.4] - 2026-02-15

### Added
- Complete SETUP_GUIDE.md - German installation guide
- OpenAPI Specification for HA Integration services
- LazyHistoryLoader for on-demand history caching
- MUPL Phase2 Caching and Query Optimization

### Merged
- dev/mupl-phase2-v0.8.1
- dev/openapi-spec-v0.8.2
- dev/vector-store-v0.8.3

## [0.9.3] - 2026-02-15

### Added
- Phase 6.1 Core Features:
  - Predictive Automation (suggest_automation service)
  - Anomaly Alert (check_and_alert service)
  - Energy Insights (get_energy_insights service)
  - Habit Learning V2 (learn_habits, predict_sequence services)

### Changed
- button.py refactored (40KB → 8 modules)
- Critical fixes: N+1 queries, memory leak, blocking I/O
- Tags API verified (Flask + Auth)

### Tests
- 100+ new tests (Core + Integration)
