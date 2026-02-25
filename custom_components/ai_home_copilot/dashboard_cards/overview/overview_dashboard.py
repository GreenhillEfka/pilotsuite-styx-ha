"""Complete dashboard builders for comprehensive dashboard.

Functions:
- create_complete_dashboard: All-in-one dashboard for desktop
- create_mobile_dashboard: Mobile-optimized dashboard
- dashboard_to_yaml: Export to YAML format
"""
from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..data_classes import DashboardData


def create_complete_dashboard(
    data: "DashboardData",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create the complete all-in-one dashboard.
    
    Layout:
    1. Overview Section (full width)
    2. Presence + Activity (2 columns)
    3. Energy + Media (2 columns)
    4. Weather + Calendar (2 columns)
    
    Mobile: Stacks vertically
    Desktop: Grid layout
    """
    # Lazy imports to avoid circular dependencies
    from ..overview.overview_cards import create_dashboard_overview_card
    from ..presence.presence_activity_cards import create_presence_card, create_activity_card
    from ..energy.energy_media_cards import create_energy_card, create_media_card
    from ..weather.weather_calendar_cards import create_weather_card, create_calendar_card
    
    config = config or {}
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "🏠 PilotSuite - Styx"),
        "cards": [
            # === SECTION 1: OVERVIEW ===
            create_dashboard_overview_card(data, {"title": "📊 Übersicht"}),
            
            # === SECTION 2: PRESENCE + ACTIVITY ===
            {
                "type": "grid",
                "columns": 2,
                "cards": [
                    create_presence_card(data.presence),
                    create_activity_card(data.activity),
                ],
            },
            
            # === SECTION 3: ENERGY + MEDIA ===
            {
                "type": "grid",
                "columns": 2,
                "cards": [
                    create_energy_card(data.energy),
                    create_media_card(data.media),
                ],
            },
            
            # === SECTION 4: WEATHER + CALENDAR ===
            {
                "type": "grid",
                "columns": 2,
                "cards": [
                    create_weather_card(data.weather),
                    create_calendar_card(data.calendar),
                ],
            },
        ],
    }


def create_mobile_dashboard(
    data: "DashboardData",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create mobile-optimized dashboard.
    
    Single column layout, optimized for touch.
    """
    # Lazy imports to avoid circular dependencies
    from ..presence.presence_activity_cards import create_presence_card, create_activity_card
    from ..energy.energy_media_cards import create_energy_card, create_media_card
    from ..weather.weather_calendar_cards import create_weather_card, create_calendar_card
    
    config = config or {}
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "🏠 PilotSuite - Styx"),
        "cards": [
            # Overview (compact)
            {
                "type": "horizontal-stack",
                "cards": [
                    {
                        "type": "gauge",
                        "entity": "sensor.system_health_score",
                        "name": "System",
                        "min": 0,
                        "max": 100,
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.ai_home_copilot_mood",
                        "name": "Stimmung",
                        "icon": "mdi:emoticon",
                    },
                ],
            },
            
            # Presence
            create_presence_card(data.presence, {"title": "👥 Anwesenheit"}),
            
            # Activity
            create_activity_card(data.activity, {"title": "⚡ Aktivität"}),
            
            # Energy
            create_energy_card(data.energy, {"title": "⚡ Energie"}),
            
            # Media
            create_media_card(data.media, {"title": "📺 Media"}),
            
            # Weather
            create_weather_card(data.weather, {"title": "🌤️ Wetter"}),
            
            # Calendar
            create_calendar_card(data.calendar, {"title": "📅 Kalender"}),
        ],
    }


def dashboard_to_yaml(
    card_config: dict[str, Any],
    indent: int = 0,
) -> str:
    """Convert card config to YAML string."""
    import yaml
    
    class NoAliasDumper(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True
    
    return yaml.dump(card_config, Dumper=NoAliasDumper, allow_unicode=True, sort_keys=False)


__all__ = [
    "create_complete_dashboard",
    "create_mobile_dashboard",
    "dashboard_to_yaml",
]
