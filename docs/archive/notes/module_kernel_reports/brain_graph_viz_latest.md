# Brain Graph Viz (latest)

Date: 2026-02-08

## Goal
Minimal but visible “first neurons” visualization for the next HA integration release.

## What was implemented
### 1) New HA Button entity (diagnostic, disabled-by-default)
- Entity name: **`AI Home CoPilot publish brain graph viz`**
- Category: `diagnostic`
- Entity registry enabled by default: `False`

Behavior on press:
- Fetches core graph state via coordinator API:
  - `GET /api/v1/graph/state?limitNodes=120&limitEdges=240`
- Generates a **local-only** HTML page containing an **inline SVG**:
  - Nodes rendered as circles in a simple **circular layout**
  - Edges rendered as lines
  - Score influences node radius + opacity (best-effort; missing score defaults to mid emphasis)
- Publishes to:
  - `/config/www/ai_home_copilot/brain_graph_latest.html`
  - Optional best-effort archive: `/config/www/ai_home_copilot/archive/brain_graph_YYYYmmdd_HHMMSS.html`
- Creates a **Persistent Notification** with the URL:
  - `/local/ai_home_copilot/brain_graph_latest.html`
  - plus a Lovelace `iframe` card example.

### 2) Helper module
- New file: `custom_components/ai_home_copilot/brain_graph_viz.py`
- Wired into `custom_components/ai_home_copilot/button.py`.

### 3) Privacy-first handling
- Node IDs and labels are passed through `privacy.sanitize_text(...)` with tight `max_chars` clamps.
- No meta dumps / no raw payload storage; only minimal fields used (`id`, `label`, `score`, `from`, `to`).

## Branch + commits
- Branch: `wip/brain-graph-viz`
- Commit(s):
  - `2344d72` Add button to publish brain graph HTML/SVG viz

## Diffstat
```
 custom_components/ai_home_copilot/brain_graph_viz.py | 251 +++++++++++++++++++++
 custom_components/ai_home_copilot/button.py          |  20 ++
 2 files changed, 271 insertions(+)
```

## How to test (manual)
1. In Home Assistant, reload/restart the integration (or restart HA).
2. Go to **Settings → Devices & services → AI Home CoPilot → Entities**.
3. Find and **enable** the (disabled-by-default) button entity:
   - `AI Home CoPilot publish brain graph viz`
4. Press the button.
5. Open the generated page:
   - `http(s)://<your-ha>/local/ai_home_copilot/brain_graph_latest.html`
6. (Optional) Add to a Dashboard via **Lovelace iframe card**:
   ```yaml
   type: iframe
   url: /local/ai_home_copilot/brain_graph_latest.html
   aspect_ratio: 60%
   ```

## Build / sanity
- Ran: `python3 -m py_compile` on all `custom_components/**.py` files (no errors).

## Status
**READY FOR USER OK**
