# CHANGELOG - AI Home CoPilot Core

## [0.4.32] - 2026-02-15

### Added
- **Voice Context API** (`api/v1/voice_context.py`):
  - `/api/v1/voice/context` - GET current voice context
  - `/api/v1/voice/context` - POST update from neural system
  - `/api/v1/voice/prompt` - GET natural language prompt
  - `/api/v1/voice/mood_history` - GET mood trend history
  - `/api/v1/voice/suggestions` - GET voice-friendly suggestions

- **VoiceContextProvider** (`voice_context.py`):
  - Mood-to-tone mapping (relax, focus, active, sleep, away, alert, social, recovery)
  - Zone-based context (Wohnzimmer, Schlafzimmer, Küche, Büro, Bad)
  - Natural language suggestion generation
  - Mood history tracking

### Features
- HA 2025.8+ Assist integration ready
- Mood-based voice response personalization
- Zone context for location-aware responses
- Proactive suggestions in natural language

---

## [0.4.31] - 2026-02-15

### Added
- **mmWave Presence Neurons** (`neurons/presence.py`):
  - `mmWavePresenceNeuron`: High-precision presence via mmWave radar
  - `MotionPresenceNeuron`: Traditional PIR/motion sensor presence
  - `CombinedPresenceNeuron`: Multi-sensor fusion for robust presence
  - Privacy-friendly, no cameras, breathing detection
  - Industry trend 2026: 25-40% energy savings

- **Predictive Energy Neurons** (`neurons/energy.py`):
  - `PVForecastNeuron`: Solar production forecasting
  - `EnergyCostNeuron`: Grid price optimization
  - `GridOptimizationNeuron`: Charge/discharge timing
  - Optimal consumption scheduling

### Features
- mmWave detects presence without movement (breathing)
- Sensor fusion with configurable weights (mmWave 70%, motion 30%)
- PV forecast with hourly predictions
- Peak/off-peak price optimization
- Battery charge/discharge recommendations

---

## [0.4.30] - 2026-02-15

### Added
- **Tag → Zone Integration** (`tagging/zone_integration.py`):
  - `TagZoneIntegration`: Automatic zone membership from place tags
  - When entity tagged with `aicp.place.X` → auto-joins `HabitusZone("X")`
  - Safety-critical role handling (`aicp.role.safety_critical`)
  - Zone governance rules (confirmation required, auto-learning toggle)
  - Pattern application checks (can_auto_apply, requires_confirmation)
  - Zone statistics and configuration management

### Philosophy
- **HABITUS_PHILOSOPHY.md**: Core philosophy documented
  - "Ein Smart Home ist nur so schlau wie sein Nutzer"
  - HabitusZones = Brücke zwischen statischen Regeln und individuellen Mustern
  - Tags geben Bedeutung, Zonen geben Kontext
  - Vorschläge, nicht Automatik

### Architecture
```
Tag Assignment → TagZoneIntegration → HabitusZone update
                          ↓
                   Habitus Miner (zone-filtered)
```

---

## [0.4.29] - 2026-02-15

### Fixed
- **RESTORED tagging/ module** - Was incorrectly deleted by Autopilot in v0.4.25
  - `tagging/` is NOT a duplicate of `tags/` - they serve different purposes:
  - `tagging/` = TagAssignmentStore, TagRegistry with persistence & validation
  - `tags/` = Tag System v0.2 with HabitusZone integration
  - Both modules are needed for full functionality
- Restored tests: test_tag_assignment_store.py, test_tag_registry.py

### Architecture
```
tagging/                    # Persistence Layer
├── assignments.py          # TagAssignmentStore with JSON persistence
├── models.py               # Tag, TagDisplay, TagGovernance, TagHAConfig
└── registry.py             # TagRegistry with YAML loading

tags/                       # Integration Layer (v0.2)
├── __init__.py             # TagRegistry with HabitusZone support
└── api.py                  # REST API endpoints
```

---

## [0.4.28] - 2026-02-15

### Added
- **Weather Context Neuron** (`neurons/weather.py`):
  - `WeatherContextNeuron`: Evaluates weather for PV potential, comfort, activity suggestions
  - `PVForecastNeuron`: Evaluates PV forecast for energy optimization
  - `WeatherCondition` enum for weather categorization
  - Methods: `get_pv_potential()`, `get_comfort_score()`, `should_suppress_outdoor_suggestions()`
- **Weather API** (`api/v1/weather.py`):
  - `GET /api/v1/weather` - Current weather snapshot
  - `GET /api/v1/weather/forecast` - Multi-day forecast
  - `GET /api/v1/weather/pv-recommendations` - PV-based energy recommendations
  - `WeatherService` class with caching (15min TTL)
  - PV production estimation based on cloud cover and UV index

### Changed
- `neurons/__init__.py`: Export new weather neurons
- `api/v1/blueprint.py`: Register weather blueprint

---

## [0.4.27] - 2026-02-15

### Fixed
- **BrainGraphStore naming**: Renamed `GraphStore` to `BrainGraphStore` with backwards-compatible alias
  - `brain_graph/store.py`: Class renamed to `BrainGraphStore`
  - `brain_graph/__init__.py`: Added `GraphStore` alias
  - `brain_graph/service.py`: Added `GraphStore` alias
  - `core_setup.py`: Added `GraphStore` alias
- **Dataclass field ordering**: Fixed `habitus_miner/model.py` Rule dataclass
  - Non-default fields (`observation_period_days`, `baseline_p_b`) now come before default fields
- **Obsolete tests**: Disabled `test_tag_assignment_store.py` and `test_tag_registry.py`
  - Tests were for old `tagging/` module removed in v0.4.25
  - Renamed to `.py.disabled` to prevent import errors

---

## [0.4.30] - 2026-02-15

### Added
- **Zone-based Mining** (`habitus_miner/zone_mining.py`):
  - ZoneBasedMiner: Zone-aware pattern discovery
  - ZoneMiningConfig: Per-zone thresholds and governance
  - Filter events by zone membership
  - Safety-critical entity blocking
  - Top suggestions with explanations

### Changed
- **habitus_miner/__init__.py**: Updated to v0.2.0, exports zone mining API
- Zone-filtered patterns now respect zone governance rules

### Documentation
- `docs/HABITUS_PHILOSOPHY.md`: Complete Habitus vision and philosophy

---

## [0.4.26] - 2026-02-15

### Fixed
- **RESTORED mood/ module** - Autopilot incorrectly deleted it
  - mood/ contains MoodService, MoodEngine, MoodOrchestrator, MoodScorer, API
  - neurons/mood.py only has MoodNeuron classes, NOT the infrastructure
  - All imports were broken after deletion
- `tagging/` removal was correct (duplicate of `tags/`)

## [0.4.25] - 2026-02-15 [YANKED]

### Removed
- **Redundant modules cleaned up** [INCORRECT - SEE 0.4.26]:
  - `mood/` directory (replaced by `neurons/mood.py`) [WRONG - RESTORED IN 0.4.26]
  - `tagging/` directory (duplicate of `tags/`) [CORRECT]

---

## [0.4.24] - 2026-02-15

### Fixed
- **API Response Format**: All endpoints now return `{success: true, data: {...}}`
- **Consistent Data Structure**: mood, neurons, evaluate all use same format

---

## [0.4.23] - 2026-02-15

### Added
- **NeuronManager** (`neurons/manager.py`):
  - Singleton manager for all neurons
  - Creates and configures 18 default neurons
  - Creates 30+ default synapse connections
  - Evaluates full neural pipeline (Context → State → Mood)
  - Generates suggestions from mood neurons
  - Learning from user feedback
- **Neuron API** (`api/v1/neurons.py`):
  - `GET /api/v1/neurons` - List all neurons
  - `GET /api/v1/neurons/<id>` - Get neuron state
  - `POST /api/v1/neurons/evaluate` - Run evaluation
  - `GET /api/v1/neurons/mood` - Get current mood
  - `POST /api/v1/neurons/mood/evaluate` - Force mood evaluation
  - `GET /api/v1/neurons/suggestions` - Get active suggestions
  - `POST /api/v1/neurons/feedback` - Submit user feedback
  - `GET /api/v1/neurons/stats` - Network statistics

### Architecture (NOW INTEGRATED!)
```
HA States → NeuronManager.evaluate()
         → Context Neurons (4)
         → SynapseManager.propagate()
         → State Neurons (6)
         → SynapseManager.propagate()
         → Mood Neurons (8)
         → Suggestion Generation
         → HA Actions (via feedback)
```

### Integration
- API registered in blueprint.py
- Neurons accessible via REST API
- Ready for HA Integration connection

---

## [0.4.22] - 2026-02-15

### Added
- **Synapse System** (`synapses/`):
  - `Synapse` model: Connection between neurons with weight, threshold, learning
  - `SynapseType`: Excitatory, Inhibitory, Modulatory
  - `SynapseState`: Active, Dormant, Learning, Pruned
  - `Suggestion` model: Action suggestions from mood neurons
  - `SynapseManager`: Full synapse network management
- **Features**:
  - Signal propagation between neurons
  - Hebbian-like learning with reward signals
  - Decay for inactive synapses
  - Automatic suggestion generation from moods
  - Mood-specific actions (relax→dim, focus→optimize, sleep→night_mode)
  - User feedback learning

### Architecture
```
Context → State → Mood → Suggestion → Action
         ↑________________↓
              Learning
```

---

## [0.4.21] - 2026-02-15

### Added
- **State Neurons** (`neurons/state.py`):
  - `EnergyLevelNeuron`: Energy based on activity and time
  - `StressIndexNeuron`: Stress from calendar, routine deviation, environment
  - `RoutineStabilityNeuron`: Pattern deviation analysis
  - `SleepDebtNeuron`: Accumulated sleep deficit
  - `AttentionLoadNeuron`: Cognitive load from media/devices
  - `ComfortIndexNeuron`: Environmental comfort (temp, humidity)
- **Mood Neurons** (`neurons/mood.py`):
  - `RelaxMoodNeuron`: Relaxed, calm state
  - `FocusMoodNeuron`: Concentrated, productive state
  - `ActiveMoodNeuron`: Active, energetic state
  - `SleepMoodNeuron`: Sleepy, rest-needed state
  - `AwayMoodNeuron`: User not present
  - `AlertMoodNeuron`: Alert, attention-needed state
  - `SocialMoodNeuron`: Social, interactive state
  - `RecoveryMoodNeuron`: Recovery, healing state
- **Neural Pipeline**: Full Context → State → Mood flow

### Architecture
- State neurons use lower smoothing (0.15) for inertial behavior
- Mood neurons aggregate inputs with configurable weights
- Factory functions for dynamic neuron creation

---

## [0.4.20] - 2026-02-15

### Added
- **Neurons Module** (`copilot_core/neurons/`):
  - `BaseNeuron` abstract class with evaluate(), update(), decay(), reset()
  - `NeuronState` dataclass for neuron state tracking
  - `NeuronConfig` dataclass for neuron configuration
  - `NeuronType` enum: CONTEXT, STATE, MOOD
  - `MoodType` enum: relax, focus, active, sleep, away, alert, social, recovery
- **Context Neurons** (`neurons/context.py`):
  - `PresenceNeuron`: Evaluates presence in zones/house
  - `TimeOfDayNeuron`: Maps time to continuous value (night/morning/day/evening)
  - `LightLevelNeuron`: Evaluates ambient light from lux sensors and sun position
  - `WeatherNeuron`: Evaluates weather conditions
  - Factory: `create_context_neuron(name, config)`
- **Features**:
  - EMA smoothing for stable values
  - Decay when inactive
  - Threshold triggering with callbacks
  - Full test coverage

### Architecture
- Neuron hierarchy: Context → State → Mood
- Each neuron outputs 0.0-1.0 value with confidence
- Mood neurons aggregate inputs for suggestion triggers

---

## [0.4.19] - 2026-02-15

### Added
- **Vector Store Module** (`copilot_core/vector_store/`):
  - Local feature-based embeddings for entities, user preferences, and patterns
  - Optional Ollama integration for semantic embeddings
  - SQLite persistence with in-memory cache
  - Cosine similarity search with configurable threshold
- **Vector Store API** (`/api/v1/vector/`):
  - `POST /api/v1/vector/embeddings` - Create embedding (entity, user_preference, pattern)
  - `POST /api/v1/vector/embeddings/bulk` - Bulk create embeddings
  - `GET /api/v1/vector/similar/<entry_id>` - Find similar entries
  - `GET /api/v1/vector/vectors` - List vectors
  - `GET /api/v1/vector/vectors/<id>` - Get specific vector
  - `DELETE /api/v1/vector/vectors/<id>` - Delete vector
  - `POST /api/v1/vector/similarity` - Compute similarity between two entries
  - `GET /api/v1/vector/stats` - Vector store statistics
- **Embedding Features**:
  - Entity embeddings: domain, area, capabilities, tags, state features
  - User preference embeddings: brightness, temperature, volume, mood weights
  - Pattern embeddings: type, entities, conditions, confidence
- **MUPL Integration**: User preference similarity for recommendations
- **Tests**: Comprehensive unit tests for embeddings, store, and API

### Technical Details
- Embedding dimension: 128 (configurable)
- Storage: SQLite at `/data/vector_store.db`
- Cache: LRU cache with configurable size (default 500)
- Environment variables: `COPILOT_VECTOR_DB_PATH`, `COPILOT_USE_OLLAMA`, `COPILOT_OLLAMA_MODEL`

---

## [0.4.18] - 2026-02-15

### Added
- **Knowledge Graph Module** (`copilot_core/knowledge_graph/`):
  - Neo4j-backed graph storage with SQLite fallback for dual backend support
  - Node types: ENTITY, DOMAIN, AREA, ZONE, PATTERN, MOOD, CAPABILITY, TAG, TIME_CONTEXT, USER
  - Edge types: BELONGS_TO, HAS_CAPABILITY, HAS_TAG, TRIGGERS, CORRELATES_WITH, ACTIVE_DURING, RELATES_TO_MOOD, PREFERRED_BY, AVOIDED_BY
  - GraphStore: Dual backend (Neo4j/SQLite), CRUD operations, graph queries
  - GraphBuilder: Build graph from HA states, entities, areas, tags
  - PatternImporter: Import Habitus A→B rules as PATTERN nodes with TRIGGERS edges
- **Knowledge Graph API** (`/api/v1/kg/`):
  - `GET /kg/stats` - Graph statistics
  - `GET/POST /kg/nodes` - Node CRUD
  - `GET/POST /kg/edges` - Edge CRUD
  - `POST /kg/query` - Graph queries (semantic, structural, causal, temporal, contextual)
  - `GET /kg/entity/<id>/related` - Get related entities
  - `GET /kg/zone/<id>/entities` - Get entities in zone
  - `GET /kg/mood/<mood>/patterns` - Get patterns for mood
  - `POST /kg/import/entities` - Import from HA states
  - `POST /kg/import/patterns` - Import from Habitus miner output
- **Tests**: Comprehensive unit tests for models, store, builder, importer, API

### Technical Details
- Environment variables: `COPILOT_NEO4J_URI`, `COPILOT_NEO4J_USER`, `COPILOT_NEO4J_PASSWORD`, `COPILOT_NEO4J_ENABLED`
- SQLite fallback at `/data/knowledge_graph.db`
- Thread-safe singleton pattern for GraphStore
- Pattern filtering by confidence, support, lift thresholds

---

## [0.4.17] - 2026-02-15

### Added
- **OpenAPI Specification** (`docs/openapi.yaml`):
  - Complete REST API documentation for Core Add-on
  - Habitus, Graph, Mood, Tags, Events, Candidates, System endpoints
  - Request/response schemas with examples
  - Authentication and idempotency documentation

---

## [0.4.16] - 2026-02-15

### Security Fixes (P0)

**log_fixer_tx API: Add authentication requirement**
- All endpoints now require `@require_api_key` decorator
- Fixes P0 security issue: `/api/v1/log_fixer_tx/*` without auth
- Prevents unauthorized transaction creation/rollback

### Changed
- `log_fixer_tx.py`: Added import and decorators to all 6 endpoints
- `/status`, `/transactions`, `/transactions/<id>`, `/rollback`, `/recover`, `/transactions (POST)`

---

## [0.4.15] - 2026-02-14

### Added
- **Habitus Zones v2 — Zone-Aware Pattern Mining**:
  - **BrainGraphService Zone Methods**:
    - `get_zone_entities(zone_id)`: Get all entities in a specific zone
    - `get_zones()`: List all discovered zones with entity counts
  - **HabitusMiner Zone Filter**:
    - `mine_patterns(lookback_hours, zone=...)`: Filter patterns by zone
    - Only patterns where both antecedent and consequent entities belong to the specified zone
  - **HabitusService Integration**:
    - Zone parameter passed through to miner and stored in candidate metadata
    - `zone_filter` field in candidate metadata tracks zone context
  - **REST API Extensions**:
    - `POST /api/v1/habitus/mine`: New `zone` parameter for zone-filtered mining
    - `GET /api/v1/habitus/zones`: New endpoint to list available zones

### Technical Details
- **Zone Normalization**: Accepts both "kitchen" and "zone:kitchen" formats
- **Discovery Method**: Candidates created from zone-filtered mining use `habitus_miner_v2`
- **Entity Count**: Zones endpoint includes entity count for each zone

### Tests
- 9 new unit tests covering zone functionality
- Tests for `get_zones()`, `get_zone_entities()`, zone-filtered mining

---

## [0.4.14] - 2026-02-14

### Added
- **Tag System v0.2 — Decision Matrix Implementation**:
  - **Decision Matrix P1 Features**:
    - HA-Labels materialisieren: nur ausgewählte Facetten (`role.*`, `state.*`)
    - Subjects: alle HA-Label-Typen (`entity`, `device`, `area`, `automation`, `scene`, `script`, `helper`)
    - Subject IDs: Mix aus Registry-ID + Fallback (`unique_id` > `device_id` > `entity_id`)
    - Namespace: `user.*` NICHT als intern (nur HA-Labels importieren)
    - Lokalisierung: nur `display.de` + `en`
    - Learned Tags → HA-Labels: NIE automatisch (explizite Bestätigung nötig)
    - Farben/Icons: HA als UI-Quelle
    - Konflikte: existierende HA-Labels ohne `aicp.*` ignorieren
    - Habitus-Zonen: eigene interne Objekte mit Policies
  - **In-Memory Registry**: Einfache, schnelle Tag-Verwaltung
  - **Suggest/Confirm Workflow**: Learned Tags brauchen explizite Bestätigung
  - **REST API Endpoints** (unter `/api/v1/tags2`):
    - `POST /api/v1/tags2/tags` — Tag erstellen
    - `POST /api/v1/tags2/tags/suggest` — Learned Tag vorschlagen
    - `POST /api/v1/tags2/tags/{id}/confirm` — Learned Tag bestätigen
    - `GET /api/v1/tags2/tags` — Tags auflisten
    - `POST /api/v1/tags2/subjects` — Subject registrieren
    - `POST /api/v1/tags2/assignments` — Tag zu Subject zuweisen
    - `GET /api/v1/tags2/labels/export` — Export für HA Labels Sync

### Technical Details
- **Privacy-First**: Learned Tags werden NIE automatisch als HA-Labels materialisiert
- **Modular Architecture**: Integriert in Core Setup
- **Kompatibel mit bestehendem Tag System** (YAML-basiert in `/api/v1/tag-system`)

### Added
- **UniFi Neuron v0.1 — Network Monitoring Module**:
  - **WAN Status**: Uplink status, latency, packet loss monitoring
  - **Client Roaming**: Recent client roam events with timestamps
  - **Traffic Baselines**: Historical traffic patterns for anomaly detection
  - **Integration Ready**: Plugs into Core Setup with other Neurons

### REST API Endpoints
- `GET /api/v1/unifi` — Full snapshot (WAN, clients, roaming, baselines)
- `GET /api/v1/unifi/wan` — WAN uplink status and metrics
- `GET /api/v1/unifi/clients` — Connected client list with details
- `GET /api/v1/unifi/roaming` — Recent roaming events
- `GET /api/v1/unifi/baselines` — Traffic baseline data
- `GET /api/v1/unifi/health` — Service health status

### Technical Details
- **UniFi Network API Integration**: Reads from UniFi Network entities
- **Caching**: 2-minute TTL for WAN/clients, 10-minute for baselines
- **Modular Pattern**: Consistent with Mood, SystemHealth, Energy modules
- **Privacy-First**: Local metrics only, no external transmission

## [0.4.12] - 2026-02-14

### Added
- **Brain Graph Configurable Limits**: Brain Graph module now supports runtime configuration:
  - `max_nodes` (default: 500, range: 100-5000)
  - `max_edges` (default: 1500, range: 300-15000)
  - `node_half_life_hours` (default: 24.0, range: 1-168)
  - `edge_half_life_hours` (default: 12.0, range: 1-168)
  - `node_min_score` (default: 0.1, range: 0.01-1.0)
  - `edge_min_weight` (default: 0.1, range: 0.01-1.0)

### Technical Details
- Config schema updated in `config.json` with validation bounds
- `core_setup.py` now accepts optional `config` parameter for service initialization
- Graph limits can be tuned per deployment without code changes
- Maintains backward compatibility with existing deployments (uses defaults if not specified)

## [0.4.11] - 2026-02-14

### Added
- **Energy Neuron v0.1 — Energy Monitoring and Optimization Module**:
  - **Energy Consumption Monitoring**: Track daily consumption, production (solar/PV), current power draw, peak power
  - **Anomaly Detection**: Detect unusual consumption patterns with severity levels (low/medium/high)
  - **Load Shifting Opportunities**: Identify optimal times for running high-power devices
  - **Suggestion Explainability**: Explain why energy suggestions are made
  - **Baseline Learning**: Device-type baselines for washer, dryer, dishwasher, EV charger, heat pump, HVAC
  - **Suppression Logic**: Auto-suppress suggestions when high-severity anomalies detected

### REST API Endpoints
- `GET /api/v1/energy` — Full energy snapshot (consumption, production, power, baselines)
- `GET /api/v1/energy/anomalies` — Detected consumption anomalies
- `GET /api/v1/energy/shifting` — Load shifting opportunities
- `GET /api/v1/energy/explain/<suggestion_id>` — Explain why a suggestion was made
- `GET /api/v1/energy/baselines` — Energy consumption baselines per device type
- `GET /api/v1/energy/suppress` — Check if suggestions should be suppressed
- `GET /api/v1/energy/health` — Service health status

### Technical Details
- **HA Entity Integration**: Reads from sensor.energy_* entities
- **Caching**: 5-minute TTL for all metrics
- **Modular Design**: Follows same pattern as Mood, SystemHealth, UniFi modules
- **Privacy-First**: No external data transmission, local metrics only

### Use Cases
- "Deine Waschmaschine verbraucht 40% mehr als üblich"
- "PV-Überschuss jetzt verfügbar → Geschirrspüler starten?"
- "Peak-Zeit bald vorbei → Klimaanlage runterfahren"
- Energy savings estimates with cost calculations

## [0.4.10] - 2026-02-14

### Added
- **UniFi Neuron v0.1 — Network Monitoring Module**:
  - **WAN Status**: Online/offline, latency, packet loss, uptime, IP address
  - **Client Management**: Connected device list with device type detection (phone/laptop/IoT)
  - **Roaming Events**: Client roaming detection and tracking
  - **Traffic Baselines**: Upload/download averages and peaks
  - **Suggestion Suppression**: Auto-suppress when WAN unstable or roaming storms detected

### REST API Endpoints
- `GET /api/v1/unifi` — Full network snapshot (WAN, clients, roams, baselines)
- `GET /api/v1/unifi/wan` — WAN uplink status
- `GET /api/v1/unifi/clients` — Connected clients (with optional filters)
- `GET /api/v1/unifi/roaming` — Recent roaming events
- `GET /api/v1/unifi/baselines` — Traffic baselines
- `GET /api/v1/unifi/suppress` — Check suppression status
- `GET /api/v1/unifi/health` — Service health check

### Technical Details
- **HA Entity Integration**: Reads from device_tracker entities for client info
- **UniFi Ready**: Designed for UniFi Network API integration when available
- **Caching**: 5-minute TTL for all metrics
- **Modular Design**: Follows same pattern as Mood, SystemHealth modules
- **Privacy-First**: No external data transmission, local metrics only

### Use Cases
- Detect network instability → suppress automation suggestions
- Client presence detection → location-aware suggestions
- Traffic anomalies → energy-saving opportunities
- Network context for security/camera suggestions

## [0.4.9] - 2026-02-14

### Added
- **SystemHealth Neuron** — Monitor Zigbee/Z-Wave Mesh, Recorder, and system updates:
  - **Zigbee Mesh Monitoring (ZHA)**: Coordinator online status, device count, unavailable device detection
  - **Z-Wave Mesh Monitoring**: Network state, node ready/sleeping count, readiness percentage
  - **Recorder Database Health**: Database size tracking, recording state monitoring
  - **Update Availability**: Core, OS, Supervised update detection
  - **Overall Health Status**: healthy/degraded/unhealthy aggregation across all subsystems
  - **Suggestion Suppression**: `should_suppress_suggestions()` API for suggestion relevance decisions

### REST API Endpoints
- `GET /api/v1/system_health` — Full health snapshot (all subsystems)
- `GET /api/v1/system_health/zigbee` — Zigbee mesh status
- `GET /api/v1/system_health/zwave` — Z-Wave mesh status
- `GET /api/v1/system_health/recorder` — Database health
- `GET /api/v1/system_health/updates` — Available updates
- `GET /api/v1/system_health/suppress` — Check if suggestions should be suppressed

### Technical Details
- **Caching**: 5-minute TTL for all health metrics
- **Lazy Initialization**: Service only active when hass object available
- **Privacy-First**: No external data transmission, all metrics local
- **Modular Design**: Follows same pattern as Mood, BrainGraph, Habitus modules

### Use Cases
- Suppress automation suggestions when Zigbee/Z-Wave mesh is unstable
- Prioritize suggestions based on system stability
- Alert users to large databases or pending updates
- Provide diagnostic data for support/debugging

## [0.4.8] - 2026-02-14

### Changed
- **Modular Architecture Refactor**: Extracted service initialization and blueprint registration into separate module
  - New `copilot_core/core_setup.py`: Contains `init_services()` and `register_blueprints()` functions
  - New `copilot_core/__init__.py`: Package version marker
  - `main.py` reduced from 176→93 lines (47% reduction)
  - Follows same pattern as HA Integration v0.5.4 (services_setup.py extraction)
  - Enables easier testing and dependency injection

### Benefits
- Cleaner main.py entry point
- Services dict returned for testing/DI purposes
- Blueprints registered in one place
- Easier to add/remove modules without touching main.py

## [0.4.7] - 2026-02-11

### Added
- **Mood Module v0.1 — Context-Aware Comfort/Frugality/Joy Scoring**:
  - **MoodService**: Per-zone mood metrics from MediaContext + Habitus signals
  - **ZoneMoodSnapshot**: comfort (0–1), frugality (0–1), joy (0–1) + metadata
  - **Mood Updates**: `update_from_media_context()` + `update_from_habitus()`
  - **Suggestion Context**: `should_suppress_energy_saving()`, `get_suggestion_relevance_multiplier()`
  - **REST API**: GET `/api/v1/mood`, POST `/update-media`, POST `/update-habitus`, etc.
  - **Exponential Smoothing**: Mood values smoothed for continuity (α=0.3)

### Use Cases
- Suppress energy-saving during entertainment (joy > 0.6)
- Weight comfort automations by comfort priority
- Suppress energy-saving if user prioritizes comfort (comfort > 0.7, frugality < 0.5)
- Adjust suggestion confidence by zone mood context

### Technical Details
- Time-of-day aware comfort baselines (morning/afternoon/evening/night)
- Media activity detection (music/TV) → joy boost
- Occupancy level + time-of-day → joy baseline
- Suggestion relevance multipliers: energy_saving, comfort, entertainment, security

## [0.4.6] - 2026-02-11

### Fixed
- **API Security Decorator**: New `require_api_key()` decorator in `security.py`
  - Proper Flask route authentication (not just validation helper)
  - Consistent imports across all API modules
  - Returns 401 Unauthorized for invalid tokens
- **E2E Test Fixes**: All 17 tests passing
  - `BrainGraphService.get_graph_state()` method name fix
  - `CandidateStore(storage_path=)` parameter naming
  - `HabitusMiner` returns Dict (not List)
  - Graceful Flask API smoke test skipping

## [0.4.5] - 2026-02-10

### Added
- **N2 Habitus Miner — Complete A→B Pattern Discovery** — Vervollständigung des N2 Core API Milestones:
  - **Temporal Sequence Mining**: Analyse zeit-geordneter Aktionsfolgen im Brain Graph mit konfigurierbaren Delta-Zeit-Fenstern
  - **Statistical Evidence**: Berechnung von Support/Confidence/Lift Metriken für jedes A→B Muster nach Association Rule Mining Prinzipien
  - **Debounce Logic**: Intelligent noise reduction um wiederholte Aktionen als separate Events zu behandeln
  - **REST API**: `/api/v1/habitus/mine` (POST), `/api/v1/habitus/stats` (GET), `/api/v1/habitus/patterns` (GET)
  - **Auto-Candidate Creation**: Entdeckte Muster werden automatisch als Candidates erstellt für HA Repairs Integration
  - **Configurable Thresholds**: Anpassbare min_confidence (0.6), min_support (0.1), min_lift (1.2) für Pattern-Qualität

### Technical Details
- HabitusMiner: Zeit-Fenster-basierte Sequenz-Analyse (15min Delta, 5min Debounce default)
- HabitusService: High-level Orchestrierung von Mining → Candidate Creation Pipeline
- Pattern Evidence: Support = P(A ∩ B), Confidence = P(B|A), Lift = P(B|A)/P(B)
- API Integration: Vollständige Integration in Core Add-on mit Flask Blueprint
- **N2 Milestone ✅ Complete**: Events API + Candidate Storage + Habitus Mining = Core API v1

## [0.4.4] - 2026-02-10

### Added  
- **Candidate Storage System** — vollständige Automation-Vorschlag-Lifecycle-Verwaltung:
  - **REST API**: `/api/v1/candidates` für Create/Read/Update von Suggestion-Kandidaten
  - **Persistence**: JSON-basierte lokale Speicherung mit atomischen Schreibvorgängen
  - **Lifecycle States**: pending → offered → accepted/dismissed/deferred mit Retry-Logic
  - **Evidence Tracking**: Support/Confidence/Lift Metriken für jede Suggestion  
  - **Cleanup**: Automatische Entfernung alter accepted/dismissed Kandidaten

### Technical Details
- Candidate Store: `/data/candidates.json` mit atomischen Updates via temp files
- API Endpoints: GET/POST `/api/v1/candidates`, GET/PUT `/api/v1/candidates/{id}`, GET `/api/v1/candidates/stats`
- Privacy-First: Alle Daten bleiben lokal, keine externe Übertragung
- N2 Core API Milestone: Candidate storage foundations für HA Repairs Integration

## [0.4.3] - 2026-02-10

### Enhanced
- **Brain Graph Intelligence** — erweiterte Zone-Inferenz und Intent-Tracking basierend auf Alpha Worker N3/N4 Spezifikation:
  - **Zone-Inferenz**: Multi-Source Zone-Erkennung (state values, friendly_name patterns, entity_id patterns) mit konfidenz-basierter Gewichtung
  - **Intentional Actions**: Service Calls erhalten erhöhte Salienz (2.0x) + stärkere Edges zu betroffenen Entities (1.5x weight)
  - **Spatial Intent**: Service → Entity → Zone Ketten für räumliche Kontext-Ableitung  
  - **Trigger Inference**: Context parent_id basierte Kausalitäts-Erkennung zwischen Events
  - **Pattern API**: Neuer `/api/v1/graph/patterns` Endpunkt für häufig kontrollierte Entities und Zone-Activity-Hubs
  - **Device Integration**: device_id → Entity Verknüpfungen für Hardware-Context

### Technical Details
- Implementiert Alpha Worker N3 "Forwarder Quality" + N4 "Brain Graph Core" Empfehlungen
- Erhöhte Salience für interaktive Domains (light, switch, cover, media_player)  
- Confidence-weighted zone links: Direct state (1.0) > Friendly name (0.7) > Entity name (0.5)
- Pattern inference für Automation-Hints und UI-Priorisierung

## [0.4.2] - 2026-02-10

### Added
- **Event Processing Pipeline** — completes the real-time data flow from HA → EventStore → BrainGraph
  - `EventProcessor` bridges event ingest with Brain Graph service for automatic knowledge graph updates
  - State changes create entity + zone nodes with `located_in` relationship edges
  - Service calls create service nodes with `targets` edges to affected entities (higher salience for intentional actions)
  - Post-ingest callback hook (non-blocking) enables pluggable downstream consumers
  - `EventStore.ingest_batch` now returns accepted events for immediate downstream processing
  - **11 new unit tests** (total: 76 across all Core modules)

## [0.4.1] - 2026-02-10

### Added
- **Brain Graph Module** (`/api/v1/graph/*`): Complete knowledge representation system
  - **`/api/v1/graph/state`**: JSON API for bounded graph state with filtering (kind, domain, center/hops, limits)
  - **`/api/v1/graph/snapshot.svg`**: DOT/SVG visualization with themes (light/dark), layouts (dot/neato/fdp), hard render limits
  - **`/api/v1/graph/stats`**: Graph statistics + configuration (node/edge counts, limits, decay parameters)
  - **`/api/v1/graph/prune`**: Manual pruning trigger
  - **Privacy-first storage**: PII redaction, bounded metadata (2KB max), automatic salience management
  - **Exponential decay**: 24h half-life for nodes, 12h for edges with effective score calculation
  - **SQLite backend**: Bounded capacity (500 nodes, 1500 edges), automatic pruning, neighborhood queries
  - **HA event processing**: Hooks for state_changed and call_service events
  - **Complete test coverage**: 27 unit tests covering privacy, bounds, decay, pruning, neighborhood queries
- **Dependencies**: Added `graphviz` package to Dockerfile for SVG rendering

### Technical Details
- This establishes the central knowledge representation for entity/zone/device relationships
- Privacy-first design with automatic PII redaction and bounded storage
- No breaking changes, new endpoints accessible immediately
- All compile checks and unit tests passing ✓

---

## [0.4.0] - 2026-02-10

### 🎉 Major Release: Tag System + Event Pipeline Foundation

This release introduces the foundational data architecture for the AI Home CoPilot system.

#### Added
- **Tag System Module** (`/api/v1/tag-system`): Complete privacy-first tag registry and assignment management
  - Canonical tag definitions with multi-language support
  - Persistent tag-assignment store with CRUD operations
  - Subject validation (entity/device/area/automation/scene/script)
  - Default tags: `aicp.kind.light`, `aicp.role.safety_critical`, `aicp.state.needs_repair`, `sys.debug.no_export`

- **Event Ingest Pipeline** (`/api/v1/events`): HA→Core data forwarding infrastructure
  - Bounded ring buffer with JSONL persistence
  - Thread-safe deduplication with TTL-based cleanup
  - Privacy-first validation and context ID truncation
  - Query endpoints with domain/entity/zone/temporal filters
  - Comprehensive statistics and diagnostics

- **API Security**: Shared authentication helper for token-based endpoint protection

#### Technical
- **Dependencies**: Added PyYAML 6.0.1 for tag registry YAML parsing
- **Storage**: Configurable paths via environment variables
- **Testing**: 19+ unit tests covering core functionality (tag registry, event store, API validation)

#### Developer Notes
- All tests passing ✓
- Code compiles cleanly with `python3 -m compileall`
- Ready for production deployment
- Privacy-first design with automatic redaction policies

---

## [0.1.1] - 2026-02-07

### Added
- Initial MVP scaffold with health endpoints
- Basic service framework
- Ingress configuration for web UI access

## [0.1.0] - 2026-02-07

### Added
- Initial release
- Core service foundations