"""Waste Collection Reminder Module - AI Home CoPilot

Integrates with hacs_waste_collection_schedule to provide:
- Automated reminders (evening before + morning of collection)
- TTS announcements via proactive engine
- Persistent notifications in HA
- Context injection for LLM conversations
- Forwarding waste context to Core addon

Reads sensor entities created by waste_collection_schedule and tracks
the `daysTo` attribute to determine when reminders should fire.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from typing import Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util

from .module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)

# Waste type icons for TTS / notifications
WASTE_ICONS = {
    "restmüll": "🗑️",
    "restmuell": "🗑️",
    "residual": "🗑️",
    "biotonne": "🟤",
    "bio": "🟤",
    "organic": "🟤",
    "papier": "📦",
    "paper": "📦",
    "gelber sack": "🟡",
    "gelbe tonne": "🟡",
    "yellow": "🟡",
    "packaging": "🟡",
    "glas": "🫙",
    "glass": "🫙",
    "sperrmüll": "🚚",
    "sperrmuell": "🚚",
    "bulky": "🚚",
}

# German waste type display names
WASTE_NAMES_DE = {
    "restmüll": "Restmüll",
    "restmuell": "Restmüll",
    "biotonne": "Biotonne",
    "bio": "Biotonne",
    "papier": "Papier",
    "paper": "Papier",
    "gelber sack": "Gelber Sack",
    "gelbe tonne": "Gelbe Tonne",
    "glas": "Glas",
    "glass": "Glas",
    "sperrmüll": "Sperrmüll",
    "sperrmuell": "Sperrmüll",
}


def _get_icon(waste_type: str) -> str:
    """Get icon for a waste type."""
    lower = waste_type.lower()
    for key, icon in WASTE_ICONS.items():
        if key in lower:
            return icon
    return "♻️"


def _get_display_name(waste_type: str) -> str:
    """Get display name for a waste type."""
    lower = waste_type.lower()
    for key, name in WASTE_NAMES_DE.items():
        if key in lower:
            return name
    return waste_type


@dataclass
class WasteCollection:
    """Single waste collection entry."""
    waste_type: str
    entity_id: str
    days_to: int
    next_date: Optional[str] = None
    icon: str = ""

    def __post_init__(self):
        if not self.icon:
            self.icon = _get_icon(self.waste_type)


@dataclass
class WasteReminderState:
    """State for the waste reminder module."""
    collections: list[WasteCollection] = field(default_factory=list)
    next_collection: Optional[WasteCollection] = None
    tomorrow_collections: list[WasteCollection] = field(default_factory=list)
    today_collections: list[WasteCollection] = field(default_factory=list)
    last_scan: Optional[datetime] = None
    last_reminder_date: Optional[str] = None
    reminders_sent_today: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "collections": [
                {
                    "waste_type": c.waste_type,
                    "entity_id": c.entity_id,
                    "days_to": c.days_to,
                    "next_date": c.next_date,
                    "icon": c.icon,
                }
                for c in self.collections
            ],
            "next_collection": {
                "waste_type": self.next_collection.waste_type,
                "days_to": self.next_collection.days_to,
                "next_date": self.next_collection.next_date,
                "icon": self.next_collection.icon,
            } if self.next_collection else None,
            "tomorrow_types": [c.waste_type for c in self.tomorrow_collections],
            "today_types": [c.waste_type for c in self.today_collections],
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "reminders_sent_today": self.reminders_sent_today,
        }


class WasteReminderModule(CopilotModule):
    """Waste collection reminder module.

    Reads waste_collection_schedule sensors and:
    1. Tracks upcoming collections (daysTo attribute)
    2. Fires evening reminders (day before, configurable hour)
    3. Fires morning reminders (day of, configurable hour)
    4. Delivers via TTS + persistent notification
    5. Exposes context for LLM and Core addon
    """

    @property
    def name(self) -> str:
        return "waste_reminder"

    @property
    def version(self) -> str:
        return "0.1.0"

    def __init__(self):
        self._state = WasteReminderState()
        self._hass: Optional[HomeAssistant] = None
        self._entry_id: Optional[str] = None
        self._unsub_callbacks: list = []
        self._waste_entities: list[str] = []
        self._tts_enabled: bool = True
        self._tts_entity: str = ""
        self._reminder_evening_hour: int = 19
        self._reminder_morning_hour: int = 7
        self._api_client = None

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the waste reminder module."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry_id

        config = ctx.entry.options or ctx.entry.data

        # Enable-flag guard
        from ...const import CONF_WASTE_ENABLED, DEFAULT_WASTE_ENABLED
        if not config.get(CONF_WASTE_ENABLED, DEFAULT_WASTE_ENABLED):
            _LOGGER.debug("WasteReminder module disabled in config, skipping setup")
            return

        # Read config
        from ...const import (
            CONF_WASTE_ENTITIES,
            CONF_WASTE_TTS_ENABLED,
            CONF_WASTE_TTS_ENTITY,
            CONF_WASTE_REMINDER_EVENING_HOUR,
            CONF_WASTE_REMINDER_MORNING_HOUR,
            DEFAULT_WASTE_ENTITIES,
            DEFAULT_WASTE_TTS_ENABLED,
            DEFAULT_WASTE_TTS_ENTITY,
            DEFAULT_WASTE_REMINDER_EVENING_HOUR,
            DEFAULT_WASTE_REMINDER_MORNING_HOUR,
        )

        raw = config.get(CONF_WASTE_ENTITIES, DEFAULT_WASTE_ENTITIES)
        if isinstance(raw, str):
            self._waste_entities = [e.strip() for e in raw.split(",") if e.strip()]
        elif isinstance(raw, list):
            self._waste_entities = list(raw)
        else:
            self._waste_entities = []

        self._tts_enabled = config.get(CONF_WASTE_TTS_ENABLED, DEFAULT_WASTE_TTS_ENABLED)
        self._tts_entity = config.get(CONF_WASTE_TTS_ENTITY, DEFAULT_WASTE_TTS_ENTITY)
        self._reminder_evening_hour = config.get(
            CONF_WASTE_REMINDER_EVENING_HOUR, DEFAULT_WASTE_REMINDER_EVENING_HOUR
        )
        self._reminder_morning_hour = config.get(
            CONF_WASTE_REMINDER_MORNING_HOUR, DEFAULT_WASTE_REMINDER_MORNING_HOUR
        )

        _LOGGER.info(
            "Setting up WasteReminder module v%s: %d entities, TTS=%s",
            self.version,
            len(self._waste_entities),
            self._tts_enabled,
        )

        # Store state
        ctx.hass.data.setdefault("ai_home_copilot", {})
        ctx.hass.data["ai_home_copilot"].setdefault(ctx.entry_id, {})
        ctx.hass.data["ai_home_copilot"][ctx.entry_id]["waste_reminder"] = self

        # Get API client for Core forwarding
        entry_store = ctx.hass.data.get("ai_home_copilot", {}).get(ctx.entry_id, {})
        coord = entry_store.get("coordinator") if isinstance(entry_store, dict) else None
        self._api_client = getattr(coord, "api", None) if coord else None

        # Auto-discover waste sensors if none configured
        if not self._waste_entities:
            self._waste_entities = self._discover_waste_sensors()

        # Initial scan
        await self._async_scan()

        # Track state changes on waste sensors
        if self._waste_entities:
            unsub = async_track_state_change_event(
                ctx.hass,
                self._waste_entities,
                self._async_waste_state_changed,
            )
            self._unsub_callbacks.append(unsub)

        # Schedule evening reminder
        unsub = async_track_time_change(
            ctx.hass,
            self._async_evening_reminder,
            hour=self._reminder_evening_hour,
            minute=0,
            second=0,
        )
        self._unsub_callbacks.append(unsub)

        # Schedule morning reminder
        unsub = async_track_time_change(
            ctx.hass,
            self._async_morning_reminder,
            hour=self._reminder_morning_hour,
            minute=0,
            second=0,
        )
        self._unsub_callbacks.append(unsub)

        _LOGGER.info(
            "WasteReminder setup complete: %d sensors, reminders at %d:00 / %d:00",
            len(self._waste_entities),
            self._reminder_evening_hour,
            self._reminder_morning_hour,
        )

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the module."""
        for unsub in self._unsub_callbacks:
            unsub()
        self._unsub_callbacks.clear()
        return True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_state(self) -> WasteReminderState:
        return self._state

    def get_context_for_llm(self) -> str:
        """Return a human-readable summary for LLM system prompt injection."""
        if not self._state.collections:
            return ""

        lines = ["Müllabfuhr:"]
        for c in sorted(self._state.collections, key=lambda x: x.days_to):
            name = _get_display_name(c.waste_type)
            if c.days_to == 0:
                lines.append(f"  {c.icon} {name}: HEUTE")
            elif c.days_to == 1:
                lines.append(f"  {c.icon} {name}: MORGEN")
            else:
                lines.append(f"  {c.icon} {name}: in {c.days_to} Tagen ({c.next_date})")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Discovery + Scanning
    # ------------------------------------------------------------------

    def _discover_waste_sensors(self) -> list[str]:
        """Auto-discover waste_collection_schedule sensors."""
        if not self._hass:
            return []
        found = []
        for state in self._hass.states.async_all():
            eid = state.entity_id
            if not eid.startswith("sensor."):
                continue
            # hacs_waste_collection_schedule creates sensors with these markers
            attrs = state.attributes
            if "daysTo" in attrs or "days" in attrs:
                found.append(eid)
            elif any(kw in eid.lower() for kw in ("waste", "muell", "müll", "abfall", "tonne")):
                found.append(eid)
        if found:
            _LOGGER.info("Auto-discovered %d waste sensors: %s", len(found), found)
        return found

    async def _async_scan(self) -> None:
        """Scan all waste sensors and update state."""
        if not self._hass:
            return

        collections = []
        for entity_id in self._waste_entities:
            state = self._hass.states.get(entity_id)
            if not state or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                continue

            attrs = state.attributes
            days_to = attrs.get("daysTo") or attrs.get("days")
            if days_to is None:
                # Try parsing state as number
                try:
                    days_to = int(float(state.state))
                except (ValueError, TypeError):
                    continue

            try:
                days_to = int(days_to)
            except (ValueError, TypeError):
                continue

            waste_type = attrs.get("waste_type") or state.name or entity_id
            next_date = attrs.get("next_date", "")

            collections.append(WasteCollection(
                waste_type=waste_type,
                entity_id=entity_id,
                days_to=days_to,
                next_date=str(next_date) if next_date else "",
            ))

        # Sort by days_to
        collections.sort(key=lambda c: c.days_to)

        self._state.collections = collections
        self._state.next_collection = collections[0] if collections else None
        self._state.tomorrow_collections = [c for c in collections if c.days_to == 1]
        self._state.today_collections = [c for c in collections if c.days_to == 0]
        self._state.last_scan = dt_util.utcnow()

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    @callback
    async def _async_waste_state_changed(self, event) -> None:
        """Handle waste sensor state changes."""
        await self._async_scan()

    async def _async_evening_reminder(self, now) -> None:
        """Fire evening reminder for tomorrow's collections."""
        await self._async_scan()

        if not self._state.tomorrow_collections:
            return

        # Reset daily counter
        today_str = dt_util.now().strftime("%Y-%m-%d")
        if self._state.last_reminder_date != today_str:
            self._state.reminders_sent_today = 0
            self._state.last_reminder_date = today_str

        types = [_get_display_name(c.waste_type) for c in self._state.tomorrow_collections]
        icons = [c.icon for c in self._state.tomorrow_collections]
        types_str = ", ".join(f"{i} {t}" for i, t in zip(icons, types))

        message = f"Erinnerung: Morgen wird abgeholt: {types_str}. Bitte Tonnen rausstellen!"
        title = "Müllabfuhr morgen"

        await self._deliver_reminder(title, message)
        self._state.reminders_sent_today += 1

        # Forward to Core addon
        await self._forward_to_core("evening_reminder", types)

    async def _async_morning_reminder(self, now) -> None:
        """Fire morning reminder for today's collections."""
        await self._async_scan()

        if not self._state.today_collections:
            return

        types = [_get_display_name(c.waste_type) for c in self._state.today_collections]
        icons = [c.icon for c in self._state.today_collections]
        types_str = ", ".join(f"{i} {t}" for i, t in zip(icons, types))

        message = f"Heute wird abgeholt: {types_str}."
        title = "Müllabfuhr heute"

        await self._deliver_reminder(title, message)
        self._state.reminders_sent_today += 1

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    async def _deliver_reminder(self, title: str, message: str) -> None:
        """Deliver reminder via TTS and/or persistent notification."""
        if not self._hass:
            return

        # Persistent notification
        try:
            await self._hass.services.async_call(
                "persistent_notification",
                "create",
                {"title": title, "message": message, "notification_id": "waste_reminder"},
                blocking=False,
            )
        except Exception:
            _LOGGER.debug("Failed to create persistent notification", exc_info=True)

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
                _LOGGER.info("TTS waste reminder sent to %s", self._tts_entity)
            except Exception:
                _LOGGER.debug("TTS delivery failed", exc_info=True)

        _LOGGER.info("Waste reminder delivered: %s", title)

    async def _forward_to_core(self, event_type: str, waste_types: list[str]) -> None:
        """Forward waste event to Core addon."""
        if not self._api_client:
            return
        try:
            await self._api_client.async_post(
                "/api/v1/waste/event",
                {
                    "event_type": event_type,
                    "waste_types": waste_types,
                    "timestamp": dt_util.utcnow().isoformat(),
                },
            )
        except Exception:
            _LOGGER.debug("Failed to forward waste event to Core", exc_info=True)


def get_waste_reminder_module(hass, entry_id):
    """Return the WasteReminderModule instance for a config entry, or None."""
    data = hass.data.get("ai_home_copilot", {}).get(entry_id, {})
    return data.get("waste_reminder")
