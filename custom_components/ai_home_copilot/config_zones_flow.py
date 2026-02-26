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
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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

_ROLE_FIELD_MAP: dict[str, str] = {
    "brightness": "brightness_entity_ids",
    "noise": "noise_entity_ids",
    "humidity": "humidity_entity_ids",
    "co2": "co2_entity_ids",
    "temperature": "temperature_entity_ids",
    "heating": "heating_entity_ids",
    "camera": "camera_entity_ids",
    "media": "media_entity_ids",
    "power": "power_entity_ids",
    "energy": "energy_entity_ids",
    "door": "door_entity_ids",
    "window": "window_entity_ids",
    "cover": "cover_entity_ids",
    "lock": "lock_entity_ids",
}

_ROLE_LABELS: dict[str, str] = {
    "brightness": "Helligkeit",
    "noise": "Laerm",
    "humidity": "Luftfeuchte",
    "co2": "CO2",
    "temperature": "Temperatur",
    "heating": "Heizung/Klima",
    "camera": "Kamera",
    "media": "Media",
    "power": "Leistung",
    "energy": "Energie",
    "door": "Tuer",
    "window": "Fenster",
    "cover": "Rollo/Cover",
    "lock": "Schloss",
}


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


def _normalize_area_ids(raw: Any) -> list[str]:
    """Normalize area selector payload to list[str]."""
    if raw is None:
        return []
    if isinstance(raw, list):
        result: list[str] = []
        seen: set[str] = set()
        for item in raw:
            value = str(item).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result
    if isinstance(raw, str):
        value = raw.strip()
        return [value] if value else []
    value = str(raw).strip()
    return [value] if value else []


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


def _infer_optional_role(entity_id: str) -> str:
    """Infer optional role from entity id/domain naming hints."""
    eid = str(entity_id or "").lower()
    domain = eid.split(".", 1)[0] if "." in eid else ""

    if domain == "camera":
        return "camera"
    if domain == "media_player":
        return "media"
    if domain == "climate":
        return "heating"
    if domain == "cover":
        return "cover"
    if domain == "lock":
        return "lock"
    if domain in ("switch", "number", "input_number", "water_heater") and any(
        key in eid for key in ("heat", "heiz", "boiler", "therm")
    ):
        return "heating"

    if domain in ("sensor", "binary_sensor"):
        if any(key in eid for key in ("co2", "carbon", "ppm")):
            return "co2"
        if any(key in eid for key in ("humid", "feucht")):
            return "humidity"
        if any(key in eid for key in ("noise", "sound", "laerm", "larm", "db")):
            return "noise"
        if any(key in eid for key in ("lux", "illuminance", "brightness", "hellig")):
            return "brightness"
        if "temp" in eid:
            return "temperature"
        if any(key in eid for key in ("power", "watt", "leistung")):
            return "power"
        if any(key in eid for key in ("energy", "kwh", "verbrauch", "energie")):
            return "energy"

    if domain == "binary_sensor":
        if any(key in eid for key in ("door", "tuer", "tür")):
            return "door"
        if any(key in eid for key in ("window", "fenster")):
            return "window"

    return "other"


def _split_optional_entities(entity_ids: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    """Split optional entities into known role buckets."""
    role_map: dict[str, list[str]] = {role: [] for role in _ROLE_FIELD_MAP}
    other: list[str] = []
    seen: set[str] = set()
    for entity_id in entity_ids:
        eid = str(entity_id or "").strip()
        if not eid or eid in seen:
            continue
        seen.add(eid)
        role = _infer_optional_role(eid)
        if role in role_map:
            role_map[role].append(eid)
        else:
            other.append(eid)
    return role_map, other


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


def _list_area_options(hass: HomeAssistant) -> list[selector.SelectOptionDict]:
    """Build deterministic area dropdown options."""
    ar = area_registry.async_get(hass)
    areas = sorted(
        ar.areas.values(),
        key=lambda area: (area.name or area.id or "").lower(),
    )
    return [
        selector.SelectOptionDict(
            value=area.id,
            label=area.name or area.id,
        )
        for area in areas
    ]


async def _suggest_entities_for_areas(hass: HomeAssistant, area_ids: list[str]) -> dict[str, list[str]]:
    """Merge suggestions for multiple areas."""
    merged = {"motion": [], "lights": [], "optional": []}
    seen: dict[str, set[str]] = {"motion": set(), "lights": set(), "optional": set()}

    for area_id in area_ids:
        suggestions = await _suggest_entities_for_area(hass, area_id)
        for key in ("motion", "lights", "optional"):
            for entity_id in suggestions.get(key, []):
                if entity_id in seen[key]:
                    continue
                seen[key].add(entity_id)
                merged[key].append(entity_id)

    return merged


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
    area_ids: list[str],
    area_options: list[selector.SelectOptionDict],
    name: str,
    motion_entity_id: str | None,
    light_entity_ids: list[str],
    role_entity_ids: dict[str, list[str]],
    optional_entity_ids: list[str],
) -> vol.Schema:
    """Build schema for create/edit zone forms."""
    fields: dict[Any, Any] = {}
    if area_options:
        fields[vol.Optional("area_ids", default=area_ids)] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=area_options,
                multiple=True,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

    fields[vol.Optional("name", default=name)] = str
    fields[vol.Optional("motion_entity_id", default=motion_entity_id)] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"], multiple=False)
    )
    fields[vol.Optional("light_entity_ids", default=light_entity_ids)] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="light", multiple=True)
    )
    fields[vol.Optional("brightness_entity_ids", default=role_entity_ids.get("brightness", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "binary_sensor"], multiple=True)
    )
    fields[vol.Optional("noise_entity_ids", default=role_entity_ids.get("noise", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "binary_sensor"], multiple=True)
    )
    fields[vol.Optional("humidity_entity_ids", default=role_entity_ids.get("humidity", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "binary_sensor"], multiple=True)
    )
    fields[vol.Optional("co2_entity_ids", default=role_entity_ids.get("co2", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "binary_sensor"], multiple=True)
    )
    fields[vol.Optional("temperature_entity_ids", default=role_entity_ids.get("temperature", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor", "climate"], multiple=True)
    )
    fields[vol.Optional("heating_entity_ids", default=role_entity_ids.get("heating", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["climate", "switch", "number", "input_number", "water_heater"], multiple=True)
    )
    fields[vol.Optional("camera_entity_ids", default=role_entity_ids.get("camera", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["camera"], multiple=True)
    )
    fields[vol.Optional("media_entity_ids", default=role_entity_ids.get("media", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["media_player"], multiple=True)
    )
    fields[vol.Optional("power_entity_ids", default=role_entity_ids.get("power", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor"], multiple=True)
    )
    fields[vol.Optional("energy_entity_ids", default=role_entity_ids.get("energy", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["sensor"], multiple=True)
    )
    fields[vol.Optional("door_entity_ids", default=role_entity_ids.get("door", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["binary_sensor"], multiple=True)
    )
    fields[vol.Optional("window_entity_ids", default=role_entity_ids.get("window", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["binary_sensor"], multiple=True)
    )
    fields[vol.Optional("cover_entity_ids", default=role_entity_ids.get("cover", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["cover"], multiple=True)
    )
    fields[vol.Optional("lock_entity_ids", default=role_entity_ids.get("lock", []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["lock"], multiple=True)
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


async def _sync_zones_to_core(
    hass: HomeAssistant,
    config: dict,
    zones: list,
) -> None:
    """Push zone data to Core API (fire-and-forget)."""
    import aiohttp
    from .core_endpoint import build_base_url, DEFAULT_CORE_PORT

    host = str(config.get("host", "")).strip()
    try:
        port = int(config.get("port", DEFAULT_CORE_PORT))
    except (TypeError, ValueError):
        port = DEFAULT_CORE_PORT
    if not host:
        return

    base = build_base_url(host, port).rstrip("/")
    token = str(config.get("token") or config.get("auth_token") or "").strip()
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-Auth-Token"] = token

    session = async_get_clientsession(hass)

    zone_payload = []
    for z in zones:
        item: dict[str, Any] = {
            "zone_id": z.zone_id,
            "name": z.name,
            "entity_ids": list(z.entity_ids),
        }
        if z.entities:
            item["entities"] = {k: list(v) for k, v in z.entities.items()}
        if z.metadata and isinstance(z.metadata, dict):
            item["metadata"] = z.metadata
        zone_payload.append(item)

    # Try new Habitus Zones API first, fall back to legacy Hub endpoint
    sync_ok = False
    for endpoint in ("/api/v1/habitus/zones/sync", "/api/v1/hub/zones/sync"):
        try:
            async with session.post(
                f"{base}{endpoint}",
                json={"zones": zone_payload, "full_sync": True},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (200, 201):
                    _LOGGER.debug("Synced %d zones to Core via %s", len(zone_payload), endpoint)
                    sync_ok = True
                    break
                _LOGGER.debug("Core zone sync via %s returned %s", endpoint, resp.status)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Core zone sync via %s failed: %s", endpoint, exc)

    if not sync_ok:
        _LOGGER.debug("Core zone sync failed on all endpoints (non-blocking)")


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

    area_options = _list_area_options(flow.hass)
    default_area_ids: list[str] = []
    default_name = ""
    default_motion: str | None = None
    default_lights: list[str] = []
    default_roles: dict[str, list[str]] = {role: [] for role in _ROLE_FIELD_MAP}
    default_optional: list[str] = []

    if zone is not None:
        default_name = zone.name or ""
        metadata = zone.metadata if isinstance(zone.metadata, dict) else {}
        default_area_ids = _normalize_area_ids(metadata.get("ha_area_ids"))
        if not default_area_ids and metadata.get("ha_area_id"):
            default_area_ids = _normalize_area_ids(metadata.get("ha_area_id"))
        ent_map = getattr(zone, "entities", None)
        if isinstance(ent_map, dict):
            motion_list = _normalize_entity_ids(ent_map.get("motion"))
            lights_list = _normalize_entity_ids(ent_map.get("lights"))
            default_motion = motion_list[0] if motion_list else None
            default_lights = lights_list
            for role in _ROLE_FIELD_MAP:
                default_roles[role] = _normalize_entity_ids(ent_map.get(role))
            default_optional = _normalize_entity_ids(ent_map.get("other"))
        else:
            for eid in zone.entity_ids:
                if eid.startswith("light."):
                    default_lights.append(eid)
                elif eid.startswith(("binary_sensor.", "sensor.")) and default_motion is None:
                    default_motion = eid
                else:
                    role_map, remainder = _split_optional_entities([eid])
                    assigned = False
                    for role, values in role_map.items():
                        if values:
                            default_roles[role].extend(values)
                            assigned = True
                    if not assigned:
                        default_optional.extend(remainder or [eid])

    if user_input is None:
        schema = _build_zone_form_schema(
            mode=mode,
            area_ids=default_area_ids,
            area_options=area_options,
            name=default_name,
            motion_entity_id=default_motion,
            light_entity_ids=default_lights,
            role_entity_ids=default_roles,
            optional_entity_ids=default_optional,
        )
        return flow.async_show_form(step_id=step_id, data_schema=schema)

    area_ids = _normalize_area_ids(user_input.get("area_ids"))
    if not area_ids:
        # Backward compatibility for old payloads.
        area_ids = _normalize_area_ids(user_input.get("area_id"))
    if not area_ids and mode == "edit":
        area_ids = list(default_area_ids)

    name = str(user_input.get("name") or "").strip()
    motion = str(user_input.get("motion_entity_id") or "").strip()
    lights = _normalize_entity_ids(user_input.get("light_entity_ids"))
    role_entities: dict[str, list[str]] = {}
    for role, field_key in _ROLE_FIELD_MAP.items():
        role_entities[role] = _normalize_entity_ids(user_input.get(field_key))
    optional = _normalize_entity_ids(user_input.get("optional_entity_ids"))

    auto_hints: list[str] = []
    if area_ids and (not motion or not lights):
        suggestions = await _suggest_entities_for_areas(flow.hass, area_ids)
        if not motion and suggestions["motion"]:
            motion = suggestions["motion"][0]
            auto_hints.append("Motion wurde automatisch aus dem gewaehlten Bereich uebernommen.")
        if not lights and suggestions["lights"]:
            lights = suggestions["lights"]
            auto_hints.append("Lichter wurden automatisch aus dem gewaehlten Bereich uebernommen.")
        if not optional:
            optional = suggestions["optional"][:8]
        suggested_roles, suggested_other = _split_optional_entities(suggestions["optional"])
        for role in _ROLE_FIELD_MAP:
            if not role_entities.get(role) and suggested_roles.get(role):
                role_entities[role] = suggested_roles[role][:4]
        if not optional and suggested_other:
            optional = suggested_other[:8]

    area_names = [name for name in (_area_name(flow.hass, aid) for aid in area_ids) if name]
    area_name_summary = " + ".join(area_names) if area_names else ""

    if mode == "edit" and zone is not None:
        zid = zone.zone_id
        zone_name = name or zone.name or zid
    else:
        base_name = name or area_name_summary or "Zone"
        zid = _zone_id_from_name(base_name)
        zid = _ensure_unique_zone_id(zid, set(existing))
        zone_name = base_name

    errors: dict[str, str] = {}
    has_role_entities = any(role_entities.get(role) for role in _ROLE_FIELD_MAP)
    if not motion and not lights and not optional and not has_role_entities:
        errors["base"] = "invalid"
    if errors:
        schema = _build_zone_form_schema(
            mode=mode,
            area_ids=area_ids,
            area_options=area_options,
            name=name,
            motion_entity_id=motion or None,
            light_entity_ids=lights,
            role_entity_ids=role_entities,
            optional_entity_ids=optional,
        )
        missing_hint = "Bitte mindestens eine Entitaet auswaehlen (Motion, Licht oder optional)."
        combined_hint = " ".join(auto_hints + [missing_hint]).strip()
        placeholders = {"hint": combined_hint}
        return flow.async_show_form(
            step_id=step_id,
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    role_order = ("brightness", "noise", "humidity", "co2", "temperature", "heating", "camera", "media",
                  "power", "energy", "door", "window", "cover", "lock")
    entity_ids = [motion] + lights
    for role in role_order:
        entity_ids.extend(role_entities.get(role, []))
    entity_ids.extend(optional)
    uniq: list[str] = []
    seen: set[str] = set()
    for entity_id in entity_ids:
        if not entity_id or entity_id in seen:
            continue
        seen.add(entity_id)
        uniq.append(entity_id)

    ent_map = {"motion": [motion], "lights": lights, "other": optional}
    for role in role_order:
        role_values = role_entities.get(role, [])
        if role_values:
            ent_map[role] = role_values
    ent_map = {key: value for key, value in ent_map.items() if value}
    base_metadata = dict(zone.metadata) if zone is not None and isinstance(zone.metadata, dict) else {}
    if area_ids:
        base_metadata["ha_area_ids"] = area_ids
    else:
        base_metadata.pop("ha_area_ids", None)
    base_metadata.pop("ha_area_id", None)

    new_zone = HabitusZoneV2(
        zone_id=zid,
        name=zone_name or zid,
        entity_ids=tuple(uniq),
        entities=ent_map or None,
        metadata=base_metadata or None,
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
            area_ids=area_ids,
            area_options=area_options,
            name=name,
            motion_entity_id=motion or None,
            light_entity_ids=lights,
            role_entity_ids=role_entities,
            optional_entity_ids=optional,
        )
        placeholders = {"hint": f"{' '.join(auto_hints)} {err}".strip()} if auto_hints else {"hint": str(err)}
        return flow.async_show_form(
            step_id=step_id,
            data_schema=schema,
            errors={"base": "invalid"},
            description_placeholders=placeholders,
        )

    await create_zone_tag(flow.hass, zid, zone_name)
    await tag_zone_entities(flow.hass, zid, uniq)

    # Sync all zones to Core API (fire-and-forget)
    try:
        from .config_helpers import merge_config_data
        config = merge_config_data(entry.data, entry.options)
        all_zones = await async_get_zones_v2(flow.hass, entry.entry_id)
        await _sync_zones_to_core(flow.hass, config, all_zones)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Zone sync to Core after save failed (non-blocking)")

    return await flow.async_step_habitus_zones()
