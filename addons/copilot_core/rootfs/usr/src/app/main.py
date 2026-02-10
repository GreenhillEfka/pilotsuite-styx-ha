import os
import json
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from waitress import serve

from copilot_core.api.security import require_token
# Import blueprints
from copilot_core.api.v1 import log_fixer_tx
from copilot_core.api.v1 import tag_system

APP_VERSION = os.environ.get("COPILOT_VERSION", "0.1.1")

DEV_LOG_PATH = "/data/dev_logs.jsonl"
DEV_LOG_MAX_CACHE = 200

app = Flask(__name__)

# Register blueprints
app.register_blueprint(log_fixer_tx.bp)
app.register_blueprint(tag_system.bp)

# In-memory ring buffer of recent dev logs.
_DEV_LOG_CACHE: list[dict] = []


def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _append_dev_log(entry: dict) -> None:
    os.makedirs(os.path.dirname(DEV_LOG_PATH), exist_ok=True)
    with open(DEV_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    _DEV_LOG_CACHE.append(entry)
    if len(_DEV_LOG_CACHE) > DEV_LOG_MAX_CACHE:
        del _DEV_LOG_CACHE[: len(_DEV_LOG_CACHE) - DEV_LOG_MAX_CACHE]


def _load_dev_log_cache() -> None:
    try:
        with open(DEV_LOG_PATH, "r", encoding="utf-8") as fh:
            lines = fh.readlines()[-DEV_LOG_MAX_CACHE :]
        for line in lines:
            try:
                _DEV_LOG_CACHE.append(json.loads(line))
            except Exception:
                continue
    except FileNotFoundError:
        return
    except Exception:
        return


_load_dev_log_cache()


@app.get("/")
def index():
    return (
        "AI Home CoPilot Core (MVP)\n"
        "Endpoints: /health, /version, /api/v1/echo\n"
        "Tag System: /api/v1/tag-system/tags, /assignments (stub)\n"
        "Dev: /api/v1/dev/logs (POST/GET)\n"
        "Note: This is a scaffold. Neuron/Mood/Synapse engines come next.\n"
    )


@app.get("/health")
def health():
    return jsonify({"ok": True, "time": _now_iso()})


@app.get("/version")
def version():
    return jsonify({"version": APP_VERSION, "time": _now_iso()})


@app.post("/api/v1/echo")
def echo():
    if not require_token(request):
        return jsonify({"error": "unauthorized"}), 401
    payload = request.get_json(silent=True) or {}
    return jsonify({"time": _now_iso(), "received": payload})


@app.post("/api/v1/dev/logs")
def ingest_dev_logs():
    if not require_token(request):
        return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    entry = {
        "received": _now_iso(),
        "payload": payload,
    }

    try:
        _append_dev_log(entry)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True, "stored": True})


@app.get("/api/v1/dev/logs")
def get_dev_logs():
    if not require_token(request):
        return jsonify({"error": "unauthorized"}), 401

    try:
        limit = int(request.args.get("limit", "50"))
    except Exception:
        limit = 50
    limit = max(1, min(limit, DEV_LOG_MAX_CACHE))

    return jsonify({
        "ok": True,
        "count": min(limit, len(_DEV_LOG_CACHE)),
        "items": _DEV_LOG_CACHE[-limit:],
    })


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8099"))
    serve(app, host=host, port=port)
