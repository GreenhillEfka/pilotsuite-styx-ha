"""Mobile Dashboard Cards for AI Home CoPilot.

Provides responsive, mobile-optimized dashboard cards:
- Quick Actions Card (compact actions for mobile)
- Mood Status Card (current mood with quick toggles)
- Entity Quick Access Card (favorite entities)
- Notification Badge Card (recent alerts)
- Calendar Today Card (today's events)
- Quick Search Card (entity/automation search)

Each card is designed for mobile-first with:
- Touch-friendly tap targets (min 44px)
- Compact layout for small screens
- Pull-to-refresh support via entity state
- Swipe actions for quick toggles
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_ON,
    STATE_OFF,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Mobile Card Data Structures
# =============================================================================

@dataclass
class MobileCard:
    """Base mobile card data."""
    card_id: str
    card_type: str
    title: str
    icon: str = ""
    order: int = 0
    enabled: bool = True


@dataclass
class QuickAction:
    """Quick action for mobile."""
    action_id: str
    label: str
    icon: str
    service: str
    service_data: Dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False


@dataclass
class FavoriteEntity:
    """Favorite entity for quick access."""
    entity_id: str
    friendly_name: str
    domain: str
    state: str
    icon: str


# =============================================================================
# Mobile Dashboard Sensor
# =============================================================================

class MobileDashboardSensor(SensorEntity):
    """Sensor providing mobile dashboard JSON data."""
    
    _attr_has_entity_name = True
    _attr_name = "Mobile Dashboard"
    _attr_unique_id = "mobile_dashboard"
    _attr_icon = "mdi:cellphone"
    _attr_entity_category = "diagnostic"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._config = entry.data or {}
    
    @property
    def native_value(self) -> str:
        """Return JSON string with all card data."""
        return json.dumps(self._get_dashboard_data())
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed card data."""
        return self._get_dashboard_data()
    
    def _get_dashboard_data(self) -> Dict[str, Any]:
        """Gather all mobile dashboard data."""
        
        # Get current mood
        mood_data = self._get_mood_data()
        
        # Get quick actions
        quick_actions = self._get_quick_actions()
        
        # Get favorite entities
        favorites = self._get_favorite_entities()
        
        # Get notifications
        notifications = self._get_notifications()
        
        # Get today's calendar
        calendar_today = self._get_calendar_today()
        
        # Get weather summary
        weather = self._get_weather()
        
        return {
            "version": "1.0",
            "last_update": dt_util.utcnow().isoformat(),
            "cards": {
                "mood": mood_data,
                "quick_actions": quick_actions,
                "favorites": favorites,
                "notifications": notifications,
                "calendar_today": calendar_today,
                "weather": weather,
            },
            "stats": {
                "total_entities": len(self._hass.states.async_all()),
                "lights_on": self._count_entities("light", STATE_ON),
                "lights_off": self._count_entities("light", STATE_OFF),
                "sensors_active": self._count_entities("sensor", "on"),
                "automations_enabled": self._count_automations_enabled(),
            }
        }
    
    def _get_mood_data(self) -> Dict[str, Any]:
        """Get current mood state."""
        mood_entity = self._hass.states.get("sensor.ai_copilot_mood")
        
        mood_icons = {
            "relax": "🧘",
            "focus": "💻",
            "active": "🏃",
            "sleep": "😴",
            "away": "🏠",
            "alert": "⚠️",
            "social": "🎉",
            "recovery": "🌿",
            "unknown": "🤖",
        }
        
        if mood_entity:
            mood = mood_entity.state
            return {
                "mood": mood,
                "icon": mood_icons.get(mood, "🤖"),
                "confidence": mood_entity.attributes.get("confidence", 0.0),
                "contributors": mood_entity.attributes.get("contributors", []),
            }
        
        return {
            "mood": "unknown",
            "icon": "🤖",
            "confidence": 0.0,
            "contributors": [],
        }
    
    def _get_quick_actions(self) -> List[Dict[str, Any]]:
        """Get configured quick actions."""
        # Default quick actions
        actions = [
            {
                "id": "all_lights_off",
                "label": "Lichter aus",
                "icon": "mdi:lightbulb-off",
                "service": "light.turn_off",
                "entity_id": "all",
            },
            {
                "id": "all_lights_on",
                "label": "Lichter an",
                "icon": "mdi:lightbulb-on",
                "service": "light.turn_on",
                "entity_id": "all",
            },
            {
                "id": "lock_all",
                "label": "Alles verriegeln",
                "icon": "mdi:lock",
                "service": "lock.lock",
                "entity_id": "all",
            },
            {
                "id": "scene_evening",
                "label": "Abendmodus",
                "icon": "mdi:weather-sunset",
                "service": "scene.turn_on",
                "entity_id": "scene.abendmodus",
            },
            {
                "id": "scene_morning",
                "label": " Morgenmodus",
                "icon": "mdi:weather-sunrise",
                "service": "scene.turn_on",
                "entity_id": "scene.morgenmodus",
            },
            {
                "id": "media_stop",
                "label": "Musik stopp",
                "icon": "mdi:music-off",
                "service": "media_player.media_stop",
                "entity_id": "all",
            },
        ]
        
        # Add custom actions from config
        custom_actions = self._config.get("quick_actions", [])
        if custom_actions:
            actions = custom_actions + actions
        
        return actions[:8]  # Limit to 8 actions
    
    def _get_favorite_entities(self) -> List[Dict[str, Any]]:
        """Get favorite entities for quick access."""
        
        # Default favorite domains
        favorite_domains = ["light", "switch", "climate", "media_player", "lock"]
        
        favorites = []
        seen_entities = set()
        
        for domain in favorite_domains:
            # Get entities for this domain
            domain_entities = [
                state for state in self._hass.states.async_all()
                if state.entity_id.startswith(f"{domain}.")
                and state.entity_id not in seen_entities
            ]
            
            # Sort by friendly name
            domain_entities.sort(
                key=lambda s: s.attributes.get("friendly_name", s.entity_id)
            )
            
            # Add first few
            for state in domain_entities[:3]:
                seen_entities.add(state.entity_id)
                
                is_on = state.state == STATE_ON
                
                favorites.append({
                    "entity_id": state.entity_id,
                    "friendly_name": state.attributes.get("friendly_name", state.entity_id),
                    "domain": domain,
                    "state": state.state,
                    "icon": self._get_entity_icon(domain, is_on),
                    "is_on": is_on,
                })
        
        return favorites[:10]  # Limit to 10 favorites
    
    def _get_notifications(self) -> List[Dict[str, Any]]:
        """Get recent notifications."""
        
        notifications = []
        
        # Check for alert sensors
        alert_entities = [
            state for state in self._hass.states.async_all()
            if "alert" in state.entity_id or state.attributes.get("device_class") == "problem"
        ]
        
        for state in alert_entities[:5]:
            if state.state not in ("ok", "clear", "normal"):
                notifications.append({
                    "entity_id": state.entity_id,
                    "title": state.attributes.get("friendly_name", state.entity_id),
                    "message": state.state,
                    "icon": "mdi:alert",
                    "severity": "warning",
                })
        
        return notifications
    
    def _get_calendar_today(self) -> Dict[str, Any]:
        """Get today's calendar events."""
        
        now = dt_util.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day.replace(hour=23, minute=59, second=59)
        
        events = []
        
        # Get calendar entities
        calendar_entities = [
            state.entity_id for state in self._hass.states.async_all()
            if state.entity_id.startswith("calendar.")
        ]
        
        # Fetch events (simplified - in production would use calendar service)
        for cal_entity in calendar_entities[:3]:
            state = self._hass.states.get(cal_entity)
            if state and state.attributes.get("events"):
                for event in state.attributes.get("events", [])[:2]:
                    events.append({
                        "title": event.get("summary", "Termin"),
                        "start": event.get("start", {}).get("dateTime", ""),
                        "end": event.get("end", {}).get("dateTime", ""),
                        "all_day": event.get("all_day", False),
                    })
        
        return {
            "events": events[:4],
            "event_count": len(events),
            "is_weekend": now.weekday() >= 5,
        }
    
    def _get_weather(self) -> Dict[str, Any]:
        """Get weather summary."""
        
        weather_entities = [
            state for state in self._hass.states.async_all()
            if state.entity_id.startswith("weather.")
        ]
        
        if not weather_entities:
            return {"available": False}
        
        # Use first weather entity
        weather = weather_entities[0]
        
        return {
            "available": True,
            "entity_id": weather.entity_id,
            "condition": weather.state,
            "temperature": weather.attributes.get("temperature"),
            "humidity": weather.attributes.get("humidity"),
            "forecast": weather.attributes.get("forecast", [])[:2],
        }
    
    def _count_entities(self, domain: str, state: str) -> int:
        """Count entities by domain and state."""
        return sum(
            1 for s in self._hass.states.async_all()
            if s.entity_id.startswith(f"{domain}.") and s.state == state
        )
    
    def _count_automations_enabled(self) -> int:
        """Count enabled automations."""
        return sum(
            1 for s in self._hass.states.async_all()
            if s.entity_id.startswith("automation.")
            and s.state == "on"
        )
    
    def _get_entity_icon(self, domain: str, is_on: bool = False) -> str:
        """Get icon for entity."""
        icons = {
            "light": "mdi:lightbulb-on" if is_on else "mdi:lightbulb",
            "switch": "mdi:toggle-switch" if is_on else "mdi:toggle-switch-off",
            "climate": "mdi:thermostat",
            "media_player": "mdi:play-circle" if is_on else "mdi:pause-circle",
            "lock": "mdi:lock-open" if is_on else "mdi:lock",
            "fan": "mdi:fan" if is_on else "mdi:fan-off",
            "cover": "mdi:blinds-open" if is_on else "mdi:blinds",
        }
        return icons.get(domain, "mdi:circle")


# =============================================================================
# Mobile Quick Actions Sensor
# =============================================================================

class MobileQuickActionsSensor(SensorEntity):
    """Sensor for mobile quick actions JSON."""
    
    _attr_has_entity_name = True
    _attr_name = "Mobile Quick Actions"
    _attr_unique_id = "mobile_quick_actions"
    _attr_icon = "mdi:gesture-tap"
    _attr_entity_category = "diagnostic"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def native_value(self) -> str:
        """Return JSON string of quick actions."""
        return json.dumps(self._get_actions())
    
    def _get_actions(self) -> List[Dict[str, Any]]:
        """Get quick action buttons."""
        
        actions = [
            {
                "id": "toggle_lights",
                "label": "Lichter",
                "icon": "mdi:lightbulb-group",
                "action": "toggle_lights",
                "color": "amber",
            },
            {
                "id": "scene_evening",
                "label": "Abend",
                "icon": "mdi:weather-sunset",
                "action": "activate_scene",
                "target": "scene.abendmodus",
                "color": "deep-orange",
            },
            {
                "id": "lock_all",
                "label": "Verriegeln",
                "icon": "mdi:lock",
                "action": "lock_all",
                "color": "blue-grey",
            },
            {
                "id": "media_toggle",
                "label": "Musik",
                "icon": "mdi:music",
                "action": "toggle_media",
                "color": "purple",
            },
            {
                "id": "climate_adjust",
                "label": "Klima",
                "icon": "mdi:thermostat",
                "action": "adjust_climate",
                "color": "teal",
            },
            {
                "id": "camera_door",
                "label": "Tür",
                "icon": "mdi:door",
                "action": "show_camera",
                "target": "camera.haustur",
                "color": "brown",
            },
        ]
        
        return actions


# =============================================================================
# Mobile Entity Grid Sensor
# =============================================================================

class MobileEntityGridSensor(SensorEntity):
    """Sensor for mobile entity grid."""
    
    _attr_has_entity_name = True
    _attr_name = "Mobile Entity Grid"
    _attr_unique_id = "mobile_entity_grid"
    _attr_icon = "mdi:view-grid"
    _attr_entity_category = "diagnostic"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def native_value(self) -> str:
        """Return JSON string of entity grid."""
        return json.dumps(self._get_grid())
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._get_grid()
    
    def _get_grid(self) -> Dict[str, Any]:
        """Get entity grid for mobile."""
        
        # Group entities by room/area
        rooms: Dict[str, List[Dict[str, Any]]] = {}
        
        for state in self._hass.states.async_all():
            # Only include toggleable entities
            if not any(state.entity_id.startswith(d) for d in ["light.", "switch.", "fan.", "cover.", "lock."]):
                continue
            
            area_id = state.attributes.get("area_id") or "unknown"
            domain = state.entity_id.split(".")[0]
            
            if area_id not in rooms:
                rooms[area_id] = []
            
            rooms[area_id].append({
                "entity_id": state.entity_id,
                "friendly_name": state.attributes.get("friendly_name", state.entity_id),
                "domain": domain,
                "state": state.state,
                "is_on": state.state == STATE_ON,
            })
        
        # Convert to list format
        room_list = [
            {"area": area, "entities": entities}
            for area, entities in rooms.items()
        ]
        
        # Sort by entity count
        room_list.sort(key=lambda r: len(r["entities"]), reverse=True)
        
        return {
            "rooms": room_list[:6],  # Top 6 rooms
            "total_rooms": len(room_list),
        }


# =============================================================================
# Setup Functions
# =============================================================================

async def async_setup_mobile_dashboard(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Setup mobile dashboard sensors."""
    
    sensors = [
        MobileDashboardSensor(hass, entry),
        MobileQuickActionsSensor(hass, entry),
        MobileEntityGridSensor(hass, entry),
    ]
    
    async_add_entities(sensors)
    
    _LOGGER.info("Mobile dashboard sensors configured")


__all__ = [
    "async_setup_mobile_dashboard",
    "MobileDashboardSensor",
    "MobileQuickActionsSensor",
    "MobileEntityGridSensor",
]
