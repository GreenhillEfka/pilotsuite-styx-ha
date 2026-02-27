# PilotSuite Styx -- User Guide

> **Version:** 10.4.0 | **Last updated:** February 2026

This guide covers the complete setup, configuration, and usage of PilotSuite Styx for Home Assistant. PilotSuite consists of two components: the **HACS Integration** (this repository) and the **Core Add-on** (backend). Together they provide 94+ sensors, 36 modules, a neural mood system, a brain graph, and intelligent automation suggestions -- all running locally on your Home Assistant instance.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Start](#2-quick-start)
3. [Three Setup Paths](#3-three-setup-paths)
4. [Auto-Setup](#4-auto-setup)
5. [Modules](#5-modules)
6. [Sensors](#6-sensors)
7. [Neural System](#7-neural-system)
8. [Mood System](#8-mood-system)
9. [Brain Graph](#9-brain-graph)
10. [Habitus Zones](#10-habitus-zones)
11. [Dashboard](#11-dashboard)
12. [Events Forwarder](#12-events-forwarder)
13. [Entity Tags](#13-entity-tags)
14. [Privacy](#14-privacy)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Overview

### What Is PilotSuite?

PilotSuite Styx is a **privacy-first, local AI assistant** for Home Assistant. It observes your home's patterns, builds a knowledge graph of entity relationships, infers household mood, and proposes intelligent automations -- all without sending a single byte to the cloud.

The human always decides. PilotSuite follows a strict **governance-first** model: it suggests, it never acts silently.

### Key Principles

| Principle | Meaning |
|-----------|---------|
| **Local-first** | All processing happens on your hardware. No cloud APIs, no telemetry, no account required. |
| **Privacy-first** | PII redaction on every data path, bounded storage, opt-in for sensitive features. |
| **Governance-first** | Suggestions before actions. The user explicitly accepts or dismisses every automation candidate. |
| **Reversible** | All changes can be rolled back. Configurations are snapshot-able via Backup/Restore. |
| **Transparent** | Every suggestion comes with evidence, confidence scores, and an explanation of contributing factors. |

### Architecture

PilotSuite is split into two cooperating components:

| Component | Description | Communication |
|-----------|-------------|---------------|
| **Core Add-on** | Flask/Waitress backend running as an HA Add-on on port 8909. Houses the Brain Graph, Mood Engine, Neurons, Habitus Miner, Candidate Manager, Vector Store, and LLM conversation engine. | REST API (token-authenticated) |
| **HACS Integration** | Home Assistant custom component (`custom_components/ai_home_copilot`). Provides 94+ sensors, 36 modules, dashboard cards, the Events Forwarder, zone management, and the Options Flow UI. | Coordinator polling (120 s) + Webhook push (real-time) |

```
Home Assistant
  |
  +-- HACS Integration (custom_components/ai_home_copilot)
  |     Sensors, Entities, Event Forwarder, Zones, Tags
  |     |
  |     +--[ HTTP / Webhook ]--> Core Add-on (:8909)
  |                                Brain Graph, Neurons, Mood Engine
  |                                Habitus Miner, Candidates, LLM
  +-- Lovelace Dashboard
        Sidebar Panel, Zone Cards, Brain Graph Viz, Mood Tracker
```

**Prerequisite:** The Core Add-on must be installed and running before the HACS Integration is configured.

---

## 2. Quick Start

### Step 1 -- Install the Core Add-on

1. Open **Settings > Add-ons > Add-on Store**.
2. Add the repository: `https://github.com/GreenhillEfka/pilotsuite-styx-core`
3. Install **PilotSuite Core**.
4. Configure the add-on (at minimum, set `auth_token`):

```yaml
log_level: info
auth_token: your-secret-token-change-me
conversation_enabled: true
conversation_ollama_model: qwen3:0.6b
conversation_prefer_local: true
```

5. Click **Start**. Verify with:

```bash
curl http://homeassistant.local:8909/health
# {"ok": true}
```

### Step 2 -- Install the HACS Integration

1. Open **HACS > Integrations**.
2. Menu (three dots) > **Custom repositories**.
3. Add URL: `https://github.com/GreenhillEfka/pilotsuite-styx-ha` -- Type: **Integration**.
4. Install **PilotSuite** and **restart Home Assistant**.

### Step 3 -- Configure the Integration

1. Go to **Settings > Devices & Services > Add Integration > PilotSuite**.
2. Choose **Zero Config** (recommended for first-time users).
3. Done. PilotSuite auto-discovers your areas, creates zones, classifies entities, and connects to Core.

### Step 4 -- Verify

After restart, check:

- `sensor.ai_home_copilot_version` -- shows the installed version.
- `sensor.ai_home_copilot_core_api_v1_status` -- should be `online`.
- The **PilotSuite** entry appears in the HA sidebar.

---

## 3. Three Setup Paths

When adding the integration, you choose one of three paths:

| Path | Description | Recommended for |
|------|-------------|-----------------|
| **Zero Config** | Instant start with default values. Styx auto-discovers devices and asks for refinements later via conversation. | First-time users, quick evaluation |
| **Quick Start** | Guided wizard (~2 min). Optional auto-discovery, zone selection, media player assignment, feature selection, network configuration. | Most users |
| **Manual Setup** | Full manual configuration of all fields. | Advanced users, non-standard network setups |

### Configuration Fields

| Field | Description | Default |
|-------|-------------|---------|
| `assistant_name` | Display name of the assistant | `Styx` |
| `host` | Hostname or IP of the Core Add-on | `homeassistant.local` |
| `port` | Core Add-on port | `8909` |
| `token` | Authentication token (empty = no auth, for first setup) | (empty) |
| `test_light_entity_id` | Optional light entity for a quick function test | (empty) |

### Quick Start Wizard Steps

1. **Discovery** -- Enable auto-discovery (scans compatible devices).
2. **Zones** -- Select suggested zones from HA Areas.
3. **Zone Entities** -- Assign entities per zone (motion, lights, sensors, media).
4. **Entities** -- Configure media players (music + TV).
5. **Features** -- Activate desired modules.
6. **Network** -- Enter host, port, token.
7. **Review** -- Verify summary and confirm.

### Post-Setup Configuration

All settings can be changed at any time via **Settings > Integrations > PilotSuite > Configure**. The Options Flow provides a main menu with sections:

- **Settings** -- All configuration fields (network, modules, forwarder, debug).
- **Habitus zones** -- Create/edit/delete zones, generate dashboards, bulk edit.
- **Entity Tags** -- Create/edit/delete tags.
- **Neurons** -- Configure the neural system (context, state, mood entities).
- **Backup/Restore** -- Configuration snapshots.

---

## 4. Auto-Setup

Auto-Setup runs once after initial configuration and sets up PilotSuite automatically.

### What Happens Automatically

1. **Area Discovery** -- All Home Assistant Areas are detected.
2. **Zone Creation** -- A Habitus Zone is created for each Area that contains entities.
3. **Entity Classification** -- Every entity is classified using 4 signals:
   - Domain (`light` maps to Light)
   - Device class (`motion` maps to Motion)
   - Unit of measurement (`lx` maps to Illuminance)
   - Name keywords (both German and English)
4. **Role Assignment** -- Entities are assigned to zone roles (motion, lights, temperature, media, etc.).
5. **Tag Creation** -- Domain-based tags are created automatically (see [Entity Tags](#13-entity-tags)).

### Verifying Results

After auto-setup, an onboarding notification shows:

- Number of zones created
- Number of entities assigned
- Number of tags created

You can review and refine everything under **Configure > Habitus zones** and **Configure > Entity Tags**.

---

## 5. Modules

PilotSuite comprises **36 modules** organized into **4 tiers**. All modules implement the `CopilotModule` interface with a standardized lifecycle (`async_setup_entry`, `async_unload_entry`, `async_reload_entry`). Modules are managed through the Runtime Registry, and failed modules are automatically isolated so they do not affect the rest of the system.

### Module Tiers

| Tier | Name | Behavior |
|------|------|----------|
| **T0 (Kernel)** | Always active, essential for operation | Cannot be disabled |
| **T1 (Brain)** | Intelligence layer, active when Core is reachable | Core connection required |
| **T2 (Context)** | Environmental awareness, activated when relevant entities exist | Enables automatically |
| **T3 (Extensions)** | Manually activatable add-ons | Opt-in via Options Flow |

### Complete Module Table

| # | Module | Registry Name | Tier | Function |
|---|--------|--------------|------|----------|
| 1 | LegacyModule | `legacy` | T0 | Base integration: Coordinator, Webhook, Blueprints, platforms (sensor, button, etc.) |
| 2 | PerformanceScalingModule | `performance_scaling` | T0 | Performance guardrails, backoff limits, concurrency guards |
| 3 | EventsForwarderModule | `events_forwarder` | T0 | Forward HA events to Core (batched, PII-redacted, persistent queue, idempotent) |
| 4 | DevSurfaceModule | `dev_surface` | T3 | Debug controls, error registry, 30-min debug timer, log-level management |
| 5 | HabitusMinerModule | `habitus_miner` | T1 | A-to-B pattern discovery, association rules, zone-based mining |
| 6 | OpsRunbookModule | `ops_runbook` | T3 | Operations runbook: common problems and resolution guides |
| 7 | UniFiModule | `unifi_module` | T2 | UniFi network diagnostics: WAN quality, Wi-Fi roaming, AP health |
| 8 | BrainGraphSyncModule | `brain_graph_sync` | T1 | Brain Graph synchronization with Core via `/api/v1/graph` endpoints |
| 9 | CandidatePollerModule | `candidate_poller` | T1 | Poll suggestions from Core (every 5 min), create HA Repairs issues, sync decisions back |
| 10 | MediaContextModule | `media_zones` | T2 | Media player tracking: music, TV, zone assignment, privacy-safe |
| 11 | MoodModule | `mood` | T1 | Local mood inference: comfort/joy/frugality vector, character integration |
| 12 | MoodContextModule | `mood_context` | T1 | Mood consumer: poll Core Mood API, zone mood cache, suggestion suppression |
| 13 | EnergyContextModule | `energy_context` | T2 | Energy monitoring: consumption, production, anomalies, load shifting |
| 14 | UnifiContextModule | `network` | T2 | Network context: WAN status, clients, roaming, traffic baselines |
| 15 | WeatherContextModule | `weather_context` | T2 | Weather data for PV forecasting and energy optimization |
| 16 | KnowledgeGraphSyncModule | `knowledge_graph_sync` | T1 | Knowledge Graph sync: entities, areas, zones, tags, capabilities |
| 17 | MLContextModule | `ml_context` | T1 | ML pipeline: anomaly detection, habit prediction, energy optimization |
| 18 | CameraContextModule | `camera_context` | T2 | Camera events: motion detection, face recognition, object detection (local) |
| 19 | QuickSearchModule | `quick_search` | T3 | Entity, automation, and service search for quick access |
| 20 | VoiceContextModule | `voice_context` | T2 | Voice control context: commands, TTS, state tracking |
| 21 | HomeAlertsModule | `home_alerts` | T1 | Critical state monitoring: battery, climate, presence, system |
| 22 | CharacterModule | `character_module` | T1 | Personality/character presets: mood weighting, tone of voice |
| 23 | WasteReminderModule | `waste_reminder` | T3 | Waste collection reminders: evening + morning, TTS, persistent notifications |
| 24 | BirthdayReminderModule | `birthday_reminder` | T3 | Birthday reminders: calendar scan, TTS, 14-day preview |
| 25 | EntityTagsModule | `entity_tags` | T1 | Entity tagging: manual + auto-tags ("Styx"), module queries |
| 26 | PersonTrackingModule | `person_tracking` | T2 | Person tracking: who is home, arrival/departure history |
| 27 | FrigateBridgeModule | `frigate_bridge` | T2 | Frigate NVR bridge: person/motion detection event forwarding |
| 28 | SceneModule | `scene_module` | T1 | Scene management: save/learn/suggest zone scenes |
| 29 | HomeKitBridgeModule | `homekit_bridge` | T3 | HomeKit bridge: expose Habitus Zones as HomeKit-compatible bridge |
| 30 | CalendarModule | `calendar_module` | T3 | Calendar integration: HA `calendar.*` entities, events for LLM context |
| 31 | UserPreferenceModule | `user_preference` | T1 | Multi-user preference learning (per-user, per-zone) |
| 32 | MultiUserPreferenceModule | `mupl` | T3 | Extended multi-user learning with privacy modes (opt-in) |
| 33 | ZoneDetector | `zone_detector` | T1 | Proactive zone-entry detection and forwarding to Core |
| 34 | HouseholdModule | `household` | T1 | Household configuration and age group management |
| 35 | PilotSuiteUIModule | `pilotsuite_ui` | T3 | Entity profiles and button groups |
| 36 | WatchdogModule | `watchdog` | T0 | Connection health-check with Core Add-on |

### Configuring Modules

Navigate to **Settings > Integrations > PilotSuite > Configure > Modules** to enable or disable individual modules and adjust their parameters.

---

## 6. Sensors

PilotSuite creates **94+ sensors** in Home Assistant. All sensors use the entity ID prefix `sensor.ai_home_copilot_*`. The `unique_id` follows the pattern `ai_home_copilot_{feature}_{name}`.

### Mood Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_copilot_mood` | Current mood state (relax/focus/active/night/away/neutral) |
| `sensor.ai_copilot_mood_confidence` | Confidence value of the mood signal |
| `sensor.ai_copilot_neuron_activity` | Aggregated neural activity |
| `sensor.ai_home_copilot_mood_dashboard` | Mood dashboard JSON (all dimensions) |
| `sensor.ai_home_copilot_mood_history` | Mood history over time |
| `sensor.ai_home_copilot_mood_explanation` | Mood explanation (contributing neurons) |
| `sensor.ai_home_copilot_mood_comfort` | Comfort dimension (0.0--1.0) |
| `sensor.ai_home_copilot_mood_joy` | Joy dimension (0.0--1.0) |
| `sensor.ai_home_copilot_mood_frugality` | Frugality dimension (0.0--1.0) |
| `sensor.ai_home_copilot_mood_energy` | Energy dimension (0.0--1.0) |
| `sensor.ai_home_copilot_mood_stress` | Stress dimension (0.0--1.0) |

### Neuron Sensors (14 Neurons + 2 Media)

| Entity ID | Neuron | Description |
|-----------|--------|-------------|
| `sensor.ai_home_copilot_presence_room` | Presence.Room | Active room based on motion entities |
| `sensor.ai_home_copilot_presence_person` | Presence.Person | Detected persons in the household |
| `sensor.ai_home_copilot_activity_level` | Activity.Level | Activity level (low/medium/high) |
| `sensor.ai_home_copilot_activity_stillness` | Activity.Stillness | Duration of stillness |
| `sensor.ai_home_copilot_time_of_day` | Time.OfDay | Time-of-day segment (morning/noon/afternoon/evening/night) |
| `sensor.ai_home_copilot_day_type` | Day.Type | Day type (workday/weekend/holiday) |
| `sensor.ai_home_copilot_routine_stability` | Routine.Stability | Stability of the daily routine |
| `sensor.ai_home_copilot_light_level` | Environment.Light | Light level from brightness sensors |
| `sensor.ai_home_copilot_noise_level` | Environment.Noise | Noise level from sound sensors |
| `sensor.ai_home_copilot_weather_context` | Weather.Context | Weather context (clear/cloudy/rain/etc.) |
| `sensor.ai_home_copilot_calendar_load` | Calendar.Load | Calendar load (free/normal/busy) |
| `sensor.ai_home_copilot_attention_load` | Cognitive.Attention | Attention load |
| `sensor.ai_home_copilot_stress_proxy` | Cognitive.Stress | Stress proxy (derived from activity, calendar, etc.) |
| `sensor.ai_home_copilot_energy_proxy` | Energy.Proxy | Energy consumption proxy |
| `sensor.ai_home_copilot_media_activity` | Media.Activity | Media usage (idle/playing/paused) |
| `sensor.ai_home_copilot_media_intensity` | Media.Intensity | Media intensity (derived from type + volume) |

### Habitus Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_home_copilot_habitus_zones_v2_count` | Number of configured Habitus Zones |
| `sensor.ai_home_copilot_habitus_zones_v2_states` | Zone states (idle/active/etc.) |
| `sensor.ai_home_copilot_habitus_zones_v2_health` | Zone health |
| `sensor.ai_home_copilot_habitus_miner_rule_count` | Number of discovered association rules |
| `sensor.ai_home_copilot_habitus_miner_status` | Mining status (idle/mining/ready) |
| `sensor.ai_home_copilot_habitus_miner_top_rule` | Strongest discovered rule |
| `sensor.ai_home_copilot_*_zone_avg_*` | Zone averages (temperature, humidity, etc.) |

### Energy Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_home_copilot_energy_insight` | Energy insight (ML-based) |
| `sensor.ai_home_copilot_energy_recommendation` | Energy recommendation |
| `sensor.ai_home_copilot_energy_proxy` | Energy consumption proxy |

### Media Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_home_copilot_music_now_playing` | Currently playing track |
| `sensor.ai_home_copilot_music_primary_area` | Area with active music |
| `sensor.ai_home_copilot_music_active_count` | Number of active music players |
| `sensor.ai_home_copilot_tv_primary_area` | Area with active TV |
| `sensor.ai_home_copilot_tv_source` | Active TV source |
| `sensor.ai_home_copilot_tv_active_count` | Number of active TV players |
| `sensor.ai_home_copilot_media_v2_active_mode` | Active media mode (v2) |
| `sensor.ai_home_copilot_media_v2_active_target` | Active media target (v2) |
| `sensor.ai_home_copilot_media_v2_active_zone` | Active media zone (v2) |

### Brain Graph / Knowledge Graph Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_copilot_neuron_dashboard` | Neuron dashboard JSON (all neuron states) |
| `sensor.ai_copilot_mood_history` | Mood history |
| `sensor.ai_copilot_suggestion` | Current suggestions |

### Calendar / Waste / Birthday Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_home_copilot_calendar_context` | Calendar context (events, focus/social weight) |
| `sensor.ai_home_copilot_calendar` | Integrated HA calendars |
| `sensor.ai_home_copilot_waste_next_collection` | Next collection (type, days until, date) |
| `sensor.ai_home_copilot_waste_today_count` | Collections scheduled today |
| `sensor.ai_home_copilot_birthday_today_count` | Birthdays today |
| `sensor.ai_home_copilot_birthday_next` | Next birthday (name, days until, age) |

### ML / Anomaly / Prediction Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_home_copilot_anomaly_alert` | Active anomaly alert |
| `sensor.ai_home_copilot_alert_history` | Alert history |
| `sensor.ai_home_copilot_habit_learning` | Learned habits |
| `sensor.ai_home_copilot_habit_prediction` | Habit prediction |
| `sensor.ai_home_copilot_sequence_prediction` | Sequence prediction |
| `sensor.ai_home_copilot_predictive_automation` | Suggested automation |
| `sensor.ai_home_copilot_predictive_automation_details` | Prediction details |

### System / Health Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_home_copilot_version` | Installed version |
| `sensor.ai_home_copilot_core_api_v1_status` | Core API status (online/offline) |
| `sensor.ai_home_copilot_pipeline_health` | Pipeline health |
| `sensor.ai_home_copilot_debug_mode` | Current debug mode (off/light/full) |
| `sensor.ai_home_copilot_entity_count` | Number of managed entities |
| `sensor.ai_home_copilot_sqlite_db_size` | SQLite database size |
| `sensor.ai_home_copilot_inventory_last_run` | Last inventory scan |

### Mesh / Network Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_home_copilot_zwave_network_health` | Z-Wave network health |
| `sensor.ai_home_copilot_zwave_devices_online` | Z-Wave devices online |
| `sensor.ai_home_copilot_zwave_battery_overview` | Z-Wave battery overview |
| `sensor.ai_home_copilot_zigbee_network_health` | Zigbee network health |
| `sensor.ai_home_copilot_zigbee_devices_online` | Zigbee devices online |
| `sensor.ai_home_copilot_zigbee_battery_overview` | Zigbee battery overview |
| `sensor.ai_home_copilot_mesh_network_overview` | Mesh network overview |
| `sensor.ai_home_copilot_network_health` | UniFi network health |

### Events Forwarder Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_home_copilot_forwarder_queue_depth` | Current queue depth |
| `sensor.ai_home_copilot_forwarder_dropped_total` | Total dropped events |
| `sensor.ai_home_copilot_forwarder_error_streak` | Current error streak |

### Home Alerts Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_home_copilot_home_alerts_count` | Number of active alerts |
| `sensor.ai_home_copilot_home_health_score` | Home health score (0--100) |
| `sensor.ai_home_copilot_home_alerts_battery` | Battery warnings |
| `sensor.ai_home_copilot_home_alerts_climate` | Climate deviations |
| `sensor.ai_home_copilot_home_alerts_presence` | Presence changes |
| `sensor.ai_home_copilot_home_alerts_system` | System warnings |

### Voice / Camera / Other Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_copilot_voice_context` | Voice context (voice control) |
| `sensor.ai_copilot_voice_prompt` | Current voice prompt |
| `sensor.ai_home_copilot_camera_motion_history` | Camera motion history |
| `sensor.ai_home_copilot_camera_presence_history` | Camera presence history |
| `sensor.ai_home_copilot_camera_activity_history` | Camera activity history |
| `sensor.ai_home_copilot_camera_zone_activity` | Camera zone activity |
| `sensor.ai_home_copilot_character_preset` | Active character preset |
| `sensor.ai_home_copilot_entity_tags` | Number of entity tags |
| `sensor.ai_home_copilot_persons_home` | Persons currently home |
| `sensor.ai_home_copilot_frigate_cameras` | Detected Frigate cameras |
| `sensor.ai_home_copilot_zone_scenes` | Saved zone scenes |
| `sensor.ai_home_copilot_homekit_bridge` | HomeKit-exposed zones |
| `sensor.ai_home_copilot_mobile_dashboard` | Mobile dashboard card data |

### Inspector Sensors (Debug)

| Entity ID | Description |
|-----------|-------------|
| `sensor.ai_home_copilot_inspector_zones` | Habitus Zones internal state |
| `sensor.ai_home_copilot_inspector_tags` | Active Tags internal state |
| `sensor.ai_home_copilot_inspector_character` | Character Profile internal state |
| `sensor.ai_home_copilot_inspector_mood` | Current Mood internal state |

---

## 7. Neural System

The Neural System consists of **14 neurons** (plus 2 media neurons) that evaluate the state of the household in real time. Neurons feed the Mood vector and influence suggestions and automations.

### Three-Layer Pipeline

Neurons are organized in three processing layers, evaluated in sequence:

| Layer | Purpose | Example Neurons |
|-------|---------|-----------------|
| **Context** | Raw environmental signals | Time.OfDay, Presence.Room, Weather.Context, Environment.Light |
| **State** | Derived behavioral states | Activity.Level, Routine.Stability, Cognitive.Stress, Energy.Proxy |
| **Mood** | Aggregate mood inference | Feeds into the 6 discrete states and 5 continuous dimensions |

### The 14 Neurons

| # | Neuron | Category | What It Measures |
|---|--------|----------|------------------|
| 1 | Time.OfDay | Time | Time-of-day segment (morning/noon/afternoon/evening/night) |
| 2 | Day.Type | Time | Day type (workday/weekend/holiday) |
| 3 | Routine.Stability | Time | Daily routine stability compared to historical averages |
| 4 | Calendar.Load | Calendar | Calendar load (appointments in the next 24 hours) |
| 5 | Attention.Load | Cognitive | Attention load (derived from calendar + activity) |
| 6 | Stress.Proxy | Cognitive | Stress proxy (calendar density + activity level + time of day) |
| 7 | Presence.Room | Presence | Active room based on motion entities across all zones |
| 8 | Presence.Person | Presence | Who is home (`person.*` / `device_tracker.*`) |
| 9 | Energy.Proxy | Energy | Energy consumption relative to baseline |
| 10 | Weather.Context | Weather | Current weather from `weather.*` entities |
| 11 | Environment.Light | Environment | Light level from illuminance sensors |
| 12 | Environment.Noise | Environment | Noise level from sound sensors |
| 13 | Activity.Level | Activity | Overall activity (low/medium/high based on state changes) |
| 14 | Activity.Stillness | Activity | Time since last detected movement/activity |

Additionally, two **media neurons** provide supplementary context:

| Neuron | Description |
|--------|-------------|
| Media.Activity | Media usage state (idle/playing/paused) |
| Media.Intensity | Media intensity (derived from content type + volume) |

### Configuring the Neural System

Under **Settings > Integrations > PilotSuite > Configure > Neurons**:

| Setting | Description | Default |
|---------|-------------|---------|
| `neuron_enabled` | Enable/disable the neural system | `true` |
| `neuron_evaluation_interval` | Evaluation interval in seconds | `60` |
| `neuron_context_entities` | Entity IDs for context neurons (CSV) | (empty) |
| `neuron_state_entities` | Entity IDs for state neurons (CSV) | (empty) |
| `neuron_mood_entities` | Entity IDs for mood neurons (CSV) | (empty) |

---

## 8. Mood System

The Mood System aggregates all 14 neuron signals into a holistic assessment of the household's current state. It operates on two parallel tracks: **6 discrete mood states** and **5 continuous dimensions**.

### 6 Discrete Mood States

The discrete state is selected via Softmax probability with EMA (Exponential Moving Average) hysteresis to prevent rapid oscillation.

| State | Description | Typical Triggers |
|-------|-------------|-----------------|
| **Away** | Nobody is home | No presence detected by any zone |
| **Night** | Night mode | Late hour, low light, low activity |
| **Relax** | Relaxation | Evening, quiet, comfortable temperature |
| **Focus** | Concentration | Daytime, little movement, single occupant |
| **Active** | High activity | Morning, movement in multiple zones, music |
| **Neutral** | Default / transition | Fallback when no other state dominates |

### 5 Continuous Dimensions

Each dimension is a floating-point value between 0.0 and 1.0, updated in real time.

| Dimension | Range | Influencing Factors |
|-----------|-------|---------------------|
| **Comfort** | 0.0--1.0 | Temperature (Gaussian comfort curve), light level, noise, presence, routine stability |
| **Frugality** | 0.0--1.0 | Energy consumption relative to baseline |
| **Joy** | 0.0--1.0 | Media activity, social events, weather, presence of multiple people |
| **Energy** | 0.0--1.0 | Activity level, circadian rhythm |
| **Stress** | 0.0--1.0 | Alarms, notifications, errors, calendar density |

### How Mood Affects Behavior

The mood vector directly influences which suggestions the system makes:

- During **high Joy** (e.g., movie night): energy-saving suggestions are suppressed.
- During **high Stress**: only critical notifications are forwarded.
- During **Night**: automation suggestions are deferred to the next day.

### Mood Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| EMA Alpha | 0.3 | Smoothing factor (lower = smoother transitions) |
| Softmax Temperature | 1.0 | Decision sharpness (higher = more uniform distribution) |
| Dwell Time | 600 s | Minimum dwell time in a mood state before switching |
| History Retention | 30 days | How long mood history is kept |

These can be adjusted under **Settings > Integrations > PilotSuite > Configure > Settings**.

### Zone-Based Mood Profiles

The Core Mood Engine maintains per-zone `ZoneMoodProfile` objects with:

- Current discrete state and probabilities
- All 5 continuous dimensions
- Confidence score
- Context data (contributing factors)
- SQLite WAL-mode persistence with a 30-day rolling window

---

## 9. Brain Graph

The Brain Graph is a lightweight knowledge graph (backed by SQLite) that records entity relationships, discovered patterns, and evidence.

### Nodes

Nodes represent items in your smart home:

- **Entities** -- lights, sensors, media players, switches, etc.
- **Zones** -- Habitus Zones
- **Automations** -- HA automations
- **Scripts** -- HA scripts
- **Patterns** -- Discovered A-to-B rules

Each node carries a **score** (relevance weight) and metadata.

### Edges

Edges represent relationships between nodes:

| Edge Type | Meaning | Example |
|-----------|---------|---------|
| `triggers` | Entity A causes state change in Entity B | Motion sensor triggers hallway light |
| `controls` | Automation controls an entity | Morning routine controls kitchen light |
| `located_in` | Entity belongs to a zone | `light.living_room` is `located_in` zone `living_room` |
| `correlated_with` | Statistical correlation between entities | Temperature sensor correlates with thermostat state |

### Decay

Nodes and edges lose relevance over time through exponential decay:

| Parameter | Default | Description |
|-----------|---------|-------------|
| Node half-life | 24 h | Nodes lose half their score every 24 hours |
| Edge half-life | 12 h | Edges decay faster than nodes |
| Auto-pruning | Every 60 min | Nodes/edges below the prune threshold are removed |
| Max nodes | 500 | Hard cap on graph size |
| Max edges | 1500 | Hard cap on edge count |
| Prune threshold | 0.1 | Minimum score to survive pruning |

### Patterns

The Brain Graph stores discovered patterns from the Habitus Miner:

- **A-to-B rules**: "When entity A changes state, entity B changes within X minutes"
- Each pattern records **support** (frequency), **confidence** (reliability), and **lift** (strength vs. random chance)
- Patterns above confidence threshold become automation **candidates**

### Visualization

The Brain Graph can be visualized in multiple ways:

- **Sidebar Panel**: The PilotSuite sidebar entry in HA includes an interactive Brain Graph view (vis.js).
- **Static SVG**: Press `button.ai_home_copilot_publish_brain_graph_viz` to generate a static visualization.
- **Interactive Panel**: Press `button.ai_home_copilot_publish_brain_graph_panel` for a full interactive panel.

Generated files are placed in `www/ai_home_copilot/` and accessible via `/local/ai_home_copilot/`.

---

## 10. Habitus Zones

Habitus Zones are **curated room profiles, independent of HA Areas**. They define spaces where PilotSuite learns zone-specific patterns and proposes matching automations.

### Requirements per Zone

Each Habitus Zone requires at minimum:

- **1 motion/presence entity** (`binary_sensor` or `sensor` with device class motion/presence/occupancy)
- **1 light entity** (`light.*`)

Without both mandatory entities, a zone cannot be created.

### Zone Types

| Type | Hierarchy Level | Description |
|------|----------------|-------------|
| `floor` | 0 | Floor (e.g., ground floor, upper floor, basement) |
| `area` | 1 | Area (e.g., living area, sleeping area) |
| `room` | 2 (default) | Individual room |
| `outdoor` | 3 | Outdoor area |

### Entity Roles

Each zone assigns its entities to roles:

| Role | Description | Example |
|------|-------------|---------|
| `motion` | Motion/presence sensor (required) | `binary_sensor.living_room_motion` |
| `lights` | Light control (required) | `light.living_room_ceiling` |
| `brightness` / `illuminance` | Brightness sensor | `sensor.living_room_lux` |
| `temperature` | Temperature sensor | `sensor.living_room_temperature` |
| `humidity` | Humidity sensor | `sensor.living_room_humidity` |
| `co2` | CO2 sensor | `sensor.living_room_co2` |
| `heating` / `climate` | Heating/climate | `climate.living_room` |
| `cover` | Blinds/shutters | `cover.living_room_blinds` |
| `door` | Door sensor | `binary_sensor.living_room_door` |
| `window` | Window sensor | `binary_sensor.living_room_window` |
| `lock` | Lock | `lock.front_door` |
| `media` | Media player | `media_player.living_room_sonos` |
| `power` / `energy` | Power/energy measurement | `sensor.living_room_power` |
| `noise` | Noise level | `sensor.living_room_noise` |
| `pressure` | Air pressure | `sensor.living_room_pressure` |
| `other` | Other entities | any |

Role aliases are resolved automatically (e.g., `presence` becomes `motion`, `rollo` becomes `cover`, `luftfeuchte` becomes `humidity`).

### Creating Zones via Options Flow

Under **Settings > Integrations > PilotSuite > Configure > Habitus zones**:

- **Create zone** -- Enter zone ID, name, select motion entity, light entities, and optional entities.
- **Edit zone** -- Select an existing zone from the dropdown and modify fields.
- **Delete zone** -- Select a zone from the dropdown and delete it.
- **Suggest zones from Core** -- Let Core analyze your entities and suggest zones. Adopt the ones you want.

### Bulk Edit (YAML/JSON)

For larger adjustments, use **Bulk Edit**. Paste your entire zone configuration as YAML or JSON. The system validates the input and shows errors.

Example (YAML):

```yaml
- id: zone:living_room
  name: Living Room
  entities:
    motion:
      - binary_sensor.living_room_motion
    lights:
      - light.living_room_ceiling
      - light.living_room_floor_lamp
    temperature:
      - sensor.living_room_temperature
    humidity:
      - sensor.living_room_humidity
    media:
      - media_player.living_room_sonos

- id: zone:bedroom
  name: Bedroom
  entities:
    motion:
      - binary_sensor.bedroom_motion
    lights:
      - light.bedroom_ceiling
    cover:
      - cover.bedroom_blinds
```

Alternatively, use a flat `entity_ids` list instead of the categorized `entities` map:

```yaml
- id: zone:kitchen
  name: Kitchen
  entity_ids:
    - binary_sensor.kitchen_motion
    - light.kitchen_ceiling
    - sensor.kitchen_temperature
```

JSON format and the `{"zones": [...]}` wrapper are also accepted.

### Zone Hierarchy and Conflicts

Zones support parent-child relationships (`parent_zone_id`, `child_zone_ids`). When entities overlap between active zones, conflict resolution applies:

1. **Hierarchy** -- More specific zones (children) override more general ones (parents).
2. **Priority** -- Higher priority value wins (0 = low, 10 = high).
3. **User Prompt** -- The user is asked to resolve remaining conflicts.

### Zone States

Each zone has a state that is persisted across HA restarts:

| State | Meaning |
|-------|---------|
| `idle` | No activity detected |
| `active` | Person present, zone active |
| `transitioning` | State is changing |
| `disabled` | Zone is manually disabled |
| `error` | Error condition |

---

## 11. Dashboard

### Sidebar Panel

PilotSuite automatically registers a **"PilotSuite"** entry in the Home Assistant sidebar. This opens the Core dashboard, which includes:

- Brain Graph visualization
- Mood Engine status
- Neuron activity
- Automation candidates
- System health

### YAML Dashboard Generation

Dashboards are generated as Lovelace YAML files. There are two methods:

**Via Options Flow:**

1. Navigate to **Settings > Integrations > PilotSuite > Configure > Habitus zones > Generate dashboard**.
2. A YAML file is created in the `ai_home_copilot/` configuration folder.
3. **Publish dashboard** copies the file to `www/ai_home_copilot/` for a stable download URL.

**Via Buttons:**

| Button | Function |
|--------|----------|
| `button.ai_home_copilot_generate_habitus_dashboard` | Generate Habitus Zones dashboard YAML |
| `button.ai_home_copilot_download_habitus_dashboard` | Download Habitus Zones dashboard |
| `button.ai_home_copilot_generate_pilotsuite_dashboard` | Generate PilotSuite overview dashboard |
| `button.ai_home_copilot_download_pilotsuite_dashboard` | Download PilotSuite overview dashboard |

The generated dashboard includes 7 tabs: System, Neurons, Brain Graph, Core, Media, Habitus, and ML.

### Dashboard Content

The generated Habitus Zones dashboard includes per zone:

- **Entities Card** -- All assigned entities with state display.
- **Status Cards** -- Zone state, aggregated averages.
- **Action Buttons** -- Activate scenes, zone settings.

### Lovelace Cards

Core serves custom Lovelace cards under `/api/v1/cards/`. These are automatically registered as Lovelace resources.

Example cards:

```yaml
# Zone Context Card
type: custom:pilotsuite-zone-context
title: Living Room
zone: living_room
show_roles:
  - lights
  - temperature
  - motion
```

```yaml
# Brain Graph Card
type: custom:pilotsuite-brain-graph
title: Home Neural Network
center: zone.living_room
hops: 2
theme: dark
layout: dot
```

### Mobile Dashboard

Three sensors provide data optimized for mobile dashboard cards:

| Sensor | Purpose |
|--------|---------|
| `sensor.ai_home_copilot_mobile_dashboard` | Mobile-optimized overview |
| `sensor.ai_home_copilot_mobile_quick_actions` | Quick-access actions |
| `sensor.ai_home_copilot_mobile_entity_grid` | Entity grid for mobile view |

---

## 12. Events Forwarder

The Events Forwarder sends HA state changes to the Core Add-on in the **N3 envelope format**. It is **opt-in** (disabled by default).

### Activation

Under **Settings > Integrations > PilotSuite > Configure > Settings**:

| Setting | Default | Description |
|---------|---------|-------------|
| `events_forwarder_enabled` | `false` | Enable/disable the forwarder |
| `events_forwarder_flush_interval_seconds` | `5` | Flush interval (1--300 s) |
| `events_forwarder_max_batch` | `50` | Max events per batch (1--5000) |
| `events_forwarder_forward_call_service` | `false` | Also forward `call_service` events |
| `events_forwarder_idempotency_ttl_seconds` | `300` | Idempotency TTL (10--86400 s) |

### Batching

Events are collected in memory and flushed to Core every `flush_interval_seconds` as a batch. Each batch contains at most `max_batch` events. On error, events are not lost but retried in the next cycle.

### Persistent Queue

An optional crash-safe persistent queue can be enabled:

| Setting | Default | Description |
|---------|---------|-------------|
| `events_forwarder_persistent_queue_enabled` | `false` | Enable persistent queue |
| `events_forwarder_persistent_queue_max_size` | `500` | Maximum queue size (10--50000) |
| `events_forwarder_persistent_queue_flush_interval_seconds` | `5` | Persistent flush interval |

Events in the persistent queue survive HA restarts. The queue uses the HA Storage API with size limits.

### Idempotency

Every event receives an idempotency key based on `event_type:context.id`. Events with a known key within the TTL are not re-sent. Default TTL is 300 seconds (5 minutes).

### N3 Envelope and PII Redaction

The N3 envelope format reduces attributes to a minimum per domain:

| Domain | Allowed Attributes |
|--------|-------------------|
| `light` | brightness, color_temp, rgb_color, color_mode |
| `climate` | temperature, current_temperature, hvac_action, humidity |
| `media_player` | media_content_type, media_title, source, volume_level |
| `sensor` | unit_of_measurement, device_class, state_class |
| `person` | source_type (no GPS coordinates, no IP addresses) |

The following attributes are **always removed**: `entity_picture`, `media_image_url`, `latitude`, `longitude`, `gps_accuracy`, `access_token`, `token`.

Additionally, regex patterns strip tokens, API keys, secrets, and passwords.

### Entity Filtering

| Setting | Default | Description |
|---------|---------|-------------|
| `events_forwarder_include_habitus_zones` | `true` | Include zone entities |
| `events_forwarder_include_media_players` | `true` | Include media players |
| `events_forwarder_additional_entities` | (empty) | Additional entity IDs (CSV) |

### Monitoring

Three sensors monitor the forwarder:

- `sensor.ai_home_copilot_forwarder_queue_depth` -- Current queue depth.
- `sensor.ai_home_copilot_forwarder_dropped_total` -- Total dropped events.
- `sensor.ai_home_copilot_forwarder_error_streak` -- Current error streak.

---

## 13. Entity Tags

Entity Tags allow custom grouping of HA entities independent of domains, areas, or zones. Modules can query tags to find entities by semantic category (e.g., "all entities tagged Light"). Tags are also used by the Neuron System and LLM context enrichment.

### 16 Auto-Tag Categories

When auto-setup runs, the following tags are created automatically:

| Tag | Description | Color |
|-----|-------------|-------|
| Licht | All `light.*` entities | Yellow (#fbbf24) |
| Bewegung | Motion/presence sensors | Red (#f87171) |
| Temperatur | Temperature sensors | Orange (#f97316) |
| Helligkeit | Illuminance sensors | Gold (#eab308) |
| Feuchtigkeit | Humidity sensors | Cyan (#06b6d4) |
| Energie | Power/energy sensors | Green (#22c55e) |
| Media | Media players | Purple (#a78bfa) |
| Klima | Climate entities | Teal (#34d399) |
| Beschattung | Covers/blinds | Orange (#fb923c) |
| Schalter | Switch entities | Indigo (#6366f1) |
| Kamera | Cameras | Pink (#f472b6) |
| Person | Person entities | Purple (#a78bfa) |
| Tuer | Door contacts | Violet (#8b5cf6) |
| Fenster | Window contacts | Blue (#0ea5e9) |
| Sicherheit | Smoke detectors/gas sensors | Red (#ef4444) |
| Batterie | Battery sensors | Lime (#84cc16) |

Note: Tag IDs use German names internally as stable identifiers. This is intentional and does not change with UI language settings.

### Managing Tags via Options Flow

Under **Settings > Integrations > PilotSuite > Configure > Entity Tags**:

- **Add tag** -- Enter tag ID (slug, lowercase), name, entity IDs, and color.
- **Edit tag** -- Select an existing tag from the list and modify entities.
- **Delete tag** -- Select a tag from the list and delete it.

Tag IDs must match the pattern `^[a-z0-9_aeoeuess]+$` (lowercase, digits, underscores, umlauts).

### Auto-Tagging ("Styx")

The EntityTagsModule automatically assigns the tag `styx` to every entity that PilotSuite actively interacts with. This helps identify which entities are being used by the system.

### Manual Override

- Tags can be edited at any time.
- Manual entity assignments override auto-tags.
- Tags are synchronized with Core for use in the Knowledge Graph and LLM context.

### Tag in Sensors

The sensor `sensor.ai_home_copilot_entity_tags` shows the total number of defined tags. The `extra_state_attributes` contain the complete tag list with associated entities.

---

## 14. Privacy

PilotSuite follows a **privacy-first, local-first** approach. All data stays on your hardware.

### No Cloud Dependency

- All processing happens locally (Home Assistant + Core Add-on).
- No external API calls.
- No telemetry upload.
- No account required.

### PII Redaction

The privacy module (`privacy.py`) implements systematic redaction of sensitive data:

| Pattern | Treatment |
|---------|-----------|
| Email addresses | `[REDACTED_EMAIL]` |
| Phone numbers | `[REDACTED_PHONE]` |
| Public IP addresses | `[REDACTED_IP]` |
| Private IP addresses | Partially masked (e.g., `192.168.x.x`) |
| JWTs and Bearer tokens | `[REDACTED_SECRET]` |
| URLs with token parameters | `[REDACTED_URL]` |
| Long Base64/Hex strings | `[REDACTED_SECRET]` |

### Bounded Storage

All data stores have hard limits to prevent unbounded growth:

| Resource | Limit |
|----------|-------|
| String values | Max 500 characters (configurable) |
| Object traversal depth | 4 levels |
| Lists/dicts per level | 200 entries |
| Brain Graph nodes | 500 (configurable) |
| Brain Graph edges | 1500 (configurable) |
| Persistent event queue | 500 events (configurable, max 50000) |
| Mood history | 100 entries (default) |
| Suggestion history | 200 entries (default) |

### Opt-In Design

The following features are **disabled by default** and must be explicitly enabled:

| Feature | Config Key | Default |
|---------|-----------|---------|
| Events Forwarder | `events_forwarder_enabled` | `false` |
| Persistent Queue | `events_forwarder_persistent_queue_enabled` | `false` |
| call_service Forwarding | `events_forwarder_forward_call_service` | `false` |
| HA Error Digest | `ha_errors_digest_enabled` | `false` |
| DevLog Push | `devlog_push_enabled` | `false` |
| ML Context | `ml_enabled` | `false` |
| Watchdog | `watchdog_enabled` | `false` |
| Multi-User Learning (MUPL) | `mupl_enabled` | `false` |
| Calendar Context | `calendar_context_enabled` | `false` |
| Waste Reminders | `waste_enabled` | `false` |
| Birthday Reminders | `birthday_enabled` | `false` |

### Domain Projection

The Events Forwarder transmits only the absolute minimum attributes per domain (N3 specification):

- `light`: Only brightness, color_temp, color_mode (no firmware info, no network details).
- `person`: Only source_type (no GPS coordinates, no IP addresses).
- `media_player`: Only media_type, title, source, volume (no album art, no account info).

### MUPL Privacy

The Multi-User Preference Learning module offers two privacy modes:

| Mode | Description |
|------|-------------|
| `opt-in` (default) | Only explicitly approved users are tracked |
| `opt-out` | All users are tracked; individuals can opt out |

Retention is bounded (default: 90 days, configurable 1--3650 days).

---

## 15. Troubleshooting

### cannot_connect

**Symptom:** The Config Flow shows `cannot_connect` during setup.

| Check | Solution |
|-------|----------|
| Core Add-on not started | Start the add-on under **Settings > Add-ons** |
| Wrong host | Use default `homeassistant.local`, or the IP address of your HA host |
| Wrong port | Ensure port is `8909`; check Core Add-on configuration |
| Port blocked | Check firewall rules; port 8909 must be internally reachable |
| Token mismatch | Leave token empty (first setup) or use the correct token from Core configuration |

### Module Not Loading

**Symptom:** A module does not appear or throws errors at startup.

1. **Check logs**: Under **Settings > System > Logs**, filter for `ai_home_copilot`.
2. **Enable debug**: Options Flow > Settings > `debug_level` set to `full`.
3. **Module isolation**: Failed modules are automatically skipped; the rest load normally (isolation via try/except in the Runtime).
4. **Reload integration**: **Settings > Integrations > PilotSuite > Menu > Reload**.

### Sensors Unavailable

**Symptom:** Sensors show `unavailable` or `unknown`.

| Cause | Solution |
|-------|----------|
| Core Add-on offline | Start/restart the add-on |
| Coordinator timeout | The coordinator polls every 30 s; wait briefly during network issues |
| Module disabled | Check whether the relevant module is enabled in Options |
| Missing configuration | E.g., waste/birthday sensors need configured calendars/entities |

### No Entities Visible

**Symptom:** No `ai_home_copilot.*` entities appear after setup.

1. Check that `async_config_entry_first_refresh` succeeded (look in logs).
2. Verify the entity profile: the `core` profile shows only essential entities; switch to `full` for all.
3. Restart Home Assistant.

### Auto-Setup Created No Zones

1. Check that HA Areas exist (**Settings > Areas & Zones**).
2. Areas must have entities assigned to them.
3. Create zones manually: **Configure > Habitus zones > Create zone**.

### Webhook Issues

**Symptom:** Core does not send real-time updates (mood, suggestions).

1. **Check webhook URL**: Options Flow > Settings shows the generated webhook URL.
2. **Match tokens**: The webhook token must match the token in Core configuration.
3. **Internal access**: The webhook URL must be reachable from the Core Add-on (same host).
4. **Check logs**: Look for `Rejected webhook: invalid token`.

### Events Forwarder Not Sending

**Symptom:** Queue depth increases, events do not reach Core.

1. Verify `events_forwarder_enabled` is `true`.
2. Ensure Core Add-on is reachable on port 8909.
3. Check `sensor.ai_home_copilot_forwarder_error_streak`.
4. Verify entity allowlist: are the desired entities in zones or the `additional_entities` list?

### Habitus Zone Errors

**Symptom:** A zone cannot be created.

- Every zone needs at least **1 motion/presence entity** + **1 light entity**.
- Zone IDs must be unique.
- Bulk edit: check YAML/JSON syntax; the error message shows parse/validation details.

### Dashboard Not in Sidebar

1. The panel is only registered when Core is reachable.
2. Check logs for: `"Failed to register PilotSuite sidebar panel"`.
3. Alternative: Open Core directly via **Supervisor > PilotSuite Core > Ingress**.

### Mixed Languages in UI

As of v10.4.0, the UI defaults to English. Domain tags (Licht, Bewegung, etc.) remain German as internal identifiers. This is by design.

### General Tips

- **Reload the integration**: Resolves most transient issues.
- **Restart HA**: For persistent problems after configuration changes.
- **Update via HACS**: Ensure the latest version is installed.
- **Core Add-on logs**: Check `docker logs addon_copilot_core` for backend errors.
- **Diagnostics**: Under **Settings > Integrations > PilotSuite > Menu > Download diagnostics**, sanitized debug information is available.
- **Enable debug logging**: Add the following to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.ai_home_copilot: debug
```

---

*PilotSuite Styx v10.4.0 -- User Guide*
