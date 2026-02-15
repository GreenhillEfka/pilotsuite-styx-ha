from __future__ import annotations

import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from flask import Blueprint, jsonify, request

from copilot_core.brain_graph.provider import get_graph_service

bp = Blueprint("graph_ops", __name__, url_prefix="/graph")


# --- minimal idempotency (v0.1) ---

@dataclass
class _IdemCfg:
    ttl_seconds: int = 20 * 60
    lru_max: int = 5000


_IDEM = _IdemCfg()
_IDEM_CACHE: dict[str, int] = {}


def _now() -> int:
    return int(time.time())


def _idem_prune(now: int) -> None:
    # Remove expired.
    ttl = int(_IDEM.ttl_seconds)
    expired = [k for k, ts in _IDEM_CACHE.items() if now - int(ts) > ttl]
    for k in expired:
        _IDEM_CACHE.pop(k, None)

    # Drop oldest if above LRU max.
    if len(_IDEM_CACHE) <= _IDEM.lru_max:
        return
    # sort by ts asc
    items = sorted(_IDEM_CACHE.items(), key=lambda kv: kv[1])
    for k, _ in items[: max(0, len(items) - _IDEM.lru_max)]:
        _IDEM_CACHE.pop(k, None)


def _idem_key(payload: dict[str, Any]) -> str:
    # Prefer explicit Idempotency-Key header.
    hdr = request.headers.get("Idempotency-Key", "").strip()
    if hdr:
        return f"hdr:{hdr}"

    k = str(payload.get("idempotency_key") or payload.get("key") or payload.get("id") or "").strip()
    if k:
        return f"p:{k}"

    # Fallback: stable hash over important fields.
    raw = (
        str(payload.get("op") or "")
        + "|"
        + str(payload.get("from") or "")
        + "|"
        + str(payload.get("type") or "")
        + "|"
        + str(payload.get("to") or "")
    ).encode("utf-8")
    return "h:" + sha256(raw).hexdigest()[:16]


_ALLOWED_EDGE_TYPES = {"observed_with", "controls"}


@bp.post("/ops")
def graph_ops():
    """Apply a bounded set of Brain Graph operations.

    v0.1: only supports touch_edge/touch_node semantics.

    Request JSON:
      { op: "touch_edge", from, to, type, delta?, meta?, idempotency_key? }

    Security/Privacy:
    - Bounded, allowlisted edge types.
    - meta is ignored in v0.1.
    """

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "expected_json_object"}), 400

    op = str(payload.get("op") or "").strip().lower()
    if op not in {"touch_edge"}:
        return jsonify({"ok": False, "error": "unsupported_op"}), 400

    from_id = str(payload.get("from") or "").strip()
    to_id = str(payload.get("to") or "").strip()
    edge_type = str(payload.get("type") or "").strip()

    if not from_id or not to_id or not edge_type:
        return jsonify({"ok": False, "error": "missing_fields"}), 400

    if edge_type not in _ALLOWED_EDGE_TYPES:
        return jsonify({"ok": False, "error": "edge_type_not_allowed", "allowed": sorted(_ALLOWED_EDGE_TYPES)}), 400

    try:
        delta = float(payload.get("delta") if payload.get("delta") is not None else 1.0)
    except Exception:
        delta = 1.0

    # Hard caps.
    if delta < 0:
        delta = 0.0
    if delta > 5:
        delta = 5.0

    now = _now()
    _idem_prune(now)
    key = _idem_key(payload)
    if key in _IDEM_CACHE:
        return jsonify({"ok": True, "idempotent": True, "key": key}), 200
    _IDEM_CACHE[key] = now

    svc = get_graph_service()

    # Ensure nodes exist (minimal scores).
    svc.touch_node(from_id, delta=0.1)
    svc.touch_node(to_id, delta=0.1)

    e = svc.touch_edge(from_id, edge_type, to_id, delta=delta)
    svc.persist_best_effort()

    return jsonify(
        {
            "ok": True,
            "idempotent": False,
            "key": key,
            "edge": {
                "id": getattr(e, "id", None),
                "from": from_id,
                "to": to_id,
                "type": edge_type,
                "delta": delta,
            },
        }
    )
