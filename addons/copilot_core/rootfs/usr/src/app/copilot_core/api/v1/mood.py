from flask import Blueprint, current_app, jsonify, request

from copilot_core.mood.scoring import MoodScorer
from copilot_core.storage.events import EventStore

bp = Blueprint("mood", __name__, url_prefix="/mood")

_SCORER: MoodScorer | None = None


def _scorer() -> MoodScorer:
    global _SCORER
    if _SCORER is not None:
        return _SCORER
    cfg = current_app.config.get("COPILOT_CFG")
    _SCORER = MoodScorer(window_seconds=int(getattr(cfg, "mood_window_seconds", 3600)))
    return _SCORER


def _event_store_if_available() -> EventStore | None:
    # Import-time singletons can vary; we keep mood module decoupled.
    try:
        from copilot_core.api.v1.events import _store as events_store_factory

        return events_store_factory()
    except Exception:
        return None


@bp.post("/score")
def score():
    """Return a mood score.

    Inputs:
    - Optional body {events:[...]} for stateless scoring.
    - If omitted, uses recent ingested events from event store.
    """

    payload = request.get_json(silent=True) or {}

    events = None
    if isinstance(payload, dict) and isinstance(payload.get("events"), list):
        events = [e for e in payload["events"] if isinstance(e, dict)]

    if events is None:
        store = _event_store_if_available()
        if store is None:
            events = []
        else:
            # use current cache tail
            events = store.list(limit=200)

    score = _scorer().score_from_events(events)
    return jsonify({"ok": True, "mood": score.to_dict()})


@bp.get("/state")
def state():
    # Scaffold: compute on-demand using stored events
    store = _event_store_if_available()
    events = store.list(limit=200) if store else []
    score = _scorer().score_from_events(events)
    return jsonify({"ok": True, "mood": score.to_dict()})
