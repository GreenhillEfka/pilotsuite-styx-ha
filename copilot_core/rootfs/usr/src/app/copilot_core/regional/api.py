"""Regional Context API endpoints (v5.19.0)."""

from __future__ import annotations

import logging
from flask import Blueprint, jsonify, request
from dataclasses import asdict

from copilot_core.api.security import require_token

logger = logging.getLogger(__name__)

regional_bp = Blueprint("regional", __name__, url_prefix="/api/v1/regional")

_provider = None
_warning_manager = None
_fuel_tracker = None
_tariff_engine = None
_alert_engine = None


def init_regional_api(
    provider=None,
    warning_manager=None,
    fuel_tracker=None,
    tariff_engine=None,
    alert_engine=None,
) -> None:
    """Initialize all regional services."""
    global _provider, _warning_manager, _fuel_tracker, _tariff_engine, _alert_engine
    _provider = provider
    _warning_manager = warning_manager
    _fuel_tracker = fuel_tracker
    _tariff_engine = tariff_engine
    _alert_engine = alert_engine
    logger.info(
        "Regional API initialized (warnings: %s, fuel: %s, tariff: %s, alerts: %s)",
        warning_manager is not None,
        fuel_tracker is not None,
        tariff_engine is not None,
        alert_engine is not None,
    )


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


# ── Fuel Price endpoints (v5.17.0) ───────────────────────────────────────


@regional_bp.route("/fuel/prices", methods=["GET"])
@require_token
def get_fuel_prices():
    """Get current fuel prices summary."""
    if not _fuel_tracker:
        return jsonify({"error": "Fuel tracker not initialized"}), 503
    prices = _fuel_tracker.get_prices()
    if not prices:
        return jsonify({"ok": True, "prices": None, "message": "No price data yet"})
    return jsonify({"ok": True, **asdict(prices)})


@regional_bp.route("/fuel/compare", methods=["GET"])
@require_token
def get_fuel_compare():
    """Get cost-per-100km comparison (Strom vs Diesel vs Benzin vs E10)."""
    if not _fuel_tracker:
        return jsonify({"error": "Fuel tracker not initialized"}), 503
    cost = _fuel_tracker.get_cost_per_100km()
    if not cost:
        return jsonify({"ok": True, "comparison": None, "message": "No price data yet"})
    return jsonify({"ok": True, **asdict(cost)})


@regional_bp.route("/fuel/dashboard", methods=["GET"])
@require_token
def get_fuel_dashboard():
    """Get dashboard-ready fuel data with all comparisons and history."""
    if not _fuel_tracker:
        return jsonify({"error": "Fuel tracker not initialized"}), 503
    dashboard = _fuel_tracker.get_dashboard_data()
    return jsonify({"ok": True, **asdict(dashboard)})


@regional_bp.route("/fuel/stations", methods=["GET"])
@require_token
def get_fuel_stations():
    """Get nearby fuel stations with current prices."""
    if not _fuel_tracker:
        return jsonify({"error": "Fuel tracker not initialized"}), 503
    stations = [s for s in _fuel_tracker._stations if s.is_open]
    return jsonify({
        "ok": True,
        "stations": [asdict(s) for s in sorted(stations, key=lambda x: x.dist)[:20]],
        "total": len(stations),
    })


@regional_bp.route("/fuel/ingest", methods=["POST"])
@require_token
def ingest_fuel_prices():
    """Ingest fuel prices from Tankerkoenig or manual input.

    JSON body: {"source": "tankerkoenig"|"manual", "data": {...}}
    For manual: {"source": "manual", "data": {"diesel": 1.45, "e5": 1.65, "e10": 1.59}}
    """
    if not _fuel_tracker:
        return jsonify({"error": "Fuel tracker not initialized"}), 503

    body = request.get_json(silent=True) or {}
    source = body.get("source", "manual")
    data = body.get("data", {})

    try:
        if source == "tankerkoenig":
            stations = _fuel_tracker.process_tankerkoenig_response(data)
        else:
            stations = _fuel_tracker.process_manual_prices(
                diesel=data.get("diesel"),
                e5=data.get("e5"),
                e10=data.get("e10"),
            )

        logger.info("Ingested fuel prices from %s: %d stations", source, len(stations))
        prices = _fuel_tracker.get_prices()
        return jsonify({
            "ok": True,
            "source": source,
            "station_count": len(stations),
            "prices": asdict(prices) if prices else None,
        })
    except Exception as exc:
        logger.error("Fuel price ingestion failed: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 500


@regional_bp.route("/fuel/config", methods=["POST"])
@require_token
def configure_fuel():
    """Configure fuel tracker (API key, consumption values).

    JSON body: {
        "api_key": "...",
        "ev_kwh_per_100km": 18.0,
        "diesel_l_per_100km": 6.0,
        "benzin_l_per_100km": 7.5,
        "radius_km": 10.0
    }
    """
    if not _fuel_tracker:
        return jsonify({"error": "Fuel tracker not initialized"}), 503

    body = request.get_json(silent=True) or {}

    if "api_key" in body:
        _fuel_tracker.set_api_key(body["api_key"])
    if "radius_km" in body:
        _fuel_tracker.update_location(
            _fuel_tracker._lat, _fuel_tracker._lon, float(body["radius_km"])
        )
    _fuel_tracker.update_consumption(
        ev_kwh=body.get("ev_kwh_per_100km"),
        diesel_l=body.get("diesel_l_per_100km"),
        benzin_l=body.get("benzin_l_per_100km"),
        e10_l=body.get("e10_l_per_100km"),
    )
    if "grid_price_eur_kwh" in body:
        _fuel_tracker.update_grid_price(float(body["grid_price_eur_kwh"]))

    return jsonify({"ok": True, "configured": True, "has_api_key": _fuel_tracker.has_api_key})


# ── Tariff Engine endpoints (v5.18.0) ────────────────────────────────────


@regional_bp.route("/tariff/summary", methods=["GET"])
@require_token
def get_tariff_summary():
    """Get electricity tariff summary with current price and stats."""
    if not _tariff_engine:
        return jsonify({"error": "Tariff engine not initialized"}), 503
    summary = _tariff_engine.get_summary()
    return jsonify({"ok": True, **asdict(summary)})


@regional_bp.route("/tariff/prices", methods=["GET"])
@require_token
def get_tariff_prices():
    """Get hourly electricity prices."""
    if not _tariff_engine:
        return jsonify({"error": "Tariff engine not initialized"}), 503
    prices = _tariff_engine.get_hourly_prices()
    return jsonify({
        "ok": True,
        "prices": [asdict(p) for p in prices],
        "total": len(prices),
        "tariff_type": _tariff_engine.tariff_type,
    })


@regional_bp.route("/tariff/optimal", methods=["GET"])
@require_token
def get_optimal_window():
    """Find cheapest time window for consumption.

    Query param: ?hours=3 (default 3)
    """
    if not _tariff_engine:
        return jsonify({"error": "Tariff engine not initialized"}), 503
    hours = int(request.args.get("hours", 3))
    window = _tariff_engine.find_optimal_window(duration_hours=hours)
    if not window:
        return jsonify({"ok": True, "window": None, "message": "Not enough data"})
    return jsonify({"ok": True, **asdict(window)})


@regional_bp.route("/tariff/recommendation", methods=["GET"])
@require_token
def get_tariff_recommendation():
    """Get tariff-based energy recommendation."""
    if not _tariff_engine:
        return jsonify({"error": "Tariff engine not initialized"}), 503
    rec = _tariff_engine.get_recommendation()
    return jsonify({"ok": True, **asdict(rec)})


@regional_bp.route("/tariff/ingest", methods=["POST"])
@require_token
def ingest_tariff_prices():
    """Ingest electricity prices from aWATTar or manual input.

    JSON body: {"source": "awattar"|"manual", "data": {...}}
    """
    if not _tariff_engine:
        return jsonify({"error": "Tariff engine not initialized"}), 503

    body = request.get_json(silent=True) or {}
    source = body.get("source", "manual")
    data = body.get("data", {})

    try:
        if source in ("awattar", "awattar_de", "awattar_at"):
            prices = _tariff_engine.process_awattar_response(data)
        else:
            prices_list = data if isinstance(data, list) else data.get("prices", [])
            prices = _tariff_engine.process_manual_prices(prices_list)

        summary = _tariff_engine.get_summary()
        return jsonify({
            "ok": True,
            "source": source,
            "hours_ingested": len(prices),
            **asdict(summary),
        })
    except Exception as exc:
        logger.error("Tariff ingestion failed: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 500


@regional_bp.route("/tariff/config", methods=["POST"])
@require_token
def configure_tariff():
    """Configure tariff engine.

    JSON body: {
        "country": "DE",
        "tariff_type": "dynamic"|"time_of_use"|"fixed",
        "fixed_rate_eur_kwh": 0.30,
        "feed_in_eur_kwh": 0.082
    }
    """
    if not _tariff_engine:
        return jsonify({"error": "Tariff engine not initialized"}), 503

    body = request.get_json(silent=True) or {}
    _tariff_engine.update_config(
        country=body.get("country"),
        tariff_type=body.get("tariff_type"),
        fixed_rate=body.get("fixed_rate_eur_kwh"),
        feed_in=body.get("feed_in_eur_kwh"),
    )
    return jsonify({"ok": True, "configured": True, "tariff_type": _tariff_engine.tariff_type})


# ── Proactive Alert endpoints (v5.19.0) ──────────────────────────────────


@regional_bp.route("/alerts", methods=["GET"])
@require_token
def get_alerts():
    """Get all active proactive alerts."""
    if not _alert_engine:
        return jsonify({"error": "Alert engine not initialized"}), 503
    summary = _alert_engine.get_summary()
    return jsonify({"ok": True, **asdict(summary)})


@regional_bp.route("/alerts/evaluate", methods=["POST"])
@require_token
def evaluate_alerts():
    """Trigger alert evaluation with current data from all services."""
    if not _alert_engine:
        return jsonify({"error": "Alert engine not initialized"}), 503

    # Gather data from available services
    warning_data = None
    tariff_data = None
    pv_factor = 0.0
    solar_data = None

    if _warning_manager:
        overview = _warning_manager.get_overview()
        warning_data = asdict(overview)

    if _tariff_engine:
        summary = _tariff_engine.get_summary()
        tariff_data = asdict(summary)

    if _provider:
        pv_factor = _provider.get_pv_factor()
        solar = _provider.get_solar_position()
        solar_data = asdict(solar)

    new_alerts = _alert_engine.evaluate_combined(
        warning_overview=warning_data,
        tariff_summary=tariff_data,
        pv_factor=pv_factor,
        solar_data=solar_data,
    )

    summary = _alert_engine.get_summary()
    return jsonify({
        "ok": True,
        "new_alerts": len(new_alerts),
        **asdict(summary),
    })


@regional_bp.route("/alerts/dismiss", methods=["POST"])
@require_token
def dismiss_alert():
    """Dismiss/acknowledge an alert.

    JSON body: {"alert_id": "alert-1"}
    """
    if not _alert_engine:
        return jsonify({"error": "Alert engine not initialized"}), 503

    body = request.get_json(silent=True) or {}
    alert_id = body.get("alert_id", "")

    result = _alert_engine.dismiss_alert(alert_id)
    return jsonify({"ok": True, "dismissed": result, "alert_id": alert_id})


@regional_bp.route("/alerts/config", methods=["POST"])
@require_token
def configure_alerts():
    """Configure alert thresholds.

    JSON body: {
        "price_spike_ct": 35.0,
        "price_low_ct": 20.0,
        "pv_drop_pct": 50.0
    }
    """
    if not _alert_engine:
        return jsonify({"error": "Alert engine not initialized"}), 503

    body = request.get_json(silent=True) or {}
    _alert_engine.configure(
        price_spike_ct=body.get("price_spike_ct"),
        price_low_ct=body.get("price_low_ct"),
        pv_drop_pct=body.get("pv_drop_pct"),
    )
    return jsonify({"ok": True, "configured": True})
