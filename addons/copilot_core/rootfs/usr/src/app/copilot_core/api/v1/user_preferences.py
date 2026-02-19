"""User Preference API endpoints for AI Home CoPilot Core.

Provides endpoints for Multi-User Preference Learning (MUP-L).
Privacy-first: user IDs remain local and are never forwarded to external services.

Design Doc: docs/MUPL_DESIGN.md
"""
from __future__ import annotations

import logging
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from copilot_core.storage.user_preferences import (
    UserPreferences,
    get_user_preference_store,
)

bp = Blueprint("user_preferences", __name__, url_prefix="/user")

from copilot_core.api.security import validate_token as _validate_token


@bp.before_request
def _require_auth():
    if not _validate_token(request):
        return jsonify({"error": "unauthorized", "message": "Valid X-Auth-Token or Bearer token required"}), 401

_LOGGER = logging.getLogger(__name__)


def _get_ha_client():
    """Get Home Assistant client from app config."""
    cfg = current_app.config.get("COPILOT_CFG")
    if hasattr(cfg, "ha_client"):
        return cfg.ha_client
    return None


def _store():
    """Get the user preference store."""
    return get_user_preference_store()


@bp.get("/<user_id>/preferences")
def get_user_preferences(user_id: str):
    """Get all preferences for a user.
    
    Args:
        user_id: User ID (person entity_id)
        
    Returns:
        JSON with user_id and preferences dict
    """
    user = _store().get_user(user_id)
    if user:
        prefs = user.preferences
    else:
        prefs = {
            "light_brightness": {"default": 0.8, "by_zone": {}},
            "media_volume": {"default": 0.5, "by_zone": {}},
            "temperature": {"default": 21.0, "by_zone": {}},
            "mood_weights": {"comfort": 0.5, "frugality": 0.5, "joy": 0.5},
        }
    
    return jsonify({
        "user_id": user_id,
        "preferences": prefs,
    })


@bp.get("/<user_id>/zone/<zone_id>/preference")
def get_user_zone_preference(user_id: str, zone_id: str):
    """Get preference for a user in a specific zone.
    
    Args:
        user_id: User ID (person entity_id)
        zone_id: Zone ID (e.g., "living", "bedroom")
        
    Returns:
        JSON with user_id, zone_id, and preference
    """
    user = _store().get_user(user_id)
    
    if user:
        prefs = user.preferences
        mood = prefs.get("mood_weights", {"comfort": 0.5, "frugality": 0.5, "joy": 0.5})
    else:
        mood = {"comfort": 0.5, "frugality": 0.5, "joy": 0.5}
    
    return jsonify({
        "user_id": user_id,
        "zone_id": zone_id,
        "preference": {
            "mood_weights": mood,
        },
    })


@bp.post("/<user_id>/preference")
def update_user_preference(user_id: str):
    """Update a user's preference for a zone.
    
    Args:
        user_id: User ID (person entity_id)
        
    Body:
        zone_id: Zone ID (required)
        comfort_bias: Comfort bias (0.0-1.0, optional)
        frugality_bias: Frugality bias (0.0-1.0, optional)
        joy_bias: Joy bias (0.0-1.0, optional)
        
    Returns:
        Updated preference dict
    """
    data = request.get_json(silent=True) or {}
    
    zone_id = data.get("zone_id")
    if not zone_id:
        return jsonify({"error": "zone_id_required"}), 400
    
    # Build preference update
    prefs_update = {}
    mood = {}
    
    if "comfort_bias" in data:
        mood["comfort"] = max(0.0, min(1.0, float(data["comfort_bias"])))
    if "frugality_bias" in data:
        mood["frugality"] = max(0.0, min(1.0, float(data["frugality_bias"])))
    if "joy_bias" in data:
        mood["joy"] = max(0.0, min(1.0, float(data["joy_bias"])))
    
    if mood:
        prefs_update["mood_weights"] = mood
    
    # Update via store
    user = _store().update_user_preferences(user_id, prefs_update)
    
    _LOGGER.info("Updated preference for user %s in zone %s: %s", user_id, zone_id, mood)
    
    return jsonify({
        "user_id": user_id,
        "zone_id": zone_id,
        "preference": {"mood_weights": user.preferences.get("mood_weights", {})},
    })


@bp.get("/active")
def get_active_users():
    """Get list of currently active (home) users.
    
    Queries Home Assistant person entities to find users currently home.
    
    Returns:
        List of active user dicts with user_id and name
    """
    ha_client = _get_ha_client()
    active = []
    
    if ha_client:
        try:
            # Get all person entities
            states = ha_client.get_states()
            for state in states:
                if state.get("entity_id", "").startswith("person."):
                    if state.get("state") == "home":
                        user_id = state["entity_id"]
                        active.append({
                            "user_id": user_id,
                            "name": state.get("attributes", {}).get("friendly_name", user_id),
                        })
                        # Update store
                        _store().add_active_user(user_id)
        except Exception as e:
            _LOGGER.warning("Failed to get active users from HA: %s", e)
    
    return jsonify({
        "status": "ok",
        "users": active,
        "count": len(active),
    })


@bp.get("/all")
def get_all_users():
    """Get all known users with their preferences.
    
    Returns:
        Dict of user_id to user data
    """
    users = _store().get_all_users()
    
    return jsonify({
        "status": "ok",
        "users": {uid: u.to_dict() for uid, u in users.items()},
        "count": len(users),
    })


@bp.post("/<user_id>/priority")
def set_user_priority(user_id: str):
    """Set user priority for conflict resolution.
    
    Args:
        user_id: User ID
        
    Body:
        priority: Priority value (0.0-1.0, higher = more important)
        
    Returns:
        Updated user data
    """
    data = request.get_json(silent=True) or {}
    
    priority = data.get("priority")
    if priority is None:
        return jsonify({"error": "priority_required"}), 400
    
    priority = max(0.0, min(1.0, float(priority)))
    
    ok = _store().update_user_priority(user_id, priority)
    
    if not ok:
        return jsonify({"error": "user_not_found"}), 404
    
    _LOGGER.info("Set priority %.2f for user %s", priority, user_id)
    
    return jsonify({
        "user_id": user_id,
        "priority": priority,
    })


@bp.delete("/<user_id>")
def delete_user_data(user_id: str):
    """Delete all data for a user (privacy/GDPR).
    
    Args:
        user_id: User to delete
        
    Returns:
        Status dict
    """
    ok = _store().delete_user(user_id)
    
    if not ok:
        return jsonify({"error": "user_not_found"}), 404
    
    _LOGGER.info("Deleted all data for user: %s", user_id)
    
    return jsonify({"status": "deleted", "user_id": user_id})


@bp.get("/<user_id>/export")
def export_user_data(user_id: str):
    """Export all data for a user (privacy/GDPR).
    
    Args:
        user_id: User to export
        
    Returns:
        User data dict
    """
    data = _store().export_user_data(user_id)
    
    if not data:
        return jsonify({"error": "user_not_found"}), 404
    
    return jsonify(data)


# ==================== Aggregated Mood ====================


@bp.get("/mood/aggregated")
def get_aggregated_mood():
    """Get aggregated mood for multiple users.
    
    Query params:
        users: Comma-separated list of user IDs (optional, defaults to active users)
        
    Returns:
        Aggregated mood dict with comfort, frugality, joy
    """
    users_param = request.args.get("users")
    
    if users_param:
        user_ids = [u.strip() for u in users_param.split(",") if u.strip()]
    else:
        user_ids = _store().get_active_users()
    
    mood = _store().get_aggregated_mood(user_ids)
    
    return jsonify({
        "status": "ok",
        "mood": mood,
        "user_count": len(user_ids),
    })