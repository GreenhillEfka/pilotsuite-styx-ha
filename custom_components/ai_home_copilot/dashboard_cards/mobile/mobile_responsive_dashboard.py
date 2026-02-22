"""
Mobile Responsive Dashboard Module
==================================

Mobile-optimized dashboard with:
- Responsive Grid Layout
- Adaptive Cards
- Dark/Light Mode Support
- Touch-optimized Controls

Path: custom_components/ai_home_copilot/dashboard_cards/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)


# ============================================================================
# RESPONSIVE GRID LAYOUT
# ============================================================================

@dataclass
class ResponsiveConfig:
    """Configuration for responsive dashboard."""
    # Grid breakpoints
    mobile_max_width: int = 480
    tablet_max_width: int = 768
    desktop_min_width: int = 1024
    
    # Column counts
    mobile_columns: int = 1
    tablet_columns: int = 2
    desktop_columns: int = 4
    
    # Card sizes
    mobile_card_height: str = "auto"
    tablet_card_height: str = "200px"
    desktop_card_height: str = "180px"
    
    # Theme
    default_theme: str = "auto"  # "auto", "light", "dark"


def create_responsive_grid(
    cards: list[dict[str, Any]],
    config: ResponsiveConfig | None = None,
) -> dict[str, Any]:
    """
    Create a responsive grid layout.
    
    Automatically adjusts columns based on screen size.
    Uses CSS grid with media queries for responsive behavior.
    """
    config = config or ResponsiveConfig()
    
    # Desktop: 4 columns
    desktop_cards = _distribute_cards(cards, config.desktop_columns)
    
    # Tablet: 2 columns
    tablet_cards = _distribute_cards(cards, config.tablet_columns)
    
    # Mobile: 1 column
    mobile_cards = _distribute_cards(cards, config.mobile_columns)
    
    return {
        "type": "custom:stack-in-card",
        "mode": "vertical",
        "cards": [
            # Desktop view
            {
                "type": "custom:grid-layout",
                "view_layout": {
                    "show": True,
                    "column": "1 / -1",
                },
                "cards": desktop_cards,
            },
            # Tablet view (hidden on desktop)
            {
                "type": "custom:grid-layout",
                "view_layout": {
                    "show": "if_mobile",
                },
                "cards": tablet_cards,
            },
            # Mobile view (hidden on tablet+)
            {
                "type": "vertical-stack",
                "view_layout": {
                    "show": "if_mobile",
                },
                "cards": mobile_cards,
            },
        ],
    }


def _distribute_cards(cards: list[dict[str, Any]], columns: int) -> list[dict[str, Any]]:
    """Distribute cards into rows of specified column count."""
    rows = []
    for i in range(0, len(cards), columns):
        row = {
            "type": "horizontal-stack" if columns > 1 else "vertical-stack",
            "cards": cards[i:i+columns],
        }
        rows.append(row)
    return rows


# ============================================================================
# ADAPTIVE CARDS
# ============================================================================

def create_adaptive_card(
    card_type: str,
    data: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create an adaptive card that changes based on screen size.
    
    Card types:
    - compact: Minimal info, small
    - standard: Balanced info
    - detailed: Full info, larger
    """
    config = config or {}
    
    # Compact version (mobile)
    compact = {
        "type": "button",
        "name": data.get("name", ""),
        "icon": data.get("icon", "mdi:circle"),
        "show_state": True,
    }
    
    # Standard version (tablet)
    standard = {
        "type": "entity",
        "entity": data.get("entity", ""),
        "name": data.get("name", ""),
        "icon": data.get("icon", "mdi:circle"),
        "secondary_info": data.get("secondary", None),
    }
    
    # Detailed version (desktop)
    detailed = {
        "type": "vertical-stack",
        "title": data.get("name", ""),
        "cards": [
            standard,
            {
                "type": "stat",
                "name": data.get("stat_name", "Wert"),
                "value": str(data.get("value", "")),
                "icon": data.get("icon", "mdi:circle"),
            },
        ],
    }
    
    # Return based on type
    if card_type == "compact":
        return compact
    elif card_type == "detailed":
        return detailed
    return standard


def create_adaptive_stat_card(
    value: Any,
    name: str,
    icon: str = "mdi:circle",
    unit: str = "",
    trend: str | None = None,
    color: str | None = None,
) -> dict[str, Any]:
    """
    Create an adaptive stat card that shows more info on larger screens.
    """
    base = {
        "type": "stat",
        "name": name,
        "value": f"{value}{unit}",
        "icon": icon,
    }
    
    if color:
        base["styles"] = {
            "icon": {
                "color": color,
            },
        }
    
    # Add trend indicator
    if trend:
        trend_icons = {
            "up": "mdi:trending-up",
            "down": "mdi:trending-down",
            "stable": "mdi:trending-neutral",
        }
        base["icon"] = trend_icons.get(trend, icon)
    
    return base


# ============================================================================
# DARK/LIGHT MODE SUPPORT
# ============================================================================

def get_theme_colors(theme: str = "auto") -> dict[str, str]:
    """
    Get color palette based on theme preference.
    
    Args:
        theme: "auto", "light", or "dark"
        
    Returns:
        Dict with color variables
    """
    light_colors = {
        "background": "#f5f5f5",
        "card_background": "#ffffff",
        "text_primary": "#212121",
        "text_secondary": "#757575",
        "primary": "#2196F3",
        "secondary": "#FFC107",
        "success": "#4CAF50",
        "warning": "#FF9800",
        "error": "#F44336",
        "divider": "#e0e0e0",
    }
    
    dark_colors = {
        "background": "#121212",
        "card_background": "#1e1e1e",
        "text_primary": "#ffffff",
        "text_secondary": "#b0b0b0",
        "primary": "#64B5F6",
        "secondary": "#FFD54F",
        "success": "#81C784",
        "warning": "#FFB74D",
        "error": "#E57373",
        "divider": "#424242",
    }
    
    if theme == "light":
        return light_colors
    elif theme == "dark":
        return dark_colors
    
    # Auto: return CSS variables (will be resolved by HA)
    return {
        "background": "var(--ha-card-background, #f5f5f5)",
        "card_background": "var(--ha-card-background, #ffffff)",
        "text_primary": "var(--primary-text-color, #212121)",
        "text_secondary": "var(--secondary-text-color, #757575)",
        "primary": "var(--primary-color, #2196F3)",
        "secondary": "var(--accent-color, #FFC107)",
        "success": "var(--success-color, #4CAF50)",
        "warning": "var(--warning-color, #FF9800)",
        "error": "var(--error-color, #F44336)",
        "divider": "var(--divider-color, #e0e0e0)",
    }


def apply_theme_styles(
    card: dict[str, Any],
    theme: str = "auto",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Apply theme styles to a card.
    
    Adds card_mod styling for dark/light mode support.
    """
    colors = get_theme_colors(theme)
    config = config or {}
    
    # Deep copy to avoid modifying original
    import copy
    card = copy.deepcopy(card)
    
    # Apply card_mod style
    card["card_mod"] = {
        "style": {
            "--card-background-color": colors["card_background"],
            "--text-primary-color": colors["text_primary"],
            "--text-secondary-color": colors["text_secondary"],
            "--primary-color": colors["primary"],
            "--divider-color": colors["divider"],
            "border-radius": config.get("border_radius", "16px"),
            "padding": config.get("padding", "12px"),
            "margin": config.get("margin", "8px"),
            "box-shadow": config.get("box_shadow", "0 2px 4px rgba(0,0,0,0.1)"),
        }
    }
    
    return card


# ============================================================================
# TOUCH-OPTIMIZED CONTROLS
# ============================================================================

def create_touch_card(
    card: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Optimize a card for touch interaction.
    
    Features:
    - Larger tap targets
    - Haptic feedback (if supported)
    - Swipe gestures
    """
    config = config or {}
    
    import copy
    card = copy.deepcopy(card)
    
    # Ensure card has tap_action
    if "tap_action" not in card and "entity" in card:
        card["tap_action"] = {
            "action": "more-info",
        }
    
    # Add haptic feedback for supported platforms
    if config.get("haptic", True):
        if "tap_action" in card:
            card["tap_action"]["haptic"] = "medium"
        if "hold_action" in card:
            card["hold_action"]["haptic"] = "heavy"
    
    # Set minimum size for touch targets
    card["card_mod"] = card.get("card_mod", {})
    card["card_mod"]["style"] = card["card_mod"].get("style", {})
    card["card_mod"]["style"]["min-height"] = config.get("min_height", "48px")
    card["card_mod"]["style"]["min-width"] = config.get("min_width", "48px")
    
    return card


def create_swipeable_card(
    front_card: dict[str, Any],
    back_card: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a card with swipe gesture support.
    
    Swipe left/right to reveal back content.
    """
    config = config or {}
    
    return {
        "type": "custom:swipe-card",
        "cards": [front_card, back_card],
        "config": {
            "swipe": {
                "animate": config.get("animate", "slide"),
                "velocity_threshold": config.get("velocity_threshold", 300),
            },
        },
    }


# ============================================================================
# MOBILE DASHBOARD LAYOUTS
# ============================================================================

def create_mobile_overview_layout(
    items: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a mobile-optimized overview layout.
    
    Features:
    - Single column stack
    - Collapsible sections
    - Pull-to-refresh (if supported)
    """
    config = config or {}
    
    sections = []
    for item in items:
        section = {
            "type": "vertical-stack",
            "title": item.get("title", ""),
            "cards": item.get("cards", []),
        }
        
        # Add collapse capability
        if config.get("collapsible", True):
            section["card_mod"] = {
                "style": {
                    "--collapse-height": "200px",
                }
            }
        
        sections.append(section)
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "🏠 Übersicht"),
        "cards": sections,
    }


def create_mobile_dashboard_layout(
    categories: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a full mobile dashboard with categories.
    
    Uses swipe navigation between categories.
    """
    config = config or {}
    
    category_cards = []
    for cat in categories:
        category_cards.append({
            "type": "vertical-stack",
            "title": cat.get("title", ""),
            "icon": cat.get("icon", "mdi:folder"),
            "cards": cat.get("cards", []),
        })
    
    return {
        "type": "custom:swipe-card",
        "cards": category_cards,
        "config": {
            "titles": [cat.get("title", "") for cat in categories],
            "indicators": True,
        },
    }


# ============================================================================
# RESPONSIVE SENSOR CARDS
# ============================================================================

def create_responsive_sensor_card(
    entity_id: str,
    name: str,
    icon: str,
    unit: str = "",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a sensor card that adapts to screen size.
    """
    config = config or {}
    
    # Mobile: Simple stat
    mobile = {
        "type": "stat",
        "entity": entity_id,
        "name": name,
        "icon": icon,
    }
    
    # Tablet: Add graph
    tablet = {
        "type": "custom:mini-graph-card",
        "entities": [{"entity": entity_id}],
        "name": name,
        "icon": icon,
        "hours_to_show": 6,
        "points_per_hour": 4,
    }
    
    # Desktop: Full with history
    desktop = {
        "type": "vertical-stack",
        "title": name,
        "cards": [
            {
                "type": "entity",
                "entity": entity_id,
                "icon": icon,
            },
            {
                "type": "history-graph",
                "entities": [entity_id],
                "hours_to_show": 24,
            },
        ],
    }
    
    return {
        "type": "custom:responsive-card",
        "breakpoints": {
            "mobile": mobile,
            "tablet": tablet,
            "desktop": desktop,
        },
    }


# ============================================================================
# COMPLETE MOBILE DASHBOARD
# ============================================================================

def create_complete_mobile_dashboard(
    data: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create the complete mobile-optimized dashboard.
    """
    config = config or {}
    
    # Apply theme
    theme = config.get("theme", "auto")
    colors = get_theme_colors(theme)
    
    # Build sections
    sections = []
    
    # 1. Header with system status
    sections.append({
        "title": "📊 Status",
        "icon": "mdi:view-dashboard",
        "cards": [
            apply_theme_styles({
                "type": "gauge",
                "entity": data.get("health_entity", "sensor.system_health"),
                "name": "System",
                "min": 0,
                "max": 100,
            }, theme),
            apply_theme_styles({
                "type": "entity",
                "entity": data.get("mood_entity", "sensor.ai_home_copilot_mood"),
                "name": "Stimmung",
                "icon": "mdi:emoticon",
            }, theme),
        ],
    })
    
    # 2. Presence section
    if "presence" in data:
        sections.append({
            "title": "👥 Anwesenheit",
            "icon": "mdi:account-multiple",
            "cards": [
                apply_theme_styles(create_adaptive_card("standard", {
                    "entity": "sensor.total_presence",
                    "name": "Anwesend",
                    "icon": "mdi:account-multiple-check",
                    "value": data.get("presence", {}).get("count", 0),
                }), theme),
            ],
        })
    
    # 3. Energy section
    if "energy" in data:
        sections.append({
            "title": "⚡ Energie",
            "icon": "mdi:lightning-bolt",
            "cards": [
                apply_theme_styles(create_adaptive_stat_card(
                    value=data.get("energy", {}).get("consumption", 0),
                    name="Verbrauch",
                    unit=" kWh",
                    icon="mdi:flash",
                    color=colors["warning"],
                ), theme),
                apply_theme_styles(create_adaptive_stat_card(
                    value=data.get("energy", {}).get("production", 0),
                    name="Produktion",
                    unit=" kWh",
                    icon="mdi:solar-panel",
                    color=colors["success"],
                ), theme),
            ],
        })
    
    # 4. Weather section
    if "weather" in data:
        sections.append({
            "title": "🌤️ Wetter",
            "icon": "mdi:weather-partly-cloudy",
            "cards": [
                apply_theme_styles({
                    "type": "entity",
                    "entity": data.get("weather_entity", "weather.home"),
                    "name": "Aktuell",
                    "icon": "mdi:thermometer",
                }, theme),
            ],
        })
    
    # 5. Media section
    if "media" in data:
        sections.append({
            "title": "📺 Media",
            "icon": "mdi:television",
            "cards": [
                apply_theme_styles({
                    "type": "entity",
                    "entity": data.get("media_entity", "media_player.main"),
                    "name": "Wiedergabe",
                    "icon": "mdi:play-circle",
                }, theme),
            ],
        })
    
    # 6. Calendar section
    if "calendar" in data:
        sections.append({
            "title": "📅 Kalender",
            "icon": "mdi:calendar",
            "cards": [
                apply_theme_styles({
                    "type": "entity",
                    "entity": "calendar.primary",
                    "name": "Nächster Termin",
                    "icon": "mdi:calendar-clock",
                }, theme),
            ],
        })
    
    # Return complete layout
    return create_mobile_dashboard_layout(sections, config)


# ============================================================================
# THEME SWITCHER
# ============================================================================

def create_theme_switcher_card(
    current_theme: str = "auto",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a card for switching between light/dark/auto themes.
    """
    config = config or {}
    
    themes = [
        {"id": "auto", "name": "Auto", "icon": "mdi:theme-light-dark"},
        {"id": "light", "name": "Hell", "icon": "mdi:weather-sunny"},
        {"id": "dark", "name": "Dunkel", "icon": "mdi:weather-night"},
    ]
    
    buttons = []
    for theme in themes:
        is_selected = theme["id"] == current_theme
        
        buttons.append({
            "type": "button",
            "name": theme["name"],
            "icon": theme["icon"],
            "show_state": False,
            "tap_action": {
                "action": "call-service",
                "service": "frontend.set_theme",
                "service_data": {
                    "name": theme["id"],
                },
            },
            "styles": {
                "card": {
                    "background-color": colors["primary"] if is_selected else colors["card_background"],
                } if (colors := get_theme_colors()) else {},
            },
        })
    
    return {
        "type": "horizontal-stack",
        "title": "🎨 Design",
        "cards": buttons,
    }
