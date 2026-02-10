"""Shared authentication helpers for API blueprints."""
from __future__ import annotations

import json
import os
from typing import Any

from flask import Request

OPTIONS_PATH = "/data/options.json"


def get_auth_token(options_path: str = OPTIONS_PATH) -> str:
    """Return the configured shared token, if any."""

    token = os.environ.get("COPILOT_AUTH_TOKEN", "").strip()
    if token:
        return token

    try:
        with open(options_path, "r", encoding="utf-8") as fh:
            opts: Any = json.load(fh) or {}
        return str(opts.get("auth_token", "")).strip()
    except Exception:
        return ""


def require_token(request: Request) -> bool:
    """Validate the shared token against the incoming request."""

    token = get_auth_token()
    if not token:
        return True

    header_token = (request.headers.get("X-Auth-Token") or "").strip()
    if header_token and header_token == token:
        return True

    auth_header = (request.headers.get("Authorization") or "").strip()
    if auth_header.startswith("Bearer "):
        candidate = auth_header.split(" ", 1)[1].strip()
        if candidate == token:
            return True

    return False
