"""Overview cards for comprehensive dashboard.

Cards:
- Dashboard Overview Card (main entry point)
- Neuron Status Card
- Mood Overview Card
- Zone Overview Card
- System Health Card
"""
from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..data_classes import (
        DashboardData,
        NeuronStatus,
        MoodData,
    )


def create_dashboard_overview_card(
    data: DashboardData,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create the main Dashboard Overview Card.
    
    Features:
    - Neuronen Status (grid of all neurons)
    - Mood Overview (current mood with icon)
    - Zone Overview (active zones)
    - System Health (health score, alerts)
    
    Args:
        data: Dashboard data
        config: Optional configuration overrides
        
    Returns:
        Lovelace card configuration dict
    """
    config = config or {}
    
    cards = [
        _create_neuron_status_card(data),
        _create_mood_overview_card(data),
        _create_zone_overview_card(data),
        _create_system_health_card(data),
    ]
    
    card_config = {
        "type": "vertical-stack",
        "title": config.get("title", "🏠 AI Home Copilot Dashboard"),
        "cards": cards,
    }
    
    # Add styling for dark/light mode
    card_config["card_mod"] = {
        "style": {
            "margin": "8px",
            "padding": "12px",
        }
    }
    
    return card_config


def _create_neuron_status_card(data: DashboardData) -> dict[str, Any]:
    """Create neuron status overview card."""
    neuron_cards = []
    
    # Group neurons by status
    status_groups = {
        "active": [],
        "inactive": [],
        "warning": [],
        "error": [],
    }
    
    for neuron in data.neurons:
        status_groups[neuron.status].append(neuron)
    
    # Create grid of neuron buttons
    for status, neurons in status_groups.items():
        if not neurons:
            continue
            
        icon_map = {
            "active": "mdi:check-circle",
            "inactive": "mdi:circle-outline",
            "warning": "mdi:alert-circle",
            "error": "mdi:close-circle",
        }
        
        color_map = {
            "active": "#4CAF50",
            "inactive": "#9E9E9E",
            "warning": "#FF9800",
            "error": "#F44336",
        }
        
        neuron_cards.append({
            "type": "horizontal-stack",
            "cards": [
                {
                    "type": "button",
                    "name": neuron.name,
                    "icon": neuron.icon,
                    "show_state": True,
                    "state_color": True,
                    "tap_action": {
                        "action": "navigate",
                        "navigation_path": f"/ai-home/neurons/{neuron.entity_id}",
                    },
                    "hold_action": {
                        "action": "more-info",
                    },
                    "styles": {
                        "card": {
                            "background-color": color_map.get(neuron.status, "#9E9E9E"),
                            "border-radius": "12px",
                        },
                    },
                }
                for neuron in neurons[:4]  # Max 4 per row
            ],
        })
    
    if not neuron_cards:
        neuron_cards.append({
            "type": "markdown",
            "content": "**Keine Neuronen aktiv**",
        })
    
    return {
        "type": "vertical-stack",
        "title": "🧠 Neuronen Status",
        "cards": neuron_cards,
        "card_mod": {
            "style": {
                "background": "var(--card-background-color, #fff)",
                "border-radius": "16px",
                "padding": "8px",
            }
        },
    }


def _create_mood_overview_card(data: DashboardData) -> dict[str, Any]:
    """Create mood overview card."""
    mood = data.mood
    
    if not mood:
        return {
            "type": "entity",
            "entity": "sensor.ai_home_copilot_mood",
            "name": "🎭 Stimmung",
            "icon": "mdi:emoticon-outline",
        }
    
    mood_icon = mood.get("icon", "mdi:emoticon-outline")
    mood_color = mood.get("color", "#9E9E9E")
    mood_name = mood.get("name_de", "Neutral")
    confidence = mood.get("confidence", 0.0)
    
    return {
        "type": "vertical-stack",
        "title": "🎭 Stimmungsübersicht",
        "cards": [
            {
                "type": "picture-elements",
                "elements": [
                    {
                        "type": "icon",
                        "icon": mood_icon,
                        "style": {
                            "color": mood_color,
                            "font-size": "48px",
                            "position": "center",
                        },
                    },
                    {
                        "type": "state-badge",
                        "style": {
                            "position": "absolute",
                            "top": "8px",
                            "right": "8px",
                        },
                    },
                ],
            },
            {
                "type": "entities",
                "entities": [
                    {
                        "entity": "sensor.ai_home_copilot_mood",
                        "name": mood_name,
                        "secondary_info": f"Confidence: {confidence:.0%}",
                    },
                ],
            },
        ],
    }


def _create_zone_overview_card(data: DashboardData) -> dict[str, Any]:
    """Create zone overview card."""
    zones = []
    
    # Get zones from presence data
    for user_id, user_data in data.presence.users.items():
        zone_name = user_data.get("zone", "Unbekannt")
        status = user_data.get("status", "unknown")
        
        status_icon = {
            "home": "mdi:home",
            "away": "mdi:home-export-outline",
            "sleep": "mdi:sleep",
        }.get(status, "mdi:account")
        
        zones.append({
            "type": "entity",
            "entity": user_id,
            "name": user_data.get("name", user_id),
            "icon": status_icon,
            "secondary_info": f"Zone: {zone_name}",
        })
    
    if not zones:
        zones.append({
            "type": "markdown",
            "content": "Keine Benutzer erkannt",
        })
    
    return {
        "type": "vertical-stack",
        "title": "🏠 Zonenübersicht",
        "cards": [
            {
                "type": "grid",
                "columns": 2,
                "cards": [
                    {
                        "type": "stat",
                        "entity": "sensor.total_presence",
                        "name": "Anwesend",
                        "icon": "mdi:account-multiple",
                    },
                    {
                        "type": "stat",
                        "entity": "sensor.guest_count",
                        "name": "Gäste",
                        "icon": "mdi:account-group",
                    },
                ],
            },
            {
                "type": "entities",
                "entities": zones[:6],
            },
        ],
    }


def _create_system_health_card(data: DashboardData) -> dict[str, Any]:
    """Create system health card."""
    health = data.system_health
    
    # Determine health color
    if health.health_score >= 80:
        health_color = "#4CAF50"
        health_icon = "mdi:check-circle"
    elif health.health_score >= 50:
        health_color = "#FF9800"
        health_icon = "mdi:alert-circle"
    else:
        health_color = "#F44336"
        health_icon = "mdi:close-circle"
    
    return {
        "type": "vertical-stack",
        "title": "💚 System Status",
        "cards": [
            {
                "type": "gauge",
                "entity": "sensor.system_health_score",
                "min": 0,
                "max": 100,
                "name": "System Health",
                "severity": {
                    "green": 80,
                    "yellow": 50,
                    "red": 0,
                },
            },
            {
                "type": "entities",
                "entities": [
                    {
                        "type": "section",
                        "label": f"Aktive Neuronen: {health.active_neurons}/{health.total_neurons}",
                    },
                ],
            },
        ],
    }


__all__ = [
    "create_dashboard_overview_card",
    "_create_neuron_status_card",
    "_create_mood_overview_card",
    "_create_zone_overview_card",
    "_create_system_health_card",
]
