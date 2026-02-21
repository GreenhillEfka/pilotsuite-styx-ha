"""Energy Neuron API endpoints."""

from flask import Blueprint, jsonify, request

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


# ═══════════════════════════════════════════════════════════════════════════
# v5.1.0 — Zone Energy API
# ═══════════════════════════════════════════════════════════════════════════

@energy_bp.route("/api/v1/energy/zone/<zone_id>", methods=["POST"])
@require_api_key
def register_zone_energy(zone_id: str):
    """Register energy entities for a zone.

    Body: {"entity_ids": ["sensor.kitchen_power", ...], "zone_name": "Kitchen"}
    """
    if not _energy_service:
        return jsonify({"error": "Energy service not initialized"}), 503

    body = request.get_json(silent=True) or {}
    entity_ids = body.get("entity_ids", [])
    zone_name = body.get("zone_name", zone_id)

    if not isinstance(entity_ids, list):
        return jsonify({"ok": False, "error": "entity_ids must be a list"}), 400

    # Store zone energy mapping
    if not hasattr(_energy_service, "_zone_energy_map"):
        _energy_service._zone_energy_map = {}

    _energy_service._zone_energy_map[zone_id] = {
        "zone_name": zone_name,
        "entity_ids": entity_ids,
        "registered_at": _energy_service._get_timestamp(),
    }

    return jsonify({
        "ok": True,
        "zone_id": zone_id,
        "zone_name": zone_name,
        "entity_count": len(entity_ids),
    }), 201


@energy_bp.route("/api/v1/energy/zone/<zone_id>", methods=["GET"])
@require_api_key
def get_zone_energy(zone_id: str):
    """Get energy data for a specific zone."""
    if not _energy_service:
        return jsonify({"error": "Energy service not initialized"}), 503

    zone_map = getattr(_energy_service, "_zone_energy_map", {})
    zone_config = zone_map.get(zone_id)

    if not zone_config:
        return jsonify({
            "ok": False,
            "error": f"No energy entities registered for zone '{zone_id}'",
        }), 404

    # Aggregate zone energy from HA entities
    entity_ids = zone_config["entity_ids"]
    total_power = 0.0
    breakdown = []

    for eid in entity_ids:
        value = _energy_service._find_single_entity_value(eid)
        if value is not None:
            total_power += value
            breakdown.append({"entity_id": eid, "value": round(value, 2), "status": "ok"})
        else:
            breakdown.append({"entity_id": eid, "value": None, "status": "unavailable"})

    return jsonify({
        "ok": True,
        "zone_id": zone_id,
        "zone_name": zone_config["zone_name"],
        "total_power_watts": round(total_power, 2),
        "entity_count": len(entity_ids),
        "active_count": sum(1 for b in breakdown if b["status"] == "ok"),
        "breakdown": breakdown,
        "timestamp": _energy_service._get_timestamp(),
    })


@energy_bp.route("/api/v1/energy/zones", methods=["GET"])
@require_api_key
def get_all_zone_energy():
    """Get energy overview for all registered zones."""
    if not _energy_service:
        return jsonify({"error": "Energy service not initialized"}), 503

    zone_map = getattr(_energy_service, "_zone_energy_map", {})
    zones = []

    for zone_id, config in zone_map.items():
        total_power = 0.0
        active = 0
        for eid in config["entity_ids"]:
            value = _energy_service._find_single_entity_value(eid)
            if value is not None:
                total_power += value
                active += 1

        zones.append({
            "zone_id": zone_id,
            "zone_name": config["zone_name"],
            "total_power_watts": round(total_power, 2),
            "entity_count": len(config["entity_ids"]),
            "active_count": active,
        })

    # Sort by power descending (highest consuming zone first)
    zones.sort(key=lambda z: z["total_power_watts"], reverse=True)

    return jsonify({
        "ok": True,
        "zones": zones,
        "total_zones": len(zones),
        "global_power_watts": round(sum(z["total_power_watts"] for z in zones), 2),
        "timestamp": _energy_service._get_timestamp(),
    })
