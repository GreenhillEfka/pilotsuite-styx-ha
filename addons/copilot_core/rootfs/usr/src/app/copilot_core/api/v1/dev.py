"""Developer-oriented debug endpoints.

Kept for MVP parity with previous scaffold.
"""

import json
import os
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("dev", __name__)

DEV_LOG_MAX_CACHE_DEFAULT = 200


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dev_log_path() -> str:
    cfg = current_app.config.get("COPILOT_CFG")
    data_dir = getattr(cfg, "data_dir", "/data")
    return os.path.join(data_dir, "dev_logs.jsonl")


# In-memory ring buffer of recent dev logs.
_DEV_LOG_CACHE: list[dict] = []
_DEV_LOG_CACHE_LOADED = False


def _ensure_dev_log_cache_loaded() -> None:
    """Load last dev logs into memory.

    Must run inside an application context (uses current_app).
    """

    global _DEV_LOG_CACHE_LOADED
    if _DEV_LOG_CACHE_LOADED:
        return
    _DEV_LOG_CACHE_LOADED = True

    path = _dev_log_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()[-DEV_LOG_MAX_CACHE_DEFAULT :]
        for line in lines:
            try:
                _DEV_LOG_CACHE.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return


def _append_dev_log(entry: dict) -> None:
    path = _dev_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    max_cache = DEV_LOG_MAX_CACHE_DEFAULT
    try:
        cfg = current_app.config.get("COPILOT_CFG")
        max_cache = int(getattr(cfg, "dev_log_cache_max", DEV_LOG_MAX_CACHE_DEFAULT))
    except Exception:
        pass

    _DEV_LOG_CACHE.append(entry)
    if len(_DEV_LOG_CACHE) > max_cache:
        del _DEV_LOG_CACHE[: len(_DEV_LOG_CACHE) - max_cache]


@bp.post("/dev/logs")
def ingest_dev_logs():
    _ensure_dev_log_cache_loaded()
    payload = request.get_json(silent=True) or {}
    entry = {"received": _now_iso(), "payload": payload}

    try:
        _append_dev_log(entry)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True, "stored": True})


@bp.get("/dev/logs")
def get_dev_logs():
    _ensure_dev_log_cache_loaded()
    try:
        limit = int(request.args.get("limit", "50"))
    except Exception:
        limit = 50
    limit = max(1, min(limit, DEV_LOG_MAX_CACHE_DEFAULT))

    return jsonify({"ok": True, "count": min(limit, len(_DEV_LOG_CACHE)), "items": _DEV_LOG_CACHE[-limit:]})
