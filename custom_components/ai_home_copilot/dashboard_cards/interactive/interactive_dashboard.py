"""
Interactive Dashboard Cards Module
===================================

Interactive elements for the comprehensive dashboard:
- Clickable Neuron Cards
- Detail View Cards
- Filter Cards
- Modal Dialogs

Path: /config/.openclaw/workspace/ai_home_copilot_hacs_repo/custom_components/ai_home_copilot/dashboard_cards/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


# ============================================================================
# INTERACTIVE NEURON CARDS
# ============================================================================

def create_neuron_detail_card(
    neuron_id: str,
    neuron_name: str,
    neuron_type: str,
    status: str,
    value: Any,
    history: list[dict[str, Any]] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a clickable neuron detail card.
    
    Features:
    - Tap: Show more-info dialog
    - Hold: Navigate to neuron detail view
    - Double-tap: Quick action (toggle, etc.)
    """
    config = config or {}
    
    # Icon mapping for neuron types
    type_icons = {
        "presence": "mdi:account-check",
        "activity": "mdi:motion-sensor",
        "energy": "mdi:lightning-bolt",
        "media": "mdi:television",
        "weather": "mdi:weather-partly-cloudy",
        "calendar": "mdi:calendar",
        "mood": "mdi:emoticon",
        "system": "mdi:cog",
    }
    
    # Status colors
    status_colors = {
        "active": "#4CAF50",
        "inactive": "#9E9E9E",
        "warning": "#FF9800",
        "error": "#F44336",
        "unknown": "#607D8B",
    }
    
    neuron_icon = type_icons.get(neuron_type, "mdi:brain")
    status_color = status_colors.get(status, "#9E9E9E")
    
    return {
        "type": "button",
        "name": neuron_name,
        "icon": neuron_icon,
        "show_state": True,
        "state_color": True,
        "entity": neuron_id,
        "tap_action": {
            "action": "more-info",
            "entity": neuron_id,
        },
        "hold_action": {
            "action": "navigate",
            "navigation_path": f"/ai-home/neurons/{neuron_id}",
        },
        "double_tap_action": config.get("double_tap_action", {
            "action": "call-service",
            "service": "ai_home_copilot.toggle_neuron",
            "service_data": {"neuron_id": neuron_id},
        }),
        "styles": {
            "card": {
                "background-color": status_color,
                "border-radius": "12px",
                "transition": "all 0.3s ease",
            },
            "icon": {
                "color": "white",
            },
            "name": {
                "color": "white",
                "font-weight": "bold",
            },
        },
    }


def create_neuron_grid_card(
    neurons: list[dict[str, Any]],
    columns: int = 4,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a grid of clickable neuron cards.
    
    Args:
        neurons: List of neuron dicts with keys: id, name, type, status, value
        columns: Number of columns in grid
        config: Optional configuration
    """
    config = config or {}
    
    neuron_cards = [
        create_neuron_detail_card(
            neuron_id=n["id"],
            neuron_name=n["name"],
            neuron_type=n.get("type", "system"),
            status=n.get("status", "unknown"),
            value=n.get("value"),
            config=config,
        )
        for n in neurons
    ]
    
    # Split into rows
    rows = []
    for i in range(0, len(neuron_cards), columns):
        rows.append({
            "type": "horizontal-stack",
            "cards": neuron_cards[i:i+columns],
        })
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "🧠 Alle Neuronen"),
        "cards": rows,
    }


# ============================================================================
# FILTER CARDS
# ============================================================================

def create_filter_card(
    filter_type: str,
    options: list[dict[str, Any]],
    current_filter: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a filter card for dashboard views.
    
    Args:
        filter_type: Type of filter (zone, status, type, etc.)
        options: List of options with keys: id, name, icon, count
        current_filter: Currently selected filter
        config: Optional configuration
    """
    config = config or {}
    
    filter_buttons = []
    for opt in options:
        is_selected = opt["id"] == current_filter
        
        filter_buttons.append({
            "type": "button",
            "name": opt["name"],
            "icon": opt.get("icon", "mdi:filter"),
            "show_state": True,
            "state_color": is_selected,
            "tap_action": {
                "action": "navigate",
                "navigation_path": f"/ai-home/dashboard?filter={filter_type}:{opt['id']}",
            },
            "styles": {
                "card": {
                    "background-color": "var(--primary-color)" if is_selected else "var(--card-background-color)",
                    "border-radius": "8px",
                },
            },
        })
    
    return {
        "type": "horizontal-scroll",
        "cards": filter_buttons,
    }


def create_zone_filter_card(
    zones: list[dict[str, Any]],
    current_zone: str | None = None,
) -> dict[str, Any]:
    """Create a zone filter card."""
    options = [
        {
            "id": zone["id"],
            "name": zone["name"],
            "icon": zone.get("icon", "mdi:home"),
            "count": zone.get("user_count", 0),
        }
        for zone in zones
    ]
    
    # Add "All" option
    all_option = {
        "id": "all",
        "name": "Alle",
        "icon": "mdi:home-group",
        "count": sum(opt["count"] for opt in options),
    }
    
    return create_filter_card("zone", [all_option] + options, current_zone)


def create_status_filter_card(
    statuses: list[dict[str, Any]],
    current_status: str | None = None,
) -> dict[str, Any]:
    """Create a status filter card."""
    options = [
        {
            "id": status["id"],
            "name": status["name"],
            "icon": status.get("icon", "mdi:circle"),
            "count": status.get("count", 0),
        }
        for status in statuses
    ]
    
    return create_filter_card("status", options, current_status)


# ============================================================================
# DETAIL VIEW CARDS
# ============================================================================

def create_neuron_detail_view(
    neuron_id: str,
    neuron_data: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a detailed view for a single neuron.
    
    Shows:
    - Current status and value
    - Historical chart
    - Configuration
    - Actions
    """
    config = config or {}
    
    return {
        "type": "vertical-stack",
        "title": f"🧠 {neuron_data.get('name', neuron_id)}",
        "cards": [
            # Header with status
            {
                "type": "horizontal-stack",
                "cards": [
                    {
                        "type": "entity",
                        "entity": neuron_id,
                        "name": "Status",
                        "icon": neuron_data.get("icon", "mdi:brain"),
                    },
                    {
                        "type": "gauge",
                        "entity": f"sensor.{neuron_id}_value",
                        "name": "Wert",
                        "min": 0,
                        "max": 100,
                    },
                ],
            },
            
            # History graph
            {
                "type": "history-graph",
                "title": "Verlauf",
                "entities": [neuron_id],
                "hours_to_show": 24,
            },
            
            # Configuration section
            {
                "type": "entities",
                "title": "Konfiguration",
                "entities": [
                    {
                        "entity": f"input_select.{neuron_id}_mode",
                        "name": "Modus",
                    },
                    {
                        "entity": f"input_number.{neuron_id}_threshold",
                        "name": "Schwellenwert",
                    },
                ],
            },
            
            # Actions
            {
                "type": "horizontal-stack",
                "cards": [
                    {
                        "type": "button",
                        "name": "Aktualisieren",
                        "icon": "mdi:refresh",
                        "tap_action": {
                            "action": "call-service",
                            "service": "ai_home_copilot.refresh_neuron",
                            "service_data": {"neuron_id": neuron_id},
                        },
                    },
                    {
                        "type": "button",
                        "name": "Deaktivieren",
                        "icon": "mdi:pause",
                        "tap_action": {
                            "action": "call-service",
                            "service": "ai_home_copilot.disable_neuron",
                            "service_data": {"neuron_id": neuron_id},
                        },
                    },
                    {
                        "type": "button",
                        "name": "Einstellungen",
                        "icon": "mdi:cog",
                        "tap_action": {
                            "action": "navigate",
                            "navigation_path": f"/ai-home/settings/neurons/{neuron_id}",
                        },
                    },
                ],
            },
        ],
    }


def create_zone_detail_view(
    zone_id: str,
    zone_data: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a detailed view for a zone.
    
    Shows:
    - Zone entities (lights, climate, etc.)
    - Activity history
    - User presence
    """
    config = config or {}
    
    entity_cards = []
    for entity_type, entities in zone_data.get("entities", {}).items():
        type_icons = {
            "lights": "mdi:lightbulb",
            "climate": "mdi:thermostat",
            "cover": "mdi:blinds",
            "media": "mdi:television",
            "sensor": "mdi:sensor",
            "binary_sensor": "mdi:motion-sensor",
        }
        
        entity_cards.append({
            "type": "entities",
            "title": entity_type.title(),
            "icon": type_icons.get(entity_type, "mdi:circle"),
            "entities": [
                {"entity": e, "name": e.split(".")[-1].replace("_", " ").title()}
                for e in entities
            ],
        })
    
    return {
        "type": "vertical-stack",
        "title": f"🏠 {zone_data.get('name', zone_id)}",
        "cards": [
            # Zone overview
            {
                "type": "grid",
                "columns": 2,
                "cards": [
                    {
                        "type": "stat",
                        "name": "Benutzer",
                        "value": str(zone_data.get("user_count", 0)),
                        "icon": "mdi:account-multiple",
                    },
                    {
                        "type": "stat",
                        "name": "Aktivität",
                        "value": f"{zone_data.get('activity_score', 0):.0%}",
                        "icon": "mdi:flash",
                    },
                ],
            },
            
            # Entity sections
            *entity_cards,
            
            # Zone controls
            {
                "type": "horizontal-stack",
                "cards": [
                    {
                        "type": "button",
                        "name": "Alle Lichter aus",
                        "icon": "mdi:lightbulb-off",
                        "tap_action": {
                            "action": "call-service",
                            "service": "light.turn_off",
                            "target": {
                                "area_id": zone_id,
                            },
                        },
                    },
                    {
                        "type": "button",
                        "name": "Heizung aus",
                        "icon": "mdi:thermostat-off",
                        "tap_action": {
                            "action": "call-service",
                            "service": "climate.turn_off",
                            "target": {
                                "area_id": zone_id,
                            },
                        },
                    },
                ],
            },
        ],
    }


# ============================================================================
# MODAL DIALOGS
# ============================================================================

def create_info_modal(
    title: str,
    content: str,
    icon: str = "mdi:information",
) -> dict[str, Any]:
    """Create an info modal dialog."""
    return {
        "type": "picture-elements",
        "elements": [
            {
                "type": "icon",
                "icon": icon,
                "style": {
                    "color": "var(--primary-color)",
                    "font-size": "48px",
                    "position": "center",
                },
            },
            {
                "type": "markdown",
                "content": f"## {title}\n\n{content}",
                "style": {
                    "position": "absolute",
                    "bottom": "0",
                    "left": "0",
                    "right": "0",
                    "background": "var(--card-background-color)",
                    "padding": "16px",
                },
            },
        ],
    }


def create_confirm_dialog(
    title: str,
    message: str,
    confirm_service: str,
    confirm_data: dict[str, Any],
    cancel_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a confirmation dialog card."""
    cancel_action = cancel_action or {"action": "back"}
    
    return {
        "type": "vertical-stack",
        "title": title,
        "cards": [
            {
                "type": "markdown",
                "content": message,
            },
            {
                "type": "horizontal-stack",
                "cards": [
                    {
                        "type": "button",
                        "name": "Abbrechen",
                        "icon": "mdi:cancel",
                        "tap_action": cancel_action,
                    },
                    {
                        "type": "button",
                        "name": "Bestätigen",
                        "icon": "mdi:check",
                        "tap_action": {
                            "action": "call-service",
                            "service": confirm_service,
                            "service_data": confirm_data,
                        },
                        "styles": {
                            "card": {
                                "background-color": "var(--error-color, #F44336)",
                            },
                        },
                    },
                ],
            },
        ],
    }


# ============================================================================
# DASHBOARD WITH FILTERS
# ============================================================================

def create_filterable_dashboard(
    neurons: list[dict[str, Any]],
    zones: list[dict[str, Any]],
    current_filter: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a dashboard with filter capability.
    
    Args:
        neurons: List of neuron dicts
        zones: List of zone dicts
        current_filter: Current filter string (type:id)
        config: Optional configuration
    """
    config = config or {}
    
    # Parse current filter
    filter_type, filter_id = None, None
    if current_filter and ":" in current_filter:
        filter_type, filter_id = current_filter.split(":", 1)
    
    # Create filter section
    filters = []
    
    # Zone filter
    if config.get("show_zone_filter", True):
        filters.append(create_zone_filter_card(zones, filter_id if filter_type == "zone" else None))
    
    # Status filter
    if config.get("show_status_filter", True):
        statuses = [
            {"id": "active", "name": "Aktiv", "icon": "mdi:check-circle", "count": len([n for n in neurons if n.get("status") == "active"])},
            {"id": "inactive", "name": "Inaktiv", "icon": "mdi:circle-outline", "count": len([n for n in neurons if n.get("status") == "inactive"])},
            {"id": "warning", "name": "Warnung", "icon": "mdi:alert-circle", "count": len([n for n in neurons if n.get("status") == "warning"])},
        ]
        filters.append(create_status_filter_card(statuses, filter_id if filter_type == "status" else None))
    
    # Apply filter
    filtered_neurons = neurons
    if filter_id and filter_id != "all":
        if filter_type == "zone":
            filtered_neurons = [n for n in neurons if n.get("zone") == filter_id]
        elif filter_type == "status":
            filtered_neurons = [n for n in neurons if n.get("status") == filter_id]
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "🧠 Neuronen"),
        "cards": [
            # Filter bar
            *filters,
            
            # Neuron grid
            create_neuron_grid_card(filtered_neurons, columns=config.get("columns", 4)),
            
            # Statistics
            {
                "type": "grid",
                "columns": 4,
                "cards": [
                    {
                        "type": "stat",
                        "name": "Gesamt",
                        "value": str(len(neurons)),
                        "icon": "mdi:brain",
                    },
                    {
                        "type": "stat",
                        "name": "Aktiv",
                        "value": str(len([n for n in neurons if n.get("status") == "active"])),
                        "icon": "mdi:check-circle",
                    },
                    {
                        "type": "stat",
                        "name": "Warnung",
                        "value": str(len([n for n in neurons if n.get("status") == "warning"])),
                        "icon": "mdi:alert-circle",
                    },
                    {
                        "type": "stat",
                        "name": "Fehler",
                        "value": str(len([n for n in neurons if n.get("status") == "error"])),
                        "icon": "mdi:close-circle",
                    },
                ],
            },
        ],
    }
