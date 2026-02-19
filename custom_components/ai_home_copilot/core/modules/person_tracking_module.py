"""Person Tracking Module for AI Home CoPilot.

Tracks who is home and where they are using HA person.* and device_tracker.*
entities. Provides presence state, arrival/departure history, and LLM context
for the PilotSuite conversation engine.

Privacy-first: only local entity data, no external tracking.
"""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.const import EVENT_STATE_CHANGED

from ...const import DOMAIN
from .module import CopilotModule

_LOGGER = logging.getLogger(__name__)

# Domains we listen to for presence updates.
_TRACKED_DOMAINS = frozenset({"person", "device_tracker"})

# HA built-in states for person / device_tracker entities.
_STATE_HOME = "home"
_STATE_NOT_HOME = "not_home"

# States we treat as "away" (device_tracker can also report these).
_AWAY_STATES = frozenset({_STATE_NOT_HOME, "away"})

# States that are not meaningful for presence tracking.
_IGNORED_STATES = frozenset({"unknown", "unavailable", ""})


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PersonPresence:
    """Current presence state of a single person."""

    person_id: str          # e.g. "person.max"
    name: str               # Friendly name, e.g. "Max"
    state: str              # "home" / "not_home" / zone name
    zone: str | None        # Resolved zone name ("Wohnzimmer") or None
    since: datetime         # Timestamp of the last state change
    source: str             # "person" or "device_tracker"

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    @property
    def is_home(self) -> bool:
        """Return True when the person is considered home."""
        return self.state == _STATE_HOME or (
            self.state not in _AWAY_STATES
            and self.state not in _IGNORED_STATES
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "person_id": self.person_id,
            "name": self.name,
            "state": self.state,
            "zone": self.zone,
            "since": self.since.isoformat(),
            "source": self.source,
            "is_home": self.is_home,
        }


@dataclass
class PresenceEvent:
    """A single arrival / departure / zone-change event."""

    person_name: str
    event_type: str         # "arrived" / "departed" / "zone_changed"
    zone: str | None
    timestamp: datetime
    source: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "person_name": self.person_name,
            "event_type": self.event_type,
            "zone": self.zone,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class PersonTrackingModule(CopilotModule):
    """Tracks persons in the home using HA person.* and device_tracker.* entities."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        super().__init__(hass, entry_id)
        self._hass = hass
        self._entry_id = entry_id
        self._presence_map: dict[str, PersonPresence] = {}
        self._history: deque[PresenceEvent] = deque(maxlen=100)
        self._listeners: list[Any] = []
        self._fallback_user = "admin"
        self._tracked_person_entities: list[str] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:  # noqa: D401 – simple property
        return "Person Tracking"

    @property
    def enabled(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_setup(self) -> bool:
        """Discover person.* entities, seed the presence map, register listeners."""
        _LOGGER.info("Setting up Person Tracking Module")

        # 1. Discover all person.* entities and read their current state.
        self._discover_persons()

        # 2. Also consider device_tracker.* entities that are NOT already
        #    backing a person entity (standalone trackers).
        self._discover_standalone_trackers()

        # 3. Register a single EVENT_STATE_CHANGED listener for both domains.
        self._listeners.append(
            self._hass.bus.async_listen(EVENT_STATE_CHANGED, self._on_state_changed)
        )

        # 4. Parse optional household config from hass.data (set by the
        #    household module if present).  We only use it for the fallback
        #    user name – the rest comes from HA entity attributes.
        self._load_household_config()

        # 5. Store ourselves in hass.data so other modules can find us.
        domain_data = self._hass.data.setdefault(DOMAIN, {})
        entry_data = domain_data.setdefault(self._entry_id, {})
        entry_data["person_tracking_module"] = self

        _LOGGER.info(
            "Person Tracking Module initialised – tracking %d person(s), "
            "%d total entries in presence map",
            len(self._tracked_person_entities),
            len(self._presence_map),
        )
        return True

    async def async_shutdown(self) -> None:
        """Remove event listeners and clean up hass.data reference."""
        _LOGGER.info("Shutting down Person Tracking Module")

        for unsub in self._listeners:
            if unsub is not None:
                try:
                    unsub()
                except Exception:  # noqa: BLE001 – best-effort cleanup
                    pass
        self._listeners.clear()

        # Remove from hass.data
        domain_data = self._hass.data.get(DOMAIN, {})
        entry_data = domain_data.get(self._entry_id, {})
        entry_data.pop("person_tracking_module", None)

        _LOGGER.debug("Person Tracking Module shut down")

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    def _discover_persons(self) -> None:
        """Read all person.* entities and seed the presence map."""
        now = datetime.now()

        for state_obj in self._hass.states.async_all("person"):
            entity_id: str = state_obj.entity_id
            self._tracked_person_entities.append(entity_id)

            friendly_name = self._extract_friendly_name(state_obj)
            raw_state = state_obj.state  # "home", "not_home", or a zone name

            zone = self._resolve_zone(raw_state)

            self._presence_map[entity_id] = PersonPresence(
                person_id=entity_id,
                name=friendly_name,
                state=raw_state,
                zone=zone,
                since=now,
                source="person",
            )
            _LOGGER.debug(
                "Discovered person %s (%s) – state=%s, zone=%s",
                entity_id,
                friendly_name,
                raw_state,
                zone,
            )

    def _discover_standalone_trackers(self) -> None:
        """Add device_tracker.* entities that don't back a person entity."""
        # Build a set of device_tracker entity IDs that are already
        # represented through a person entity (via the source attribute).
        person_sources: set[str] = set()
        for state_obj in self._hass.states.async_all("person"):
            sources = state_obj.attributes.get("source", "")
            if isinstance(sources, str) and sources:
                person_sources.add(sources)
            elif isinstance(sources, list):
                person_sources.update(sources)

        now = datetime.now()

        for state_obj in self._hass.states.async_all("device_tracker"):
            entity_id: str = state_obj.entity_id
            if entity_id in person_sources:
                # Already tracked via a person.* entity.
                continue

            friendly_name = self._extract_friendly_name(state_obj)
            raw_state = state_obj.state
            zone = self._resolve_zone(raw_state)

            self._presence_map[entity_id] = PersonPresence(
                person_id=entity_id,
                name=friendly_name,
                state=raw_state,
                zone=zone,
                since=now,
                source="device_tracker",
            )
            _LOGGER.debug(
                "Discovered standalone tracker %s (%s) – state=%s",
                entity_id,
                friendly_name,
                raw_state,
            )

    def _load_household_config(self) -> None:
        """Load household config from hass.data (optional)."""
        try:
            domain_data = self._hass.data.get(DOMAIN, {})
            entry_data = domain_data.get(self._entry_id, {})
            household = entry_data.get("household", {})
            if isinstance(household, dict):
                fallback = household.get("primary_user")
                if fallback and isinstance(fallback, str):
                    self._fallback_user = fallback
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Event handler
    # ------------------------------------------------------------------

    @callback
    def _on_state_changed(self, event: Event) -> None:
        """Handle person.* and device_tracker.* state changes."""
        entity_id: str = event.data.get("entity_id", "")
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""

        if domain not in _TRACKED_DOMAINS:
            return

        new_state_obj = event.data.get("new_state")
        old_state_obj = event.data.get("old_state")

        if new_state_obj is None:
            # Entity was removed – clean up.
            self._presence_map.pop(entity_id, None)
            return

        new_state: str = new_state_obj.state or ""
        old_state: str = old_state_obj.state if old_state_obj else ""

        # Skip ignored/unchanged states.
        if new_state in _IGNORED_STATES:
            return
        if new_state == old_state:
            return

        now = datetime.now()
        friendly_name = self._extract_friendly_name(new_state_obj)
        zone = self._resolve_zone(new_state)
        source = "person" if domain == "person" else "device_tracker"

        # Determine event type.
        event_type: str | None = None
        old_is_home = self._state_is_home(old_state)
        new_is_home = self._state_is_home(new_state)

        if not old_is_home and new_is_home:
            event_type = "arrived"
        elif old_is_home and not new_is_home:
            event_type = "departed"
        elif old_is_home and new_is_home and old_state != new_state:
            # Zone changed while still home (e.g. "Wohnzimmer" -> "Kueche").
            event_type = "zone_changed"

        # Update the presence map.
        self._presence_map[entity_id] = PersonPresence(
            person_id=entity_id,
            name=friendly_name,
            state=new_state,
            zone=zone,
            since=now,
            source=source,
        )

        # Record the event in history.
        if event_type is not None:
            presence_event = PresenceEvent(
                person_name=friendly_name,
                event_type=event_type,
                zone=zone,
                timestamp=now,
                source=source,
            )
            self._history.append(presence_event)
            _LOGGER.debug(
                "Person tracking event: %s %s (zone=%s, source=%s)",
                friendly_name,
                event_type,
                zone,
                source,
            )

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def get_persons_home(self) -> list[str]:
        """Return friendly names of persons currently home."""
        return [
            p.name
            for p in self._presence_map.values()
            if p.is_home
        ]

    def get_persons_away(self) -> list[str]:
        """Return friendly names of persons currently away."""
        return [
            p.name
            for p in self._presence_map.values()
            if not p.is_home
        ]

    def get_presence_map(self) -> dict[str, dict[str, Any]]:
        """Return the full presence map as a JSON-serialisable dict."""
        return {
            entity_id: presence.to_dict()
            for entity_id, presence in self._presence_map.items()
        }

    def get_person_count(self) -> int:
        """Return the number of persons currently home."""
        return sum(1 for p in self._presence_map.values() if p.is_home)

    def get_history(self) -> list[dict[str, Any]]:
        """Return recent presence events (newest first)."""
        return [evt.to_dict() for evt in reversed(self._history)]

    def get_context_for_llm(self) -> str:
        """Build a compact German-language context string for the LLM system prompt.

        Example output:
            Anwesend: Max (Wohnzimmer, seit 14:30), Lisa (zu Hause, seit 15:12).
            Abwesend: Papa (seit 08:15).
        """
        home_parts: list[str] = []
        away_parts: list[str] = []

        for presence in self._presence_map.values():
            since_str = presence.since.strftime("%H:%M")

            if presence.is_home:
                location = presence.zone if presence.zone else "zu Hause"
                home_parts.append(f"{presence.name} ({location}, seit {since_str})")
            else:
                away_parts.append(f"{presence.name} (seit {since_str})")

        parts: list[str] = []
        if home_parts:
            parts.append(f"Anwesend: {', '.join(home_parts)}.")
        if away_parts:
            parts.append(f"Abwesend: {', '.join(away_parts)}.")

        if not parts:
            return "Keine Personen erfasst."

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_friendly_name(state_obj: Any) -> str:
        """Extract a human-readable name from a HA state object."""
        if state_obj is None:
            return "Unbekannt"
        # Prefer the friendly_name attribute.
        friendly = state_obj.attributes.get("friendly_name")
        if friendly:
            return str(friendly)
        # Fall back to the object_id portion of the entity_id.
        entity_id: str = getattr(state_obj, "entity_id", "")
        if "." in entity_id:
            return entity_id.split(".", 1)[1].replace("_", " ").title()
        return str(entity_id) or "Unbekannt"

    @staticmethod
    def _resolve_zone(state_value: str) -> str | None:
        """Translate a raw HA state into a human-readable zone name.

        HA person/device_tracker entities can report:
        - "home" – at home, no specific zone
        - "not_home" / "away" – away
        - A zone slug like "wohnzimmer" or "Wohnzimmer"

        Returns None for generic home/away, or the zone name for specific zones.
        """
        if not state_value:
            return None
        lower = state_value.lower()
        if lower in (_STATE_HOME, _STATE_NOT_HOME, "away", "unknown", "unavailable"):
            return None
        # The state IS a zone name.  Return it as-is (HA often stores the
        # friendly zone name directly).
        return state_value

    @staticmethod
    def _state_is_home(state_value: str) -> bool:
        """Return True when the raw state means the person is home."""
        if not state_value:
            return False
        lower = state_value.lower()
        if lower == _STATE_HOME:
            return True
        if lower in _AWAY_STATES or lower in _IGNORED_STATES:
            return False
        # Any other value is a specific zone name – person is home in that zone.
        return True


# ---------------------------------------------------------------------------
# Module-level getter (convenience for other modules)
# ---------------------------------------------------------------------------

def get_person_tracking_module(
    hass: HomeAssistant,
    entry_id: str,
) -> PersonTrackingModule | None:
    """Retrieve the PersonTrackingModule instance from hass.data."""
    data = hass.data.get(DOMAIN, {}).get(entry_id, {})
    return data.get("person_tracking_module")


__all__ = [
    "PersonTrackingModule",
    "PersonPresence",
    "PresenceEvent",
    "get_person_tracking_module",
]
