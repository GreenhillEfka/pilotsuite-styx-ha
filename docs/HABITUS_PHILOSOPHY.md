# HABITUS_PHILOSOPHY.md - The Learned Home

> **Version:** 0.12.1 (HA Integration) + 0.7.0 (Core Add-on)  
> **Concept:** AI Home CoPilot learns your home's patterns to suggest intelligent automations

---

## 🏠 The Learned Home Concept

### What is Habitus?

**Habitus** (Latin for "condition" or "state") is AI Home CoPilot's pattern discovery engine. It observes your home's behavior over time and learns recurring patterns to suggest helpful automations.

### Core Philosophy

Your home is unique. No two households follow the same routine. Habitus respects this by:

1. **Observing, Not Assuming** — Learns from actual behavior, not pre-programmed rules
2. **Privacy-First** — All learning happens locally, nothing leaves your network
3. **Suggestion, Not Action** — Proposes automations, never executes without permission
4. **Continuous Learning** — Adapts to lifestyle changes over time

### What Habitus Discovers

| Pattern Type | Example | Result |
|--------------|---------|--------|
| **Time-based** | Lights on at 7:00 AM weekdays | Morning routine suggestion |
| **Trigger-based** | Motion → Lights on | Occupancy automation |
| **Sequence** | Door unlock → Hall lights → Thermostat | Arrival routine |
| **Contextual** | Movie time → Media lights dim | Activity-based scene |

### Confidence & Quality

Habitus uses **confidence scores** to indicate pattern reliability:

| Confidence | Meaning | Action |
|------------|---------|--------|
| 0.9+ | Very strong pattern | High recommendation |
| 0.7-0.9 | Strong pattern | Good suggestion |
| 0.5-0.7 | Moderate pattern | Consider testing |
| <0.5 | Weak pattern | Informational only |

---

## 🔄 Tag → Zone Integration

### How Tags and Zones Work Together

Tags and Zones form the foundation of AI Home CoPilot's spatial-semantic understanding:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Entity    │────▶│    Zone     │────▶│     Tag     │
│  (device)   │     │  (spatial)  │     │ (semantic)  │
└─────────────┘     └─────────────┘     └─────────────┘
```

### The Integration Flow

#### 1. Entity → Zone Mapping

Entities are assigned to zones based on:
- **Home Assistant Areas:** Automatic assignment from HA
- **Explicit Roles:** User-defined role assignments
- **Discovered Patterns:** AI-infferred relationships

```
Entity: light.wohnen_szene
  → Zone: wohnzimmer (room)
  → Area: wohnbereich (area)  
  → Floor: eg (floor)
  → Roles: [lights]
```

#### 2. Zone → Tag Assignment

Zones can be tagged for semantic filtering:

```
Zone: wohnzimmer
  → Tags: [aicp.kind.living_space, aicp.role.family_area]
  → Entities: [lights.*, media.*, motion.*]
```

#### 3. Tag-Based Queries

Tags enable powerful cross-zone queries:

```yaml
# Find all safety-critical devices in the house
query:
  tags: [aicp.role.safety_critical]
  include_children: true

# Find all media devices in the living area
query:
  zone: wohnbereich
  roles: [media]
```

### Tag Categories for Zone Integration

| Category | Purpose | Examples |
|----------|---------|----------|
| `kind` | Entity type | `aicp.kind.light`, `aicp.kind.sensor` |
| `location` | Room/area | `aicp.location.bathroom`, `aicp.location.outdoor` |
| `role` | Function | `aicp.role.entertainment`, `aicp.role.security` |
| `state` | Condition | `aicp.state.needs_attention`, `aicp.state.low_battery` |
| `routine` | Time-based | `aicp.role.morning`, `aicp.role.evening` |

### Practical Examples

#### Example 1: Morning Routine Discovery

1. **Observation:** At 7:00-7:30 AM on weekdays:
   - Motion sensor in hallway activates
   - Kitchen lights turn on
   - Coffee machine starts

2. **Tagging:**
   - Rule gets tags: `aicp.role.morning`, `aicp.kind.routine`
   - Zone gets tags: `aicp.role.weekday_morning`

3. **Suggestion:**
   ```
   "I noticed you usually start your day around 7 AM.
   Want me to create a 'Morning Routine' automation?"
   ```

#### Example 2: Energy Saving

1. **Observation:**
   - No motion in living room for 30 minutes
   - Lights still on
   - TV in standby

2. **Tagging:**
   - Entities: `aicp.role.energy_waste`, `aicp.state.idle`
   - Rule: `aicp.role.energy_saving`

3. **Suggestion:**
   ```
   "I notice lights are often left on when nobody's
   in the living room. Create an 'Auto Off' rule?"
   ```

#### Example 3: Security Enhancement

1. **Observation:**
   - Door lock engaged after 11 PM
   - All lights off
   - Security system armed

2. **Tagging:**
   - Zone: `aicp.role.night_mode`
   - Rule: `aicp.role.bedtime`, `aicp.kind.security`

3. **Suggestion:**
   ```
   "Your bedtime routine seems consistent.
   Add 'Good Night' automation?"
   ```

---

## 💡 Entity Suggestion Workflow

### How AI Home CoPilot Suggests Entities

The suggestion system transforms raw data into actionable recommendations:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Raw Data   │───▶│  Processing  │───▶│  Suggestion  │
│  (Events)    │    │   (Habitus)  │    │   (Output)   │
└──────────────┘    └──────────────┘    └──────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
  State Changes     Pattern Mining      Automation Candidates
  Service Calls     Confidence Calc     Tag Refinement
  Time Context      Zone Correlation    UI Presentation
```

### Step-by-Step Workflow

#### Step 1: Data Collection

Events flow from HA to Core:

1. **State Changes:** `light.wohnen on` → `off`
2. **Service Calls:** `light.turn_on` with parameters
3. **Time Context:** Timestamp + day of week
4. **Zone Context:** Which zone was involved

#### Step 2: Pattern Mining

Habitus analyzes the event stream:

1. **Temporal Patterns:** Time-based sequences
2. **Causal Relationships:** A frequently precedes B
3. **Support Calculation:** How often does this occur?
4. **Confidence Scoring:** Statistical reliability

#### Step 3: Candidate Generation

Patterns become automation candidates:

```json
{
  "candidate": {
    "id": "cand_123",
    "trigger": "entity.motion_hallway",
    "action": "light.kitchen.turn_on",
    "conditions": ["time.between_6_30_8_00", "weekday.mon_fri"],
    "confidence": 0.82,
    "tags": ["aicp.role.morning", "aicp.kind.routine"],
    "zones": ["hallway", "kitchen"]
  }
}
```

#### Step 4: User Presentation

Suggestions appear in the dashboard:

| Element | Description |
|---------|-------------|
| **Title** | Human-readable automation description |
| **Confidence** | Visual indicator (green/yellow/red) |
| **Tags** | Semantic categorization |
| **Zones** | Affected areas |
| **Actions** | Accept / Modify / Dismiss |

### Confidence Calculation

```
Confidence = (Support × Consistency × Recency) / Complexity

Where:
- Support: How often does A lead to B? (0-1)
- Consistency: How reliable is this pattern? (0-1)
- Recency: How recent is this pattern? (0-1)
- Complexity: Number of conditions (penalty)
```

### Suggestion Filtering

Users can filter suggestions by:

| Filter | Effect |
|--------|--------|
| **Confidence threshold** | Only show ≥ X confidence |
| **Tags** | Only show specific categories |
| **Zones** | Only show for specific rooms |
| **Time** | Only show relevant time of day |

### The Feedback Loop

AI Home CoPilot learns from user responses:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Suggestion │────▶│   User      │────▶│   Learning  │
│   Shown     │     │   Feedback  │     │   Update    │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
      Accepted       Modified        Dismissed
          │               │               │
          ▼               ▼               ▼
    Boost similar   Adjust params   Reduce weight
    suggestions     Filter future    for pattern
```

---

## 🎯 Best Practices

### For Users

1. **Give it time** — Habitus needs 1-2 weeks of data
2. **Review suggestions** — Accept/modify/dismiss to train
3. **Use zones** — Proper zone setup improves suggestions
4. **Add tags** — Manual tagging helps AI understand context

### For Automation

1. **Start simple** — Single trigger → single action
2. **Build confidence** — High confidence rules work best
3. **Consider context** — Time, day, season matter
4. **Test first** — Use "suggest" mode before "auto" mode

---

## 🔮 Future Vision

### Planned Enhancements

| Feature | Description |
|---------|-------------|
| **ML Pipeline** | Advanced pattern recognition with neural networks |
| **Predictive Suggestions** | Anticipate needs before they occur |
| **Cross-Home Learning** | Learn from similar homes (privacy-preserving) |
| **Natural Language** | Describe automations in plain text |

### The Goal: Truly Intelligent Home

> "The best automation is one you never have to think about."

AI Home CoPilot aims to reach a point where:
- Your home anticipates your needs
- Suggestions become seamless
- Privacy is never compromised
- You have full control

---

## 📚 Related Documentation

- [PILOTSUITE_VISION.md](./PILOTSUITE_VISION.md) — Architecture overview
- [USER_MANUAL.md](./USER_MANUAL.md) — Setup and configuration
- [API.md](./API.md) — Technical API reference

---

*Concept: AI Home CoPilot — Your Home, Learned Locally*  
*Last Updated: 2026-02-16*
