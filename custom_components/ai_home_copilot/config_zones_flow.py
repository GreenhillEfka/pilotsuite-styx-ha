"""Zone management flow logic extracted from config_flow.py."""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import area_registry, device_registry, entity_registry, selector

_LOGGER = logging.getLogger(__name__)

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


def _normalize_entity_ids(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        text = raw.strip()
        return [text] if text else []
    text = str(raw).strip()
    return [text] if text else []


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).strip("_").lower()
    return slug or "zone"


def _zone_id_from_name(name: str) -> str:
    slug = _slugify(name)
    return slug if slug.startswith("zone:") else f"zone:{slug}"


def _ensure_unique_zone_id(candidate: str, existing_ids: set[str]) -> str:
    if candidate not in existing_ids:
        return candidate
    suffix = 2
    while True:
        probe = f"{candidate}_{suffix}"
        if probe not in existing_ids:
            return probe
        suffix += 1


def _is_motion_candidate(hass: HomeAssistant, entity_id: str, reg_entry) -> bool:
    if reg_entry.domain not in ("binary_sensor", "sensor"):
        return False

    st = hass.states.get(entity_id)
    device_class = st.attributes.get("device_class") if st is not None else None
    if isinstance(device_class, str):
        if device_class.lower() in ("motion", "presence", "occupancy"):
            return True

    if isinstance(getattr(reg_entry, "device_class", None), str):
        if reg_entry.device_class.lower() in ("motion", "presence", "occupancy"):
            return True

    labels: list[str] = [entity_id.lower()]
    original_name = getattr(reg_entry, "original_name", None)
    if isinstance(original_name, str) and original_name:
        labels.append(original_name.lower())
    state_name = st.attributes.get("friendly_name") if st is not None else None
    if isinstance(state_name, str) and state_name:
        labels.append(state_name.lower())
    merged = " ".join(labels)
    return any(hint in merged for hint in _MOTION_HINTS)


def _entity_area_id(dev_reg, reg_entry) -> str | None:
    if reg_entry.area_id:
        return reg_entry.area_id
    if reg_entry.device_id:
        device = dev_reg.async_get(reg_entry.device_id)
        if device is not None:
            return device.area_id
    return None


async def _suggest_entities_for_area(hass: HomeAssistant, area_id: str) -> dict[str, list[str]]:
    """Suggest zone entities for an HA area."""
    ent_reg = entity_registry.async_get(hass)
    dev_reg = device_registry.async_get(hass)

    suggestions = {"motion": [], "lights": [], "optional": []}
    for entity_id, reg_entry in ent_reg.entities.items():
        if reg_entry.disabled_by is not None:
            continue
        if _entity_area_id(dev_reg, reg_entry) != area_id:
            continue

        domain = reg_entry.domain
        if domain == "light":
            suggestions["lights"].append(entity_id)
            continue
        if _is_motion_candidate(hass, entity_id, reg_entry):
            suggestions["motion"].append(entity_id)
            continue
        suggestions["optional"].append(entity_id)

    suggestions["motion"].sort()
    suggestions["lights"].sort()
    suggestions["optional"].sort()
    return suggestions


def _area_name(hass: HomeAssistant, area_id: str | None) -> str:
    if not area_id:
        return ""
    ar = area_registry.async_get(hass)
    area = ar.async_get_area(area_id)
    if area is None:
        return ""
    return area.name or ""


def _build_zone_form_schema(
    *,
    mode: str,
    area_id: str | None,
    name: str,
    motion_entity_id: str | None,
    light_entity_ids: list[str],
    optional_entity_ids: list[str],
) -> vol.Schema:
    """Build schema for create/edit zone forms."""
    fields: dict[Any, Any] = {}
    if mode == "create":
        fields[vol.Optional("area_id", default=area_id)] = selector.AreaSelector(
            selector.AreaSelectorConfig()
        )

    fields[vol.Optional("name", default=name)] = str
    fields[vol.Optional("motion_entity_id", default=motion_entity_id)] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"], multiple=False)
    )
    fields[vol.Optional("light_entity_ids", default=light_entity_ids)] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="light", multiple=True)
    )
    fields[vol.Optional("optional_entity_ids", default=optional_entity_ids)] = selector.EntitySelector(
        selector.EntitySelectorConfig(multiple=True)
    )
    return vol.Schema(fields)


async def create_zone_tag(hass: HomeAssistant, zone_id: str, zone_name: str) -> None:
    """Auto-create tag when zone is created."""
    try:
        from homeassistant.components import tag

        tag_id = f"aicp.place.{zone_id.replace('zone:', '')}"
        existing_tags = await tag.async_get_tags(hass)
        if tag_id not in [t.get("tag_id") for t in existing_tags.values()]:
            await tag.async_create_tag(
                hass,
                tag_id=tag_id,
                name=f"Zone: {zone_name}",
            )
            _LOGGER.info("Auto-created tag: %s for zone: %s", tag_id, zone_name)
    except Exception as ex:  # noqa: BLE001
        _LOGGER.debug("Could not auto-create tag: %s", ex)


async def tag_zone_entities(hass: HomeAssistant, zone_id: str, entity_ids: list[str]) -> None:
    """Auto-tag entities when added to zone."""
    try:
        from homeassistant.components import tag

        zone_tag = f"aicp.place.{zone_id.replace('zone:', '')}"
        for entity_id in entity_ids:
            try:
                await tag.async_tag_entity(hass, entity_id=entity_id, tag_id=zone_tag)
            except Exception:  # noqa: BLE001
                continue
        _LOGGER.info("Auto-tagged %d entities with tag: %s", len(entity_ids), zone_tag)
    except Exception as ex:  # noqa: BLE001
        _LOGGER.debug("Could not auto-tag entities: %s", ex)


async def get_zone_entity_suggestions(hass: HomeAssistant, zone_name: str) -> dict:
    """Get entity suggestions for a zone name."""
    suggestions = {
        "motion": [],
        "lights": [],
        "sensors": [],
        "media": [],
        "other": [],
    }
    zone_name_lower = zone_name.lower().replace("bereich", "").strip()
    if not zone_name_lower:
        return suggestions

    ar = area_registry.async_get(hass)
    match = next(
        (area for area in ar.areas.values() if zone_name_lower in (area.name or "").lower()),
        None,
    )
    if match is not None:
        area_suggestions = await _suggest_entities_for_area(hass, match.id)
        suggestions["motion"] = area_suggestions["motion"]
        suggestions["lights"] = area_suggestions["lights"]
        suggestions["other"] = area_suggestions["optional"]
        return suggestions

    try:
        ent_reg = entity_registry.async_get(hass)
        for entity_id, reg_entry in ent_reg.entities.items():
            if reg_entry.disabled_by is not None:
                continue
            if zone_name_lower not in entity_id.lower():
                continue
            domain = entity_id.split(".")[0]
            if domain == "light":
                suggestions["lights"].append(entity_id)
            elif domain in ("binary_sensor", "sensor") and _is_motion_candidate(hass, entity_id, reg_entry):
                suggestions["motion"].append(entity_id)
            elif domain == "sensor":
                suggestions["sensors"].append(entity_id)
            elif domain == "media_player":
                suggestions["media"].append(entity_id)
            else:
                suggestions["other"].append(entity_id)
    except Exception as ex:  # noqa: BLE001
        _LOGGER.debug("Could not get zone suggestions: %s", ex)

    return suggestions


async def async_step_zone_form(
    flow,
    *,
    mode: str,
    user_input: dict | None,
    zone_id: str | None = None,
) -> FlowResult:
    """Handle zone create/edit form (extracted from OptionsFlowHandler)."""
    from .habitus_zones_store_v2 import HabitusZoneV2, async_get_zones_v2, async_set_zones_v2

    entry = flow._entry
    zones = await async_get_zones_v2(flow.hass, entry.entry_id)
    existing = {z.zone_id: z for z in zones}

    zone = existing.get(zone_id) if zone_id else None
    if mode == "edit" and zone is None:
        return flow.async_abort(reason="no_zones")

    step_id = "create_zone" if mode == "create" else "edit_zone_form"

    default_area_id: str | None = None
    default_name = ""
    default_motion: str | None = None
    default_lights: list[str] = []
    default_optional: list[str] = []

    if zone is not None:
        default_name = zone.name or ""
        ent_map = getattr(zone, "entities", None)
        if isinstance(ent_map, dict):
            motion_list = _normalize_entity_ids(ent_map.get("motion"))
            lights_list = _normalize_entity_ids(ent_map.get("lights"))
            other_list = _normalize_entity_ids(ent_map.get("other"))
            default_motion = motion_list[0] if motion_list else None
            default_lights = lights_list
            default_optional = other_list
        else:
            for eid in zone.entity_ids:
                if eid.startswith("light."):
                    default_lights.append(eid)
                elif eid.startswith(("binary_sensor.", "sensor.")) and default_motion is None:
                    default_motion = eid
                else:
                    default_optional.append(eid)

    if user_input is None:
        schema = _build_zone_form_schema(
            mode=mode,
            area_id=default_area_id,
            name=default_name,
            motion_entity_id=default_motion,
            light_entity_ids=default_lights,
            optional_entity_ids=default_optional,
        )
        return flow.async_show_form(step_id=step_id, data_schema=schema)

    area_id_raw = user_input.get("area_id") if mode == "create" else None
    area_id = str(area_id_raw).strip() if isinstance(area_id_raw, str) and area_id_raw else None

    name = str(user_input.get("name") or "").strip()
    motion = str(user_input.get("motion_entity_id") or "").strip()
    lights = _normalize_entity_ids(user_input.get("light_entity_ids"))
    optional = _normalize_entity_ids(user_input.get("optional_entity_ids"))

    auto_hint = ""
    if area_id and (not motion or not lights):
        suggestions = await _suggest_entities_for_area(flow.hass, area_id)
        if not motion and suggestions["motion"]:
            motion = suggestions["motion"][0]
            auto_hint = "Motion wurde automatisch aus dem gewählten Bereich übernommen."
        if not lights and suggestions["lights"]:
            lights = suggestions["lights"]
            if auto_hint:
                auto_hint = f"{auto_hint} Lichter wurden ebenfalls automatisch übernommen."
            else:
                auto_hint = "Lichter wurden automatisch aus dem gewählten Bereich übernommen."
        if not optional:
            optional = suggestions["optional"][:8]

    if mode == "edit" and zone is not None:
        zid = zone.zone_id
        zone_name = name or zone.name or zid
    else:
        base_name = name or _area_name(flow.hass, area_id) or "Zone"
        zid = _zone_id_from_name(base_name)
        zid = _ensure_unique_zone_id(zid, set(existing))
        zone_name = base_name

    errors: dict[str, str] = {}
    if not motion:
        errors["motion_entity_id"] = "required"
    if not lights:
        errors["light_entity_ids"] = "required"
    if errors:
        schema = _build_zone_form_schema(
            mode=mode,
            area_id=area_id,
            name=name,
            motion_entity_id=motion or None,
            light_entity_ids=lights,
            optional_entity_ids=optional,
        )
        placeholders = {"hint": auto_hint} if auto_hint else None
        return flow.async_show_form(
            step_id=step_id,
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    entity_ids = [motion] + lights + optional
    uniq: list[str] = []
    seen: set[str] = set()
    for entity_id in entity_ids:
        if not entity_id or entity_id in seen:
            continue
        seen.add(entity_id)
        uniq.append(entity_id)

    ent_map = {"motion": [motion], "lights": lights, "other": optional}
    ent_map = {key: value for key, value in ent_map.items() if value}

    new_zone = HabitusZoneV2(
        zone_id=zid,
        name=zone_name or zid,
        entity_ids=tuple(uniq),
        entities=ent_map or None,
    )

    replace_zone_id = zone.zone_id if zone is not None else zid
    new_list = [existing_zone for existing_zone in zones if existing_zone.zone_id != replace_zone_id]
    new_list.append(new_zone)

    try:
        await async_set_zones_v2(flow.hass, entry.entry_id, new_list)
    except ValueError as err:
        _LOGGER.debug("Zone validation failed for %s: %s", zid, err)
        schema = _build_zone_form_schema(
            mode=mode,
            area_id=area_id,
            name=name,
            motion_entity_id=motion or None,
            light_entity_ids=lights,
            optional_entity_ids=optional,
        )
        placeholders = {"hint": f"{auto_hint} {err}".strip()} if auto_hint else {"hint": str(err)}
        return flow.async_show_form(
            step_id=step_id,
            data_schema=schema,
            errors={"base": "invalid"},
            description_placeholders=placeholders,
        )

    await create_zone_tag(flow.hass, zid, zone_name)
    await tag_zone_entities(flow.hass, zid, uniq)
    return await flow.async_step_habitus_zones()
