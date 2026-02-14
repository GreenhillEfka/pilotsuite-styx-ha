"""Energy Neuron API endpoints."""

from flask import Blueprint, jsonify

from .service import EnergyService
from ..api.security import require_api_key

energy_bp = Blueprint("energy", __name__)

# Global service instance (initialized in core_setup.py)
_energy_service: EnergyService = None


def init_energy_api(service: EnergyService):
    """Initialize energy service with global instance (consistent with other modules)."""
    global _energy_service
    _energy_service = service


def get_energy_service() -> EnergyService:
    """Get the energy service instance."""
    return _energy_service


@energy_bp.route("/api/v1/energy", methods=["GET"])
@require_api_key
def get_energy():
    """Get complete energy snapshot."""
    if not _energy_service:
        return jsonify({"error": "Energy service not initialized"}), 503
    
    snapshot = _energy_service.get_energy_snapshot()
    return jsonify({
        "timestamp": snapshot.timestamp,
        "total_consumption_today_kwh": snapshot.total_consumption_today,
        "total_production_today_kwh": snapshot.total_production_today,
        "current_power_watts": snapshot.current_power,
        "peak_power_today_watts": snapshot.peak_power_today,
        "anomalies_detected": snapshot.anomalies_detected,
        "shifting_opportunities": snapshot.shifting_opportunities,
        "baselines": snapshot.baselines
    })


@energy_bp.route("/api/v1/energy/anomalies", methods=["GET"])
@require_api_key
def get_anomalies():
    """Get detected energy anomalies."""
    if not _energy_service:
        return jsonify({"error": "Energy service not initialized"}), 503
    
    anomalies = _energy_service.detect_anomalies()
    return jsonify({
        "timestamp": _energy_service._get_timestamp(),
        "count": len(anomalies),
        "anomalies": [
            {
                "id": a.id,
                "timestamp": a.timestamp,
                "device_id": a.device_id,
                "device_type": a.device_type,
                "expected_value": a.expected_value,
                "actual_value": a.actual_value,
                "deviation_percent": a.deviation_percent,
                "severity": a.severity,
                "description": a.description
            }
            for a in anomalies
        ]
    })


@energy_bp.route("/api/v1/energy/shifting", methods=["GET"])
@require_api_key
def get_shifting():
    """Get load shifting opportunities."""
    if not _energy_service:
        return jsonify({"error": "Energy service not initialized"}), 503
    
    opportunities = _energy_service.detect_shifting_opportunities()
    return jsonify({
        "timestamp": _energy_service._get_timestamp(),
        "count": len(opportunities),
        "opportunities": [
            {
                "id": o.id,
                "timestamp": o.timestamp,
                "device_type": o.device_type,
                "reason": o.reason,
                "current_cost_eur": o.current_cost,
                "optimal_cost_eur": o.optimal_cost,
                "savings_estimate_eur": o.savings_estimate,
                "suggested_window_start": o.suggested_time_window[0],
                "suggested_window_end": o.suggested_time_window[1],
                "confidence": o.confidence
            }
            for o in opportunities
        ]
    })


@energy_bp.route("/api/v1/energy/explain/<suggestion_id>", methods=["GET"])
@require_api_key
def explain_suggestion(suggestion_id: str):
    """Get explanation for an energy suggestion."""
    if not _energy_service:
        return jsonify({"error": "Energy service not initialized"}), 503
    
    explanation = _energy_service.explain_suggestion(suggestion_id)
    return jsonify(explanation)


@energy_bp.route("/api/v1/energy/baselines", methods=["GET"])
@require_api_key
def get_baselines():
    """Get energy consumption baselines."""
    if not _energy_service:
        return jsonify({"error": "Energy service not initialized"}), 503
    
    return jsonify({
        "timestamp": _energy_service._get_timestamp(),
        "baselines": _energy_service._get_baselines()
    })


@energy_bp.route("/api/v1/energy/suppress", methods=["GET"])
@require_api_key
def get_suppress():
    """Check if energy suggestions should be suppressed."""
    if not _energy_service:
        return jsonify({"error": "Energy service not initialized"}), 503
    
    status = _energy_service.get_suppression_status()
    return jsonify(status)


@energy_bp.route("/api/v1/energy/health", methods=["GET"])
@require_api_key
def get_health():
    """Get energy service health status."""
    if not _energy_service:
        return jsonify({"error": "Energy service not initialized"}), 503
    
    return jsonify(_energy_service.get_health())
