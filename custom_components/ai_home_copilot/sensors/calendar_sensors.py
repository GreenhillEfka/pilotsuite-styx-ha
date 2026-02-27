"""Calendar sensor for PilotSuite Neurons.

Sensor:
- CalendarLoadSensor: Calendar load (busyness) estimation
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class CalendarLoadSensor(CoordinatorEntity, SensorEntity):
    """Sensor for calendar load (busyness).
    
    Connected to:
    - calendar_context module for event data
    - Module Connector for calendar.load Neuron
    """
    
    _attr_name = "PilotSuite Calendar Load"
    _attr_unique_id = "ai_copilot_calendar_load"
    _attr_icon = "mdi:calendar-clock"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Calculate calendar load for today.
        
        Uses data from:
        1. Calendar entities state
        2. Calendar context module (if available)
        3. Module connector signals
        """
        calendar_states = self._hass.states.async_all("calendar")
        
        now = dt_util.now()
        calendar_count = len(calendar_states)
        event_count = 0
        meetings_today = 0
        is_weekend = now.weekday() >= 5
        
        # Try to get calendar context from module connector
        calendar_context_data = None
        try:
            from ..module_connector import get_module_connector
            entry_id = self.coordinator.config_entry.entry_id if hasattr(self.coordinator, 'config_entry') else "default"
            connector = await get_module_connector(self._hass, entry_id)
            calendar_context_data = connector.calendar_context.to_dict()
        except Exception:  # noqa: BLE001
            pass
        
        # Try to get calendar events via service
        try:
            for cal in calendar_states:
                # Count calendars that are "known" (available)
                if cal.state not in ("unknown", "unavailable"):
                    event_count += 1

                # Fetch today's events (best effort). We keep this bounded: if the
                # service fails or does not support return_response, we simply
                # degrade to a coarse load estimation.
                result = await self._hass.services.async_call(
                    "calendar",
                    "get_events",
                    {
                        "entity_id": cal.entity_id,
                        "start_date_time": now.isoformat(),
                        "end_date_time": (now + timedelta(days=1)).isoformat(),
                    },
                    blocking=True,
                    return_response=True,
                )
                if isinstance(result, dict) and cal.entity_id in result:
                    events = result[cal.entity_id].get("events", [])
                    if isinstance(events, list):
                        meetings_today += len(events)
        except Exception as err:
            _LOGGER.debug("Error fetching calendar events: %s", err)
        
        # Use data from calendar context if available
        if calendar_context_data:
            event_count = calendar_context_data.get("event_count", event_count)
            meetings_today = calendar_context_data.get("meetings_today", meetings_today)
            is_weekend = calendar_context_data.get("is_weekend", is_weekend)
            focus_weight = calendar_context_data.get("focus_weight", 0.0)
            social_weight = calendar_context_data.get("social_weight", 0.0)
            relax_weight = calendar_context_data.get("relax_weight", 0.0)
            has_conflicts = calendar_context_data.get("has_conflicts", False)
            next_meeting_in_minutes = calendar_context_data.get("next_meeting_in_minutes")
        else:
            focus_weight = 0.0
            social_weight = 0.0
            relax_weight = 0.0
            has_conflicts = False
            next_meeting_in_minutes = None
        
        # Classify load based on event count
        if meetings_today == 0:
            load = "free"
        elif meetings_today < 3:
            load = "light"
        elif meetings_today < 6:
            load = "moderate"
        else:
            load = "busy"
        
        # Adjust based on focus weight (meetings = more load)
        if focus_weight > 0.5:
            if load == "light":
                load = "moderate"
            elif load == "moderate":
                load = "busy"
        
        self._attr_native_value = load
        self._attr_extra_state_attributes = {
            "calendar_count": calendar_count,
            "event_count": event_count,
            "meetings_today": meetings_today,
            "hour": now.hour,
            "is_weekend": is_weekend,
            "focus_weight": focus_weight,
            "social_weight": social_weight,
            "relax_weight": relax_weight,
            "has_conflicts": has_conflicts,
            "next_meeting_in_minutes": next_meeting_in_minutes,
            "source": "calendar_context_module" if calendar_context_data else "calendar_entities",
        }
