from flask import Blueprint, current_app, jsonify, request

from copilot_core.storage.events import EventStore

bp = Blueprint("events", __name__, url_prefix="/events")

# Lazy singleton per-process
_STORE: EventStore | None = None


def _store() -> EventStore:
    global _STORE
    if _STORE is not None:
        return _STORE

    cfg = current_app.config.get("COPILOT_CFG")
    _STORE = EventStore(
        cache_max=int(getattr(cfg, "events_cache_max", 500)),
        persist=bool(getattr(cfg, "events_persist", False)),
        jsonl_path=str(getattr(cfg, "events_jsonl_path", "/data/events.jsonl")),
        idempotency_ttl_seconds=int(getattr(cfg, "events_idempotency_ttl_seconds", 20 * 60)),
        idempotency_lru_max=int(getattr(cfg, "events_idempotency_lru_max", 10_000)),
    )
    return _STORE


@bp.post("")
def ingest_event():
    payload = request.get_json(silent=True) or {}

    # Accept either a single event or a batch: {items:[...]}
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        n = _store().extend([x for x in payload["items"] if isinstance(x, dict)])
        return jsonify({"ok": True, "ingested": n})

    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "expected JSON object"}), 400

    idem = (
        request.headers.get("Idempotency-Key")
        or request.headers.get("X-Idempotency-Key")
        or request.headers.get("X-Event-Id")
        or ""
    )

    evt, stored = _store().append(payload, idempotency_key=str(idem))
    return jsonify({"ok": True, "stored": stored, "deduped": (not stored), "event": evt})


@bp.get("")
def list_events():
    try:
        limit = int(request.args.get("limit", "50"))
    except Exception:
        limit = 50

    since = request.args.get("since")
    items = _store().list(limit=limit, since_ts=since)
    return jsonify({"ok": True, "count": len(items), "items": items})
