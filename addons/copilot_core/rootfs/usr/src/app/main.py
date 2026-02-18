"""
AI Home CoPilot Core - Main Application Entry Point

Minimal entry point that delegates service initialization and blueprint
registration to modular components (core_setup.py).
"""

import json
import os

from flask import Flask, request, jsonify
from flask_compress import Compress
from waitress import serve

from copilot_core.api.security import require_token, validate_token
from copilot_core.core_setup import init_services, register_blueprints

APP_VERSION = os.environ.get("COPILOT_VERSION", "0.9.9")


def _load_options_json(path: str = "/data/options.json") -> dict:
    """Lade Add-on Konfiguration aus options.json (Home Assistant Supervisor)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}

DEV_LOG_PATH = "/data/dev_logs.jsonl"
DEV_LOG_MAX_CACHE = 200

app = Flask(__name__)

# Initialize compression for API responses
Compress(app)
app.config['COMPRESS_MIMETYPES'] = ['application/json', 'text/html']
app.config['COMPRESS_LEVEL'] = 6  # Balance between compression ratio and CPU
app.config['COMPRESS_MIN_SIZE'] = 500  # Only compress responses > 500 bytes
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit

# Konfiguration aus /data/options.json laden und an Services durchreichen
_options = _load_options_json()

# Initialize all services (returns dict for potential testing/DI)
import logging as _logging
_main_logger = _logging.getLogger(__name__)

try:
    _services = init_services(config=_options)
except Exception:
    _main_logger.exception("CRITICAL: init_services failed — starting with empty services")
    _services = {}

# Register all API blueprints (pass services for tag system & global accessors)
try:
    register_blueprints(app, _services)
except Exception:
    _main_logger.exception("CRITICAL: register_blueprints failed")

# In-memory ring buffer of recent dev logs (thread-safe).
import threading as _threading
_DEV_LOG_CACHE: list[dict] = []
_DEV_LOG_LOCK = _threading.Lock()


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _append_dev_log(entry: dict) -> None:
    import json
    os.makedirs(os.path.dirname(DEV_LOG_PATH), exist_ok=True)
    with open(DEV_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    with _DEV_LOG_LOCK:
        _DEV_LOG_CACHE.append(entry)
        if len(_DEV_LOG_CACHE) > DEV_LOG_MAX_CACHE:
            del _DEV_LOG_CACHE[: len(_DEV_LOG_CACHE) - DEV_LOG_MAX_CACHE]


def _load_dev_log_cache() -> None:
    import json
    try:
        with open(DEV_LOG_PATH, "r", encoding="utf-8") as fh:
            lines = fh.readlines()[-DEV_LOG_MAX_CACHE:]
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
        "PilotSuite Core v0.9.9\n"
        "Endpoints: /health, /version, /api/v1/echo\n"
        "OpenAI API: /v1/chat/completions, /v1/models (for extended_openai_conversation)\n"
        "Chat: /chat/completions, /chat/status, /chat/characters, /chat/models/recommended\n"
        "Tag System: /api/v1/tag-system/tags, /assignments (store)\n"
        "Event Ingest: /api/v1/events (POST/GET), /api/v1/events/stats\n"
        "Brain Graph: /api/v1/graph/state, /snapshot.svg, /stats, /prune, /patterns\n"
        "Candidates: /api/v1/candidates (POST/GET), /{id} (GET/PUT), /stats, /cleanup\n"
        "Habitus: /api/v1/habitus/mine, /patterns, /stats, /health\n"
        "Mood: /api/v1/mood, /summary, /{zone_id}, /suppress-energy-saving, /relevance\n"
        "Dev: /api/v1/dev/logs (POST/GET)\n"
        "Pipeline: Events -> EventProcessor -> BrainGraph -> Habitus -> Candidates (real-time)\n"
        "LLM: Ollama (bundled) with lfm2.5-thinking default model\n"
    )


@app.get("/health")
def health():
    return jsonify({"ok": True, "time": _now_iso()})


@app.get("/version")
def version():
    return jsonify({"version": APP_VERSION, "time": _now_iso()})


@app.post("/api/v1/echo")
@require_token
def echo():
    payload = request.get_json(silent=True) or {}
    return jsonify({"time": _now_iso(), "received": payload})


@app.post("/api/v1/dev/logs")
@require_token
def ingest_dev_logs():
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
@require_token
def get_dev_logs():
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
