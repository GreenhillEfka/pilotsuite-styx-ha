import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, request

from copilot_core.api.v1.blueprint import api_v1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class CopilotConfig:
    version: str = os.environ.get("COPILOT_VERSION", "0.2.1")

    # Auth
    auth_token: str = ""

    # Storage locations (HA add-on has /data)
    data_dir: str = "/data"

    # Events: minimal persistence; defaults to memory-only.
    events_persist: bool = False
    events_jsonl_path: str = "/data/events.jsonl"
    events_cache_max: int = 500

    # Candidates: minimal persistence; defaults to memory-only.
    candidates_persist: bool = False
    candidates_json_path: str = "/data/candidates.json"
    candidates_max: int = 500

    # Mood scaffolding
    mood_window_seconds: int = 3600


def _load_options_json(path: str = "/data/options.json") -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def _build_config() -> CopilotConfig:
    opts = _load_options_json()

    token = os.environ.get("COPILOT_AUTH_TOKEN", "").strip()
    if not token:
        token = str(opts.get("auth_token", "")).strip()

    data_dir = str(opts.get("data_dir", "/data"))

    events_persist = bool(opts.get("events_persist", False))
    events_jsonl_path = str(opts.get("events_jsonl_path", os.path.join(data_dir, "events.jsonl")))
    events_cache_max = int(opts.get("events_cache_max", 500))

    candidates_persist = bool(opts.get("candidates_persist", False))
    candidates_json_path = str(opts.get("candidates_json_path", os.path.join(data_dir, "candidates.json")))
    candidates_max = int(opts.get("candidates_max", 500))

    mood_window_seconds = int(opts.get("mood_window_seconds", 3600))

    return CopilotConfig(
        auth_token=token,
        data_dir=data_dir,
        events_persist=events_persist,
        events_jsonl_path=events_jsonl_path,
        events_cache_max=max(1, min(events_cache_max, 10_000)),
        candidates_persist=candidates_persist,
        candidates_json_path=candidates_json_path,
        candidates_max=max(1, min(candidates_max, 10_000)),
        mood_window_seconds=max(60, min(mood_window_seconds, 24 * 3600)),
    )


def create_app() -> Flask:
    cfg = _build_config()

    app = Flask(__name__)

    # Attach config to app (simple, explicit)
    app.config["COPILOT_CFG"] = cfg

    # Register API modules
    app.register_blueprint(api_v1)

    @app.get("/")
    def index():
        return (
            "AI Home CoPilot Core (scaffold)\n"
            "Endpoints: /health, /version, /api/v1/*\n"
            "Modules: events, candidates, mood (scaffolding)\n"
        )

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "time": _now_iso()})

    @app.get("/version")
    def version():
        return jsonify({"version": cfg.version, "time": _now_iso()})

    @app.get("/api/v1/capabilities")
    def capabilities():
        return jsonify(
            {
                "ok": True,
                "time": _now_iso(),
                "modules": {
                    "events": {
                        "enabled": True,
                        "persist": cfg.events_persist,
                        "cache_max": cfg.events_cache_max,
                    },
                    "candidates": {
                        "enabled": True,
                        "persist": cfg.candidates_persist,
                        "max": cfg.candidates_max,
                    },
                    "mood": {"enabled": True, "window_seconds": cfg.mood_window_seconds},
                },
            }
        )

    @app.before_request
    def _auth_middleware():
        # Optional shared-token auth.
        # Accept either:
        # - X-Auth-Token: <token>
        # - Authorization: Bearer <token>
        token = cfg.auth_token.strip()
        if not token:
            return None

        if request.path in ("/", "/health", "/version"):
            return None

        if request.headers.get("X-Auth-Token", "") == token:
            return None

        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer ") and auth.split(" ", 1)[1].strip() == token:
            return None

        return jsonify({"error": "unauthorized"}), 401

    return app
