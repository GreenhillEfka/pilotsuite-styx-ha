# Brain Graph (Dev surface) – concept + implementation plan

Goal: make the system **observable** and **understandable** by showing what is active and how modules/inputs connect.

This is primarily a **developer/ops surface** (not a consumer UI) and must remain:
- **privacy-first** (Habitus zones allowlist)
- **governance-first** (no silent changes)
- **bounded** (top-K edges, decay, caps)

## Model

### Neurons (nodes)
We do **not** model “everything in HA” by default.

Node types:
- `entity` – HA entity_id (default scope: Habitus zones)
- `zone` – Habitus zone (curated abstraction)
- `module` – integration/core modules (MediaContext, Habitus Miner, Fixer, Seeds, …)
- later: `concept` – derived concepts (bedtime, cooking, tv_session)

### Synapses (edges)
Edges are derived from **co-activity** within a time window.

- When two nodes are active within `Δt` (e.g. 30–120s), the edge weight increases.
- Edge weights apply **decay** (e.g. half-life 7 days) so the brain stays “alive”.
- Storage is bounded by keeping only **Top-K edges per node**.

## Data source
- Primary input: forwarded HA state change events (N3) with Habitus zones allowlist.
- Optional input: MediaContext signals (music vs TV/other) as module nodes.

## Rendering strategy (HA-friendly)
### MVP
- Core generates a **Graphviz DOT** snapshot and renders to **SVG**.
- Integration publishes SVG to `/local/ai_home_copilot/brain.svg`.
- Lovelace displays it with a Picture card + a small list of top active nodes/edges.

### Later
- Optional interactive D3 panel (more maintenance; keep optional).

## API surface (draft)
- `GET /api/v1/graph/state` → summary + top nodes/edges
- `GET /api/v1/graph/snapshot.svg` → current SVG

## Safety & privacy
- Default allowlist = Habitus zones entities only.
- Minimal attributes; no names/locations unless explicitly opted in.
- Capped retention (events + graph).
