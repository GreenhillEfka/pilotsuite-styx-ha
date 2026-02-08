import os
import json
import re
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from waitress import serve

APP_VERSION = os.environ.get("COPILOT_VERSION", "0.1.1")

DEV_LOG_PATH = "/data/dev_logs.jsonl"
DEV_LOG_MAX_CACHE = 200

app = Flask(__name__)

# In-memory ring buffer of recent dev logs.
_DEV_LOG_CACHE: list[dict] = []

# Minimal error-code registry (v0.1). Keep keys stable.
ERROR_REGISTRY: dict[str, dict[str, str]] = {
    "unauthorized": {
        "title": "Unauthorized",
        "hint": "Check the shared token configuration (Home Assistant add-on options).",
    },
    "bad_request": {
        "title": "Bad request",
        "hint": "Verify request JSON shape.",
    },
    "internal": {
        "title": "Internal error",
        "hint": "Retry; if it persists, attach diagnostics/dev logs.",
    },
}

_RE_JWT = re.compile(r"(?<![A-Za-z0-9_-])(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})")
_RE_BEARER = re.compile(r"(?i)(bearer\s+)(\S+)")
_RE_URL_CREDS = re.compile(r"(?i)(https?://)([^\s:/]+):([^\s@/]+)@")

_TO_REDACT_KEYS = {
    "token",
    "auth_token",
    "access_token",
    "refresh_token",
    "password",
    "api_key",
    "key",
    "secret",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _get_token() -> str:
    token = os.environ.get("COPILOT_AUTH_TOKEN", "").strip()
    if token:
        return token

    # Home Assistant add-ons provide user options at /data/options.json
    try:
        with open("/data/options.json", "r", encoding="utf-8") as fh:
            opts = json.load(fh) or {}
        token = str(opts.get("auth_token", "")).strip()
        return token
    except Exception:
        return ""


def _require_token() -> bool:
    """Optional shared-token auth.

    Accept either:
    - X-Auth-Token: <token>
    - Authorization: Bearer <token>
    """

    token = _get_token()
    if not token:
        return True

    if request.headers.get("X-Auth-Token", "") == token:
        return True

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and auth.split(" ", 1)[1].strip() == token:
        return True

    return False


def _sanitize_str(s: str, *, max_chars: int = 4000) -> str:
    s = _RE_URL_CREDS.sub(r"\1**REDACTED**:**REDACTED**@", s)
    s = _RE_BEARER.sub(r"\1**REDACTED**", s)
    s = _RE_JWT.sub("**REDACTED_JWT**", s)
    if len(s) > max_chars:
        s = s[: max_chars - 50] + "...(truncated)..."
    return s


def _sanitize_payload(obj):
    """Best-effort sanitation for dev log payloads.

    Privacy-first: avoid persisting obvious secrets.
    """

    if isinstance(obj, str):
        return _sanitize_str(obj)

    if isinstance(obj, dict):
        out = {}
        for k, v in list(obj.items())[:200]:
            ks = str(k)
            if ks.lower() in _TO_REDACT_KEYS:
                out[ks] = "**REDACTED**" if v else ""
            else:
                out[ks] = _sanitize_payload(v)
        return out

    if isinstance(obj, list):
        return [_sanitize_payload(v) for v in obj[:200]]

    return obj


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
        "Dev: /api/v1/dev/status, /api/v1/dev/logs (POST/GET), /api/v1/dev/support_bundle (stub)\n"
        "Note: This is a scaffold. Neuron/Mood/Synapse engines come next.\n"
    )


@app.get("/health")
def health():
    return jsonify({"ok": True, "time": _now_iso()})


@app.get("/version")
def version():
    return jsonify({"version": APP_VERSION, "time": _now_iso()})


@app.get("/api/v1/dev/status")
def dev_status():
    if not _require_token():
        return jsonify({"error": "unauthorized", "error_key": "unauthorized"}), 401

    token_set = bool(_get_token())
    return jsonify(
        {
            "ok": True,
            "time": _now_iso(),
            "version": APP_VERSION,
            "auth": {"enabled": token_set},
            "dev_logs": {
                "cache_count": len(_DEV_LOG_CACHE),
                "max_cache": DEV_LOG_MAX_CACHE,
                "path": DEV_LOG_PATH,
            },
            "error_registry": ERROR_REGISTRY,
        }
    )


@app.get("/api/v1/dev/support_bundle")
def dev_support_bundle():
    if not _require_token():
        return jsonify({"error": "unauthorized", "error_key": "unauthorized"}), 401

    # v0.1 stub: do not generate or persist bundles yet.
    return jsonify(
        {
            "ok": True,
            "time": _now_iso(),
            "not_implemented": True,
            "notes": [
                "Support bundle generation is intentionally stubbed in v0.1.",
                "Use Home Assistant diagnostics download + /api/v1/dev/logs export instead.",
            ],
            "would_include": [
                "core /version and /health",
                "dev log tail (sanitized)",
                "(later) event store tail",
            ],
        }
    )


@app.post("/api/v1/echo")
def echo():
    if not _require_token():
        return jsonify({"error": "unauthorized", "error_key": "unauthorized"}), 401
    payload = request.get_json(silent=True) or {}
    return jsonify({"time": _now_iso(), "received": _sanitize_payload(payload)})


@app.post("/api/v1/dev/logs")
def ingest_dev_logs():
    if not _require_token():
        return jsonify({"error": "unauthorized", "error_key": "unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    entry = {
        "received": _now_iso(),
        "payload": _sanitize_payload(payload),
    }

    try:
        _append_dev_log(entry)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "error_key": "internal"}), 500

    return jsonify({"ok": True, "stored": True})


@app.get("/api/v1/dev/logs")
def get_dev_logs():
    if not _require_token():
        return jsonify({"error": "unauthorized", "error_key": "unauthorized"}), 401

    try:
        limit = int(request.args.get("limit", "50"))
    except Exception:
        limit = 50
    limit = max(1, min(limit, DEV_LOG_MAX_CACHE))

    return jsonify(
        {
            "ok": True,
            "count": min(limit, len(_DEV_LOG_CACHE)),
            "items": _DEV_LOG_CACHE[-limit:],
        }
    )


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8099"))
    serve(app, host=host, port=port)
