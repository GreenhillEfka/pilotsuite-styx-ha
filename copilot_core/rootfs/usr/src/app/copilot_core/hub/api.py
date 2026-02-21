"""Hub API endpoints for PilotSuite (v6.1.0)."""

from __future__ import annotations

import logging
from flask import Blueprint, jsonify, request
from dataclasses import asdict

from copilot_core.api.security import require_token

logger = logging.getLogger(__name__)

hub_bp = Blueprint("hub", __name__, url_prefix="/api/v1/hub")

_dashboard: object | None = None
_plugin_manager: object | None = None
_multi_home: object | None = None
_maintenance_engine: object | None = None


def init_hub_api(dashboard=None, plugin_manager=None, multi_home=None, maintenance_engine=None) -> None:
    """Initialize hub services."""
    global _dashboard, _plugin_manager, _multi_home, _maintenance_engine
    _dashboard = dashboard
    _plugin_manager = plugin_manager
    _multi_home = multi_home
    _maintenance_engine = maintenance_engine
    logger.info(
        "Hub API initialized (dashboard: %s, plugins: %s, multi_home: %s)",
        dashboard is not None,
        plugin_manager is not None,
        multi_home is not None,
    )


# ── Dashboard endpoints ──────────────────────────────────────────────────


@hub_bp.route("/dashboard", methods=["GET"])
@require_token
def get_dashboard():
    """Get complete dashboard overview."""
    if not _dashboard:
        return jsonify({"error": "Dashboard not initialized"}), 503
    overview = _dashboard.get_overview()
    return jsonify({"ok": True, **asdict(overview)})


@hub_bp.route("/dashboard/widget/<widget_type>", methods=["GET"])
@require_token
def get_widget(widget_type):
    """Get a single widget's data."""
    if not _dashboard:
        return jsonify({"error": "Dashboard not initialized"}), 503
    widget = _dashboard.get_widget(widget_type)
    if not widget:
        return jsonify({"ok": False, "error": "Widget not found"}), 404
    return jsonify({"ok": True, **widget})


@hub_bp.route("/dashboard/layout", methods=["POST"])
@require_token
def set_layout():
    """Set dashboard layout.

    JSON body: {"name": "custom", "columns": 3, "theme": "dark", "language": "de"}
    """
    if not _dashboard:
        return jsonify({"error": "Dashboard not initialized"}), 503
    body = request.get_json(silent=True) or {}
    _dashboard.set_layout(
        name=body.get("name", "default"),
        columns=body.get("columns", 3),
        theme=body.get("theme", "auto"),
        language=body.get("language", "de"),
    )
    return jsonify({"ok": True, "layout": body})


@hub_bp.route("/dashboard/widget", methods=["POST"])
@require_token
def add_widget():
    """Add a widget.

    JSON body: {"widget_type": "...", "title": "...", "icon": "...", "size": "medium"}
    """
    if not _dashboard:
        return jsonify({"error": "Dashboard not initialized"}), 503
    body = request.get_json(silent=True) or {}
    result = _dashboard.add_widget(
        body.get("widget_type", ""),
        body.get("title", "Widget"),
        body.get("icon", "mdi:puzzle"),
        body.get("size", "medium"),
    )
    return jsonify({"ok": result})


@hub_bp.route("/dashboard/widget/<widget_type>", methods=["DELETE"])
@require_token
def remove_widget(widget_type):
    """Remove a widget."""
    if not _dashboard:
        return jsonify({"error": "Dashboard not initialized"}), 503
    result = _dashboard.remove_widget(widget_type)
    return jsonify({"ok": result})


# ── Plugin endpoints ─────────────────────────────────────────────────────


@hub_bp.route("/plugins", methods=["GET"])
@require_token
def get_plugins():
    """Get plugin registry summary."""
    if not _plugin_manager:
        return jsonify({"error": "Plugin manager not initialized"}), 503
    summary = _plugin_manager.get_summary()
    return jsonify({"ok": True, **asdict(summary)})


@hub_bp.route("/plugins/<plugin_id>", methods=["GET"])
@require_token
def get_plugin(plugin_id):
    """Get plugin details."""
    if not _plugin_manager:
        return jsonify({"error": "Plugin manager not initialized"}), 503
    info = _plugin_manager.get_plugin(plugin_id)
    if not info:
        return jsonify({"ok": False, "error": "Plugin not found"}), 404
    return jsonify({"ok": True, **info})


@hub_bp.route("/plugins/<plugin_id>/activate", methods=["POST"])
@require_token
def activate_plugin(plugin_id):
    """Activate a plugin."""
    if not _plugin_manager:
        return jsonify({"error": "Plugin manager not initialized"}), 503
    result = _plugin_manager.activate_plugin(plugin_id)
    return jsonify({"ok": result, "plugin_id": plugin_id, "action": "activate"})


@hub_bp.route("/plugins/<plugin_id>/disable", methods=["POST"])
@require_token
def disable_plugin(plugin_id):
    """Disable a plugin."""
    if not _plugin_manager:
        return jsonify({"error": "Plugin manager not initialized"}), 503
    result = _plugin_manager.disable_plugin(plugin_id)
    return jsonify({"ok": result, "plugin_id": plugin_id, "action": "disable"})


@hub_bp.route("/plugins/<plugin_id>/config", methods=["POST"])
@require_token
def configure_plugin(plugin_id):
    """Configure a plugin.

    JSON body: {"key": "value", ...}
    """
    if not _plugin_manager:
        return jsonify({"error": "Plugin manager not initialized"}), 503
    body = request.get_json(silent=True) or {}
    result = _plugin_manager.configure_plugin(plugin_id, body)
    return jsonify({"ok": result, "plugin_id": plugin_id})


# ── Multi-Home endpoints ─────────────────────────────────────────────────


@hub_bp.route("/homes", methods=["GET"])
@require_token
def get_homes():
    """Get multi-home summary."""
    if not _multi_home:
        return jsonify({"error": "Multi-home manager not initialized"}), 503
    summary = _multi_home.get_summary()
    return jsonify({"ok": True, **asdict(summary)})


@hub_bp.route("/homes/<home_id>", methods=["GET"])
@require_token
def get_home(home_id):
    """Get home details."""
    if not _multi_home:
        return jsonify({"error": "Multi-home manager not initialized"}), 503
    info = _multi_home.get_home(home_id)
    if not info:
        return jsonify({"ok": False, "error": "Home not found"}), 404
    return jsonify({"ok": True, **info})


@hub_bp.route("/homes", methods=["POST"])
@require_token
def add_home():
    """Add a home.

    JSON body: {"home_id": "...", "name": "...", "address": "...", "core_url": "...", "token": "..."}
    """
    if not _multi_home:
        return jsonify({"error": "Multi-home manager not initialized"}), 503
    body = request.get_json(silent=True) or {}
    result = _multi_home.add_home(
        home_id=body.get("home_id", ""),
        name=body.get("name", "Home"),
        address=body.get("address", ""),
        latitude=float(body.get("latitude", 0)),
        longitude=float(body.get("longitude", 0)),
        core_url=body.get("core_url", ""),
        token=body.get("token", ""),
        icon=body.get("icon", "mdi:home"),
    )
    return jsonify({"ok": result})


@hub_bp.route("/homes/<home_id>", methods=["DELETE"])
@require_token
def remove_home(home_id):
    """Remove a home."""
    if not _multi_home:
        return jsonify({"error": "Multi-home manager not initialized"}), 503
    result = _multi_home.remove_home(home_id)
    return jsonify({"ok": result})


@hub_bp.route("/homes/<home_id>/activate", methods=["POST"])
@require_token
def set_active_home(home_id):
    """Switch active home."""
    if not _multi_home:
        return jsonify({"error": "Multi-home manager not initialized"}), 503
    result = _multi_home.set_active_home(home_id)
    return jsonify({"ok": result, "active_home_id": home_id})


@hub_bp.route("/homes/<home_id>/status", methods=["POST"])
@require_token
def update_home_status(home_id):
    """Update home status.

    JSON body: {"status": "online", "device_count": 42, "energy_kwh": 15.3, "cost_eur": 4.59}
    """
    if not _multi_home:
        return jsonify({"error": "Multi-home manager not initialized"}), 503
    body = request.get_json(silent=True) or {}
    result = _multi_home.update_home_status(
        home_id=home_id,
        status=body.get("status", "online"),
        device_count=body.get("device_count"),
        energy_kwh=body.get("energy_kwh"),
        cost_eur=body.get("cost_eur"),
    )
    return jsonify({"ok": result})


# ── Predictive Maintenance endpoints (v6.1.0) ────────────────────────────


@hub_bp.route("/maintenance", methods=["GET"])
@require_token
def get_maintenance_summary():
    """Get predictive maintenance summary."""
    if not _maintenance_engine:
        return jsonify({"error": "Maintenance engine not initialized"}), 503
    summary = _maintenance_engine.get_summary()
    return jsonify({"ok": True, **asdict(summary)})


@hub_bp.route("/maintenance/device/<device_id>", methods=["GET"])
@require_token
def get_device_health(device_id):
    """Get device health details."""
    if not _maintenance_engine:
        return jsonify({"error": "Maintenance engine not initialized"}), 503
    info = _maintenance_engine.get_device(device_id)
    if not info:
        return jsonify({"ok": False, "error": "Device not found"}), 404
    return jsonify({"ok": True, **info})


@hub_bp.route("/maintenance/register", methods=["POST"])
@require_token
def register_device():
    """Register a device for monitoring.

    JSON body: {"device_id": "...", "name": "...", "device_type": "sensor"}
    """
    if not _maintenance_engine:
        return jsonify({"error": "Maintenance engine not initialized"}), 503
    body = request.get_json(silent=True) or {}
    _maintenance_engine.register_device(
        body.get("device_id", ""),
        body.get("name", "Device"),
        body.get("device_type", "sensor"),
    )
    return jsonify({"ok": True, "device_id": body.get("device_id", "")})


@hub_bp.route("/maintenance/ingest", methods=["POST"])
@require_token
def ingest_device_metrics():
    """Ingest device metrics.

    JSON body: {"metrics": [{"device_id": "...", "metric": "...", "value": ...}, ...]}
    """
    if not _maintenance_engine:
        return jsonify({"error": "Maintenance engine not initialized"}), 503
    body = request.get_json(silent=True) or {}
    metrics = body.get("metrics", [])
    count = _maintenance_engine.ingest_metrics_batch(metrics)
    return jsonify({"ok": True, "ingested": count})


@hub_bp.route("/maintenance/evaluate", methods=["POST"])
@require_token
def evaluate_devices():
    """Trigger health evaluation for all devices."""
    if not _maintenance_engine:
        return jsonify({"error": "Maintenance engine not initialized"}), 503
    results = _maintenance_engine.evaluate_all()
    summary = _maintenance_engine.get_summary()
    return jsonify({"ok": True, "evaluated": len(results), **asdict(summary)})
