"""Calendar Module — HA calendar entity integration for PilotSuite.

Reads events from HA calendar.* entities and provides:
- Today/upcoming events for LLM context
- Per-household-member calendars
- Event-aware proactive suggestions
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)

# HA calendar domains
CALENDAR_DOMAIN = "calendar"


class CalendarModule(CopilotModule):
    """Module integrating HA calendar entities with PilotSuite."""

    @property
    def name(self) -> str:
        return "calendar_module"

    @property
    def version(self) -> str:
        return "0.1.0"

    def __init__(self):
        self._hass: Optional[HomeAssistant] = None
        self._entry_id: Optional[str] = None
        self._calendar_entities: list[str] = []

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        self._hass = ctx.hass
        self._entry_id = ctx.entry_id

        # Discover calendar entities
        self._calendar_entities = self._discover_calendars()

        ctx.hass.data.setdefault("ai_home_copilot", {})
        ctx.hass.data["ai_home_copilot"].setdefault(ctx.entry_id, {})
        ctx.hass.data["ai_home_copilot"][ctx.entry_id]["calendar_module"] = self

        _LOGGER.info(
            "CalendarModule setup: %d calendars found: %s",
            len(self._calendar_entities),
            ", ".join(self._calendar_entities[:5]),
        )

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        entry_store = ctx.hass.data.get("ai_home_copilot", {}).get(ctx.entry_id, {})
        if isinstance(entry_store, dict):
            entry_store.pop("calendar_module", None)
        return True

    # ------------------------------------------------------------------
    # Calendar discovery
    # ------------------------------------------------------------------

    def _discover_calendars(self) -> list[str]:
        """Find all calendar.* entities in HA."""
        if not self._hass:
            return []
        return [
            state.entity_id
            for state in self._hass.states.async_all(CALENDAR_DOMAIN)
        ]

    def refresh_calendars(self) -> None:
        """Re-scan for calendar entities."""
        self._calendar_entities = self._discover_calendars()

    # ------------------------------------------------------------------
    # Event retrieval
    # ------------------------------------------------------------------

    async def async_get_events_today(self) -> list[dict[str, Any]]:
        """Get all events for today across all calendars."""
        if not self._hass:
            return []

        now = dt_util.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return await self._fetch_events(start, end)

    async def async_get_events_upcoming(self, days: int = 7) -> list[dict[str, Any]]:
        """Get upcoming events for the next N days."""
        if not self._hass:
            return []

        now = dt_util.now()
        end = now + timedelta(days=days)
        return await self._fetch_events(now, end)

    async def _fetch_events(
        self, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        """Fetch events from all calendar entities via HA service."""
        all_events: list[dict[str, Any]] = []

        for entity_id in self._calendar_entities:
            try:
                result = await self._hass.services.async_call(
                    "calendar",
                    "get_events",
                    {
                        "entity_id": entity_id,
                        "start_date_time": start.isoformat(),
                        "end_date_time": end.isoformat(),
                    },
                    blocking=True,
                    return_response=True,
                )
                if result and entity_id in result:
                    events = result[entity_id].get("events", [])
                    for ev in events:
                        ev["calendar_entity_id"] = entity_id
                        # Extract friendly calendar name
                        state = self._hass.states.get(entity_id)
                        ev["calendar_name"] = (
                            state.attributes.get("friendly_name", entity_id)
                            if state
                            else entity_id
                        )
                    all_events.extend(events)
            except Exception as exc:
                _LOGGER.debug("Failed to fetch events from %s: %s", entity_id, exc)

        # Sort by start time
        all_events.sort(key=lambda e: e.get("start", ""))
        return all_events

    # ------------------------------------------------------------------
    # Read API (sync — safe for sensors)
    # ------------------------------------------------------------------

    def get_calendar_count(self) -> int:
        return len(self._calendar_entities)

    def get_calendar_entities(self) -> list[str]:
        return list(self._calendar_entities)

    def get_summary(self) -> dict[str, Any]:
        """Structured summary for sensor attributes."""
        return {
            "calendar_count": len(self._calendar_entities),
            "calendars": self._calendar_entities[:10],
        }

    # ------------------------------------------------------------------
    # LLM Context
    # ------------------------------------------------------------------

    def get_context_for_llm(self) -> str:
        """Inject calendar info into LLM system prompt.

        Note: This is sync. For events we cache the last fetch or
        provide just the calendar list. Full event context is injected
        asynchronously by the Core addon's conversation pipeline.
        """
        if not self._calendar_entities:
            return ""
        names = []
        for eid in self._calendar_entities[:8]:
            state = self._hass.states.get(eid) if self._hass else None
            name = state.attributes.get("friendly_name", eid) if state else eid
            names.append(name)
        suffix = (
            f" (+{len(self._calendar_entities) - 8})"
            if len(self._calendar_entities) > 8
            else ""
        )
        return f"Kalender ({len(self._calendar_entities)}): {', '.join(names)}{suffix}"


def get_calendar_module(
    hass: HomeAssistant, entry_id: str
) -> Optional[CalendarModule]:
    """Return the CalendarModule instance for a config entry, or None."""
    data = hass.data.get("ai_home_copilot", {}).get(entry_id, {})
    return data.get("calendar_module")
