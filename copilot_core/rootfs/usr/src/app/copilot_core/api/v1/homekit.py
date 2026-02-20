"""HomeKit Bridge REST API — manage HomeKit exposure per habitus zone.

Provides endpoints to toggle HomeKit for zones and check status.
Proxies to the HACS HomeKitBridgeModule via Supervisor API.
"""

from flask import Blueprint, request, jsonify
import logging
import os

import requests as http_requests

from copilot_core.api.security import require_token

logger = logging.getLogger(__name__)

homekit_bp = Blueprint("homekit", __name__, url_prefix="/api/v1/homekit")

# Cache of HomeKit-enabled zones (synced from HACS)
_homekit_zones: dict[str, dict] = {}


@homekit_bp.route("/status", methods=["GET"])
@require_token
def homekit_status():
    """Get HomeKit bridge status — which zones are enabled."""
    return jsonify({
        "enabled_zones": [
            z for z in _homekit_zones.values() if z.get("enabled")
        ],
        "total_zones": sum(1 for z in _homekit_zones.values() if z.get("enabled")),
        "total_entities": sum(
            len(z.get("entity_ids", []))
            for z in _homekit_zones.values()
            if z.get("enabled")
        ),
    })


@homekit_bp.route("/toggle", methods=["POST"])
@require_token
def toggle_homekit():
    """Toggle HomeKit for a habitus zone.

    Body: {
        "zone_id": "zone:wohnzimmer",
        "zone_name": "Wohnzimmer",
        "entity_ids": ["light.wohnzimmer", ...],
        "enabled": true
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    zone_id = data.get("zone_id", "")
    zone_name = data.get("zone_name", zone_id)
    entity_ids = data.get("entity_ids", [])
    enabled = data.get("enabled", True)

    if not zone_id:
        return jsonify({"error": "zone_id is required"}), 400

    if enabled and not entity_ids:
        return jsonify({"error": "entity_ids required when enabling"}), 400

    # Filter to HomeKit-supported domains
    supported_domains = {
        "light", "switch", "cover", "climate", "fan", "lock",
        "media_player", "sensor", "binary_sensor", "input_boolean",
    }
    supported = [
        eid for eid in entity_ids
        if eid.split(".", 1)[0] in supported_domains
    ] if enabled else []

    if enabled and not supported:
        return jsonify({"error": "Keine HomeKit-kompatiblen Entitaeten gefunden"}), 400

    _homekit_zones[zone_id] = {
        "zone_id": zone_id,
        "zone_name": zone_name,
        "entity_ids": supported,
        "enabled": enabled,
    }

    # Try to reload HomeKit integration via HA Supervisor API
    ha_url = os.environ.get("SUPERVISOR_API", "http://supervisor/core/api")
    ha_token = os.environ.get("SUPERVISOR_TOKEN", "")
    if ha_token:
        headers = {"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"}
        try:
            http_requests.post(
                f"{ha_url}/services/homekit/reload",
                json={}, headers=headers, timeout=10,
            )
            logger.info("HomeKit reload triggered after zone toggle")
        except Exception as exc:
            logger.warning("HomeKit reload failed (may not be installed): %s", exc)

    action = "aktiviert" if enabled else "deaktiviert"
    logger.info("HomeKit %s for zone %s (%d entities)", action, zone_name, len(supported))

    return jsonify({
        "success": True,
        "zone_id": zone_id,
        "zone_name": zone_name,
        "enabled": enabled,
        "entities_exposed": len(supported),
    })


@homekit_bp.route("/update", methods=["POST"])
@require_token
def update_homekit_cache():
    """Receive HomeKit zone data from HACS integration (sync)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    zones = data.get("zones", [])
    for z in zones:
        zid = z.get("zone_id")
        if zid:
            _homekit_zones[zid] = z
    return jsonify({"success": True, "synced": len(zones)})


def get_homekit_context_for_llm() -> str:
    """Build HomeKit context string for LLM system prompt injection."""
    enabled = [z for z in _homekit_zones.values() if z.get("enabled")]
    if not enabled:
        return ""
    total = sum(len(z.get("entity_ids", [])) for z in enabled)
    zone_list = ", ".join(z.get("zone_name", z.get("zone_id", "?")) for z in enabled)
    return f"HomeKit-Bridge: {len(enabled)} Zonen aktiv ({total} Entitaeten) — {zone_list}"
