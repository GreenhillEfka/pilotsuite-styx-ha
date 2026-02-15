"""Weather and Calendar cards for comprehensive dashboard.

Cards:
- Weather Card: Current conditions, forecast
- Calendar Card: Meetings, day type, mood influences
"""
from __future__ import annotations

from typing import Any, Optional

# Try to import context types
try:
    from .weather_context import WeatherSnapshot
    from .calendar_context import CalendarContext
except ImportError:
    WeatherSnapshot = Any
    CalendarContext = Any


def create_weather_card(
    weather_data: Optional[Any],  # WeatherSnapshot | None
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create detailed Weather Card.
    
    Shows:
    - Current conditions
    - Temperature, humidity, UV
    - Sunrise/sunset
    - PV production forecast
    """
    config = config or {}
    
    if not weather_data:
        return {
            "type": "markdown",
            "content": "**Wetterdaten nicht verfügbar**",
        }
    
    # Weather icon mapping
    weather_icon_map = {
        "sunny": "mdi:weather-sunny",
        "cloudy": "mdi:weather-cloudy",
        "rainy": "mdi:weather-rainy",
        "stormy": "mdi:weather-lightning",
        "clear": "mdi:weather-night",
        "partly_cloudy": "mdi:weather-partly-cloudy",
    }
    
    condition = getattr(weather_data, 'condition', 'unknown')
    weather_icon = weather_icon_map.get(condition, "mdi:weather-cloudy")
    temp = getattr(weather_data, 'temperature_c', 0)
    
    cards = [
        {
            "type": "picture-entity",
            "entity": "weather.home",
            "name": f"{condition.title()} • {temp:.1f}°C",
            "camera_image": "camera.weather",
            "show_info": True,
            "tap_action": {
                "action": "navigate",
                "navigation_path": "/ai-home/weather",
            },
        },
        {
            "type": "grid",
            "columns": 3,
            "cards": [
                {
                    "type": "stat",
                    "name": "Luftfeuchtigkeit",
                    "value": f"{getattr(weather_data, 'humidity_percent', 0):.0f}",
                    "unit": "%",
                    "icon": "mdi:water-percent",
                },
                {
                    "type": "stat",
                    "name": "UV-Index",
                    "value": f"{getattr(weather_data, 'uv_index', 0):.1f}",
                    "icon": "mdi:sun-wireless",
                },
                {
                    "type": "stat",
                    "name": "PV Prognose",
                    "value": f"{getattr(weather_data, 'forecast_pv_production_kwh', 0):.1f}",
                    "unit": "kWh",
                    "icon": "mdi:solar-power",
                },
            ],
        },
        {
            "type": "entities",
            "entities": [
                {
                    "type": "section",
                    "label": f"🌅 Sonnenaufgang: {getattr(weather_data, 'sunrise', '--:--')}",
                },
                {
                    "type": "section",
                    "label": f"🌇 Sonnenuntergang: {getattr(weather_data, 'sunset', '--:--')}",
                },
            ],
        },
    ]
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "🌤️ Wetter"),
        "cards": cards,
    }


def create_calendar_card(
    calendar_data: Optional[Any],  # CalendarContext | None
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create detailed Calendar Card.
    
    Shows:
    - Current/upcoming meetings
    - Mood influences
    - Day type (weekend, vacation)
    - Conflicts
    """
    config = config or {}
    
    if not calendar_data:
        return {
            "type": "markdown",
            "content": "**Kalenderdaten nicht verfügbar**",
        }
    
    cards = []
    
    # Current meeting
    has_meeting_now = getattr(calendar_data, 'has_meeting_now', False)
    meeting_title = getattr(calendar_data, 'meeting_title', '')
    
    if has_meeting_now and meeting_title:
        cards.append({
            "type": "entity",
            "entity": "calendar.primary",
            "name": f"📅 Jetzt: {meeting_title}",
            "icon": "mdi:calendar-clock",
        })
    else:
        has_meeting_soon = getattr(calendar_data, 'has_meeting_soon', False)
        next_meeting = getattr(calendar_data, 'next_meeting_title', '')
        
        if has_meeting_soon and next_meeting:
            cards.append({
                "type": "entity",
                "entity": "calendar.primary",
                "name": f"📅 Bald: {next_meeting}",
                "icon": "mdi:calendar-alert",
            })
    
    # Day type indicators
    is_weekend = getattr(calendar_data, 'is_weekend', False)
    is_holiday = getattr(calendar_data, 'is_holiday', False)
    is_vacation = getattr(calendar_data, 'is_vacation', False)
    
    day_type_indicators = []
    if is_weekend:
        day_type_indicators.append({"label": "Wochenende", "color": "#9C27B0"})
    if is_holiday:
        day_type_indicators.append({"label": "Feiertag", "color": "#E91E63"})
    if is_vacation:
        day_type_indicators.append({"label": "Urlaub", "color": "#00BCD4"})
    
    if day_type_indicators:
        cards.append({
            "type": "entities",
            "entities": [
                {
                    "type": "section",
                    "label": f"🏷️ {' | '.join([d['label'] for d in day_type_indicators])}",
                },
            ],
        })
    
    # Mood weights
    focus = getattr(calendar_data, 'focus_weight', 0.0)
    social = getattr(calendar_data, 'social_weight', 0.0)
    relax = getattr(calendar_data, 'relax_weight', 0.0)
    alert = getattr(calendar_data, 'alert_weight', 0.0)
    
    cards.append({
        "type": "grid",
        "columns": 4,
        "cards": [
            {
                "type": "stat",
                "name": "Fokus",
                "value": f"{focus:.0%}",
                "icon": "mdi:target",
            },
            {
                "type": "stat",
                "name": "Sozial",
                "value": f"{social:.0%}",
                "icon": "mdi:account-group",
            },
            {
                "type": "stat",
                "name": "Entspannt",
                "value": f"{relax:.0%}",
                "icon": "mdi:sofa",
            },
            {
                "type": "stat",
                "name": "Alarm",
                "value": f"{alert:.0%}",
                "icon": "mdi:alert",
            },
        ],
    })
    
    # Conflicts
    has_conflicts = getattr(calendar_data, 'has_conflicts', False)
    conflict_count = getattr(calendar_data, 'conflict_count', 0)
    
    if has_conflicts and conflict_count:
        cards.append({
            "type": "markdown",
            "content": f"⚠️ **{conflict_count} Termin-Konflikte erkannt!**",
        })
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "📅 Kalender"),
        "cards": cards,
    }


__all__ = [
    "create_weather_card",
    "create_calendar_card",
]
