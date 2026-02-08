# CoPilot Core `/api/v1` scaffold (proposal + implemented skeleton)

This add-on is intentionally **minimal**:
- **Memory-first** stores with strict caps
- **Optional persistence** (off by default) to `/data/*.json*` for HA add-on friendly storage
- **Modular Flask blueprints** so features can be enabled/extended independently

## Auth (shared-token)

Optional. If `auth_token` is set (env `COPILOT_AUTH_TOKEN` or add-on `options.json`), requests must include:
- `X-Auth-Token: <token>` **or**
- `Authorization: Bearer <token>`

## Options (Home Assistant add-on)

Read from `/data/options.json`.

Suggested keys:
```json
{
  "auth_token": "...",
  "data_dir": "/data",

  "events_persist": false,
  "events_jsonl_path": "/data/events.jsonl",
  "events_cache_max": 500,

  "candidates_persist": false,
  "candidates_json_path": "/data/candidates.json",
  "candidates_max": 500,

  "mood_window_seconds": 3600
}
```

## Modules

### 1) Events ingest

#### Data model: `Event`
A canonical envelope that maps cleanly from HA event/state changes.

```json
{
  "id": "evt_...",
  "ts": "2026-02-07T16:20:00+00:00",
  "type": "state_changed|intent|...",
  "source": "home_assistant|webhook|...",
  "entity_id": "light.kitchen",
  "user_id": "<ha_user_id> (optional)",
  "text": "optional human text",
  "attributes": {"any": "json"},
  "received": "server timestamp" 
}
```

#### Endpoints
- `POST /api/v1/events`
  - body: single event object, or `{ "items": [ ... ] }`
- `GET /api/v1/events?limit=50&since=<iso8601>`

Persistence (optional): JSONL append-only at `events_jsonl_path`.

### 2) Candidate store

A **candidate** is an intermediate hypothesis produced by upstream pipelines (NLU, entity resolution, task extraction, etc.).

#### Data model: `Candidate`
```json
{
  "id": "cand_...",
  "kind": "intent|entity|task|...",
  "label": "Turn off kitchen light",
  "score": 0.82,
  "created": "...",
  "updated": "...",
  "source": "nlu_v1|rules|...",
  "attributes": {"any": "json"}
}
```

#### Endpoints
- `POST /api/v1/candidates` (upsert)
- `GET /api/v1/candidates?limit=50&kind=intent`
- `GET /api/v1/candidates/<id>`
- `DELETE /api/v1/candidates/<id>`

Persistence (optional): compact JSON snapshot at `candidates_json_path`.

### 3) Mood scoring (scaffolding)

Purpose: a stable API contract for Home Assistant sensors/automations while the scoring engine evolves.

#### Data model: `MoodScore`
```json
{
  "ts": "...",
  "window_seconds": 3600,
  "score": -1.0,
  "label": "negative|neutral|positive",
  "signals": {"pos": 0, "neg": 0, "n_events": 12}
}
```

#### Endpoints
- `POST /api/v1/mood/score`
  - optional body `{ "events": [ ... ] }` for stateless scoring
  - if omitted, scores from recently ingested events
- `GET /api/v1/mood/state`

## HA integration notes

- Add-on endpoints can be called via `rest_command`, `rest` sensor, or a custom integration.
- Recommended pattern for HA sensors:
  - create a REST sensor pulling `/api/v1/mood/state`
  - template the `mood.label` / `mood.score`
- For HA event stream ingestion:
  - a custom integration can subscribe to HA event bus and `POST /api/v1/events` batches.

## Future extension points (non-breaking)

- Replace stores with plug-in backends (SQLite/Redis) behind same interfaces.
- Add filtering by `source/entity_id/user_id`.
- Add `/api/v1/mood/feedback` to accept explicit user feedback signals.
- Add `/api/v1/candidates/query` for retrieval/ranking.
