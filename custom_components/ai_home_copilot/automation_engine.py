"""PilotSuite Automation Engine — Presence, Light, Brightness & Media Control.

Orchestrates real-time automation within Home Assistant by listening to
habitus zone sensor states, periodically evaluating lighting conditions
via the Core API, and controlling lights and media players accordingly.

Features:
- Presence detection via motion/presence binary_sensor state changes
- Brightness tracking from indoor lux sensors + optional outdoor sensor
- Light automation: periodic evaluation via Core API + HA service calls
- Media control: activate/deactivate Musikwolke based on zone occupancy
- Zone sync: push habitus zones + auto-tagged entities to Core backend
- Entity auto-tagging: detect domain and assign tags when entities join zones

Privacy: All data stays local (HA ↔ Core Add-on). No cloud dependency.
"""
from __future__ import annotations

import asyncio
import logging
import time
import unicodedata
import re
from datetime import timedelta
from typing import Any, TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import DOMAIN
from .habitus_zones_store_v2 import async_get_zones_v2, HabitusZoneV2
from .entity_tags_store import async_upsert_tag, async_get_entity_tags

if TYPE_CHECKING:
    from .coordinator import CopilotApiClient

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain → Tag auto-mapping
# ---------------------------------------------------------------------------
# When entities are assigned to a habitus zone, auto-detect their HA domain
# and create / update tags so users can filter by domain + zone.
#
# Format: domain → (tag_id, display_name, color, icon)
DOMAIN_TAG_MAP: dict[str, tuple[str, str, str, str]] = {
    "light": ("licht", "Licht", "#fbbf24", "mdi:lightbulb"),
    "binary_sensor": ("bewegung", "Bewegung", "#f87171", "mdi:motion-sensor"),
    "sensor": ("sensor", "Sensor", "#60a5fa", "mdi:thermometer"),
    "media_player": ("media", "Media", "#a78bfa", "mdi:speaker"),
    "climate": ("klima", "Klima", "#34d399", "mdi:thermostat"),
    "cover": ("beschattung", "Beschattung", "#fb923c", "mdi:window-shutter"),
    "switch": ("schalter", "Schalter", "#6366f1", "mdi:toggle-switch"),
}

# States that indicate active presence / motion
_ACTIVE_STATES = frozenset({"on", "detected", "home", "playing"})

# Default evaluation interval in seconds
_DEFAULT_EVAL_INTERVAL = 30

# Default outdoor lux sensor entity (can be overridden via config)
_DEFAULT_OUTDOOR_LUX_ENTITY = "sensor.outdoor_lux"


def _slugify(text: str) -> str:
    """Create a stable slug from a display name (ASCII, lowercase, underscores).

    Used to derive zone tag IDs from zone display names, e.g.
    "Wohnbereich" → "wohnbereich", "Büro OG" → "buero_og".
    """
    # Normalize unicode → ASCII approximation
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "zone"


def _entity_domain(entity_id: str) -> str:
    """Extract the domain part of an entity_id."""
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


# ---------------------------------------------------------------------------
# AutomationEngine
# ---------------------------------------------------------------------------

class AutomationEngine:
    """Central automation engine for presence, light, brightness, and media control.

    Lifecycle:
        engine = AutomationEngine(hass, entry, client)
        await engine.async_start()
        ...
        await engine.async_stop()

    The engine subscribes to state changes on motion/presence sensors in each
    habitus zone, runs periodic evaluations (brightness + light control), and
    pushes context to the Core API for brain-graph-aware decisions.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: CopilotApiClient,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client  # CopilotApiClient (coordinator.api)

        # Listener unsubscribe callbacks
        self._unsub_listeners: list[CALLBACK_TYPE] = []

        # Periodic evaluation
        self._eval_interval: int = _DEFAULT_EVAL_INTERVAL
        self._eval_cancel: CALLBACK_TYPE | None = None

        # Cache: zone_id → occupied (True/False)
        self._zone_occupancy: dict[str, bool] = {}

        # Reverse index: entity_id → zone
        self._entity_zone_map: dict[str, HabitusZoneV2] = {}

        # Guard against concurrent evaluations
        self._eval_lock = asyncio.Lock()

        self._started = False

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    async def async_start(self) -> None:
        """Start the automation engine.

        1. Load zones and build internal indexes.
        2. Subscribe to state changes on motion/presence sensors.
        3. Start periodic evaluation loop.
        4. Sync zones + auto-tag entities to Core.
        """
        if self._started:
            _LOGGER.warning("AutomationEngine already started — skipping")
            return

        _LOGGER.info("Starting AutomationEngine for entry %s", self.entry.entry_id)

        # Load zones and build lookup
        zones = await async_get_zones_v2(self.hass, self.entry.entry_id)
        self._build_entity_zone_map(zones)

        # Subscribe to motion/presence sensor state changes
        await self._setup_zone_listeners(zones)

        # Start periodic evaluation (brightness + light + media)
        self._eval_cancel = async_track_time_interval(
            self.hass,
            self._periodic_evaluation,
            timedelta(seconds=self._eval_interval),
        )

        # Initial sync: zones → Core + auto-tag
        self.hass.async_create_task(self._sync_zones_to_core())
        for zone in zones:
            self.hass.async_create_task(self._auto_tag_zone_entities(zone))

        self._started = True
        _LOGGER.info(
            "AutomationEngine started: %d zones, %d tracked entities",
            len(zones),
            len(self._entity_zone_map),
        )

    async def async_stop(self) -> None:
        """Stop the engine and release all listeners."""
        if not self._started:
            return

        _LOGGER.info("Stopping AutomationEngine for entry %s", self.entry.entry_id)

        # Cancel periodic evaluation
        if self._eval_cancel is not None:
            self._eval_cancel()
            self._eval_cancel = None

        # Unsubscribe all state listeners
        for unsub in self._unsub_listeners:
            try:
                unsub()
            except Exception:  # noqa: BLE001
                pass
        self._unsub_listeners.clear()

        # Clear caches
        self._zone_occupancy.clear()
        self._entity_zone_map.clear()

        self._started = False
        _LOGGER.info("AutomationEngine stopped")

    # ------------------------------------------------------------------
    # Zone listeners
    # ------------------------------------------------------------------

    def _build_entity_zone_map(self, zones: list[HabitusZoneV2]) -> None:
        """Build reverse index: entity_id → HabitusZoneV2."""
        self._entity_zone_map.clear()
        for zone in zones:
            for entity_id in zone.get_all_entities():
                self._entity_zone_map[entity_id] = zone

    async def _setup_zone_listeners(self, zones: list[HabitusZoneV2]) -> None:
        """Subscribe to state changes on motion/presence sensors in every zone.

        Only binary_sensor and sensor entities assigned to the ``motion``
        role (or present in ``entity_ids`` with a motion-like device class)
        are tracked.
        """
        tracked_entities: list[str] = []

        for zone in zones:
            # Prefer explicit motion role; fall back to scanning entity_ids
            motion_entities = zone.get_role_entities("motion")
            if not motion_entities:
                # Heuristic: any binary_sensor in the flat entity list
                motion_entities = [
                    eid for eid in zone.entity_ids
                    if _entity_domain(eid) in ("binary_sensor", "sensor")
                ]
            tracked_entities.extend(motion_entities)

        if not tracked_entities:
            _LOGGER.debug("No motion/presence entities found in any zone")
            return

        # De-duplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for eid in tracked_entities:
            if eid not in seen:
                seen.add(eid)
                unique.append(eid)

        unsub = async_track_state_change_event(
            self.hass, unique, self._on_sensor_state_change
        )
        self._unsub_listeners.append(unsub)
        _LOGGER.debug("Tracking %d motion/presence entities", len(unique))

    # ------------------------------------------------------------------
    # State change handler
    # ------------------------------------------------------------------

    @callback
    def _on_sensor_state_change(self, event: Event) -> None:
        """Handle state change events from motion/presence sensors.

        Runs in the HA event loop (sync callback context). Creates async
        tasks for Core API calls and zone evaluation.
        """
        entity_id: str = event.data.get("entity_id", "")
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        # Find which zone this entity belongs to
        zone = self._find_zone_for_entity(entity_id)
        if zone is None:
            return

        # Determine activation state
        is_active = new_state.state in _ACTIVE_STATES

        # Update local occupancy cache
        self._zone_occupancy[zone.zone_id] = is_active

        # Push presence to Core (fire-and-forget)
        self.hass.async_create_task(
            self._push_presence_to_core(zone.zone_id, entity_id, is_active)
        )

        # Evaluate zone immediately (fire-and-forget)
        self.hass.async_create_task(
            self._evaluate_zone(zone.zone_id, zone)
        )

    def _find_zone_for_entity(self, entity_id: str) -> HabitusZoneV2 | None:
        """Look up the habitus zone an entity belongs to."""
        return self._entity_zone_map.get(entity_id)

    # ------------------------------------------------------------------
    # Core API pushes
    # ------------------------------------------------------------------

    async def _push_presence_to_core(
        self,
        zone_id: str,
        entity_id: str,
        is_active: bool,
    ) -> None:
        """Push a presence event to the Core API."""
        try:
            await self.client.async_post(
                "/api/v1/zone-automation/sensor-update",
                {
                    "entity_id": entity_id,
                    "new_state": "on" if is_active else "off",
                    "attributes": {"zone_id": zone_id},
                },
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Failed to push presence to Core: %s", err)

    # ------------------------------------------------------------------
    # Periodic evaluation loop
    # ------------------------------------------------------------------

    async def _periodic_evaluation(self, _now: Any = None) -> None:
        """Run every ``_eval_interval`` seconds.

        For each habitus zone:
        1. Read brightness sensors (indoor + outdoor lux).
        2. Send context to Core API for evaluation.
        3. Apply light settings via HA service calls.
        4. Check media presence control.
        """
        if self._eval_lock.locked():
            _LOGGER.debug("Periodic evaluation skipped (previous run still active)")
            return

        async with self._eval_lock:
            zones = await async_get_zones_v2(self.hass, self.entry.entry_id)
            if not zones:
                return

            # Refresh entity → zone mapping in case zones changed
            self._build_entity_zone_map(zones)

            for zone in zones:
                try:
                    await self._evaluate_zone(zone.zone_id, zone)
                except Exception as err:  # noqa: BLE001
                    _LOGGER.warning(
                        "Zone evaluation failed for %s: %s", zone.zone_id, err
                    )

    # ------------------------------------------------------------------
    # Single-zone evaluation
    # ------------------------------------------------------------------

    async def _evaluate_zone(self, zone_id: str, zone: HabitusZoneV2) -> None:
        """Evaluate a single zone: brightness, light settings, media control."""

        # 1. Read brightness sensors
        indoor_lux, outdoor_lux = await self._read_brightness_sensors(zone)

        # 2. Determine occupancy (cached from state changes, fallback to live read)
        occupied = self._zone_occupancy.get(zone_id)
        if occupied is None:
            occupied = self._check_zone_occupied_now(zone)
            self._zone_occupancy[zone_id] = occupied

        # 3. Call Core API for lighting evaluation
        evaluation = await self._evaluate_lighting_via_core(
            zone_id, zone, indoor_lux, outdoor_lux, occupied
        )

        # 4. Apply light settings if Core returned a recommendation
        if evaluation:
            await self._apply_light_settings(zone_id, evaluation, zone)

        # 5. Media presence control
        await self._check_media_presence(zone_id, occupied, zone)

    def _check_zone_occupied_now(self, zone: HabitusZoneV2) -> bool:
        """Read current motion sensor states to determine occupancy."""
        motion_entities = zone.get_role_entities("motion")
        if not motion_entities:
            # Heuristic: check binary_sensors in entity_ids
            motion_entities = [
                eid for eid in zone.entity_ids
                if _entity_domain(eid) == "binary_sensor"
            ]

        for entity_id in motion_entities:
            state = self.hass.states.get(entity_id)
            if state is not None and state.state in _ACTIVE_STATES:
                return True
        return False

    # ------------------------------------------------------------------
    # Brightness tracking
    # ------------------------------------------------------------------

    async def _read_brightness_sensors(
        self, zone: HabitusZoneV2
    ) -> tuple[float, float]:
        """Read indoor + outdoor lux values for a zone.

        Returns:
            Tuple of (indoor_lux, outdoor_lux).
        """
        indoor_lux = 0.0
        outdoor_lux = 0.0

        # Read indoor brightness sensors from zone role mapping
        brightness_entities = zone.get_role_entities("brightness")
        for entity_id in brightness_entities:
            state = self.hass.states.get(entity_id)
            if state is not None and state.state not in ("unknown", "unavailable"):
                try:
                    indoor_lux = max(indoor_lux, float(state.state))
                except (ValueError, TypeError):
                    pass

        # Read outdoor sensor (global or per-zone override via metadata)
        outdoor_entity = _DEFAULT_OUTDOOR_LUX_ENTITY
        if zone.metadata and isinstance(zone.metadata.get("outdoor_lux_entity"), str):
            outdoor_entity = zone.metadata["outdoor_lux_entity"]

        state = self.hass.states.get(outdoor_entity)
        if state is not None and state.state not in ("unknown", "unavailable"):
            try:
                outdoor_lux = float(state.state)
            except (ValueError, TypeError):
                pass

        return indoor_lux, outdoor_lux

    # ------------------------------------------------------------------
    # Core API — lighting evaluation
    # ------------------------------------------------------------------

    async def _evaluate_lighting_via_core(
        self,
        zone_id: str,
        zone: HabitusZoneV2,
        indoor_lux: float,
        outdoor_lux: float,
        occupied: bool,
    ) -> dict[str, Any] | None:
        """Ask the Core API to evaluate ideal light settings for a zone.

        The Core brain graph considers mood, time of day, habitus patterns,
        and brightness to recommend whether lights should be on and at what
        brightness / color temperature.

        Returns:
            Dict with keys ``should_be_on``, ``brightness_pct``, ``color_temp_k``
            or ``None`` on failure.
        """
        try:
            data = await self.client.async_post(
                "/api/v1/zone-automation/evaluate/" + zone_id,
                {},
            )
            ev = data.get("evaluation", data)
            # Map Core evaluation fields to the format _apply_light_settings expects
            return {
                "should_be_on": ev.get("light_action") in ("turn_on", "adjust"),
                "brightness_pct": ev.get("light_brightness_pct", 100),
                "color_temp_k": ev.get("light_color_temp_k", 4000),
            }
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug(
                "Core lighting evaluation failed for zone %s: %s", zone_id, err
            )
            return None

    # ------------------------------------------------------------------
    # Light application
    # ------------------------------------------------------------------

    async def _apply_light_settings(
        self,
        zone_id: str,
        evaluation: dict[str, Any],
        zone: HabitusZoneV2,
    ) -> None:
        """Apply evaluated light settings via HA service calls.

        Uses ``light.turn_on`` / ``light.turn_off`` on all entities in the
        zone's ``lights`` role.
        """
        light_entities = zone.get_role_entities("lights")
        if not light_entities:
            return

        if evaluation.get("should_be_on"):
            brightness_pct = evaluation.get("brightness_pct", 100)
            color_temp_k = evaluation.get("color_temp_k", 4000)

            for entity_id in light_entities:
                service_data: dict[str, Any] = {
                    "entity_id": entity_id,
                    "brightness_pct": brightness_pct,
                }
                if color_temp_k and color_temp_k > 0:
                    service_data["color_temp_kelvin"] = color_temp_k

                try:
                    await self.hass.services.async_call(
                        "light", "turn_on", service_data, blocking=False
                    )
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug(
                        "Failed to turn on %s in zone %s: %s",
                        entity_id,
                        zone_id,
                        err,
                    )
        else:
            for entity_id in light_entities:
                try:
                    await self.hass.services.async_call(
                        "light",
                        "turn_off",
                        {"entity_id": entity_id},
                        blocking=False,
                    )
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug(
                        "Failed to turn off %s in zone %s: %s",
                        entity_id,
                        zone_id,
                        err,
                    )

    # ------------------------------------------------------------------
    # Media presence control
    # ------------------------------------------------------------------

    async def _check_media_presence(
        self,
        zone_id: str,
        occupied: bool,
        zone: HabitusZoneV2,
    ) -> None:
        """Activate / deactivate Musikwolke based on zone occupancy.

        When presence is detected in a zone with media players, the Core
        music cloud player is activated for that zone. On vacancy the
        player is deactivated.
        """
        media_entities = zone.get_role_entities("media")
        if not media_entities:
            return

        try:
            if occupied:
                await self.client.async_post(
                    "/api/v1/media/cloud/activate",
                    {"zone_id": zone_id, "players": media_entities},
                )
            else:
                await self.client.async_post(
                    "/api/v1/media/cloud/deactivate",
                    {"zone_id": zone_id},
                )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug(
                "Musikwolke %s failed for zone %s: %s",
                "activate" if occupied else "deactivate",
                zone_id,
                err,
            )

    # ------------------------------------------------------------------
    # Zone sync to Core
    # ------------------------------------------------------------------

    async def _sync_zones_to_core(self) -> None:
        """Push all habitus zones to the Core backend.

        Called once at engine start and can be triggered externally when
        zones are updated.
        """
        try:
            zones = await async_get_zones_v2(self.hass, self.entry.entry_id)
            if not zones:
                _LOGGER.debug("No zones to sync to Core")
                return

            payload: list[dict[str, Any]] = []
            for zone in zones:
                zone_data: dict[str, Any] = {
                    "zone_id": zone.zone_id,
                    "name": zone.name,
                    "zone_type": zone.zone_type,
                    "entity_ids": list(zone.entity_ids),
                    "priority": zone.priority,
                    "tags": list(zone.tags),
                    "current_state": zone.current_state,
                }
                if zone.entities:
                    zone_data["entities"] = {
                        k: list(v) for k, v in zone.entities.items()
                    }
                if zone.parent_zone_id:
                    zone_data["parent_zone_id"] = zone.parent_zone_id
                if zone.child_zone_ids:
                    zone_data["child_zone_ids"] = list(zone.child_zone_ids)
                if zone.floor:
                    zone_data["floor"] = zone.floor

                payload.append(zone_data)

            await self.client.async_post(
                "/api/v1/zone-automation/sync-zones",
                {"zones": payload},
            )
            _LOGGER.debug("Synced %d zones to Core", len(payload))

        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Zone sync to Core failed: %s", err)

    # ------------------------------------------------------------------
    # Entity auto-tagging
    # ------------------------------------------------------------------

    async def _auto_tag_zone_entities(self, zone: HabitusZoneV2) -> None:
        """Auto-detect entity domains and create tags for a zone.

        For every entity in the zone:
        1. Create/update a **domain tag** (e.g. ``licht`` for ``light.*``).
        2. Create/update a **zone tag** derived from the zone name.
        3. Ensure the entity appears in both tags so that querying
           ``wohnbereich`` + ``licht`` returns all lights in that zone.
        """
        all_entities = zone.get_all_entities()
        if not all_entities:
            return

        # Derive zone tag from zone name
        zone_tag_id = _slugify(zone.name)
        zone_tag_name = zone.name

        # Collect entities per domain tag
        domain_entity_buckets: dict[str, list[str]] = {}
        zone_entity_list: list[str] = []

        for entity_id in all_entities:
            domain = _entity_domain(entity_id)
            tag_info = DOMAIN_TAG_MAP.get(domain)
            if tag_info:
                tag_id = tag_info[0]
                domain_entity_buckets.setdefault(tag_id, []).append(entity_id)
            zone_entity_list.append(entity_id)

        # Upsert domain tags — merge with existing entity lists
        existing_tags = await async_get_entity_tags(self.hass)

        for tag_id, new_entities in domain_entity_buckets.items():
            tag_info = None
            for domain, info in DOMAIN_TAG_MAP.items():
                if info[0] == tag_id:
                    tag_info = info
                    break
            if tag_info is None:
                continue

            _, display_name, color, icon = tag_info

            # Merge: keep existing entities that belong to *other* zones
            existing = existing_tags.get(tag_id)
            merged_entities: list[str]
            if existing:
                merged_set = set(existing.entity_ids) | set(new_entities)
                merged_entities = sorted(merged_set)
            else:
                merged_entities = sorted(set(new_entities))

            await async_upsert_tag(
                self.hass,
                tag_id=tag_id,
                name=display_name,
                entity_ids=merged_entities,
                color=color,
                icon=icon,
            )

        # Upsert zone tag
        if zone_entity_list:
            existing_zone_tag = existing_tags.get(zone_tag_id)
            if existing_zone_tag:
                merged_zone = sorted(
                    set(existing_zone_tag.entity_ids) | set(zone_entity_list)
                )
            else:
                merged_zone = sorted(set(zone_entity_list))

            await async_upsert_tag(
                self.hass,
                tag_id=zone_tag_id,
                name=zone_tag_name,
                entity_ids=merged_zone,
                color="#94a3b8",  # neutral slate for zone tags
                icon="mdi:home-map-marker",
            )

        _LOGGER.debug(
            "Auto-tagged %d entities in zone %s (%d domain buckets + zone tag '%s')",
            len(all_entities),
            zone.zone_id,
            len(domain_entity_buckets),
            zone_tag_id,
        )


# ---------------------------------------------------------------------------
# Module-level helpers (for integration setup)
# ---------------------------------------------------------------------------

async def async_setup_automation_engine(
    hass: HomeAssistant,
    entry: ConfigEntry,
    client: CopilotApiClient,
) -> AutomationEngine:
    """Create, start, and register the AutomationEngine.

    Call this from ``__init__.py`` or ``core/modules/legacy.py`` during
    integration setup. The engine is stored in ``hass.data`` under the
    entry's namespace so other modules and the unload path can reach it.

    Returns:
        The running AutomationEngine instance.
    """
    engine = AutomationEngine(hass, entry, client)
    await engine.async_start()

    # Store reference for unload
    entry_store = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    if isinstance(entry_store, dict):
        entry_store["automation_engine"] = engine

    return engine


async def async_unload_automation_engine(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Stop and remove the AutomationEngine for a config entry.

    Call this from the integration's ``async_unload_entry`` path.
    """
    entry_store = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if isinstance(entry_store, dict):
        engine: AutomationEngine | None = entry_store.pop("automation_engine", None)
        if engine is not None:
            await engine.async_stop()
