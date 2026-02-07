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


def _normalize_zone(obj: dict[str, Any]) -> HabitusZone | None:
    zid = str(obj.get("id") or obj.get("zone_id") or "").strip()
    name = str(obj.get("name") or zid).strip()
    ent = obj.get("entity_ids")
    if ent is None:
        ent = obj.get("entities")

    if not zid:
        return None

    entity_ids: list[str] = []
    if isinstance(ent, list):
        entity_ids = [str(x).strip() for x in ent if str(x).strip()]
    elif isinstance(ent, str) and ent.strip():
        # allow comma-separated convenience
        entity_ids = [p.strip() for p in ent.replace("\n", ",").split(",") if p.strip()]

    # De-dupe while keeping order
    seen: set[str] = set()
    uniq: list[str] = []
    for e in entity_ids:
        if e in seen:
            continue
        seen.add(e)
        uniq.append(e)

    return HabitusZone(zone_id=zid, name=name or zid, entity_ids=uniq)


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
    st = _store(hass)
    data = await st.async_load() or {}
    entries = data.setdefault("entries", {})
    if not isinstance(entries, dict):
        entries = {}
        data["entries"] = entries

    entries[entry_id] = [
        {"id": z.zone_id, "name": z.name, "entity_ids": list(z.entity_ids)} for z in zones
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

    has_motion = any(_is_motion_or_presence_entity(hass, eid) for eid in z.entity_ids)
    has_light = any(_is_light_entity(eid) for eid in z.entity_ids)

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
