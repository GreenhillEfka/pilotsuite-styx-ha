"""
Comprehensive Dashboard Cards Module
=====================================

All-in-One Dashboard for AI Home CoPilot with:
- Dashboard Overview Card (Neuronen Status, Mood, Zones, System Health)
- Detailed Cards: Presence, Activity, Energy, Media, Weather, Calendar
- Interactive Elements (Clickable neurons, detail views, filters)
- Mobile Responsive (Grid layout, adaptive cards, dark/light mode)

Path: /config/.openclaw/workspace/ai_home_copilot_hacs_repo/custom_components/ai_home_copilot/dashboard_cards/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from homeassistant.core import HomeAssistant

from .energy_context import EnergySnapshot, EnergyAnomaly, EnergyShiftingOpportunity
from .weather_context import WeatherSnapshot, WeatherForecast, PVRecommendation
from .calendar_context import CalendarContext
from .media_context import MediaContextData

_LOGGER = logging.getLogger(__name__)

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class NeuronStatus:
    """Single neuron status."""
    name: str
    entity_id: str
    status: str  # "active", "inactive", "warning", "error"
    value: Any = None
    icon: str = "mdi:brain"
    last_update: datetime | None = None


@dataclass
class PresenceData:
    """Presence data for users."""
    users: dict[str, dict[str, Any]] = field(default_factory=dict)  # user_id -> {name, zone, status, last_seen}
    guest_count: int = 0
    total_presence: int = 0


@dataclass
class ActivityData:
    """Activity data for zones."""
    zones: dict[str, dict[str, Any]] = field(default_factory=dict)  # zone_id -> {activity_score, entities, last_activity}
    overall_activity: float = 0.0  # 0.0 - 1.0


@dataclass
class SystemHealthData:
    """System health data."""
    health_score: int = 100  # 0-100
    active_neurons: int = 0
    total_neurons: int = 0
    alerts: list[dict[str, Any]] = field(default_factory=list)
    last_reload: datetime | None = None


@dataclass
class DashboardData:
    """Complete dashboard data."""
    # Overview
    neurons: list[NeuronStatus] = field(default_factory=list)
    mood: dict[str, Any] = field(default_factory=dict)
    system_health: SystemHealthData = field(default_factory=SystemHealthData)
    
    # Detailed areas
    presence: PresenceData = field(default_factory=PresenceData)
    activity: ActivityData = field(default_factory=ActivityData)
    energy: EnergySnapshot | None = None
    media: MediaContextData | None = None
    weather: WeatherSnapshot | None = None
    calendar: CalendarContext | None = None
    
    # Meta
    last_update: datetime = field(default_factory=datetime.now)


# ============================================================================
# DASHBOARD OVERVIEW CARD
# ============================================================================

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


# ============================================================================
# PRESENCE CARD
# ============================================================================

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


# ============================================================================
# ACTIVITY CARD
# ============================================================================

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


# ============================================================================
# ENERGY CARD
# ============================================================================

def create_energy_card(
    energy_data: EnergySnapshot | None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create detailed Energy Card.
    
    Shows:
    - Current consumption/production
    - Peak power today
    - Anomalies detected
    - Shifting opportunities
    """
    config = config or {}
    
    if not energy_data:
        return {
            "type": "markdown",
            "content": "**Energiedaten nicht verfügbar**",
        }
    
    cards = [
        {
            "type": "grid",
            "columns": 2,
            "cards": [
                {
                    "type": "stat",
                    "name": "Verbrauch heute",
                    "value": f"{energy_data.total_consumption_today_kwh:.1f}",
                    "unit": "kWh",
                    "icon": "mdi:flash",
                },
                {
                    "type": "stat",
                    "name": "Produktion heute",
                    "value": f"{energy_data.total_production_today_kwh:.1f}",
                    "unit": "kWh",
                    "icon": "mdi:solar-panel",
                },
            ],
        },
        {
            "type": "grid",
            "columns": 2,
            "cards": [
                {
                    "type": "stat",
                    "name": "Aktuelle Leistung",
                    "value": f"{energy_data.current_power_watts:.0f}",
                    "unit": "W",
                    "icon": "mdi:lightning-bolt",
                },
                {
                    "type": "stat",
                    "name": "Spitzenleistung",
                    "value": f"{energy_data.peak_power_today_watts:.0f}",
                    "unit": "W",
                    "icon": "mdi:chart-line-variant",
                },
            ],
        },
    ]
    
    # Add anomalies if any
    if energy_data.anomalies_detected > 0:
        cards.append({
            "type": "entity",
            "entity": "sensor.energy_anomalies",
            "name": f"{energy_data.anomalies_detected} Anomalien erkannt",
            "icon": "mdi:alert",
        })
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "⚡ Energie"),
        "cards": cards,
    }


# ============================================================================
# MEDIA CARD
# ============================================================================

def create_media_card(
    media_data: MediaContextData | None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create detailed Media Card.
    
    Shows:
    - Currently playing music
    - Active TV/source
    - Room distribution
    """
    config = config or {}
    
    if not media_data:
        return {
            "type": "markdown",
            "content": "**Keine Media-Daten verfügbar**",
        }
    
    cards = []
    
    # Music status
    if media_data.music_active:
        cards.append({
            "type": "entity",
            "entity": media_data.music_primary_entity_id or "media_player.music",
            "name": f"🎵 {media_data.music_now_playing or 'Musik'}",
            "icon": "mdi:music",
            "secondary_info": media_data.music_primary_area,
        })
    else:
        cards.append({
            "type": "markdown",
            "content": "**🎵 Keine Musik aktiv**",
        })
    
    # TV status
    if media_data.tv_active:
        cards.append({
            "type": "entity",
            "entity": media_data.tv_primary_entity_id or "media_player.tv",
            "name": f"📺 {media_data.tv_source or 'TV'}",
            "icon": "mdi:television",
            "secondary_info": media_data.tv_primary_area,
        })
    
    # Summary stats
    cards.append({
        "type": "grid",
        "columns": 2,
        "cards": [
            {
                "type": "stat",
                "name": "Aktive Player",
                "value": str(media_data.music_active_count + media_data.tv_active_count),
                "icon": "mdi:play-circle",
            },
            {
                "type": "stat",
                "name": "Musik-Player",
                "value": str(media_data.music_active_count),
                "icon": "mdi:music-note",
            },
        ],
    })
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "📺 Media"),
        "cards": cards,
    }


# ============================================================================
# WEATHER CARD
# ============================================================================

def create_weather_card(
    weather_data: WeatherSnapshot | None,
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
    
    weather_icon = weather_icon_map.get(weather_data.condition, "mdi:weather-cloudy")
    
    cards = [
        {
            "type": "picture-entity",
            "entity": "weather.home",
            "name": f"{weather_data.condition.title()} • {weather_data.temperature_c:.1f}°C",
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
                    "value": f"{weather_data.humidity_percent:.0f}",
                    "unit": "%",
                    "icon": "mdi:water-percent",
                },
                {
                    "type": "stat",
                    "name": "UV-Index",
                    "value": f"{weather_data.uv_index:.1f}",
                    "icon": "mdi:sun-wireless",
                },
                {
                    "type": "stat",
                    "name": "PV Prognose",
                    "value": f"{weather_data.forecast_pv_production_kwh:.1f}",
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
                    "label": f"🌅 Sonnenaufgang: {weather_data.sunrise}",
                },
                {
                    "type": "section",
                    "label": f"🌇 Sonnenuntergang: {weather_data.sunset}",
                },
            ],
        },
    ]
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "🌤️ Wetter"),
        "cards": cards,
    }


# ============================================================================
# CALENDAR CARD
# ============================================================================

def create_calendar_card(
    calendar_data: CalendarContext | None,
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
    if calendar_data.has_meeting_now:
        cards.append({
            "type": "entity",
            "entity": "calendar.primary",
            "name": f"📅 Jetzt: {calendar_data.meeting_title}",
            "icon": "mdi:calendar-clock",
        })
    elif calendar_data.has_meeting_soon:
        cards.append({
            "type": "entity",
            "entity": "calendar.primary",
            "name": f"📅 Bald: {calendar_data.next_meeting_title}",
            "icon": "mdi:calendar-alert",
        })
    
    # Day type indicators
    day_type_indicators = []
    if calendar_data.is_weekend:
        day_type_indicators.append({"label": "Wochenende", "color": "#9C27B0"})
    if calendar_data.is_holiday:
        day_type_indicators.append({"label": "Feiertag", "color": "#E91E63"})
    if calendar_data.is_vacation:
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
    cards.append({
        "type": "grid",
        "columns": 4,
        "cards": [
            {
                "type": "stat",
                "name": "Fokus",
                "value": f"{calendar_data.focus_weight:.0%}",
                "icon": "mdi:target",
            },
            {
                "type": "stat",
                "name": "Sozial",
                "value": f"{calendar_data.social_weight:.0%}",
                "icon": "mdi:account-group",
            },
            {
                "type": "stat",
                "name": "Entspannt",
                "value": f"{calendar_data.relax_weight:.0%}",
                "icon": "mdi:sofa",
            },
            {
                "type": "stat",
                "name": "Alarm",
                "value": f"{calendar_data.alert_weight:.0%}",
                "icon": "mdi:alert",
            },
        ],
    })
    
    # Conflicts
    if calendar_data.has_conflicts:
        cards.append({
            "type": "markdown",
            "content": f"⚠️ **{calendar_data.conflict_count} Termin-Konflikte erkannt!**",
        })
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "📅 Kalender"),
        "cards": cards,
    }


# ============================================================================
# COMPLETE DASHBOARD (ALL-IN-ONE)
# ============================================================================

def create_complete_dashboard(
    data: DashboardData,
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
    config = config or {}
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "🏠 AI Home Copilot"),
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


# ============================================================================
# MOBILE RESPONSIVE DASHBOARD
# ============================================================================

def create_mobile_dashboard(
    data: DashboardData,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create mobile-optimized dashboard.
    
    Single column layout, optimized for touch.
    """
    config = config or {}
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "🏠 AI Home Copilot"),
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


# ============================================================================
# YAML EXPORT
# ============================================================================

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
