# PilotSuite User Guide

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Features](#features)
- [Troubleshooting](#troubleshooting)

---

## Overview

PilotSuite is a Home Assistant integration that helps you:
- **Observe patterns** in your home automation
- **Discover automation opportunities** through A→B rule mining
- **Get explainable suggestions** with evidence and confidence scores
- **Apply changes safely** with explicit confirmation (Repairs + Blueprints)

### Key Principles

- **Privacy-first**: No data leaves your home
- **Governance-first**: No silent automations
- **Reversible**: All changes can be rolled back
- **Transparent**: Explainable suggestions with evidence

### What It Does

1. **Pattern Mining**: Analyzes your Home Assistant events to find A→B patterns
   - Example: "When person.anna_arrives_home, light.living_room_turns_on"
   
2. **Candidate Generation**: Creates automation suggestions based on patterns
   - Shows confidence scores and evidence
   
3. **Repaired Suggestions**: Offers suggestions via Repairs system
   - Explicit user confirmation required
   
4. **Blueprint Import**: Imports suggestions as blueprints
   - Easy to modify and customize

---

## Quick Start

### 1. Install Integration

**via HACS:**
1. HACS → Integrations → Custom repositories
2. Add: `https://github.com/GreenhillEfka/pilotsuite-styx-ha`
3. Install "PilotSuite"
4. Restart Home Assistant

**or via Add-on:**
1. Settings → Add-ons → Add-on Store → Repositories
2. Add: `https://github.com/GreenhillEfka/pilotsuite-styx-core`
3. Install "PilotSuite Core (MVP)"

### 2. Configure Integration

Settings → Devices & services → Add integration → PilotSuite

**Config fields:**
- **Host**: `homeassistant.local` (or your HA IP)
- **Port**: `8909` (default)
- **API Token**: Optional (if Core has auth)
- **Test Light**: Optional (for demo)

### 3. Verify Installation

Check these entities after restart:
- `binary_sensor.ai_home_copilot_online` → should be `on`
- `sensor.ai_home_copilot_version` → shows version number

### 4. Wait for Data Collection

The integration needs 24-48 hours of data to discover patterns.

### 5. Review Suggestions

After enough data is collected:
1. Go to Settings → Device & Services → PilotSuite
2. Check "Repairs" for automation suggestions
3. Review evidence and confidence scores
4. Click "Fix" to create automation

---

## Installation

### Method 1: HACS (Recommended)

1. **Install HACS** (if not installed)
   - Visit [hacs.xyz](https://hacs.xyz)
   
2. **Add Repository**
   - HACS → Integrations → ⋮ → Custom repositories
   - URL: `https://github.com/GreenhillEfka/pilotsuite-styx-ha`
   - Type: Integration
   - Click "Add"
   
3. **Install**
   - Search for "PilotSuite"
   - Click "Download"
   - Restart Home Assistant

4. **Configure**
   - Settings → Devices & services → Add integration
   - Select "PilotSuite"
   - Fill in configuration

### Method 2: Home Assistant Add-on

1. **Add Repository**
   - Settings → Add-ons → Add-on Store → ⋁ → Repositories
   - URL: `https://github.com/GreenhillEfka/pilotsuite-styx-core`
   - Click "Add"
   
2. **Install Add-on**
   - Find "PilotSuite Core (MVP)"
   - Click to open
   - Review configuration (optional)
   - Click "Install"
   
3. **Start**
   - Click "Start"
   - Verify logs show success

### Method 3: Manual (Development)

```bash
# Copy to custom components
cp -r pilotsuite-styx-ha/custom_components/ai_home_copilot \
    /config/custom_components/

# Restart Home Assistant
```

---

## Configuration

### Integration Configuration

```yaml
# configuration.yaml (optional)
ai_home_copilot:
  host: homeassistant.local
  port: 8909
  token: optional-api-token
  forward_entities:
    - light.*
    - switch.*
    - person.*
```

### Add-on Configuration

```json
// /config/addons-config/copilot_core/options.json
{
  "log_level": "info",
  "auth_token": "your-secret-token",
  "brain_graph": {
    "max_nodes": 500,
    "max_edges": 1500
  },
  "visualization": {
    "enabled": true
  }
}
```

### Entity Filtering

Filter which entities to process:

```yaml
ai_home_copilot:
  forward_entities:
    - light.living_room
    - switch.kitchen
    - person.*
    - sensor.weather_*
```

---

## Usage

### Checking Status

**Core online:**
```
Settings → Devices & services → PilotSuite
→ binary_sensor.ai_home_copilot_online
```

**Version info:**
```
sensor.ai_home_copilot_version
```

**Pipeline health:**
```
sensor.ai_home_copilot_pipeline_health
```

### Viewing Suggestions

**Via Repairs:**
1. Settings → System → Repairs
2. Find PilotSuite
3. Click to view details
4. Review evidence and confidence
5. Click "Fix" to create

**Via Dashboard:**
- Add brain graph panel
- View discovered patterns
- Monitor mood context

### Managing Features

**Disable feature:**
```yaml
# configuration.yaml
ai_home_copilot:
  mood_context: false
  habitus_mining: false
```

**Enable features:**
```yaml
ai_home_copilot:
  multi_user_preferences: true
  brain_graph: true
```

---

## Features

### Pattern Mining (Habitus)

Discovers A→B patterns in your automation:

| Feature | Description |
|---------|-------------|
| **A→B Rules** | Finds cause→effect patterns |
| **Confidence** | Shows statistical confidence |
| **Evidence** | Provides example instances |
| **Time Delta** | Shows typical delay between A and B |

**Example:**
```
A: person.anna_arrived_home
B: light.living_room.turn_on
Confidence: 0.78
Evidence: 18 occurrences
Time delta: 2.1 minutes
```

### Brain Graph Visualization

Interactive graph showing relationships:

**Features:**
- Entity relationships
- Pattern connections
- Mood overlays
- Real-time updates

**Usage:**
1. Add to dashboard: `custom:brain-graph-panel`
2. View entity connections
3. Click nodes for details

### Mood Context

Smart suggestion weighting based on context:

**Factors:**
- Media activity (TV, music)
- Time of day
- Weather conditions
- User preferences

**Example:**
```
Mood: joy (0.85)
Recommendation: Don't suggest energy-saving during movie night
```

### Multi-User Preferences

Learn preferences per user and zone:

**Features:**
- Per-user comfort bias
- Zone-specific settings
- Automatic learning
- Smooth transitions

**Example:**
```
User: person.anna
Zone: living
Comfort bias: 0.8
Frugality bias: 0.3
Joy bias: 0.9
```

### Candidate System

Automation suggestion lifecycle:

**States:**
- `pending`: New suggestion
- `offered`: Shown to user
- `accepted`: User confirmed
- `dismissed`: User rejected
- `deferred`: Offer again later

### Repairs Integration

Smart home repairs with automation suggestions:

**Features:**
- Non-intrusive notifications
- Evidence-based suggestions
- Blueprint import
- Easy rollback

---

## Features in Detail

### 1. Pattern Mining

**How it works:**
1. Collects events from Home Assistant
2. Identifies A→B patterns with time windows
3. Calculates confidence, lift, and leverage
4. Generates candidate automations

**Configuration:**
```yaml
ai_home_copilot:
  habitus:
    min_confidence: 0.5
    max_delta_seconds: 3600
    min_events: 5
```

### 2. Brain Graph

**Features:**
- Node types: entity, domain, area, zone, pattern, mood
- Edge types: controls, belongs_to, correlates_with, triggers
- Bounded storage (max nodes/edges)
- Privacy-first (no external sharing)

**Visualization:**
```yaml
type: custom:brain-graph-panel
title: Home Patterns
entity: sensor.ai_home_copilot_mood
```

### 3. Mood Context

**Factors:**
- Media activity (joy boost)
- Time of day (comfort baselines)
- Weather (frugality impact)
- User preferences (weighted)

**Usage:**
```yaml
# Suppress energy-saving during high-joy activities
- condition: device
  condition: ai_home_copilot
  mood: joy
  min_value: 0.6
```

### 4. Multi-User Preferences

**Setup:**
1. Create person entities for each user
2. System automatically collects preferences
3. View preferences in dashboard

**API:**
```yaml
GET /api/v1/user/{user_id}/zone/{zone_id}/preference
POST /api/v1/user/{user_id}/preference
```

---

## Troubleshooting

### Integration Not Connecting

**Check:**
1. Core is running: `curl http://localhost:8909/health`
2. Network connectivity: `ping homeassistant.local`
3. Firewall: port 8909 must be open
4. Logs: Settings → System → Logs

**Fix:**
```yaml
# Check Core service
curl http://homeassistant.local:8909/health

# Check logs
docker logs copilot-core
```

### No Suggestions Appearing

**Check:**
1. sufficient data collected (24-48 hours)
2. entities are being monitored
3. patterns meet confidence threshold

**Fix:**
```yaml
# Check event counts
sensor.ai_home_copilot_pipeline_health

# Trigger manual mining
service: ai_home_copilot.trigger_mining
```

### Core Not Starting

**Check:**
1. Docker container status: `docker ps | grep copilot`
2. Port conflict: `netstat -tlnp | grep 8909`
3. Configuration: `/data/options.json`

**Fix:**
```bash
# Restart container
docker restart copilot-core

# Check logs
docker logs copilot-core
```

### API Authentication Errors

**Check:**
1. Token matches in HA and Core
2. Token format (no special characters)
3. Header included in requests

**Fix:**
```yaml
# Verify token in config
ai_home_copilot:
  token: your-token

# Verify in Core config
auth_token: your-token
```

### Pattern Mining Not Working

**Check:**
1. Events are being collected
2. Time window is appropriate
3. Minimum event threshold met

**Fix:**
```yaml
# Adjust thresholds
ai_home_copilot:
  habitus:
    min_events: 3
    max_delta_seconds: 7200

# Trigger manual mining
service: ai_home_copilot.trigger_mining
```

### Dashboard Not Showing

**Check:**
1. Lovelace card installed
2. Entity exists
3. Browser console for errors

**Fix:**
```yaml
# Add to dashboard manually
type: custom:brain-graph-panel
entity: sensor.ai_home_copilot_mood
```

---

## Best Practices

### Data Collection

- **Minimum**: 24 hours for basic patterns
- **Optimal**: 48-72 hours for reliable suggestions
- **Long-term**: Ongoing collection improves accuracy

### Pattern Quality

- **High confidence**: >0.7
- **Good evidence**: >10 occurrences
- **Reasonable time delta**: <2 hours

### Mood Context

- **Joy threshold**: >0.6 (suppress energy-saving)
- **Comfort threshold**: >0.7 (prioritize comfort)
- **Frugality**: <0.5 (allow energy-saving)

### Security

- **Use authentication token**
- **Keep token secret**
- **Rotate periodically**
- **Limit network exposure**

---

## Support

### Documentation

- **Integration**: `pilotsuite-styx-ha/docs/`
- **Core**: `pilotsuite-styx-core/docs/`
- **OpenAPI**: `pilotsuite-styx-core/docs/openapi.yaml`

### Community

- **GitHub Issues**: Bug reports
- **GitHub Discussions**: Questions and ideas
- **Home Assistant Forum**: Community support

### Debugging

**Enable debug logging:**
```yaml
logger:
  default: info
  logs:
    custom_components.ai_home_copilot: debug
```

**Check logs:**
```
Settings → System → Logs
Filter: ai_home_copilot
```

---

## Changelog

See `CHANGELOG.md` for version history and changes.

## License

MIT License - See LICENSE file for details.
