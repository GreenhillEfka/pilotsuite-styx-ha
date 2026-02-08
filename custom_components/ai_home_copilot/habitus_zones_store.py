from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.habitus_zones"

SIGNAL_HABITUS_ZONES_UPDATED = f"{DOMAIN}_habitus_zones_updated"


@dataclass(frozen=True, slots=True)
class HabitusZone:
    zone_id: str
    name: str
    entity_ids: list[str]
    # Optional categorized entities (role -> entity_ids). If present, this drives UX.
    entities: dict[str, list[str]] | None = None


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
    "other": "other",
}


def _as_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [p.strip() for p in val.replace("\n", ",").split(",") if p.strip()]
    return []


def _parse_entities_mapping(raw: Any) -> dict[str, list[str]] | None:
    if not isinstance(raw, dict):
        return None

    out: dict[str, list[str]] = {}
    for k, v in raw.items():
        key = str(k).strip().lower()
        if not key:
            continue
        key = _ROLE_ALIASES.get(key, key)
        items = _as_list(v)
        if items:
            out.setdefault(key, []).extend(items)

    # De-dupe per role
    for key, items in list(out.items()):
        seen: set[str] = set()
        uniq: list[str] = []
        for e in items:
            if e in seen:
                continue
            seen.add(e)
            uniq.append(e)
        out[key] = uniq

    return out or None


def _normalize_zone(obj: dict[str, Any]) -> HabitusZone | None:
    zid = str(obj.get("id") or obj.get("zone_id") or "").strip()
    name = str(obj.get("name") or zid).strip()

    if not zid:
        return None

    # Legacy flat allowlist
    ent_flat = obj.get("entity_ids")
    if ent_flat is None:
        ent_flat = obj.get("entity_id")

    flat_list = _as_list(ent_flat)

    # Structured allowlist
    ent_map_raw = (
        obj.get("entities")
        or obj.get("roles")
        or obj.get("signals")
        or obj.get("kinds")
    )
    ent_map = _parse_entities_mapping(ent_map_raw)

    # If both exist, keep flat entities under "other".
    if flat_list:
        if ent_map is None:
            ent_map = None
        else:
            ent_map.setdefault("other", []).extend([e for e in flat_list if e])

    # Union entity_ids for runtime consumers.
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

    return HabitusZone(zone_id=zid, name=name or zid, entity_ids=uniq, entities=ent_map)


def _store(hass: HomeAssistant) -> Store:
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    st = global_data.get("habitus_zones_store")
    if st is None:
        st = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        global_data["habitus_zones_store"] = st
    return st


async def async_get_zones(hass: HomeAssistant, entry_id: str) -> list[HabitusZone]:
    data = await _store(hass).async_load() or {}
    entries = data.get("entries") if isinstance(data.get("entries"), dict) else {}
    raw = entries.get(entry_id, [])
    zones: list[HabitusZone] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                z = _normalize_zone(item)
                if z:
                    zones.append(z)
    return zones


async def async_set_zones(hass: HomeAssistant, entry_id: str, zones: list[HabitusZone]) -> None:
    # Enforce requirements for each zone.
    for z in zones:
        _validate_zone_requirements(hass, z)

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
            "entity_ids": list(z.entity_ids),
            **({"entities": z.entities} if isinstance(z.entities, dict) and z.entities else {}),
        }
        for z in zones
    ]

    await st.async_save(data)
    async_dispatcher_send(hass, SIGNAL_HABITUS_ZONES_UPDATED, entry_id)


def _domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def _is_light_entity(entity_id: str) -> bool:
    return _domain(entity_id) == "light"


def _is_motion_or_presence_entity(hass: HomeAssistant, entity_id: str) -> bool:
    dom = _domain(entity_id)
    if dom not in ("binary_sensor", "sensor"):
        return False

    st = hass.states.get(entity_id)
    device_class = None
    if st is not None:
        device_class = st.attributes.get("device_class")

    if device_class in ("motion", "presence", "occupancy"):
        return True

    # Fallback heuristic (best effort): allow common naming if device_class is missing.
    eid_l = entity_id.lower()
    return any(k in eid_l for k in ("motion", "presence", "occupancy"))


def _validate_zone_requirements(hass: HomeAssistant, z: HabitusZone) -> None:
    """Enforce minimal required signals for a Habitus zone.

    Policy (user decision): each zone must have:
    - at least one motion/presence entity
    - at least one light entity
    """

    # Prefer explicit roles if present.
    motion_candidates: list[str] = []
    light_candidates: list[str] = []

    if isinstance(z.entities, dict):
        motion_candidates.extend(z.entities.get("motion") or [])
        light_candidates.extend(z.entities.get("lights") or [])

    # Fallback: scan flat allowlist.
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


async def async_set_zones_from_raw(hass: HomeAssistant, entry_id: str, raw: Any) -> list[HabitusZone]:
    """Validate + normalize and persist zones.

    Accepts either:
    - list[dict]
    - dict with key "zones": list[dict]
    """

    if isinstance(raw, dict) and isinstance(raw.get("zones"), list):
        raw = raw.get("zones")

    if not isinstance(raw, list):
        raise ValueError("Zones must be a list (or {zones:[...]}).")

    zones: list[HabitusZone] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        z = _normalize_zone(item)
        if z:
            zones.append(z)

    # Ensure unique zone ids
    seen: set[str] = set()
    uniq: list[HabitusZone] = []
    for z in zones:
        if z.zone_id in seen:
            continue
        seen.add(z.zone_id)
        uniq.append(z)

    # Enforce requirements.
    for z in uniq:
        _validate_zone_requirements(hass, z)

    await async_set_zones(hass, entry_id, uniq)
    return uniq
