from flask import Blueprint, current_app, jsonify, request

from copilot_core.storage.candidates import CandidateStore

bp = Blueprint("candidates", __name__, url_prefix="/candidates")

_STORE: CandidateStore | None = None


def _store() -> CandidateStore:
    global _STORE
    if _STORE is not None:
        return _STORE

    cfg = current_app.config.get("COPILOT_CFG")
    _STORE = CandidateStore(
        max_items=int(getattr(cfg, "candidates_max", 500)),
        persist=bool(getattr(cfg, "candidates_persist", False)),
        json_path=str(getattr(cfg, "candidates_json_path", "/data/candidates.json")),
    )
    return _STORE


@bp.post("")
def upsert_candidate():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "expected JSON object"}), 400

    cand = _store().upsert(payload)
    return jsonify({"ok": True, "candidate": cand})


@bp.get("")
def list_candidates():
    try:
        limit = int(request.args.get("limit", "50"))
    except Exception:
        limit = 50

    kind = request.args.get("kind")
    items = _store().list(limit=limit, kind=kind)
    return jsonify({"ok": True, "count": len(items), "items": items})


@bp.get("/<candidate_id>")
def get_candidate(candidate_id: str):
    it = _store().get(candidate_id)
    if not it:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({"ok": True, "candidate": it})


@bp.delete("/<candidate_id>")
def delete_candidate(candidate_id: str):
    ok = _store().delete(candidate_id)
    return jsonify({"ok": ok})
