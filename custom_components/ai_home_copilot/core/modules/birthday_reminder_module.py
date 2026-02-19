"""Birthday Reminder Module - AI Home CoPilot

Scans HA calendar entities for birthday events and provides:
- Daily morning TTS announcements for today's birthdays
- Upcoming birthday list (next 14 days)
- Context injection for LLM conversations
- Persistent notifications

Integrates with the existing calendar_context module for mood weighting
(social events boost social mood weight).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)

# Keywords that indicate a birthday event
BIRTHDAY_KEYWORDS = [
    "geburtstag", "birthday", "geb.", "geb ",
    "b-day", "bday", "geboren",
]

# Age pattern: "Max (30)" or "Max wird 30" or "Max - 30. Geburtstag"
AGE_PATTERNS = [
    re.compile(r"\((\d{1,3})\)"),
    re.compile(r"wird\s+(\d{1,3})"),
    re.compile(r"(\d{1,3})\.\s*(?:geburtstag|birthday)", re.IGNORECASE),
]


def _extract_name_and_age(summary: str) -> tuple[str, Optional[int]]:
    """Extract person name and optional age from event summary."""
    age = None
    name = summary

    for pattern in AGE_PATTERNS:
        match = pattern.search(summary)
        if match:
            age = int(match.group(1))
            # Remove the age part from name
            name = pattern.sub("", summary).strip()
            break

    # Clean up name: remove birthday keywords
    for kw in BIRTHDAY_KEYWORDS:
        name = re.sub(re.escape(kw), "", name, flags=re.IGNORECASE).strip()

    # Remove common separators
    name = name.strip(" -:,.'s")

    return name if name else summary, age


@dataclass
class Birthday:
    """A detected birthday."""
    name: str
    date: datetime
    age: Optional[int] = None
    days_until: int = 0
    calendar_entity: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "date": self.date.strftime("%Y-%m-%d"),
            "age": self.age,
            "days_until": self.days_until,
            "calendar_entity": self.calendar_entity,
        }


@dataclass
class BirthdayReminderState:
    """State for the birthday reminder module."""
    today_birthdays: list[Birthday] = field(default_factory=list)
    upcoming_birthdays: list[Birthday] = field(default_factory=list)
    last_scan: Optional[datetime] = None
    last_reminder_date: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "today": [b.to_dict() for b in self.today_birthdays],
            "upcoming": [b.to_dict() for b in self.upcoming_birthdays],
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "today_count": len(self.today_birthdays),
            "upcoming_count": len(self.upcoming_birthdays),
        }


class BirthdayReminderModule(CopilotModule):
    """Birthday reminder module.

    Scans calendar entities for birthday events, generates morning
    TTS announcements, and provides context for LLM conversations.
    """

    @property
    def name(self) -> str:
        return "birthday_reminder"

    @property
    def version(self) -> str:
        return "0.1.0"

    def __init__(self):
        self._state = BirthdayReminderState()
        self._hass: Optional[HomeAssistant] = None
        self._entry_id: Optional[str] = None
        self._unsub_callbacks: list = []
        self._calendar_entities: list[str] = []
        self._lookahead_days: int = 14
        self._tts_enabled: bool = True
        self._tts_entity: str = ""
        self._reminder_hour: int = 8
        self._api_client = None

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the birthday reminder module."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry_id

        config = ctx.entry.options or ctx.entry.data

        # Enable-flag guard
        from ...const import CONF_BIRTHDAY_ENABLED, DEFAULT_BIRTHDAY_ENABLED
        if not config.get(CONF_BIRTHDAY_ENABLED, DEFAULT_BIRTHDAY_ENABLED):
            _LOGGER.debug("BirthdayReminder module disabled in config, skipping setup")
            return

        from ...const import (
            CONF_BIRTHDAY_CALENDAR_ENTITIES,
            CONF_BIRTHDAY_LOOKAHEAD_DAYS,
            CONF_BIRTHDAY_TTS_ENABLED,
            CONF_BIRTHDAY_TTS_ENTITY,
            CONF_BIRTHDAY_REMINDER_HOUR,
            DEFAULT_BIRTHDAY_CALENDAR_ENTITIES,
            DEFAULT_BIRTHDAY_LOOKAHEAD_DAYS,
            DEFAULT_BIRTHDAY_TTS_ENABLED,
            DEFAULT_BIRTHDAY_TTS_ENTITY,
            DEFAULT_BIRTHDAY_REMINDER_HOUR,
        )

        raw = config.get(CONF_BIRTHDAY_CALENDAR_ENTITIES, DEFAULT_BIRTHDAY_CALENDAR_ENTITIES)
        if isinstance(raw, str):
            self._calendar_entities = [e.strip() for e in raw.split(",") if e.strip()]
        elif isinstance(raw, list):
            self._calendar_entities = list(raw)
        else:
            self._calendar_entities = []

        self._lookahead_days = config.get(
            CONF_BIRTHDAY_LOOKAHEAD_DAYS, DEFAULT_BIRTHDAY_LOOKAHEAD_DAYS
        )
        self._tts_enabled = config.get(CONF_BIRTHDAY_TTS_ENABLED, DEFAULT_BIRTHDAY_TTS_ENABLED)
        self._tts_entity = config.get(CONF_BIRTHDAY_TTS_ENTITY, DEFAULT_BIRTHDAY_TTS_ENTITY)
        self._reminder_hour = config.get(
            CONF_BIRTHDAY_REMINDER_HOUR, DEFAULT_BIRTHDAY_REMINDER_HOUR
        )

        _LOGGER.info(
            "Setting up BirthdayReminder module v%s: %d calendars, lookahead=%d days",
            self.version,
            len(self._calendar_entities),
            self._lookahead_days,
        )

        # Store state
        ctx.hass.data.setdefault("ai_home_copilot", {})
        ctx.hass.data["ai_home_copilot"].setdefault(ctx.entry_id, {})
        ctx.hass.data["ai_home_copilot"][ctx.entry_id]["birthday_reminder"] = self

        # Get API client
        entry_store = ctx.hass.data.get("ai_home_copilot", {}).get(ctx.entry_id, {})
        coord = entry_store.get("coordinator") if isinstance(entry_store, dict) else None
        self._api_client = getattr(coord, "api", None) if coord else None

        # Auto-discover birthday calendars if none configured
        if not self._calendar_entities:
            self._calendar_entities = self._discover_birthday_calendars()

        # Initial scan
        await self._async_scan()

        # Schedule morning reminder
        unsub = async_track_time_change(
            ctx.hass,
            self._async_morning_reminder,
            hour=self._reminder_hour,
            minute=0,
            second=0,
        )
        self._unsub_callbacks.append(unsub)

        # Schedule daily rescan at midnight
        unsub = async_track_time_change(
            ctx.hass,
            self._async_daily_rescan,
            hour=0,
            minute=5,
            second=0,
        )
        self._unsub_callbacks.append(unsub)

        _LOGGER.info(
            "BirthdayReminder setup complete: %d calendars, reminder at %d:00",
            len(self._calendar_entities),
            self._reminder_hour,
        )

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        for unsub in self._unsub_callbacks:
            unsub()
        self._unsub_callbacks.clear()
        return True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_state(self) -> BirthdayReminderState:
        return self._state

    def get_context_for_llm(self) -> str:
        """Return a human-readable summary for LLM system prompt."""
        lines = []
        if self._state.today_birthdays:
            names = [
                f"{b.name}" + (f" ({b.age})" if b.age else "")
                for b in self._state.today_birthdays
            ]
            lines.append(f"Heute Geburtstag: {', '.join(names)}")

        upcoming = [b for b in self._state.upcoming_birthdays if b.days_until > 0]
        if upcoming:
            items = []
            for b in upcoming[:5]:
                entry = f"{b.name} in {b.days_until} Tagen"
                if b.age:
                    entry += f" (wird {b.age})"
                items.append(entry)
            lines.append(f"Bevorstehende Geburtstage: {', '.join(items)}")

        return "\n".join(lines) if lines else ""

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _discover_birthday_calendars(self) -> list[str]:
        """Auto-discover calendar entities that might contain birthdays."""
        if not self._hass:
            return []
        found = []
        for state in self._hass.states.async_all():
            eid = state.entity_id
            if not eid.startswith("calendar."):
                continue
            # Check for birthday-related calendar names
            name_lower = (state.name or eid).lower()
            if any(kw in name_lower for kw in ("geburtstag", "birthday", "kontakt", "contact")):
                found.append(eid)
        if found:
            _LOGGER.info("Auto-discovered %d birthday calendars: %s", len(found), found)
        return found

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    async def _async_scan(self) -> None:
        """Scan calendars for birthday events."""
        if not self._hass or not self._calendar_entities:
            return

        now = dt_util.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=self._lookahead_days)

        all_birthdays: list[Birthday] = []

        for cal_entity in self._calendar_entities:
            try:
                events = await self._fetch_events(cal_entity, start, end)
                for event in events:
                    birthday = self._parse_birthday_event(event, cal_entity, now)
                    if birthday:
                        all_birthdays.append(birthday)
            except Exception:
                _LOGGER.debug("Failed to fetch from %s", cal_entity, exc_info=True)

        # Sort by days_until
        all_birthdays.sort(key=lambda b: b.days_until)

        self._state.upcoming_birthdays = all_birthdays
        self._state.today_birthdays = [b for b in all_birthdays if b.days_until == 0]
        self._state.last_scan = now

    async def _fetch_events(
        self, calendar_entity: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        """Fetch events from a calendar entity."""
        try:
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
            if isinstance(result, dict):
                return result.get(calendar_entity, {}).get("events", [])
        except Exception:
            _LOGGER.debug("Error fetching calendar events", exc_info=True)
        return []

    def _parse_birthday_event(
        self, event: dict[str, Any], cal_entity: str, now: datetime
    ) -> Optional[Birthday]:
        """Parse a calendar event and return Birthday if it's a birthday."""
        summary = event.get("summary", "")
        description = event.get("description", "")
        text = f"{summary} {description}".lower()

        # Check if this is a birthday event
        if not any(kw in text for kw in BIRTHDAY_KEYWORDS):
            return None

        # Parse date
        start_str = event.get("start")
        if not start_str:
            return None

        try:
            if isinstance(start_str, str):
                # Could be date-only or datetime
                if "T" in start_str:
                    event_date = datetime.fromisoformat(
                        start_str.replace("Z", "+00:00")
                    )
                else:
                    event_date = datetime.strptime(start_str, "%Y-%m-%d")
                    event_date = event_date.replace(
                        tzinfo=now.tzinfo
                    ) if now.tzinfo else event_date
            else:
                return None
        except (ValueError, TypeError):
            return None

        name, age = _extract_name_and_age(summary)
        days_until = (event_date.date() - now.date()).days

        if days_until < 0:
            return None

        return Birthday(
            name=name,
            date=event_date,
            age=age,
            days_until=days_until,
            calendar_entity=cal_entity,
        )

    # ------------------------------------------------------------------
    # Reminders
    # ------------------------------------------------------------------

    async def _async_morning_reminder(self, now) -> None:
        """Fire morning birthday reminder."""
        await self._async_scan()

        if not self._state.today_birthdays:
            return

        today_str = dt_util.now().strftime("%Y-%m-%d")
        if self._state.last_reminder_date == today_str:
            return
        self._state.last_reminder_date = today_str

        names = []
        for b in self._state.today_birthdays:
            if b.age:
                names.append(f"{b.name} (wird {b.age})")
            else:
                names.append(b.name)

        if len(names) == 1:
            message = f"Heute hat {names[0]} Geburtstag! Herzlichen Glückwunsch!"
        else:
            message = f"Heute haben Geburtstag: {', '.join(names)}. Herzlichen Glückwunsch!"

        title = "Geburtstag heute"

        await self._deliver_reminder(title, message)

    async def _async_daily_rescan(self, now) -> None:
        """Daily rescan at midnight."""
        await self._async_scan()

    async def _deliver_reminder(self, title: str, message: str) -> None:
        """Deliver via persistent notification and TTS."""
        if not self._hass:
            return

        # Persistent notification
        try:
            await self._hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": title,
                    "message": message,
                    "notification_id": "birthday_reminder",
                },
                blocking=False,
            )
        except Exception:
            _LOGGER.debug("Failed to create birthday notification", exc_info=True)

        # TTS
        if self._tts_enabled and self._tts_entity:
            try:
                await self._hass.services.async_call(
                    "tts",
                    "speak",
                    {
                        "entity_id": self._tts_entity,
                        "message": message,
                    },
                    blocking=False,
                )
                _LOGGER.info("Birthday TTS sent to %s", self._tts_entity)
            except Exception:
                _LOGGER.debug("Birthday TTS failed", exc_info=True)

        _LOGGER.info("Birthday reminder: %s", message)


def get_birthday_reminder_module(hass, entry_id):
    """Return the BirthdayReminderModule instance for a config entry, or None."""
    data = hass.data.get("ai_home_copilot", {}).get(entry_id, {})
    return data.get("birthday_reminder")
