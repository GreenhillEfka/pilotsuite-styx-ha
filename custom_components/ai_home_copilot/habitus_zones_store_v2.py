"""Habitus Zones Store v2 - mit Brain Graph Integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN

STORAGE_VERSION = 2
STORAGE_KEY = f"{DOMAIN}.habitus_zones_v2"

SIGNAL_HABITUS_ZONES_V2_UPDATED = f"{DOMAIN}_habitus_zones_v2_updated"

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
    priority = int(obj.get("priority", 0))
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

    # Fallback heuristic
    eid_l = entity_id.lower()
    return any(k in eid_l for k in ("motion", "presence", "occupancy"))


def _validate_zone_v2(hass: HomeAssistant, z: HabitusZoneV2) -> None:
    """Validate zone requirements.
    
    Policy: each zone must have:
    - at least one motion/presence entity
    - at least one light entity
    """
    motion_candidates: list[str] = []
    light_candidates: list[str] = []

    if isinstance(z.entities, dict):
        motion_candidates.extend(z.entities.get("motion") or [])
        light_candidates.extend(z.entities.get("lights") or [])

    # Fallback: scan flat list
    motion_scan = any(_is_motion_or_presence_entity(hass, eid) for eid in z.entity_ids)
    light_scan = any(_is_light_entity(eid) for eid in z.entity_ids)

    has_motion = (
        any(_is_motion_or_presence_entity(hass, eid) for eid in motion_candidates)
        if motion_candidates
        else motion_scan
    )
    has_light = (
        any(_is_light_entity(eid) for eid in light_candidates) if light_candidates else light_scan
    )

    if not has_motion or not has_light:
        raise ValueError(
            f"Zone '{z.zone_id}' must include at least 1 motion/presence entity and 1 light entity. "
            f"Found motion/presence={has_motion}, light={has_light}."
        )


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
