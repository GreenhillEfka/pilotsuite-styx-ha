"""API v1 -- Prediction endpoints.

Exposes the ArrivalForecaster and EnergyOptimizer via REST.

Endpoints:
    GET  /api/v1/predict/arrival/<person_id>     -- predict next arrival
    GET  /api/v1/predict/energy/optimal-window   -- cheapest energy window
    POST /api/v1/predict/energy/schedule          -- set manual price schedule
"""
from __future__ import annotations

import logging
from flask import Blueprint, jsonify, request

from copilot_core.api.security import require_token

logger = logging.getLogger(__name__)

prediction_bp = Blueprint("prediction", __name__, url_prefix="/api/v1/predict")

_forecaster = None
_optimizer = None


def init_prediction_api(forecaster=None, optimizer=None) -> None:
    """Inject service singletons at startup."""
    global _forecaster, _optimizer
    _forecaster = forecaster
    _optimizer = optimizer
    logger.info("Prediction API initialized")


# -- GET /api/v1/predict/arrival/<person_id> ------------------------------

@prediction_bp.route("/arrival/<person_id>", methods=["GET"])
@require_token
def predict_arrival(person_id: str):
    """Predict the next arrival time for a person."""
    if _forecaster is None:
        return jsonify({"ok": False, "error": "ArrivalForecaster not initialized"}), 503

    horizon = request.args.get("horizon", 120, type=int)

    try:
        result = _forecaster.predict_arrival(person_id, horizon_minutes=horizon)
        return jsonify({"ok": True, **result}), 200
    except Exception as exc:
        logger.error("Arrival prediction failed for %s: %s", person_id, exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


# -- GET /api/v1/predict/energy/optimal-window ----------------------------

@prediction_bp.route("/energy/optimal-window", methods=["GET"])
@require_token
def energy_optimal_window():
    """Find the cheapest energy window."""
    if _optimizer is None:
        return jsonify({"ok": False, "error": "EnergyOptimizer not initialized"}), 503

    duration = request.args.get("duration", 2.0, type=float)
    within = request.args.get("within", 24.0, type=float)

    try:
        result = _optimizer.find_optimal_window(
            duration_hours=duration, within_hours=within
        )
        return jsonify({"ok": True, **result}), 200
    except Exception as exc:
        logger.error("Optimal window search failed: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


# -- POST /api/v1/predict/energy/schedule ---------------------------------

@prediction_bp.route("/energy/schedule", methods=["POST"])
@require_token
def set_energy_schedule():
    """Manually set the energy price schedule.

    Expected JSON body::

        {
            "prices": [
                {"start": "2025-01-01T00:00:00+00:00",
                 "end":   "2025-01-01T01:00:00+00:00",
                 "price_eur_kwh": 0.25},
                ...
            ]
        }
    """
    if _optimizer is None:
        return jsonify({"ok": False, "error": "EnergyOptimizer not initialized"}), 503

    body = request.get_json(silent=True) or {}
    prices = body.get("prices")
    if not isinstance(prices, list):
        return jsonify({"ok": False, "error": "Missing or invalid 'prices' list"}), 400

    try:
        _optimizer.set_price_schedule(prices)
        return jsonify({"ok": True, "slots": len(prices)}), 200
    except Exception as exc:
        logger.error("Failed to set price schedule: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500
