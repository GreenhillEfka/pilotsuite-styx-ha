"""Shared authentication helpers for API blueprints."""
from __future__ import annotations

import json
import os
from functools import wraps
from typing import Any, Callable

from flask import Request, jsonify

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


def validate_token(request: Request) -> bool:
    """Validate the shared token against the incoming request.
    
    Returns True if token is valid or not required.
    Returns False if token is required but invalid.
    """

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


# Legacy aliases for backward compatibility
def require_token(request: Request) -> bool:
    """Legacy alias for validate_token."""
    return validate_token(request)


# Decorator for Flask route handlers
def require_api_key(f: Callable) -> Callable:
    """Flask decorator to require API authentication.
    
    Usage:
        @app.route('/api/endpoint')
        @require_api_key
        def my_endpoint():
            ...
    
    Returns 401 Unauthorized if token is invalid or missing (when required).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request as flask_request
        
        if not validate_token(flask_request):
            return jsonify({
                "status": "error",
                "error": "Unauthorized"
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function
