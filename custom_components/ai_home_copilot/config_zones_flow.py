"""Zone management flow logic extracted from config_flow.py."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

_LOGGER = logging.getLogger(__name__)


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
            _LOGGER.info(f"Auto-created tag: {tag_id} for zone: {zone_name}")
    except Exception as ex:  # noqa: BLE001
        _LOGGER.debug(f"Could not auto-create tag: {ex}")


async def tag_zone_entities(hass: HomeAssistant, zone_id: str, entity_ids: list[str]) -> None:
    """Auto-tag entities when added to zone."""
    try:
        from homeassistant.components import tag

        zone_tag = f"aicp.place.{zone_id.replace('zone:', '')}"
        for entity_id in entity_ids:
            try:
                await tag.async_tag_entity(hass, entity_id=entity_id, tag_id=zone_tag)
            except Exception:  # noqa: BLE001
                pass
        _LOGGER.info(f"Auto-tagged {len(entity_ids)} entities with tag: {zone_tag}")
    except Exception as ex:  # noqa: BLE001
        _LOGGER.debug(f"Could not auto-tag entities: {ex}")


async def get_zone_entity_suggestions(hass: HomeAssistant, zone_name: str) -> dict:
    """Get entity suggestions for a zone."""
    from homeassistant.helpers import area_registry, entity_registry

    suggestions = {
        "motion": [],
        "lights": [],
        "sensors": [],
        "media": [],
        "other": [],
    }

    try:
        area_reg = area_registry.async_get(hass)
        entity_reg = entity_registry.async_get(hass)
        zone_name_lower = zone_name.lower().replace("bereich", "").strip()
        matching_areas = [
            a for a in area_reg.areas.values() if zone_name_lower in a.name.lower()
        ]

        for entity_id, entry in entity_reg.entities.items():
            if entry.disabled:
                continue
            area_match = entry.area_id and any(
                a.id == entry.area_id for a in matching_areas
            )
            name_match = zone_name_lower in entity_id.lower()
            if area_match or name_match:
                domain = entity_id.split(".")[0]
                if domain == "binary_sensor":
                    suggestions["motion"].append(entity_id)
                elif domain == "light":
                    suggestions["lights"].append(entity_id)
                elif domain == "sensor":
                    suggestions["sensors"].append(entity_id)
                elif domain == "media_player":
                    suggestions["media"].append(entity_id)
                else:
                    suggestions["other"].append(entity_id)
    except Exception as ex:  # noqa: BLE001
        _LOGGER.debug(f"Could not get zone suggestions: {ex}")

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

    if zone_id and zone_id in existing:
        z = existing[zone_id]
    else:
        z = HabitusZoneV2(zone_id="", name="", entity_ids=(), entities=None)

    if user_input is not None:
        zid = str(user_input.get("zone_id") or "").strip()
        name = str(user_input.get("name") or zid).strip()
        motion = str(user_input.get("motion_entity_id") or "").strip()
        lights = user_input.get("light_entity_ids") or []
        optional = user_input.get("optional_entity_ids") or []

        if not isinstance(lights, list):
            lights = [lights]
        if not isinstance(optional, list):
            optional = [optional]

        entity_ids = [motion] + [str(x).strip() for x in lights] + [str(x).strip() for x in optional]
        entity_ids = [e for e in entity_ids if e]

        seen: set[str] = set()
        uniq: list[str] = []
        for e in entity_ids:
            if e in seen:
                continue
            seen.add(e)
            uniq.append(e)

        ent_map = {
            "motion": [motion] if motion else [],
            "lights": [str(x).strip() for x in lights if str(x).strip()],
            "other": [str(x).strip() for x in optional if str(x).strip()],
        }
        ent_map = {k: v for k, v in ent_map.items() if v}

        new_zone = HabitusZoneV2(
            zone_id=zid, name=name or zid, entity_ids=tuple(uniq), entities=ent_map or None
        )

        new_list = [zz for zz in zones if zz.zone_id != zid]
        new_list.append(new_zone)
        await async_set_zones_v2(flow.hass, entry.entry_id, new_list)

        await create_zone_tag(flow.hass, zid, name)
        await tag_zone_entities(flow.hass, zid, entity_ids)

        return await flow.async_step_habitus_zones()

    default_motion = None
    default_lights: list[str] = []
    default_optional: list[str] = []

    ent_map = getattr(z, "entities", None)
    if isinstance(ent_map, dict):
        motion_list = ent_map.get("motion") or []
        lights_list = ent_map.get("lights") or []
        other_list = ent_map.get("other") or []
        if motion_list:
            default_motion = str(motion_list[0])
        default_lights = [str(x) for x in lights_list]
        default_optional = [str(x) for x in other_list]
    else:
        for eid in z.entity_ids:
            if eid.startswith("light."):
                default_lights.append(eid)
            elif eid.startswith("binary_sensor.") and default_motion is None:
                default_motion = eid
            else:
                default_optional.append(eid)

    schema = vol.Schema(
        {
            vol.Required("zone_id", default=(z.zone_id if mode == "edit" else "")): str,
            vol.Optional("name", default=(z.name if z.name else "")): str,
            vol.Required(
                "motion_entity_id",
                default=default_motion or "",
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"], multiple=False)
            ),
            vol.Required(
                "light_entity_ids",
                default=default_lights,
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light", multiple=True)
            ),
            vol.Optional(
                "optional_entity_ids",
                default=default_optional,
            ): selector.EntitySelector(selector.EntitySelectorConfig(multiple=True)),
        }
    )

    step_id = "create_zone" if mode == "create" else "edit_zone_form"
    return flow.async_show_form(step_id=step_id, data_schema=schema)
