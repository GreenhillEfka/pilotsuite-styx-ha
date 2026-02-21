"""Regional Context API endpoints (v5.16.0)."""

from __future__ import annotations

import logging
from flask import Blueprint, jsonify, request
from dataclasses import asdict

from copilot_core.api.security import require_token

logger = logging.getLogger(__name__)

regional_bp = Blueprint("regional", __name__, url_prefix="/api/v1/regional")

_provider = None
_warning_manager = None


def init_regional_api(provider=None, warning_manager=None) -> None:
    """Initialize regional context provider and warning manager."""
    global _provider, _warning_manager
    _provider = provider
    _warning_manager = warning_manager
    logger.info("Regional API initialized (warnings: %s)", warning_manager is not None)


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


# ── Weather Warning endpoints (v5.16.0) ──────────────────────────────────


@regional_bp.route("/warnings", methods=["GET"])
@require_token
def get_warnings():
    """Get all active weather warnings with impact assessment."""
    if not _warning_manager:
        return jsonify({"error": "Warning manager not initialized"}), 503
    overview = _warning_manager.get_overview()
    return jsonify({"ok": True, **asdict(overview)})


@regional_bp.route("/warnings/pv", methods=["GET"])
@require_token
def get_pv_warnings():
    """Get warnings that affect PV production."""
    if not _warning_manager:
        return jsonify({"error": "Warning manager not initialized"}), 503
    pv_warnings = _warning_manager.get_pv_warnings()
    return jsonify({"ok": True, "warnings": pv_warnings, "total": len(pv_warnings)})


@regional_bp.route("/warnings/grid", methods=["GET"])
@require_token
def get_grid_warnings():
    """Get warnings that affect grid stability."""
    if not _warning_manager:
        return jsonify({"error": "Warning manager not initialized"}), 503
    grid_warnings = _warning_manager.get_grid_warnings()
    return jsonify({"ok": True, "warnings": grid_warnings, "total": len(grid_warnings)})


@regional_bp.route("/warnings/summary", methods=["GET"])
@require_token
def get_warning_summary():
    """Get human-readable warning summary."""
    if not _warning_manager:
        return jsonify({"error": "Warning manager not initialized"}), 503
    lang = request.args.get("lang", "de")
    summary = _warning_manager.get_summary_text(language=lang)
    return jsonify({
        "ok": True,
        "summary": summary,
        "active_count": _warning_manager.warning_count,
        "language": lang,
    })


@regional_bp.route("/warnings/ingest", methods=["POST"])
@require_token
def ingest_warnings():
    """Ingest weather warnings from DWD or generic format.

    JSON body: {"source": "dwd"|"generic", "data": {...}}
    """
    if not _warning_manager:
        return jsonify({"error": "Warning manager not initialized"}), 503

    body = request.get_json(silent=True) or {}
    source = body.get("source", "generic")
    data = body.get("data", {})

    try:
        if source == "dwd":
            warnings = _warning_manager.process_dwd_warnings(data)
        else:
            warnings_list = data if isinstance(data, list) else data.get("warnings", [])
            warnings = _warning_manager.process_generic_warnings(
                warnings_list, source=source
            )

        logger.info("Ingested %d warnings from %s", len(warnings), source)
        overview = _warning_manager.get_overview()
        return jsonify({"ok": True, "ingested": len(warnings), **asdict(overview)})
    except Exception as exc:
        logger.error("Warning ingestion failed: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 500
