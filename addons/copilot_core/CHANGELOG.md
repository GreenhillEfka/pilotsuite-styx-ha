# Add-on Changelog – AI Home CoPilot Core (MVP)

This file exists so Home Assistant can show an add-on changelog.
For full history, see the repository-level `CHANGELOG.md`.

## 0.2.7
- Brain Graph Ops: `POST /api/v1/graph/ops` (v0.1: touch_edge; idempotent; allowlist: observed_with, controls).

## 0.2.6
- Dev Surface: `GET /api/v1/dev/status`.
- Diagnostics Contract: `GET /api/v1/dev/support_bundle` liefert ein privacy-first, bounded ZIP.
- DevLogs ingest: Payloads werden vor Persistenz best-effort sanitisiert.
- Graph→Candidates Bridge: `GET /api/v1/candidates/graph_candidates` (Preview, bounded).

## 0.2.5
- Brain Graph wird jetzt aus eingehenden `/api/v1/events` Batches gefüttert (privacy-first, bounded).
- Capabilities zeigen `brain_graph.feeding_enabled`.

## 0.2.4
- Events ingest ist jetzt idempotent (TTL+LRU Dedupe); Retries erzeugen keine doppelten Events.
- Neu: Brain Graph Skeleton API (v0.1) unter `/api/v1/graph/state` + `snapshot.svg` (Placeholder).

## 0.2.3
- Logs the listening port on startup.
- `/health` includes the effective port.
- Respects add-on `log_level` option.

## 0.2.2
- Default port changed from 8099 to 8909.

## 0.2.1
- Fix startup crash (DevLogs used current_app at import time).
