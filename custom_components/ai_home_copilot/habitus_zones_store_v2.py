"""Habitus Zones Store v2 - mit Brain Graph Integration.

Features:
- Zone-based entity management with role mapping
- Priority-based zone conflict resolution for overlapping zones
- State persistence using HA Storage API
- Brain Graph integration for context awareness
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Literal

import asyncio

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect
from homeassistant.const import EVENT_HOMEASSISTANT_START

from .const import DOMAIN

STORAGE_VERSION = 2
STORAGE_KEY = f"{DOMAIN}.habitus_zones_v2"

SIGNAL_HABITUS_ZONES_V2_UPDATED = f"{DOMAIN}_habitus_zones_v2_updated"
SIGNAL_HABITUS_ZONE_CONFLICT = f"{DOMAIN}_habitus_zone_conflict"

# Module-level lock dict for storage race condition fix (D1)
_store_locks: Dict[str, asyncio.Lock] = {}


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving zone conflicts."""
    PRIORITY = "priority"           # Higher priority zone wins
    HIERARCHY = "hierarchy"         # More specific (child) zone wins
    USER_PROMPT = "user_prompt"     # Ask user to resolve
    MERGE = "merge"                 # Merge overlapping entities
    FIRST_WINS = "first_wins"       # First active zone wins

# Zone Types
ZONE_TYPE = Literal["room", "area", "floor", "outdoor"]

# Zone States (State Machine)
ZONE_STATE = Literal["idle", "active", "transitioning", "disabled", "error"]

# Role Types (Entity Assignments)
KNOWN_ROLES = {
    "motion", "lights", "temperature", "humidity", "co2", "pressure",
    "noise", "heating", "door", "window", "cover", "lock", "media",
    "power", "energy", "brightness", "other"
}

_MOTION_HINTS = (
    "motion",
    "presence",
    "occupancy",
    "bewegung",
    "praesenz",
    "präsenz",
    "anwesenheit",
    "pir",
    "belegt",
    "besetzt",
)


@dataclass(frozen=True, slots=True)
class HabitusZoneV2:
    """Habitus Zone v2 mit Brain Graph Integration.
    
    Properties:
    - Core Identity: zone_id, name, zone_type
    - Entity Membership: entity_ids (flat), entities (role-basiert)
    - Hierarchy: parent_zone_id, child_zone_ids, floor
    - Brain Graph: graph_node_id, in_edges, out_edges
    - State Machine: current_state, state_since
    - Metadata: priority, tags, metadata
    """
    # Core Identity
    zone_id: str                           # namespaced: "zone:wohnzimmer"
    name: str                              # Display-Name
    zone_type: ZONE_TYPE = "room"          # "room", "area", "floor", "outdoor"

    # Entity Membership
    entity_ids: tuple[str, ...] = field(default_factory=tuple)  # Flat list (legacy)
    entities: dict[str, tuple[str, ...]] | None = None  # Role-basiert

    # Hierarchy
    parent_zone_id: str | None = None      # "zone:living_area"
    child_zone_ids: tuple[str, ...] = field(default_factory=tuple)
    floor: str | None = None               # "EG", "OG", "UG"

    # Brain Graph Integration
    graph_node_id: str | None = None       # Auto-sync: "zone:wohnzimmer"
    in_edges: tuple[str, ...] = field(default_factory=tuple)   # Entity-IDs in Zone
    out_edges: tuple[str, ...] = field(default_factory=tuple)  # Zone→Entity Controls

    # State Machine
    current_state: ZONE_STATE = "idle"
    state_since_ms: int | None = None

    # Metadata
    priority: int = 0                      # 0=niedrig, 10=hoch
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        """Validate zone after construction."""
        if not self.zone_id:
            raise ValueError("zone_id is required")
        if self.zone_type not in ("room", "area", "floor", "outdoor"):
            raise ValueError(f"Invalid zone_type: {self.zone_type}")
        if self.current_state not in ("idle", "active", "transitioning", "disabled", "error"):
            raise ValueError(f"Invalid state: {self.current_state}")
        
        # Auto-set graph_node_id if not provided
        if self.graph_node_id is None:
            object.__setattr__(self, 'graph_node_id', self.zone_id)

    @property
    def hierarchy_level(self) -> int:
        """Calculate hierarchy level (0=root, 1=area, 2=room)."""
        if self.zone_type == "floor":
            return 0
        elif self.zone_type == "area":
            return 1
        elif self.zone_type == "room":
            return 2
        return 3

    def get_role_entities(self, role: str) -> list[str]:
        """Get entities for a specific role."""
        if self.entities is None:
            return []
        return list(self.entities.get(role, ()))

    def get_all_entities(self) -> set[str]:
        """Get all entities (from both flat list and role mapping)."""
        result = set(self.entity_ids)
        if self.entities:
            for entities in self.entities.values():
                result.update(entities)
        return result


@dataclass(frozen=True, slots=True)
class ZoneConflict:
    """Represents a detected zone conflict.
    
    Attributes:
        zone_ids: IDs of conflicting zones
        overlapping_entities: Entity IDs that overlap between zones
        detected_at_ms: Timestamp when conflict was detected
        resolution: Strategy used to resolve (None if not yet resolved)
        winning_zone_id: Zone that won after resolution (None if unresolved)
    """
    zone_ids: tuple[str, ...]
    overlapping_entities: tuple[str, ...]
    detected_at_ms: int
    resolution: ConflictResolutionStrategy | None = None
    winning_zone_id: str | None = None


class ZoneConflictResolver:
    """Resolves conflicts between overlapping zones.
    
    A zone conflict occurs when:
    1. Two or more zones share overlapping entities
    2. Multiple zones become "active" simultaneously
    
    Resolution strategies (in order of precedence):
    1. HIERARCHY: Child zones override parent zones
    2. PRIORITY: Higher priority zones override lower ones
    3. USER_PROMPT: Emit event for user to resolve
    
    Usage:
        resolver = ZoneConflictResolver(hass, zones)
        active_zones = await resolver.resolve_conflicts(activated_zones)
    """
    
    def __init__(
        self,
        hass: HomeAssistant,
        zones: list[HabitusZoneV2],
        default_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.HIERARCHY
    ):
        """Initialize the conflict resolver.
        
        Args:
            hass: Home Assistant instance
            zones: List of all zones
            default_strategy: Default resolution strategy
        """
        self._hass = hass
        self._zones = {z.zone_id: z for z in zones}
        self._default_strategy = default_strategy
        self._entity_to_zones: dict[str, list[str]] = self._build_entity_index()
        self._conflict_history: list[ZoneConflict] = []
    
    def _build_entity_index(self) -> dict[str, list[str]]:
        """Build mapping from entity_id to zones containing it."""
        index: dict[str, list[str]] = {}
        for zone in self._zones.values():
            for entity_id in zone.get_all_entities():
                if entity_id not in index:
                    index[entity_id] = []
                index[entity_id].append(zone.zone_id)
        return index
    
    def find_overlapping_zones(self) -> list[tuple[str, str, set[str]]]:
        """Find all zone pairs that share entities.
        
        Returns:
            List of tuples: (zone_id_1, zone_id_2, overlapping_entities)
        """
        overlaps: list[tuple[str, str, set[str]]] = []
        processed: set[tuple[str, str]] = set()
        
        for entity_id, zone_ids in self._entity_to_zones.items():
            if len(zone_ids) > 1:
                # Entity belongs to multiple zones
                for i, zid1 in enumerate(zone_ids):
                    for zid2 in zone_ids[i + 1:]:
                        pair = (min(zid1, zid2), max(zid1, zid2))
                        if pair in processed:
                            continue
                        processed.add(pair)
                        
                        # Calculate all overlapping entities
                        z1 = self._zones.get(zid1)
                        z2 = self._zones.get(zid2)
                        if z1 and z2:
                            overlap = z1.get_all_entities() & z2.get_all_entities()
                            if overlap:
                                overlaps.append((zid1, zid2, overlap))
        
        return overlaps
    
    async def resolve_conflicts(
        self,
        active_zone_ids: list[str],
        strategy: ConflictResolutionStrategy | None = None
    ) -> tuple[list[str], list[ZoneConflict]]:
        """Resolve conflicts between active zones.
        
        Args:
            active_zone_ids: List of zone IDs that are currently active
            strategy: Override resolution strategy (uses default if None)
        
        Returns:
            Tuple of (resolved_active_zone_ids, conflicts_detected)
        """
        if not active_zone_ids or len(active_zone_ids) <= 1:
            return (active_zone_ids, [])
        
        strategy = strategy or self._default_strategy
        conflicts: list[ZoneConflict] = []
        resolved_zones: set[str] = set(active_zone_ids)
        
        # Check for entity overlaps between active zones
        for entity_id, zone_ids in self._entity_to_zones.items():
            active_owners = [zid for zid in zone_ids if zid in resolved_zones]
            
            if len(active_owners) > 1:
                # Conflict detected - entity belongs to multiple active zones
                import time
                conflict = ZoneConflict(
                    zone_ids=tuple(active_owners),
                    overlapping_entities=(entity_id,),
                    detected_at_ms=int(time.time() * 1000),
                )
                
                # Resolve based on strategy
                winning_zone = self._apply_resolution_strategy(
                    conflict, strategy
                )
                
                if winning_zone:
                    # Remove losing zones from active set
                    resolved_zones -= set(active_owners) - {winning_zone}
                    
                    # Update conflict record
                    conflict = ZoneConflict(
                        zone_ids=conflict.zone_ids,
                        overlapping_entities=conflict.overlapping_entities,
                        detected_at_ms=conflict.detected_at_ms,
                        resolution=strategy,
                        winning_zone_id=winning_zone,
                    )
                
                conflicts.append(conflict)
                self._conflict_history.append(conflict)
        
        # Fire HA event for any detected conflicts
        if conflicts:
            self._fire_conflict_event(conflicts, strategy)
        
        return (list(resolved_zones), conflicts)
    
    def _apply_resolution_strategy(
        self,
        conflict: ZoneConflict,
        strategy: ConflictResolutionStrategy
    ) -> str | None:
        """Apply resolution strategy to determine winning zone.
        
        Args:
            conflict: The detected conflict
            strategy: Resolution strategy to apply
        
        Returns:
            Zone ID that wins the conflict, or None if unresolved
        """
        if strategy == ConflictResolutionStrategy.HIERARCHY:
            return self._resolve_by_hierarchy(conflict.zone_ids)
        elif strategy == ConflictResolutionStrategy.PRIORITY:
            return self._resolve_by_priority(conflict.zone_ids)
        elif strategy == ConflictResolutionStrategy.FIRST_WINS:
            return conflict.zone_ids[0] if conflict.zone_ids else None
        elif strategy == ConflictResolutionStrategy.USER_PROMPT:
            # Emit event but don't auto-resolve
            return None
        elif strategy == ConflictResolutionStrategy.MERGE:
            # Not applicable for single-entity conflicts
            return conflict.zone_ids[0] if conflict.zone_ids else None
        
        return None
    
    def _resolve_by_hierarchy(self, zone_ids: tuple[str, ...]) -> str | None:
        """Resolve by hierarchy level (more specific child wins).
        
        Zones with higher hierarchy_level (more specific) win.
        """
        max_level = -1
        winning_zone = None
        
        for zid in zone_ids:
            zone = self._zones.get(zid)
            if zone and zone.hierarchy_level > max_level:
                max_level = zone.hierarchy_level
                winning_zone = zid
        
        return winning_zone
    
    def _resolve_by_priority(self, zone_ids: tuple[str, ...]) -> str | None:
        """Resolve by priority (higher priority wins)."""
        max_priority = -1
        winning_zone = None
        
        for zid in zone_ids:
            zone = self._zones.get(zid)
            if zone and zone.priority > max_priority:
                max_priority = zone.priority
                winning_zone = zid
        
        return winning_zone
    
    def _fire_conflict_event(
        self,
        conflicts: list[ZoneConflict],
        strategy: ConflictResolutionStrategy
    ) -> None:
        """Fire HA event for zone conflicts."""
        async_dispatcher_send(
            self._hass,
            SIGNAL_HABITUS_ZONE_CONFLICT,
            {
                "conflicts": [
                    {
                        "zone_ids": list(c.zone_ids),
                        "overlapping_entities": list(c.overlapping_entities),
                        "detected_at_ms": c.detected_at_ms,
                        "resolution": c.resolution.value if c.resolution else None,
                        "winning_zone_id": c.winning_zone_id,
                    }
                    for c in conflicts
                ],
                "strategy": strategy.value,
            }
        )
    
    def get_conflict_history(self) -> list[ZoneConflict]:
        """Get history of detected conflicts."""
        return list(self._conflict_history)
    
    def clear_conflict_history(self) -> None:
        """Clear conflict history."""
        self._conflict_history.clear()


# Role Aliases (wie v1)
_ROLE_ALIASES: dict[str, str] = {
    # required
    "motion": "motion",
    "presence": "motion",
    "occupancy": "motion",
    "lights": "lights",
    "light": "lights",
    # common extras
    "brightness": "brightness",
    "illuminance": "brightness",
    "heating": "heating",
    "climate": "heating",
    "humidity": "humidity",
    "luftfeuchte": "humidity",
    "temperature": "temperature",
    "temperatur": "temperature",
    "co2": "co2",
    "carbon_dioxide": "co2",
    "noise": "noise",
    "larm": "noise",
    "pressure": "pressure",
    "luftdruck": "pressure",
    "cover": "cover",
    "rollo": "cover",
    "shutter": "cover",
    "lock": "lock",
    "schloss": "lock",
    "door": "door",
    "tuer": "door",
    "window": "window",
    "fenster": "window",
    "media": "media",
    "volume": "media",
    # power/energy
    "power": "power",
    "leistung": "power",
    "strom": "power",
    "energy": "energy",
    "energie": "energy",
    "other": "other",
}


def _as_tuple(val: Any) -> tuple[str, ...]:
    """Convert value to tuple of strings."""
    if val is None:
        return ()
    if isinstance(val, (list, tuple)):
        return tuple(str(x).strip() for x in val if str(x).strip())
    if isinstance(val, str) and val.strip():
        return tuple(p.strip() for p in val.replace("\n", ",").split(",") if p.strip())
    return ()


def _parse_entities_mapping(raw: Any) -> dict[str, tuple[str, ...]] | None:
    """Parse role-based entity mapping."""
    if not isinstance(raw, dict):
        return None

    out: dict[str, tuple[str, ...]] = {}
    for k, v in raw.items():
        key = str(k).strip().lower()
        if not key:
            continue
        key = _ROLE_ALIASES.get(key, key)
        items = _as_tuple(v)
        if items:
            # De-dupe
            seen = set()
            uniq = []
            for e in items:
                if e in seen:
                    continue
                seen.add(e)
                uniq.append(e)
            out[key] = tuple(uniq)

    # Prevent cross-role duplicates in `other`
    if "other" in out:
        assigned: set[str] = set()
        for k, items in out.items():
            if k == "other":
                continue
            assigned.update(items)
        other = [e for e in out.get("other", ()) if e not in assigned]
        if other:
            out["other"] = tuple(other)
        else:
            out.pop("other", None)

    return out or None


def _normalize_zone_v2(obj: dict[str, Any], default_floor: str | None = None) -> HabitusZoneV2 | None:
    """Normalize dict to HabitusZoneV2."""
    zid = str(obj.get("id") or obj.get("zone_id") or "").strip()
    name = str(obj.get("name") or zid).strip()

    if not zid:
        return None

    # Zone type
    zone_type_raw = str(obj.get("zone_type", "room")).lower()
    zone_type: ZONE_TYPE = "room"
    if zone_type_raw in ("room", "area", "floor", "outdoor"):
        zone_type = zone_type_raw

    # Entity membership (flat)
    ent_flat = obj.get("entity_ids") or obj.get("entity_id")
    flat_list = _as_tuple(ent_flat)

    # Entity membership (role-based)
    ent_map_raw = obj.get("entities") or obj.get("roles") or obj.get("signals") or obj.get("kinds")
    ent_map = _parse_entities_mapping(ent_map_raw)

    # Merge flat list into role mapping as "other"
    if flat_list and isinstance(ent_map, dict):
        assigned: set[str] = set()
        for items in ent_map.values():
            assigned.update(items)
        extras = [e for e in flat_list if e and e not in assigned]
        if extras:
            existing = ent_map.get("other", ())
            combined = tuple(set(existing) | set(extras))
            ent_map["other"] = combined

    # Union for runtime
    all_ids: list[str] = []
    all_ids.extend(flat_list)
    if isinstance(ent_map, dict):
        for items in ent_map.values():
            all_ids.extend(items)
    
    # De-dupe while keeping order
    seen: set[str] = set()
    uniq: list[str] = []
    for e in all_ids:
        if not e or e in seen:
            continue
        seen.add(e)
        uniq.append(e)

    # Hierarchy
    parent_zone_id = obj.get("parent") or obj.get("parent_zone_id")
    if parent_zone_id:
        parent_zone_id = str(parent_zone_id).strip() or None

    child_zone_ids = _as_tuple(obj.get("child_zones") or obj.get("child_zone_ids"))
    
    # Floor
    floor = obj.get("floor") or default_floor
    if floor:
        floor = str(floor).strip() or None

    # State Machine
    current_state_raw = str(obj.get("current_state", "idle")).lower()
    current_state: ZONE_STATE = "idle"
    if current_state_raw in ("idle", "active", "transitioning", "disabled", "error"):
        current_state = current_state_raw

    # Metadata
    # E1: Crash on Bad Priority Input - handle invalid priority gracefully
    priority_raw = obj.get("priority", 0)
    try:
        priority = int(priority_raw)
    except (ValueError, TypeError):
        priority = 0
        logging.getLogger(__name__).warning("Invalid priority %r for zone %s, using default", priority_raw, zid)
    tags = _as_tuple(obj.get("tags"))
    metadata = obj.get("metadata")
    if metadata and not isinstance(metadata, dict):
        metadata = None

    # Graph node ID
    graph_node_id = obj.get("graph_node_id")

    return HabitusZoneV2(
        zone_id=zid,
        name=name or zid,
        zone_type=zone_type,
        entity_ids=tuple(uniq),
        entities=ent_map,
        parent_zone_id=parent_zone_id,
        child_zone_ids=child_zone_ids,
        floor=floor,
        graph_node_id=graph_node_id,
        current_state=current_state,
        priority=priority,
        tags=tags,
        metadata=metadata,
    )


def _store(hass: HomeAssistant) -> Store:
    """Get or create the store."""
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    st = global_data.get("habitus_zones_v2_store")
    if st is None:
        st = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        global_data["habitus_zones_v2_store"] = st
    return st


async def async_get_zones_v2(hass: HomeAssistant, entry_id: str) -> list[HabitusZoneV2]:
    """Load zones v2 for a config entry."""
    data = await _store(hass).async_load() or {}
    entries = data.get("entries") if isinstance(data.get("entries"), dict) else {}
    raw = entries.get(entry_id, [])
    zones: list[HabitusZoneV2] = []
    default_floor = data.get("default_floor")

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                z = _normalize_zone_v2(item, default_floor)
                if z:
                    zones.append(z)
    return zones


async def async_set_zones_v2(
    hass: HomeAssistant, 
    entry_id: str, 
    zones: list[HabitusZoneV2],
    validate: bool = True
) -> None:
    """Save zones v2 for a config entry."""
    # D1: Storage Race Condition fix - use per-entry lock
    lock = _store_locks.setdefault(entry_id, asyncio.Lock())
    async with lock:
        # Validate if requested
        if validate:
            for z in zones:
                _validate_zone_v2(hass, z)

        st = _store(hass)
        data = await st.async_load() or {}
        entries = data.setdefault("entries", {})
        if not isinstance(entries, dict):
            entries = {}
            data["entries"] = entries

        entries[entry_id] = [
            {
                "id": z.zone_id,
                "name": z.name,
                "zone_type": z.zone_type,
                "entity_ids": list(z.entity_ids),
                **({"entities": {k: list(v) for k, v in z.entities.items()}} if z.entities else {}),
                **({"parent": z.parent_zone_id} if z.parent_zone_id else {}),
                **({"child_zones": list(z.child_zone_ids)} if z.child_zone_ids else {}),
                **({"floor": z.floor} if z.floor else {}),
                **({"graph_node_id": z.graph_node_id} if z.graph_node_id else {}),
                "current_state": z.current_state,
                "priority": z.priority,
                "tags": list(z.tags),
                **({"metadata": z.metadata} if z.metadata else {}),
            }
            for z in zones
        ]

        await st.async_save(data)
        async_dispatcher_send(hass, SIGNAL_HABITUS_ZONES_V2_UPDATED, entry_id)


def _domain(entity_id: str) -> str:
    """Extract domain from entity_id."""
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def _is_light_entity(entity_id: str) -> bool:
    """Check if entity is a light."""
    return _domain(entity_id) == "light"


def _is_motion_or_presence_entity(hass: HomeAssistant, entity_id: str) -> bool:
    """Check if entity is a motion/presence sensor."""
    dom = _domain(entity_id)
    if dom not in ("binary_sensor", "sensor"):
        return False

    st = hass.states.get(entity_id)
    device_class = None
    if st is not None:
        device_class = st.attributes.get("device_class")

    if device_class in ("motion", "presence", "occupancy"):
        return True

    try:
        from homeassistant.helpers import entity_registry

        reg = entity_registry.async_get(hass)
        reg_ent = reg.async_get(entity_id) if reg is not None else None
        reg_dc = getattr(reg_ent, "device_class", None)
        if isinstance(reg_dc, str) and reg_dc.lower() in ("motion", "presence", "occupancy"):
            return True
        labels = [entity_id.lower()]
        if isinstance(getattr(reg_ent, "original_name", None), str):
            labels.append(reg_ent.original_name.lower())
        if st is not None and isinstance(st.attributes.get("friendly_name"), str):
            labels.append(st.attributes["friendly_name"].lower())
    except Exception:  # noqa: BLE001
        labels = [entity_id.lower()]
        if st is not None and isinstance(st.attributes.get("friendly_name"), str):
            labels.append(st.attributes["friendly_name"].lower())

    # Fallback heuristic
    merged = " ".join(labels)
    return any(k in merged for k in _MOTION_HINTS)


def _validate_zone_v2(hass: HomeAssistant, z: HabitusZoneV2) -> None:
    """Validate zone requirements.

    Policy:
    - each zone must include at least one valid entity_id
    - motion/light roles are optional (recommended, not mandatory)
    """
    motion_candidates: list[str] = []
    light_candidates: list[str] = []
    all_candidates = [str(eid).strip() for eid in z.get_all_entities() if str(eid).strip()]

    if isinstance(z.entities, dict):
        motion_candidates.extend(z.entities.get("motion") or [])
        light_candidates.extend(z.entities.get("lights") or [])

    valid_entities = [eid for eid in all_candidates if "." in eid and _domain(eid)]
    if not valid_entities:
        raise ValueError(
            f"Zone '{z.zone_id}' must include at least 1 valid entity_id (domain.object)."
        )

    # Optional quality checks (non-blocking): motion/light availability.
    motion_scan = any(_is_motion_or_presence_entity(hass, eid) for eid in z.entity_ids)
    light_scan = any(_is_light_entity(eid) for eid in z.entity_ids)

    has_motion = (
        any(_is_motion_or_presence_entity(hass, eid) for eid in motion_candidates)
        if motion_candidates
        else motion_scan
    )
    if motion_candidates and not has_motion:
        # Explicitly selected motion role: accept binary_sensor/sensor assignments
        # even when device_class metadata is missing.
        has_motion = any(_domain(eid) in ("binary_sensor", "sensor") for eid in motion_candidates)
    has_light = (
        any(_is_light_entity(eid) for eid in light_candidates) if light_candidates else light_scan
    )
    # If both key signal categories are absent, keep zone valid and let
    # higher layers surface UX hints. This avoids hard-blocking setup flows.
    _ = has_motion, has_light


async def async_set_zones_v2_from_raw(
    hass: HomeAssistant, 
    entry_id: str, 
    raw: Any,
    validate: bool = True
) -> list[HabitusZoneV2]:
    """Validate + normalize and persist zones v2.
    
    Accepts:
    - list[dict]
    - dict with key "zones": list[dict]
    """
    if isinstance(raw, dict) and isinstance(raw.get("zones"), list):
        raw = raw.get("zones")

    if not isinstance(raw, list):
        raise ValueError("Zones must be a list (or {zones:[...]}).")

    default_floor = None
    if isinstance(raw, dict):
        default_floor = raw.get("default_floor")

    zones: list[HabitusZoneV2] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        z = _normalize_zone_v2(item, default_floor)
        if z:
            zones.append(z)

    # Ensure unique zone ids
    seen: set[str] = set()
    uniq: list[HabitusZoneV2] = []
    for z in zones:
        if z.zone_id in seen:
            continue
        seen.add(z.zone_id)
        uniq.append(z)

    # Validate requirements
    if validate:
        for z in uniq:
            _validate_zone_v2(hass, z)

    await async_set_zones_v2(hass, entry_id, uniq, validate=False)
    return uniq


# =============================================================================
# State Persistence - Zone states saved across HA restarts
# =============================================================================

STATE_STORAGE_VERSION = 1
STATE_STORAGE_KEY = f"{DOMAIN}.habitus_zones_state"

SIGNAL_HABITUS_ZONE_STATE_CHANGED = f"{DOMAIN}_habitus_zone_state_changed"


def _state_store(hass: HomeAssistant) -> Store:
    """Get or create the zone state store."""
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    st = global_data.get("habitus_zones_state_store")
    if st is None:
        st = Store(hass, STATE_STORAGE_VERSION, STATE_STORAGE_KEY)
        global_data["habitus_zones_state_store"] = st
    return st


async def async_get_zone_states(
    hass: HomeAssistant,
    entry_id: str
) -> dict[str, dict[str, Any]]:
    """Load persisted zone states for a config entry.
    
    Returns dict mapping zone_id to state data:
    {
        "zone:wohnzimmer": {
            "current_state": "active",
            "state_since_ms": 1234567890,
            "last_transition_ms": 1234567890,
        },
        ...
    }
    """
    store = _state_store(hass)
    data = await store.async_load() or {}
    entries = data.get("entries") if isinstance(data.get("entries"), dict) else {}
    return entries.get(entry_id, {})


async def async_set_zone_state(
    hass: HomeAssistant,
    entry_id: str,
    zone_id: str,
    new_state: ZONE_STATE,
    fire_event: bool = True
) -> bool:
    """Persist a zone state change.
    
    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID
        zone_id: Zone ID to update
        new_state: New zone state
        fire_event: Whether to fire HA event on state change
    
    Returns:
        True if state was changed, False if already in target state
    """
    import time
    
    store = _state_store(hass)
    data = await store.async_load() or {}
    entries = data.setdefault("entries", {})
    if not isinstance(entries, dict):
        entries = {}
        data["entries"] = entries
    
    entry_states = entries.setdefault(entry_id, {})
    if not isinstance(entry_states, dict):
        entry_states = {}
        entries[entry_id] = entry_states
    
    now_ms = int(time.time() * 1000)
    
    # Get previous state
    prev_state_data = entry_states.get(zone_id, {})
    prev_state = prev_state_data.get("current_state", "idle")
    
    # Check if state is actually changing
    if prev_state == new_state:
        return False
    
    # Update state
    entry_states[zone_id] = {
        "current_state": new_state,
        "state_since_ms": now_ms,
        "last_transition_ms": now_ms,
        "previous_state": prev_state,
    }
    
    # Persist
    await store.async_save(data)
    
    # Fire event if requested
    if fire_event:
        async_dispatcher_send(
            hass,
            SIGNAL_HABITUS_ZONE_STATE_CHANGED,
            {
                "entry_id": entry_id,
                "zone_id": zone_id,
                "previous_state": prev_state,
                "new_state": new_state,
                "timestamp_ms": now_ms,
            }
        )
    
    return True


async def async_persist_all_zone_states(
    hass: HomeAssistant,
    entry_id: str,
    zones: list[HabitusZoneV2]
) -> None:
    """Persist all zone states at once (e.g., on HA shutdown).
    
    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID
        zones: List of zones with their current states
    """
    import time
    
    store = _state_store(hass)
    data = await store.async_load() or {}
    entries = data.setdefault("entries", {})
    
    now_ms = int(time.time() * 1000)
    entry_states = entries.setdefault(entry_id, {})
    
    for zone in zones:
        prev_data = entry_states.get(zone.zone_id, {})
        prev_state = prev_data.get("current_state", "idle")
        
        entry_states[zone.zone_id] = {
            "current_state": zone.current_state,
            "state_since_ms": zone.state_since_ms or now_ms,
            "last_transition_ms": now_ms if prev_state != zone.current_state else prev_data.get("last_transition_ms", now_ms),
            "previous_state": prev_state if prev_state != zone.current_state else prev_data.get("previous_state"),
        }
    
    await store.async_save(data)


async def async_restore_zone_states(
    hass: HomeAssistant,
    entry_id: str,
    zones: list[HabitusZoneV2]
) -> list[HabitusZoneV2]:
    """Restore zone states from persisted storage.
    
    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID
        zones: List of zones to restore states for
    
    Returns:
        List of zones with restored states
    """
    persisted_states = await async_get_zone_states(hass, entry_id)
    
    restored_zones: list[HabitusZoneV2] = []
    for zone in zones:
        state_data = persisted_states.get(zone.zone_id, {})
        persisted_state = state_data.get("current_state", "idle")
        state_since = state_data.get("state_since_ms")
        
        # Create zone with restored state
        restored_zone = HabitusZoneV2(
            zone_id=zone.zone_id,
            name=zone.name,
            zone_type=zone.zone_type,
            entity_ids=zone.entity_ids,
            entities=zone.entities,
            parent_zone_id=zone.parent_zone_id,
            child_zone_ids=zone.child_zone_ids,
            floor=zone.floor,
            graph_node_id=zone.graph_node_id,
            current_state=persisted_state if persisted_state in ("idle", "active", "transitioning", "disabled", "error") else "idle",
            state_since_ms=state_since,
            priority=zone.priority,
            tags=zone.tags,
            metadata=zone.metadata,
        )
        restored_zones.append(restored_zone)
    
    return restored_zones


# =============================================================================
# Conflict Resolver Factory
# =============================================================================

def get_conflict_resolver(
    hass: HomeAssistant,
    entry_id: str,
    zones: list[HabitusZoneV2] | None = None,
    strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.HIERARCHY
) -> ZoneConflictResolver | None:
    """Get or create a conflict resolver for a config entry.
    
    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID
        zones: List of zones (loaded from storage if not provided)
        strategy: Default conflict resolution strategy
    
    Returns:
        ZoneConflictResolver instance or None if no zones available
    """
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    resolvers = global_data.setdefault("conflict_resolvers", {})
    
    # Return cached resolver if exists and zones unchanged
    if entry_id in resolvers and zones is None:
        return resolvers[entry_id]
    
    # Create new resolver
    if zones is None:
        # Try to get zones from storage synchronously (for sync contexts)
        # Note: In async context, use async_get_conflict_resolver instead
        return None
    
    resolver = ZoneConflictResolver(hass, zones, strategy)
    resolvers[entry_id] = resolver
    return resolver


async def async_get_conflict_resolver(
    hass: HomeAssistant,
    entry_id: str,
    strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.HIERARCHY
) -> ZoneConflictResolver:
    """Async get or create a conflict resolver for a config entry.
    
    Loads zones from storage if resolver doesn't exist.
    
    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID
        strategy: Default conflict resolution strategy
    
    Returns:
        ZoneConflictResolver instance
    """
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    resolvers = global_data.setdefault("conflict_resolvers", {})
    
    if entry_id in resolvers:
        return resolvers[entry_id]
    
    # Load zones and create resolver
    zones = await async_get_zones_v2(hass, entry_id)
    resolver = ZoneConflictResolver(hass, zones, strategy)
    resolvers[entry_id] = resolver
    return resolver


async def async_resolve_zone_conflicts(
    hass: HomeAssistant,
    entry_id: str,
    active_zone_ids: list[str],
    strategy: ConflictResolutionStrategy | None = None
) -> tuple[list[str], list[ZoneConflict]]:
    """Convenience function to resolve zone conflicts.
    
    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID
        active_zone_ids: List of zone IDs that are currently active
        strategy: Override resolution strategy
    
    Returns:
        Tuple of (resolved_active_zone_ids, conflicts_detected)
    """
    resolver = await async_get_conflict_resolver(hass, entry_id)
    return await resolver.resolve_conflicts(active_zone_ids, strategy)


# Migration Support (v1 → v2)
async def async_migrate_from_v1(
    hass: HomeAssistant,
    entry_id: str,
    v1_zones: list["HabitusZoneV2"]  # noqa: F821 - forward ref
) -> list[HabitusZoneV2]:
    """Migrate zones from v1 format to v2.
    
    This is a helper to convert old HabitusZone to HabitusZoneV2.
    """
    v2_zones: list[HabitusZoneV2] = []
    
    for z in v1_zones:
        v2_zone = HabitusZoneV2(
            zone_id=z.zone_id,
            name=z.name,
            zone_type="room",  # Default
            entity_ids=z.entity_ids,
            entities=z.entities,
            current_state="idle",
            priority=0,
            tags=(),
            metadata={"migrated_from_v1": True},
        )
        v2_zones.append(v2_zone)
    
    return v2_zones
