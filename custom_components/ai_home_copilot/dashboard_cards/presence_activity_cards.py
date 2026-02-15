"""Presence and Activity cards for comprehensive dashboard.

Cards:
- Presence Card: User presence and status
- Activity Card: Zone activity levels
"""
from __future__ import annotations

from typing import Any, Optional

# Import data classes
from .data_classes import PresenceData, ActivityData


def create_presence_card(
    presence_data: PresenceData,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create detailed Presence Card.
    
    Shows:
    - All users with their current status
    - Zone assignment
    - Last seen timestamps
    - Guest information
    """
    config = config or {}
    
    user_entities = []
    for user_id, user_info in presence_data.users.items():
        status = user_info.get("status", "unknown")
        zone = user_info.get("zone", "Unbekannt")
        
        status_color = {
            "home": "#4CAF50",
            "away": "#607D8B",
            "sleep": "#9C27B0",
        }.get(status, "#9E9E9E")
        
        user_entities.append({
            "type": "entity",
            "entity": user_id,
            "name": user_info.get("name", user_id),
            "icon": "mdi:account",
            "secondary_info": f"{zone} • {status}",
            "tap_action": {
                "action": "navigate",
                "navigation_path": f"/ai-home/presence/{user_id}",
            },
        })
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "👥 Anwesenheit"),
        "cards": [
            {
                "type": "grid",
                "columns": 2,
                "cards": [
                    {
                        "type": "stat",
                        "name": "Anwesend",
                        "value": str(presence_data.total_presence),
                        "icon": "mdi:account-multiple-check",
                    },
                    {
                        "type": "stat",
                        "name": "Gäste",
                        "value": str(presence_data.guest_count),
                        "icon": "mdi:account-group",
                    },
                ],
            },
            {
                "type": "entities",
                "title": "Benutzer",
                "entities": user_entities if user_entities else [
                    {"type": "section", "label": "Keine Benutzer erkannt"}
                ],
            },
        ],
    }


def create_activity_card(
    activity_data: ActivityData,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create detailed Activity Card.
    
    Shows:
    - Activity score per zone
    - Active entities
    - Recent activity timeline
    """
    config = config or {}
    
    zone_cards = []
    for zone_id, zone_info in activity_data.zones.items():
        score = zone_info.get("activity_score", 0.0)
        
        # Color based on activity level
        if score >= 0.8:
            color = "#4CAF50"
            icon = "mdi:flash"
        elif score >= 0.5:
            color = "#FF9800"
            icon = "mdi:walk"
        else:
            color = "#607D8B"
            icon = "mdi:sleep"
        
        zone_cards.append({
            "type": "vertical-stack",
            "title": zone_id,
            "cards": [
                {
                    "type": "progress",
                    "value": int(score * 100),
                    "name": "Aktivität",
                    "show_percentage": True,
                },
            ],
        })
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "⚡ Aktivität"),
        "cards": [
            {
                "type": "gauge",
                "entity": "sensor.overall_activity",
                "name": "Gesamtaktivität",
                "min": 0,
                "max": 100,
            },
            {
                "type": "grid",
                "columns": 2,
                "cards": zone_cards[:4],
            },
        ],
    }


__all__ = [
    "create_presence_card",
    "create_activity_card",
]
