"""
habitus_dashboard_cards API endpoint (v0.1)

Provides dashboard pattern recommendations and templates for Home Assistant Lovelace.
Focus: core-only cards, trends, aggregates, drill-down patterns.
"""
from flask import Blueprint, jsonify, request
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


bp = Blueprint("habitus_dashboard_cards", __name__, url_prefix="/habitus/dashboard_cards")


@bp.get("")
def get_dashboard_patterns():
    """
    Return recommended dashboard patterns and card templates.
    
    Query params:
    - type: "overview" | "room" | "energy" | "sleep" (default: all)
    - format: "yaml" | "json" (default: json)
    """
    pattern_type = request.args.get("type", "all").lower()
    output_format = request.args.get("format", "json").lower()

    patterns = _get_patterns(pattern_type)

    return jsonify({
        "ok": True,
        "time": _now_iso(),
        "type": pattern_type,
        "format": output_format,
        "patterns": patterns,
        "documentation": "/docs/module_specs/habitus_dashboard_cards_v0.1.md"
    })


def _get_patterns(pattern_type: str) -> dict:
    """Return pattern templates based on type."""
    
    # Base patterns from spec
    base_patterns = {
        "principles": {
            "hierarchy": "Overview → Diagnosis → Detail",
            "time_windows": ["24h (operational)", "7 days (trend)", "30 days (seasonality)"],
            "max_lines_per_graph": 3,
            "title_convention": "Always include time window, e.g. '(24h)'"
        },
        "recommended_cards": {
            "status": ["tile", "entities", "glance"],
            "trends": ["history-graph", "statistics-graph"],
            "events": ["logbook"],
            "layout": ["grid", "vertical-stack"]
        }
    }

    templates = {}

    if pattern_type in ("all", "overview"):
        templates["overview"] = {
            "description": "Main overview page with tiles + drill-down",
            "example": {
                "type": "grid",
                "columns": 2,
                "square": False,
                "cards": [
                    {
                        "type": "tile",
                        "entity": "sensor.room_temperature",
                        "name": "Temperature",
                        "state_content": ["state", "last_changed"],
                        "tap_action": {
                            "action": "navigate",
                            "navigation_path": "/dashboard-habitus/room-detail"
                        }
                    }
                ]
            }
        }

    if pattern_type in ("all", "room"):
        templates["room_detail"] = {
            "description": "Room detail page: status + short-term + long-term trends + events",
            "sections": [
                {
                    "purpose": "Current status",
                    "card_type": "entities",
                    "entities": ["temperature", "humidity", "co2", "window_status"]
                },
                {
                    "purpose": "Short-term trend (24h)",
                    "card_type": "history-graph",
                    "hours_to_show": 24,
                    "entities": ["temperature", "humidity"]
                },
                {
                    "purpose": "Long-term aggregated trend (7 days)",
                    "card_type": "statistics-graph",
                    "period": "day",
                    "days_to_show": 7,
                    "stat_types": ["mean", "min", "max"],
                    "entities": ["temperature"]
                },
                {
                    "purpose": "Events (24h)",
                    "card_type": "logbook",
                    "hours_to_show": 24,
                    "entities": ["binary_sensor.motion", "binary_sensor.door"]
                }
            ]
        }

    if pattern_type in ("all", "energy"):
        templates["energy"] = {
            "description": "Energy consumption patterns",
            "example": {
                "type": "vertical-stack",
                "cards": [
                    {
                        "type": "tile",
                        "entity": "sensor.power_consumption",
                        "name": "Current Power (W)"
                    },
                    {
                        "type": "statistics-graph",
                        "title": "Daily Energy (7 days)",
                        "period": "day",
                        "days_to_show": 7,
                        "stat_types": ["sum"],
                        "entities": ["sensor.energy_kwh"]
                    }
                ]
            }
        }

    if pattern_type in ("all", "sleep"):
        templates["sleep"] = {
            "description": "Sleep/rest patterns",
            "example": {
                "type": "vertical-stack",
                "cards": [
                    {
                        "type": "tile",
                        "entity": "sensor.sleep_duration_last_night",
                        "name": "Last Night Sleep"
                    },
                    {
                        "type": "statistics-graph",
                        "title": "Sleep Duration - Weekly Mean",
                        "period": "week",
                        "stat_types": ["mean"],
                        "entities": ["sensor.sleep_duration"]
                    }
                ]
            }
        }

    return {
        "base": base_patterns,
        "templates": templates
    }


@bp.get("/health")
def health():
    """Health check for dashboard_cards module."""
    return jsonify({
        "ok": True,
        "time": _now_iso(),
        "module": "habitus_dashboard_cards",
        "version": "0.1.0",
        "status": "active"
    })
