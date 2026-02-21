"""Regional Context API endpoints (v5.15.0)."""

from __future__ import annotations

import logging
from flask import Blueprint, jsonify, request
from dataclasses import asdict

from copilot_core.api.security import require_token

logger = logging.getLogger(__name__)

regional_bp = Blueprint("regional", __name__, url_prefix="/api/v1/regional")

_provider = None


def init_regional_api(provider=None) -> None:
    """Initialize regional context provider."""
    global _provider
    _provider = provider
    logger.info("Regional API initialized")


@regional_bp.route("/context", methods=["GET"])
@require_token
def get_context():
    """Get complete regional context (location + solar + defaults)."""
    if not _provider:
        return jsonify({"error": "Regional provider not initialized"}), 503
    ctx = _provider.get_context()
    return jsonify({"ok": True, **asdict(ctx)})


@regional_bp.route("/solar", methods=["GET"])
@require_token
def get_solar():
    """Get current solar position."""
    if not _provider:
        return jsonify({"error": "Regional provider not initialized"}), 503
    solar = _provider.get_solar_position()
    return jsonify({"ok": True, **asdict(solar)})


@regional_bp.route("/solar/factor", methods=["GET"])
@require_token
def get_pv_factor():
    """Get current PV production factor (0-1)."""
    if not _provider:
        return jsonify({"error": "Regional provider not initialized"}), 503
    factor = _provider.get_pv_factor()
    return jsonify({"ok": True, "pv_factor": factor})


@regional_bp.route("/defaults", methods=["GET"])
@require_token
def get_defaults():
    """Get regional defaults (pricing, services, language)."""
    if not _provider:
        return jsonify({"error": "Regional provider not initialized"}), 503
    defaults = _provider.defaults
    return jsonify({"ok": True, **asdict(defaults)})


@regional_bp.route("/day-info", methods=["GET"])
@require_token
def get_day_info():
    """Get day info (sunrise, sunset, pricing, etc.)."""
    if not _provider:
        return jsonify({"error": "Regional provider not initialized"}), 503
    info = _provider.get_day_info()
    return jsonify({"ok": True, **info})


@regional_bp.route("/location", methods=["POST"])
@require_token
def update_location():
    """Update location from HA zone.home.

    JSON body: {latitude, longitude, elevation_m, timezone}
    """
    if not _provider:
        return jsonify({"error": "Regional provider not initialized"}), 503

    body = request.get_json(silent=True) or {}
    lat = body.get("latitude")
    lon = body.get("longitude")
    if lat is None or lon is None:
        return jsonify({"ok": False, "error": "latitude and longitude required"}), 400

    _provider.update_location(
        latitude=float(lat),
        longitude=float(lon),
        elevation_m=float(body.get("elevation_m", 200)),
        timezone=body.get("timezone", "Europe/Berlin"),
    )
    ctx = _provider.get_context()
    return jsonify({"ok": True, "updated": True, **asdict(ctx)})
