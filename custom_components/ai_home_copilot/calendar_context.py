"""Calendar Context Neuron - Kalender-basierter Kontext für Mood-Gewichtung.

Features:
- Meeting in 30min → Focus Mode
- Wochenende → Relax Priorität
- Gäste eingeladen → Social Mood
- Arbeitstag → Active/Focus
- Termin-Überschneidungen → Alert
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date, time
from typing import Any, Optional

from homeassistant.components.calendar import CalendarEvent
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .core.module import BaseModule

_LOGGER = logging.getLogger(__name__)

# Calendar event keywords for mood detection
FOCUS_KEYWORDS = [
    "meeting", "call", "besprechung", "anruf", "termin",
    "workshop", "präsentation", "presentation", "deadline",
    "focus", "arbeit", "work", "projekt", "project",
]

SOCIAL_KEYWORDS = [
    "geburtstag", "birthday", "party", "feier", "celebration",
    "gäste", "guests", "besuch", "visit", "dinner",
    "restaurant", "treffen", "meetup", "freund", "friend",
    "familie", "family",
]

RELAX_KEYWORDS = [
    "urlaub", "vacation", "frei", "day off", "wochenende",
    "weekend", "entspannung", "relax", "sport", "gym",
    "yoga", "meditation", "hobby",
]

ALERT_KEYWORDS = [
    "dringend", "urgent", "wichtig", "important", "asap",
    "deadline", "fällig", "due", "critical",
]

SLEEP_KEYWORDS = [
    "schlaf", "sleep", "bett", "bed", "ruhe", "rest",
]


@dataclass
class CalendarContext:
    """Context extracted from calendar events."""
    
    # Current state
    has_meeting_now: bool = False
    has_meeting_soon: bool = False  # within 30min
    meeting_title: str = ""
    meeting_start: datetime | None = None
    meeting_end: datetime | None = None
    
    # Upcoming
    next_meeting_title: str = ""
    next_meeting_start: datetime | None = None
    next_meeting_end: datetime | None = None
    
    # Day type
    is_weekend: bool = False
    is_holiday: bool = False
    is_vacation: bool = False
    
    # Mood influences
    focus_weight: float = 0.0
    social_weight: float = 0.0
    relax_weight: float = 0.0
    alert_weight: float = 0.0
    
    # Detected events
    focus_events: list[dict[str, Any]] = field(default_factory=list)
    social_events: list[dict[str, Any]] = field(default_factory=list)
    relax_events: list[dict[str, Any]] = field(default_factory=list)
    
    # Conflicts
    has_conflicts: bool = False
    conflict_count: int = 0
    
    # Raw events for reference
    all_events_today: list[dict[str, Any]] = field(default_factory=list)
    all_events_tomorrow: list[dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "has_meeting_now": self.has_meeting_now,
            "has_meeting_soon": self.has_meeting_soon,
            "meeting_title": self.meeting_title,
            "meeting_start": self.meeting_start.isoformat() if self.meeting_start else None,
            "meeting_end": self.meeting_end.isoformat() if self.meeting_end else None,
            "next_meeting_title": self.next_meeting_title,
            "next_meeting_start": self.next_meeting_start.isoformat() if self.next_meeting_start else None,
            "is_weekend": self.is_weekend,
            "is_holiday": self.is_holiday,
            "is_vacation": self.is_vacation,
            "focus_weight": self.focus_weight,
            "social_weight": self.social_weight,
            "relax_weight": self.relax_weight,
            "alert_weight": self.alert_weight,
            "focus_events_count": len(self.focus_events),
            "social_events_count": len(self.social_events),
            "relax_events_count": len(self.relax_events),
            "has_conflicts": self.has_conflicts,
            "conflict_count": self.conflict_count,
            "events_today_count": len(self.all_events_today),
            "events_tomorrow_count": len(self.all_events_tomorrow),
        }


class CalendarContextModule(BaseModule):
    """Module for extracting context from calendar events."""
    
    MODULE_NAME = "calendar_context"
    
    def __init__(self, hass: HomeAssistant, entry_id: str, config: dict[str, Any] = None):
        super().__init__(hass, entry_id, config or {})
        self._calendar_entities: list[str] = []
        self._lookahead_hours: int = 24
        self._meeting_soon_minutes: int = 30
        self._context = CalendarContext()
        self._update_interval = 300  # 5 minutes
        self._last_update: datetime | None = None
        
    @property
    def calendar_entities(self) -> list[str]:
        return self._calendar_entities
    
    @calendar_entities.setter
    def calendar_entities(self, entities: list[str]) -> None:
        self._calendar_entities = entities
    
    @property
    def context(self) -> CalendarContext:
        return self._context
    
    async def async_setup(self) -> None:
        """Setup calendar context module."""
        # Get calendar entities from config
        self._calendar_entities = self._config.get("calendar_entities", [])
        self._lookahead_hours = self._config.get("lookahead_hours", 24)
        self._meeting_soon_minutes = self._config.get("meeting_soon_minutes", 30)
        
        _LOGGER.info(
            "Calendar context module setup: %d calendars, %dh lookahead",
            len(self._calendar_entities),
            self._lookahead_hours,
        )
    
    async def async_update(self) -> CalendarContext:
        """Update calendar context and notify module connector."""
        now = dt_util.utcnow()
        
        # Check if we need to update
        if self._last_update and (now - self._last_update).total_seconds() < self._update_interval:
            return self._context
        
        self._context = CalendarContext()
        self._context.is_weekend = now.weekday() >= 5  # Saturday = 5, Sunday = 6
        
        # Fetch events from all calendars
        all_events = []
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=2)  # Today + tomorrow
        
        # Fire calendar updated event for module connector
        self._hass.bus.async_fire(
            f"{DOMAIN}_calendar_updated",
            {
                "load_level": self._get_load_level(),
                "event_count": len(all_events),
                "meetings_today": len(self._context.all_events_today),
                "is_weekend": self._context.is_weekend,
                "focus_weight": self._context.focus_weight,
                "social_weight": self._context.social_weight,
                "relax_weight": self._context.relax_weight,
                "has_conflicts": self._context.has_conflicts,
                "next_meeting_start": self._context.next_meeting_start.isoformat() if self._context.next_meeting_start else None,
            }
        )
        
        for calendar_entity in self._calendar_entities:
            try:
                events = await self._fetch_calendar_events(
                    calendar_entity,
                    start_of_day,
                    end_of_day,
                )
                all_events.extend(events)
            except Exception as err:
                _LOGGER.debug("Failed to fetch events from %s: %s", calendar_entity, err)
        
        # Categorize events
        self._categorize_events(all_events, now)
        
        # Detect conflicts
        self._detect_conflicts(all_events)
        
        # Compute mood weights
        self._compute_mood_weights(now)
        
        self._last_update = now
        return self._context
    
    async def _fetch_calendar_events(
        self,
        calendar_entity: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch events from a calendar entity."""
        
        # Try to use calendar integration
        try:
            state = self._hass.states.get(calendar_entity)
            if not state:
                return []
            
            # Get events via calendar service
            result = await self._hass.services.async_call(
                "calendar",
                "get_events",
                {
                    "entity_id": calendar_entity,
                    "start_date_time": start.isoformat(),
                    "end_date_time": end.isoformat(),
                },
                blocking=True,
                return_response=True,
            )
            
            events = []
            if isinstance(result, dict):
                for event_data in result.get(calendar_entity, {}).get("events", []):
                    events.append({
                        "summary": event_data.get("summary", ""),
                        "start": self._parse_datetime(event_data.get("start")),
                        "end": self._parse_datetime(event_data.get("end")),
                        "description": event_data.get("description", ""),
                        "location": event_data.get("location", ""),
                        "all_day": event_data.get("all_day", False),
                    })
            
            return events
            
        except Exception as err:
            _LOGGER.debug("Error fetching calendar events: %s", err)
            return []
    
    def _parse_datetime(self, dt_str: str | None) -> datetime | None:
        """Parse datetime string."""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    
    def _categorize_events(self, events: list[dict[str, Any]], now: datetime) -> None:
        """Categorize events by type and check current/upcoming status."""
        
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_tomorrow = start_of_today + timedelta(days=1)
        
        for event in events:
            start = event.get("start")
            end = event.get("end")
            summary = (event.get("summary") or "").lower()
            description = (event.get("description") or "").lower()
            
            # Determine which day
            if start:
                if start >= start_of_today and start < start_of_tomorrow:
                    self._context.all_events_today.append(event)
                elif start >= start_of_tomorrow:
                    self._context.all_events_tomorrow.append(event)
            
            # Check if meeting is now or soon
            if start and end:
                # Meeting now?
                if start <= now <= end:
                    self._context.has_meeting_now = True
                    self._context.meeting_title = event.get("summary", "")
                    self._context.meeting_start = start
                    self._context.meeting_end = end
                
                # Meeting soon?
                time_until = (start - now).total_seconds() / 60  # minutes
                if 0 < time_until <= self._meeting_soon_minutes:
                    self._context.has_meeting_soon = True
                    if not self._context.next_meeting_start or start < self._context.next_meeting_start:
                        self._context.next_meeting_title = event.get("summary", "")
                        self._context.next_meeting_start = start
                        self._context.next_meeting_end = end
            
            # Categorize by keywords
            text = f"{summary} {description}"
            
            if any(kw in text for kw in FOCUS_KEYWORDS):
                self._context.focus_events.append(event)
            
            if any(kw in text for kw in SOCIAL_KEYWORDS):
                self._context.social_events.append(event)
            
            if any(kw in text for kw in RELAX_KEYWORDS):
                self._context.relax_events.append(event)
            
            if any(kw in text for kw in ALERT_KEYWORDS):
                self._context.alert_weight = max(self._context.alert_weight, 0.8)
            
            # Check for vacation
            if "urlaub" in text or "vacation" in text:
                self._context.is_vacation = True
    
    def _detect_conflicts(self, events: list[dict[str, Any]]) -> None:
        """Detect overlapping events."""
        
        sorted_events = sorted(
            [e for e in events if e.get("start") and e.get("end")],
            key=lambda e: e.get("start"),
        )
        
        conflicts = 0
        for i, event1 in enumerate(sorted_events[:-1]):
            for event2 in sorted_events[i + 1:]:
                # Check overlap
                start1, end1 = event1.get("start"), event1.get("end")
                start2, end2 = event2.get("start"), event2.get("end")
                
                if start1 and end1 and start2 and end2:
                    if start1 < end2 and start2 < end1:
                        conflicts += 1
        
        self._context.has_conflicts = conflicts > 0
        self._context.conflict_count = conflicts
    
    def _compute_mood_weights(self, now: datetime) -> None:
        """Compute mood weights based on calendar context."""
        
        # Base weights
        focus = 0.0
        social = 0.0
        relax = 0.0
        alert = self._context.alert_weight
        
        # Weekend = more relax
        if self._context.is_weekend:
            relax += 0.3
        else:
            focus += 0.2
        
        # Vacation = more relax
        if self._context.is_vacation:
            relax += 0.5
            focus -= 0.2
        
        # Meeting now = focus
        if self._context.has_meeting_now:
            focus += 0.4
            relax -= 0.1
        
        # Meeting soon = prepare for focus
        if self._context.has_meeting_soon:
            focus += 0.3
        
        # Social events = social mood
        if self._context.social_events:
            social = min(0.7, 0.2 * len(self._context.social_events))
        
        # Focus events = focus mood
        if self._context.focus_events:
            focus = min(0.8, 0.15 * len(self._context.focus_events) + focus)
        
        # Relax events = relax mood
        if self._context.relax_events:
            relax = min(0.8, 0.2 * len(self._context.relax_events) + relax)
        
        # Conflicts = alert
        if self._context.has_conflicts:
            alert = max(alert, 0.3 + 0.1 * self._context.conflict_count)
        
        # Time of day adjustments
        hour = now.hour
        if 6 <= hour < 9:  # Morning
            focus += 0.1
        elif 12 <= hour < 14:  # Lunch
            relax += 0.1
        elif 17 <= hour < 20:  # Evening
            relax += 0.2
            focus -= 0.1
        elif 21 <= hour or hour < 6:  # Night
            relax += 0.3
            focus -= 0.2
        
        # Clamp and normalize
        self._context.focus_weight = max(0.0, min(1.0, focus))
        self._context.social_weight = max(0.0, min(1.0, social))
        self._context.relax_weight = max(0.0, min(1.0, relax))
        self._context.alert_weight = max(0.0, min(1.0, alert))
    
    def _get_load_level(self) -> str:
        """Get calendar load level based on event count.
        
        Returns:
            - free: no events today
            - light: 1-2 events
            - moderate: 3-5 events
            - busy: 6+ events
        """
        event_count = len(self._context.all_events_today)
        
        if event_count == 0:
            return "free"
        elif event_count < 3:
            return "light"
        elif event_count < 6:
            return "moderate"
        else:
            return "busy"


class CalendarContextEntity(Entity):
    """Entity exposing calendar context."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar"
    
    def __init__(self, entry_id: str, module: CalendarContextModule) -> None:
        self._entry_id = entry_id
        self._module = module
        self._attr_unique_id = f"{entry_id}_calendar_context"
        self._attr_name = "CoPilot Calendar Context"
    
    @property
    def native_value(self) -> str:
        ctx = self._module.context
        if ctx.has_meeting_now:
            return "meeting"
        elif ctx.has_meeting_soon:
            return "meeting_soon"
        elif ctx.is_vacation:
            return "vacation"
        elif ctx.is_weekend:
            return "weekend"
        return "available"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._module.context.to_dict()


async def async_setup_calendar_context(
    hass: HomeAssistant,
    entry_id: str,
    config: dict[str, Any],
    async_add_entities: AddEntitiesCallback,
) -> CalendarContextModule:
    """Setup calendar context module and entity."""
    
    module = CalendarContextModule(hass, entry_id, config)
    await module.async_setup()
    
    entity = CalendarContextEntity(entry_id, module)
    async_add_entities([entity])
    
    # Store module for updates
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry_id, {})
    hass.data[DOMAIN][entry_id]["calendar_context_module"] = module
    
    return module


async def async_update_calendar_context(hass: HomeAssistant, entry_id: str) -> CalendarContext:
    """Update calendar context and return it."""
    module = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("calendar_context_module")
    if module:
        return await module.async_update()
    return CalendarContext()