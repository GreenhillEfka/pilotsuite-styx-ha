import os
import json
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from waitress import serve

APP_VERSION = os.environ.get("COPILOT_VERSION", "0.1.0")

app = Flask(__name__)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _require_token():
    # MVP auth: optional shared token.
    # If token is set, require: Authorization: Bearer <token>
    token = os.environ.get("COPILOT_AUTH_TOKEN", "").strip()
    if not token:
        return True
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and auth.split(" ", 1)[1].strip() == token:
        return True
    return False


@app.get("/")
def index():
    return (
        "AI Home CoPilot Core (MVP)\n"
        "Endpoints: /health, /version\n"
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
    if not _require_token():
        return jsonify({"error": "unauthorized"}), 401
    payload = request.get_json(silent=True) or {}
    return jsonify({"time": _now_iso(), "received": payload})


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8099"))
    serve(app, host=host, port=port)
