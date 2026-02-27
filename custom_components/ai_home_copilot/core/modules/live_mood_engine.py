"""Live Mood Engine -- Local mood calculation from real Entity states.

Computes Comfort / Joy / Frugality per Habitus Zone purely from HA entity
states, without any dependency on the Core add-on.  Results are stored in
``hass.data[DOMAIN][entry_id]["live_mood"]`` and a dispatcher signal is fired
whenever a zone mood changes.

Roles used from zone entity mappings:
    temperature, humidity, co2, noise, brightness  --> Comfort
    media, (person.* home count)                   --> Joy
    power                                          --> Frugality
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Callable

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.dispatcher import async_dispatcher_send

from ...const import DOMAIN
from ...habitus_zones_store_v2 import HabitusZoneV2, async_get_zones_v2
from .module import CopilotModule, ModuleContext

logger = logging.getLogger(__name__)

SIGNAL_LIVE_MOOD_UPDATED = f"{DOMAIN}_live_mood_updated"

# ---------------------------------------------------------------------------
# Comfort thresholds
# ---------------------------------------------------------------------------
TEMP_OPTIMAL_LOW = 22.0
TEMP_OPTIMAL_HIGH = 24.0
TEMP_MIN = 18.0
TEMP_MAX = 28.0

HUMIDITY_OPTIMAL_LOW = 40.0
HUMIDITY_OPTIMAL_HIGH = 60.0
HUMIDITY_MIN = 20.0
HUMIDITY_MAX = 80.0

CO2_GOOD = 800.0
CO2_BAD = 1200.0

NOISE_GOOD = 50.0
NOISE_BAD = 80.0

# Brightness thresholds (time-adaptive)
BRIGHTNESS_DAY_OPTIMAL = 400.0   # lux
BRIGHTNESS_DAY_MAX = 1000.0
BRIGHTNESS_EVENING_OPTIMAL = 150.0
BRIGHTNESS_EVENING_MAX = 400.0
BRIGHTNESS_NIGHT_OPTIMAL = 5.0
BRIGHTNESS_NIGHT_MAX = 50.0

# Power thresholds (per zone, in watts)
POWER_LOW = 50.0    # < 50 W  --> frugality 1.0
POWER_HIGH = 500.0  # > 500 W --> frugality 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(hass: HomeAssistant, entity_id: str) -> float | None:
    """Read numeric state from *hass.states*, returning ``None`` on failure."""
    state = hass.states.get(entity_id)
    if state is None:
        return None
    raw = state.state
    if raw in (None, "unknown", "unavailable", ""):
        return None
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _linear_score(value: float, good_low: float, good_high: float,
                  bad_low: float, bad_high: float) -> float:
    """Map *value* linearly to 0..1.

    Returns 1.0 inside [good_low, good_high], 0.0 outside [bad_low, bad_high],
    and a linear interpolation in between.
    """
    if good_low <= value <= good_high:
        return 1.0
    if value < good_low:
        if value <= bad_low:
            return 0.0
        return (value - bad_low) / (good_low - bad_low)
    # value > good_high
    if value >= bad_high:
        return 0.0
    return (bad_high - value) / (bad_high - good_high)


def _avg(values: list[float]) -> float:
    """Return the arithmetic mean or 0.5 (neutral) if *values* is empty."""
    if not values:
        return 0.5
    return sum(values) / len(values)


def _time_period(now: datetime | None = None) -> str:
    """Return 'day', 'evening', or 'night' based on current hour."""
    if now is None:
        now = datetime.now()
    hour = now.hour
    if 7 <= hour < 18:
        return "day"
    if 18 <= hour < 22:
        return "evening"
    return "night"


# ---------------------------------------------------------------------------
# Mood calculation functions
# ---------------------------------------------------------------------------

def _compute_comfort(
    hass: HomeAssistant,
    zone: HabitusZoneV2,
) -> float:
    """Compute comfort score 0..1 from temperature, humidity, CO2, noise, brightness."""
    scores: list[float] = []

    # -- Temperature --
    for eid in zone.get_role_entities("temperature"):
        val = _safe_float(hass, eid)
        if val is not None:
            scores.append(_linear_score(val, TEMP_OPTIMAL_LOW, TEMP_OPTIMAL_HIGH, TEMP_MIN, TEMP_MAX))

    # -- Humidity --
    for eid in zone.get_role_entities("humidity"):
        val = _safe_float(hass, eid)
        if val is not None:
            scores.append(_linear_score(val, HUMIDITY_OPTIMAL_LOW, HUMIDITY_OPTIMAL_HIGH,
                                        HUMIDITY_MIN, HUMIDITY_MAX))

    # -- CO2 --
    for eid in zone.get_role_entities("co2"):
        val = _safe_float(hass, eid)
        if val is not None:
            # lower is better: 0..800 -> 1.0, 800..1200 -> linear, >1200 -> 0.0
            scores.append(_linear_score(val, 0, CO2_GOOD, 0, CO2_BAD))

    # -- Noise --
    for eid in zone.get_role_entities("noise"):
        val = _safe_float(hass, eid)
        if val is not None:
            # lower is better: 0..50 -> 1.0, 50..80 -> linear, >80 -> 0.0
            scores.append(_linear_score(val, 0, NOISE_GOOD, 0, NOISE_BAD))

    # -- Brightness (time-adaptive) --
    period = _time_period()
    if period == "day":
        bright_opt = BRIGHTNESS_DAY_OPTIMAL
        bright_max = BRIGHTNESS_DAY_MAX
    elif period == "evening":
        bright_opt = BRIGHTNESS_EVENING_OPTIMAL
        bright_max = BRIGHTNESS_EVENING_MAX
    else:
        bright_opt = BRIGHTNESS_NIGHT_OPTIMAL
        bright_max = BRIGHTNESS_NIGHT_MAX

    for eid in zone.get_role_entities("brightness"):
        val = _safe_float(hass, eid)
        if val is not None:
            # Optimal around bright_opt, 0 lux is not bad per se (night), excess is bad.
            if val <= bright_opt:
                # 0 lux..optimal -> acceptable (0.7..1.0)
                score = 0.7 + 0.3 * (val / bright_opt) if bright_opt > 0 else 1.0
            else:
                # optimal..max -> 1.0..0.3
                overshoot = (val - bright_opt) / (bright_max - bright_opt) if bright_max > bright_opt else 0
                score = max(0.3, 1.0 - overshoot * 0.7)
            scores.append(_clamp(score))

    return round(_avg(scores), 3)


def _compute_joy(
    hass: HomeAssistant,
    zone: HabitusZoneV2,
) -> float:
    """Compute joy score 0..1 from media players and person presence."""
    score = 0.0

    # -- Media players --
    media_entities = zone.get_role_entities("media")
    playing_count = 0
    for eid in media_entities:
        state = hass.states.get(eid)
        if state is not None and state.state == "playing":
            playing_count += 1
    if playing_count > 0:
        # Each playing media player adds 0.25, capped contribution at 0.6
        score += min(playing_count * 0.25, 0.6)

    # -- Person presence (global: person.* entities that are "home") --
    home_count = 0
    for state in hass.states.async_all("person"):
        if state.state == "home":
            home_count += 1
    if home_count >= 2:
        score += 0.15
    elif home_count == 1:
        score += 0.05

    # Baseline: some minimal joy when zone has any entities at all
    if score == 0.0 and zone.get_all_entities():
        score = 0.1  # quiet baseline

    return round(_clamp(score), 3)


def _compute_frugality(
    hass: HomeAssistant,
    zone: HabitusZoneV2,
) -> float:
    """Compute frugality score 0..1 from power entities (lower is more frugal)."""
    power_entities = zone.get_role_entities("power")
    if not power_entities:
        # No power monitoring -> assume neutral
        return 0.5

    total_watts = 0.0
    valid_readings = 0
    for eid in power_entities:
        val = _safe_float(hass, eid)
        if val is not None and val >= 0:
            total_watts += val
            valid_readings += 1

    if valid_readings == 0:
        return 0.5  # No valid readings -> neutral

    # Map total power consumption inversely to frugality
    # low power -> high frugality, high power -> low frugality
    if total_watts <= POWER_LOW:
        return 1.0
    if total_watts >= POWER_HIGH:
        return 0.0

    return round(1.0 - (total_watts - POWER_LOW) / (POWER_HIGH - POWER_LOW), 3)


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class LiveMoodEngine(CopilotModule):
    """CopilotModule that computes Comfort/Joy/Frugality locally per zone."""

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._entry_id: str | None = None
        self._zones: list[HabitusZoneV2] = []
        self._zone_map: dict[str, HabitusZoneV2] = {}
        self._entity_to_zones: dict[str, list[str]] = {}
        self._unsub_listeners: list[Callable[[], None]] = []
        self._live_mood: dict[str, dict[str, Any]] = {}

    # -- CopilotModule interface ------------------------------------------------

    @property
    def name(self) -> str:
        return "live_mood_engine"

    @property
    def version(self) -> str:
        return "1.0"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Load zones, register state listeners, compute initial mood."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry.entry_id

        # Load zones
        self._zones = await async_get_zones_v2(ctx.hass, ctx.entry.entry_id)
        if not self._zones:
            logger.warning("LiveMoodEngine: No Habitus zones found for entry %s", ctx.entry.entry_id)
            return

        self._zone_map = {z.zone_id: z for z in self._zones}
        logger.info("LiveMoodEngine: Loaded %d zones", len(self._zones))

        # Build entity -> zone(s) mapping
        self._entity_to_zones = {}
        tracked_entities: set[str] = set()
        for zone in self._zones:
            all_ents = zone.get_all_entities()
            for eid in all_ents:
                self._entity_to_zones.setdefault(eid, []).append(zone.zone_id)
                tracked_entities.add(eid)

        logger.info("LiveMoodEngine: Tracking %d entities across %d zones",
                     len(tracked_entities), len(self._zones))

        # Register state-change listener for all tracked entities
        if tracked_entities:
            unsub = async_track_state_change_event(
                ctx.hass,
                list(tracked_entities),
                self._handle_state_change,
            )
            self._unsub_listeners.append(unsub)

        # Compute initial mood for all zones
        self._recompute_all_zones()

        # Store in hass.data
        dom = ctx.hass.data.setdefault(DOMAIN, {})
        entry_data = dom.setdefault(ctx.entry.entry_id, {})
        if isinstance(entry_data, dict):
            entry_data["live_mood"] = self._live_mood
            entry_data["live_mood_engine"] = self

        logger.info("LiveMoodEngine: Setup complete -- initial mood computed for %d zones",
                     len(self._live_mood))

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Remove listeners and clean up."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

        dom = ctx.hass.data.get(DOMAIN, {})
        entry_data = dom.get(ctx.entry.entry_id, {})
        if isinstance(entry_data, dict):
            entry_data.pop("live_mood", None)
            entry_data.pop("live_mood_engine", None)

        self._live_mood.clear()
        self._zones = []
        self._zone_map.clear()
        self._entity_to_zones.clear()
        self._hass = None
        self._entry_id = None

        logger.info("LiveMoodEngine: Unloaded")
        return True

    # -- State change handling ---------------------------------------------------

    @callback
    def _handle_state_change(self, event: Event) -> None:
        """React to entity state changes and recompute affected zone moods."""
        entity_id = event.data.get("entity_id", "")
        affected_zone_ids = self._entity_to_zones.get(entity_id, [])

        if not affected_zone_ids or self._hass is None:
            return

        changed = False
        for zone_id in affected_zone_ids:
            zone = self._zone_map.get(zone_id)
            if zone is None:
                continue

            new_mood = self._compute_zone_mood(zone)
            old_mood = self._live_mood.get(zone_id)

            # Only fire signal when values actually changed
            if old_mood is None or self._mood_changed(old_mood, new_mood):
                self._live_mood[zone_id] = new_mood
                changed = True
                logger.debug(
                    "LiveMoodEngine: Zone %s mood updated -- C=%.2f J=%.2f F=%.2f",
                    zone_id, new_mood["comfort"], new_mood["joy"], new_mood["frugality"],
                )

        if changed:
            # Keep hass.data reference in sync
            dom = self._hass.data.get(DOMAIN, {})
            entry_data = dom.get(self._entry_id, {})
            if isinstance(entry_data, dict):
                entry_data["live_mood"] = self._live_mood

            async_dispatcher_send(self._hass, SIGNAL_LIVE_MOOD_UPDATED, {
                "entry_id": self._entry_id,
                "zone_ids": affected_zone_ids,
                "mood": {zid: self._live_mood.get(zid) for zid in affected_zone_ids},
            })

    # -- Mood computation -------------------------------------------------------

    def _compute_zone_mood(self, zone: HabitusZoneV2) -> dict[str, Any]:
        """Compute the full mood dict for a single zone."""
        assert self._hass is not None
        return {
            "comfort": _compute_comfort(self._hass, zone),
            "joy": _compute_joy(self._hass, zone),
            "frugality": _compute_frugality(self._hass, zone),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _recompute_all_zones(self) -> None:
        """Compute mood for every loaded zone."""
        for zone in self._zones:
            self._live_mood[zone.zone_id] = self._compute_zone_mood(zone)

    @staticmethod
    def _mood_changed(old: dict[str, Any], new: dict[str, Any], threshold: float = 0.01) -> bool:
        """Return True if any mood dimension changed beyond *threshold*."""
        for key in ("comfort", "joy", "frugality"):
            old_val = old.get(key, 0.5)
            new_val = new.get(key, 0.5)
            if abs(old_val - new_val) >= threshold:
                return True
        return False

    # -- Public API -------------------------------------------------------------

    def get_zone_mood(self, zone_id: str) -> dict[str, Any] | None:
        """Return the current live mood for a zone, or ``None``."""
        return self._live_mood.get(zone_id)

    def get_all_moods(self) -> dict[str, dict[str, Any]]:
        """Return a copy of all zone moods."""
        return dict(self._live_mood)

    def get_summary(self) -> dict[str, Any]:
        """Return a summary across all tracked zones."""
        moods = list(self._live_mood.values())
        if not moods:
            return {
                "zones_tracked": 0,
                "average_comfort": 0.5,
                "average_frugality": 0.5,
                "average_joy": 0.5,
            }
        return {
            "zones_tracked": len(moods),
            "average_comfort": round(_avg([m["comfort"] for m in moods]), 2),
            "average_frugality": round(_avg([m["frugality"] for m in moods]), 2),
            "average_joy": round(_avg([m["joy"] for m in moods]), 2),
        }
