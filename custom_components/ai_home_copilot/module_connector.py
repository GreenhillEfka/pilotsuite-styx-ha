"""Module Connector - Verknüpft verschiedene Module miteinander.

Implementiert:
1. Camera → Activity Neuron: Camera Motion Events → activity.level Neuron
2. Calendar → calendar.load Neuron: Calendar Events → calendar.load neuron
3. Quick Search → Suggestions: Search results → automation suggestions
4. Notifications → Mood Alerts: Notification patterns → mood alerts

Diese Verbindungen ermöglichen die Kommunikation zwischen den verschiedenen
Modulen und Neuronen des PilotSuite Systems.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Signal names for inter-module communication
SIGNAL_ACTIVITY_UPDATED = f"{DOMAIN}_activity_updated"
SIGNAL_CALENDAR_LOAD_UPDATED = f"{DOMAIN}_calendar_load_updated"
SIGNAL_SUGGESTION_GENERATED = f"{DOMAIN}_suggestion_generated"
SIGNAL_MOOD_ALERT = f"{DOMAIN}_mood_alert"

# Notification priority levels
PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_NORMAL = "normal"
PRIORITY_LOW = "low"

# Mood alert types
MOOD_ALERT_FOCUS = "focus"
MOOD_ALERT_STRESS = "stress"
MOOD_ALERT_RELAX = "relax"
MOOD_ALERT_SOCIAL = "social"


@dataclass
class ActivityContext:
    """Context data from camera/activity events."""
    source: str  # camera_motion, presence, manual
    activity_level: str  # idle, low, moderate, high
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=dt_util.utcnow)
    room: str = ""
    camera_id: str = ""
    motion_detected: bool = False
    person_detected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "activity_level": self.activity_level,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "room": self.room,
            "camera_id": self.camera_id,
            "motion_detected": self.motion_detected,
            "person_detected": self.person_detected,
        }


@dataclass
class CalendarLoadContext:
    """Context data from calendar events."""
    load_level: str  # free, light, moderate, busy
    event_count: int = 0
    meetings_today: int = 0
    next_meeting_in_minutes: int | None = None
    is_weekend: bool = False
    is_holiday: bool = False
    focus_weight: float = 0.0
    social_weight: float = 0.0
    relax_weight: float = 0.0
    has_conflicts: bool = False
    timestamp: datetime = field(default_factory=dt_util.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "load_level": self.load_level,
            "event_count": self.event_count,
            "meetings_today": self.meetings_today,
            "next_meeting_in_minutes": self.next_meeting_in_minutes,
            "is_weekend": self.is_weekend,
            "is_holiday": self.is_holiday,
            "focus_weight": self.focus_weight,
            "social_weight": self.social_weight,
            "relax_weight": self.relax_weight,
            "has_conflicts": self.has_conflicts,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SuggestionContext:
    """Context for automation/entity suggestions."""
    query: str
    suggestion_type: str  # automation, entity, service
    candidates: list[dict[str, Any]] = field(default_factory=list)
    score: float = 0.0
    timestamp: datetime = field(default_factory=dt_util.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "suggestion_type": self.suggestion_type,
            "candidates": self.candidates,
            "score": self.score,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MoodAlert:
    """Mood alert from notification patterns."""
    alert_type: str  # focus, stress, relax, social
    severity: str  # low, normal, high, critical
    priority: str  # low, normal, high, critical
    source: str  # notification, calendar, manual
    message: str = ""
    factors: list[dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=dt_util.utcnow)
    auto_dismiss_after_minutes: int = 30

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "priority": self.priority,
            "source": self.source,
            "message": self.message,
            "factors": self.factors,
            "timestamp": self.timestamp.isoformat(),
            "auto_dismiss_after_minutes": self.auto_dismiss_after_minutes,
        }


class ModuleConnector:
    """Verbindet verschiedene Module miteinander."""
    
    def __init__(self, hass: HomeAssistant, entry_id: str):
        self._hass = hass
        self._entry_id = entry_id
        self._activity_context = ActivityContext(source="", activity_level="idle")
        self._calendar_context = CalendarLoadContext(load_level="free")
        self._recent_alerts: list[MoodAlert] = []
        self._enabled = True
    
    @property
    def activity_context(self) -> ActivityContext:
        return self._activity_context
    
    @property
    def calendar_context(self) -> CalendarLoadContext:
        return self._calendar_context
    
    @property
    def recent_alerts(self) -> list[MoodAlert]:
        return self._recent_alerts
    
    async def async_setup(self) -> bool:
        """Set up module connections."""
        _LOGGER.info("Setting up Module Connector")
        
        # Set up camera → activity listener
        await self._setup_camera_activity_link()
        
        # Set up calendar → load listener
        await self._setup_calendar_load_link()
        
        # Set up notification → mood alert listener
        await self._setup_notification_mood_link()
        
        _LOGGER.info("Module Connector initialized")
        return True
    
    async def _setup_camera_activity_link(self) -> None:
        """Verknüpft Camera Events mit Activity Neuron."""
        
        @callback
        async def on_camera_event(event: Event) -> None:
            """Handle camera events and update activity context."""
            event_data = event.data
            event_type = event_data.get("type", "")
            
            if event_type == "motion":
                await self._handle_motion_event(event_data)
            elif event_type == "presence":
                await self._handle_presence_event(event_data)
            elif event_type == "zone":
                await self._handle_zone_event(event_data)
        
        # Listen for camera events
        self._hass.bus.async_listen(f"{DOMAIN}_camera_event", on_camera_event)
        
        # Also listen for binary sensor motion events
        async def on_state_change(event: Event) -> None:
            entity_id = event.data.get("entity_id", "")
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            
            if not new_state:
                return
            
            # Check for motion binary sensors
            if "motion" in entity_id.lower() and "binary_sensor" in entity_id:
                is_motion = new_state.state == "on"
                camera_id = entity_id.replace("binary_sensor.", "camera.")
                
                await self._handle_motion_event({
                    "type": "motion",
                    "camera_id": camera_id,
                    "action": "started" if is_motion else "ended",
                    "confidence": new_state.attributes.get("confidence", 1.0),
                    "timestamp": datetime.now().isoformat(),
                })
        
        self._hass.bus.async_listen("state_changed", on_state_change)
        
        _LOGGER.debug("Camera → Activity link established")
    
    async def _handle_motion_event(self, event_data: dict[str, Any]) -> None:
        """Handle motion event and update activity context."""
        
        action = event_data.get("action", "")
        camera_id = event_data.get("camera_id", "")
        camera_name = event_data.get("camera_name", "")
        
        # Update activity based on motion
        if action == "started":
            self._activity_context = ActivityContext(
                source="camera_motion",
                activity_level="moderate",
                confidence=event_data.get("confidence", 1.0),
                camera_id=camera_id,
                motion_detected=True,
                room=camera_name,
            )
        else:
            # Motion ended - check if there's still other activity
            self._activity_context.activity_level = "low"
        
        # Fire event for activity neuron update
        self._hass.bus.async_fire(
            SIGNAL_ACTIVITY_UPDATED,
            self._activity_context.to_dict()
        )
        
        _LOGGER.debug("Camera Motion → Activity Neuron: %s", self._activity_context.activity_level)
    
    async def _handle_presence_event(self, event_data: dict[str, Any]) -> None:
        """Handle presence event and update presence context."""
        
        person_name = event_data.get("person_name", "")
        entity_id = event_data.get("entity_id", "")
        
        # Update activity context with presence
        self._activity_context.person_detected = True
        self._activity_context.activity_level = "moderate"
        
        # Fire event for presence neuron update
        self._hass.bus.async_fire(
            SIGNAL_ACTIVITY_UPDATED,
            {
                **self._activity_context.to_dict(),
                "presence_detected": True,
                "person_name": person_name,
            }
        )
        
        _LOGGER.debug("Camera Presence → Presence Neuron: %s detected", person_name)
    
    async def _handle_zone_event(self, event_data: dict[str, Any]) -> None:
        """Handle zone event for spatial context."""
        
        zone_name = event_data.get("zone_name", "")
        event_type = event_data.get("event_type", "")
        camera_id = event_data.get("camera_id", "")
        
        # Update spatial context
        self._activity_context.room = zone_name
        
        # Fire event for spatial context update
        self._hass.bus.async_fire(
            SIGNAL_ACTIVITY_UPDATED,
            {
                **self._activity_context.to_dict(),
                "spatial_context": True,
                "zone_name": zone_name,
                "zone_event": event_type,
            }
        )
        
        _LOGGER.debug("Camera Zone → Spatial Context: %s %s", zone_name, event_type)
    
    async def _setup_calendar_load_link(self) -> None:
        """Verknüpft Calendar Events mit calendar.load Neuron."""
        
        @callback
        async def on_calendar_update(event: Event) -> None:
            """Handle calendar context update."""
            event_data = event.data
            
            # Extract calendar context data
            load_level = event_data.get("load_level", "free")
            event_count = event_data.get("event_count", 0)
            meetings_today = event_data.get("meetings_today", 0)
            is_weekend = event_data.get("is_weekend", False)
            has_conflicts = event_data.get("has_conflicts", False)
            
            # Calculate next meeting time
            next_meeting_in_minutes = None
            next_start = event_data.get("next_meeting_start")
            if next_start:
                try:
                    next_dt = datetime.fromisoformat(next_start.replace("Z", "+00:00"))
                    now = dt_util.utcnow()
                    delta = (next_dt - now).total_seconds() / 60
                    next_meeting_in_minutes = int(delta)
                except (ValueError, TypeError):
                    pass
            
            # Update calendar context
            self._calendar_context = CalendarLoadContext(
                load_level=load_level,
                event_count=event_count,
                meetings_today=meetings_today,
                next_meeting_in_minutes=next_meeting_in_minutes,
                is_weekend=is_weekend,
                focus_weight=event_data.get("focus_weight", 0.0),
                social_weight=event_data.get("social_weight", 0.0),
                relax_weight=event_data.get("relax_weight", 0.0),
                has_conflicts=has_conflicts,
            )
            
            # Fire event for calendar load neuron update
            self._hass.bus.async_fire(
                SIGNAL_CALENDAR_LOAD_UPDATED,
                self._calendar_context.to_dict()
            )
            
            _LOGGER.debug("Calendar → calendar.load Neuron: %s (events: %d)", 
                         load_level, event_count)
        
        # Listen for calendar context updates from calendar_context module
        self._hass.bus.async_listen(f"{DOMAIN}_calendar_updated", on_calendar_update)
        
        # Also check for calendar state changes
        async def on_calendar_state_change(event: Event) -> None:
            entity_id = event.data.get("entity_id", "")
            new_state = event.data.get("new_state")
            
            if not entity_id.startswith("calendar."):
                return
            
            # Trigger calendar reload
            await self._refresh_calendar_context()
        
        self._hass.bus.async_listen("state_changed", on_calendar_state_change)
        
        _LOGGER.debug("Calendar → calendar.load link established")
    
    async def _refresh_calendar_context(self) -> None:
        """Refresh calendar context from calendar entities."""
        
        calendar_states = self._hass.states.async_all("calendar")
        now = dt_util.now()
        
        event_count = 0
        is_weekend = now.weekday() >= 5
        
        # Count events from all calendars
        for cal in calendar_states:
            if cal.state != "unknown":
                event_count += 1
        
        # Determine load level
        if event_count == 0:
            load_level = "free"
        elif event_count < 3:
            load_level = "light"
        elif event_count < 6:
            load_level = "moderate"
        else:
            load_level = "busy"
        
        # Update context
        self._calendar_context = CalendarLoadContext(
            load_level=load_level,
            event_count=event_count,
            meetings_today=event_count,
            is_weekend=is_weekend,
        )
        
        # Fire event
        self._hass.bus.async_fire(
            SIGNAL_CALENDAR_LOAD_UPDATED,
            self._calendar_context.to_dict()
        )
    
    async def _setup_notification_mood_link(self) -> None:
        """Verknüpft Notifications mit Mood Alerts."""
        
        @callback
        async def on_notification(event: Event) -> None:
            """Handle notification and generate mood alert."""
            event_data = event.data
            
            # Extract notification data
            title = event_data.get("title", "")
            message = event_data.get("message", "")
            priority = event_data.get("priority", PRIORITY_NORMAL)
            
            # Analyze notification for mood impact
            alert = self._analyze_notification_for_mood(title, message, priority)
            
            if alert:
                # Add to recent alerts
                self._recent_alerts.insert(0, alert)
                
                # Keep only recent alerts (last 10)
                if len(self._recent_alerts) > 10:
                    self._recent_alerts = self._recent_alerts[:10]
                
                # Fire mood alert event
                self._hass.bus.async_fire(
                    SIGNAL_MOOD_ALERT,
                    alert.to_dict()
                )
                
                _LOGGER.debug("Notification → Mood Alert: %s (%s)", 
                             alert.alert_type, alert.severity)
        
        # Listen for notifications
        self._hass.bus.async_listen("notify", on_notification)
        
        # Also listen for persistent notifications
        self._hass.bus.async_listen("call_service", on_notification)
        
        _LOGGER.debug("Notification → Mood Alert link established")
    
    def _analyze_notification_for_mood(
        self, 
        title: str, 
        message: str, 
        priority: str
    ) -> Optional[MoodAlert]:
        """Analyze notification and create mood alert if needed."""
        
        text = f"{title} {message}".lower()
        
        # Keywords that indicate different mood states
        focus_keywords = ["meeting", "deadline", "call", "besprechung", "termin"]
        stress_keywords = ["urgent", "dringend", "critical", "alert", "alarm", "warning"]
        social_keywords = ["party", "birthday", "geburtstag", "guests", "gäste"]
        relax_keywords = ["vacation", "urlaub", "weekend", "wochenende", "frei"]
        
        alert_type = None
        severity = "normal"
        
        # Determine alert type
        if any(kw in text for kw in stress_keywords):
            alert_type = MOOD_ALERT_STRESS
            severity = "high"
        elif any(kw in text for kw in focus_keywords):
            alert_type = MOOD_ALERT_FOCUS
            severity = "normal"
        elif any(kw in text for kw in social_keywords):
            alert_type = MOOD_ALERT_SOCIAL
            severity = "normal"
        elif any(kw in text for kw in relax_keywords):
            alert_type = MOOD_ALERT_RELAX
            severity = "low"
        
        # Adjust severity based on priority
        if priority == PRIORITY_CRITICAL:
            severity = "critical"
        elif priority == PRIORITY_HIGH:
            severity = "high"
        elif priority == PRIORITY_LOW:
            severity = "low"
        
        if not alert_type:
            return None
        
        return MoodAlert(
            alert_type=alert_type,
            severity=severity,
            priority=priority,
            source="notification",
            message=f"{title}: {message}" if message else title,
            factors=[
                {"keyword": alert_type, "weight": 0.5},
                {"priority": priority, "weight": 0.3},
            ]
        )
    
    async def generate_search_suggestions(
        self,
        query: str,
        search_results: list[dict[str, Any]]
    ) -> SuggestionContext:
        """Generate automation suggestions from search results."""
        
        suggestions = []
        
        for result in search_results:
            result_type = result.get("type", "")
            result_id = result.get("id", "")
            result_title = result.get("title", "")
            
            # Generate automation suggestions
            if result_type == "entity":
                # Suggest automations based on entity
                suggestions.append({
                    "type": "automation_suggestion",
                    "entity_id": result_id,
                    "entity_name": result_title,
                    "suggested_actions": [
                        f"Automatisierung erstellen für {result_title}",
                        f"Template erstellen für {result_id}",
                    ],
                    "score": result.get("score", 0.0) * 0.8,
                })
            
            elif result_type == "service":
                # Suggest services that might be useful
                suggestions.append({
                    "type": "service_suggestion",
                    "service_id": result_id,
                    "service_name": result_title,
                    "suggested_automations": [
                        f"Service {result_id} in Automation nutzen",
                    ],
                    "score": result.get("score", 0.0) * 0.6,
                })
        
        # Sort by score and take top 5
        suggestions.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        context = SuggestionContext(
            query=query,
            suggestion_type="automation",
            candidates=suggestions[:5],
            score=suggestions[0].get("score", 0.0) if suggestions else 0.0,
        )
        
        # Fire event for suggestion neuron update
        self._hass.bus.async_fire(
            SIGNAL_SUGGESTION_GENERATED,
            context.to_dict()
        )
        
        return context
    
    async def trigger_mood_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        factors: list[dict[str, Any]] | None = None
    ) -> MoodAlert:
        """Manually trigger a mood alert."""
        
        alert = MoodAlert(
            alert_type=alert_type,
            severity=severity,
            priority=severity,  # Use severity as priority
            source="manual",
            message=message,
            factors=factors or [],
        )
        
        # Add to recent alerts
        self._recent_alerts.insert(0, alert)
        
        # Keep only recent alerts
        if len(self._recent_alerts) > 10:
            self._recent_alerts = self._recent_alerts[:10]
        
        # Fire mood alert event
        self._hass.bus.async_fire(
            SIGNAL_MOOD_ALERT,
            alert.to_dict()
        )
        
        return alert
    
    async def get_current_activity(self) -> ActivityContext:
        """Get current activity context."""
        return self._activity_context
    
    async def get_current_calendar_load(self) -> CalendarLoadContext:
        """Get current calendar load context."""
        return self._calendar_context
    
    async def get_recent_alerts(self, minutes: int = 60) -> list[MoodAlert]:
        """Get recent mood alerts."""
        cutoff = dt_util.utcnow() - timedelta(minutes=minutes)
        return [a for a in self._recent_alerts if a.timestamp > cutoff]
    
    async def async_shutdown(self) -> None:
        """Clean up on shutdown."""
        _LOGGER.info("Shutting down Module Connector")
        self._enabled = False


async def get_module_connector(hass: HomeAssistant, entry_id: str) -> ModuleConnector:
    """Get or create module connector."""
    key = f"{DOMAIN}_module_connector_{entry_id}"
    
    if key not in hass.data:
        connector = ModuleConnector(hass, entry_id)
        await connector.async_setup()
        hass.data[key] = connector
    
    return hass.data[key]


__all__ = [
    "ModuleConnector",
    "get_module_connector",
    "SIGNAL_ACTIVITY_UPDATED",
    "SIGNAL_CALENDAR_LOAD_UPDATED",
    "SIGNAL_SUGGESTION_GENERATED",
    "SIGNAL_MOOD_ALERT",
    "ActivityContext",
    "CalendarLoadContext",
    "SuggestionContext",
    "MoodAlert",
]
