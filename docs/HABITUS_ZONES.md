# Habituszonen (Habitus Zones)

## Motivation
Home Assistant installations often grow into an entity “wirrwarr”. Habituszonen are a user-defined, curated layer that:
- selects a **small set of relevant entities** per zone,
- makes the system **slimmer, explainable, and maintainable**,
- provides a stable foundation for **UX dashboards**, analytics, and later suggestions.

Think: **"my real rooms as I live in them"** (habitus), not necessarily HA Areas/Devices.

## Principles
- **Local-first / privacy-first:** zones and selections live locally.
- **Governance-first:** CoPilot may *suggest* assignments/tags; it must not silently rewrite HA metadata.
- **Safe defaults:** if no zones are configured, nothing changes.

## Data model
A Habituszone contains:
- `id` (stable key): e.g. `wohnbereich`
- `name` (display): e.g. "Wohnbereich"

### Option A (simple): flat allowlist
- `entity_ids`: list of entity_ids

### Option B (recommended): categorized entities (named signals)
- `entities`: mapping of **role → entity_ids**

Required roles:
- `motion`: motion/presence entity (at least 1)
- `lights`: light entities (at least 1)

Common optional roles (examples):
- `brightness` (Helligkeit)
- `heating` (Heizung / climate)
- `humidity` (Luftfeuchte)
- `temperature` (Temperatur)
- `co2` (CO₂)
- `noise` (Lärm)
- `pressure` (Luftdruck)
- `cover` (Rollo)
- `door` (Türsensor)
- `window` (Fenstersensor)
- `lock` (Schloss)
- `media` (Media / Lautstärke)
- `power` (Leistung / W)
- `energy` (Energie / kWh)
- `other`

Example:
```yaml
- id: wohnbereich
  name: Wohnbereich
  entities:
    motion:
      - binary_sensor.bewegung_wohnzimmer
    lights:
      - light.deckenlicht
      - light.beleuchtung_durchgangsbereich
    brightness:
      - sensor.helligkeit_wohnzimmer
    heating:
      - climate.thermostat_wohnzimmer_links
      - climate.thermostat_wohnzimmer_rechts
    humidity:
      - sensor.thermostat_wohnzimmer_links_luftfeuchtigkeit
      - sensor.thermostat_wohnzimmer_rechts_luftfeuchtigkeit
    temperature:
      - sensor.thermostat_wohnzimmer_links_temperatur
      - sensor.thermostat_wohnzimmer_rechts_temperatur
    co2:
      - sensor.co2_wohnbereich_messstation
    cover:
      - cover.rollo_terrassentur
    media:
      - media_player.wohnbereich
      - media_player.fernseher_im_wohnzimmer
      - media_player.apple_tv_wohnzimmer
```

Notes:
- `entity_ids` is still supported for backwards compatibility.
- Internally, CoPilot will always keep a union list (`entity_ids`) so other modules can consume zones easily.

## Configuration UX (incremental)
### Phase 1 (fast, robust)
- A dashboard-editable **JSON text entity** holding a list of zones.
- Buttons:
  - "validate zones" (check entity existence + minimum requirements)
  - "generate habitus dashboard" (create a YAML dashboard file)
  - "download habitus dashboard" (publish to `/local/…`)

### Phase 2 (nice UX)
- Options flow wizard:
  - create/edit/delete zone
  - pick **required**: motion/presence + one or more lights
  - pick optional entities (multi-select)

### Phase 3 (labels/tags integration)
- If HA Labels exist: allow zone inclusion via labels.
- CoPilot may suggest labels via Repairs (confirm-gated):
  - "Add label room:wohnbereich to these entities"

## Runtime usage
Once zones exist, other modules consume zones as their primary scope:
- MediaContext: per-zone music vs tv signals
- Mood: per-zone mood proxy + house mood aggregation
- Habitus miner: routines per zone
- Suggestions: only use zone-curated entities

## UX dashboards (PilotSuite)
Habituszonen enable generating a per-zone dashboard view:
- key sensors (temp/humidity/occupancy)
- trends (history graphs)
- media controls
- activity summary (time occupied)

**Recommended:** generate YAML files locally and let user import (governance-first).

## Open questions (for implementation)
- Does your HA version support Labels? (If not, we keep everything internal.)
- How strict should "minimum required" be? (Warn vs block.)
- Should zones map to HA Areas by default, or be independent by default?
