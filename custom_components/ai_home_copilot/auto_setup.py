"""Auto-setup module — discover HA areas, create Habitus zones, tag entities.

Runs once after config entry creation (first run only). Non-blocking: if it
fails, the integration still works normally. The auto-setup populates Habitus
zones from HA areas and auto-tags entities by domain using DOMAIN_TAG_MAP.

This gives new users a working baseline without any manual configuration.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry

from .const import DOMAIN, DOMAIN_TAG_MAP, ENTITY_ROLE_MAP
from .entity_tags_store import async_get_entity_tags, async_save_entity_tags, EntityTag
from .habitus_zones_store_v2 import (
    HabitusZoneV2,
    async_get_zones_v2,
    async_set_zones_v2,
)

_LOGGER = logging.getLogger(__name__)

# Device classes that map to specific zone roles
_DEVICE_CLASS_ROLE_MAP: dict[str, str] = {
    "motion": "motion",
    "presence": "motion",
    "occupancy": "motion",
    "temperature": "temperature",
    "humidity": "humidity",
    "illuminance": "brightness",
    "carbon_dioxide": "co2",
    "pressure": "pressure",
    "energy": "energy",
    "power": "power",
    "door": "door",
    "window": "window",
    "noise": "noise",
    "sound_pressure": "noise",
}


def _slugify(name: str) -> str:
    """Convert area name to a zone_id-compatible slug."""
    slug = name.lower().strip()
    slug = slug.replace(" ", "_").replace("-", "_")
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "zone"


def _get_entity_area_id(
    dev_reg: device_registry.DeviceRegistry,
    ent_entry: entity_registry.RegistryEntry,
) -> str | None:
    """Resolve the effective area_id for an entity (entity > device fallback)."""
    if ent_entry.area_id:
        return ent_entry.area_id
    if ent_entry.device_id:
        device = dev_reg.async_get(ent_entry.device_id)
        if device and device.area_id:
            return device.area_id
    return None


def _get_device_class(
    hass: HomeAssistant,
    ent_entry: entity_registry.RegistryEntry,
) -> str | None:
    """Get the device_class from registry or state attributes."""
    # Try registry first
    if ent_entry.device_class:
        return str(ent_entry.device_class)
    if ent_entry.original_device_class:
        return str(ent_entry.original_device_class)
    # Fall back to state attributes
    state = hass.states.get(ent_entry.entity_id)
    if state and state.attributes.get("device_class"):
        return str(state.attributes["device_class"])
    return None


def _classify_entity_role(
    hass: HomeAssistant,
    ent_entry: entity_registry.RegistryEntry,
) -> str:
    """Classify an entity into a zone role based on device_class and domain.

    Returns a role string from KNOWN_ROLES (e.g. 'motion', 'lights', 'temperature').
    """
    device_class = _get_device_class(hass, ent_entry)

    # Device class takes precedence
    if device_class and device_class in _DEVICE_CLASS_ROLE_MAP:
        return _DEVICE_CLASS_ROLE_MAP[device_class]

    # Fall back to domain-based mapping
    domain = ent_entry.domain
    return ENTITY_ROLE_MAP.get(domain, "other")


async def async_run_auto_setup(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    """Run auto-setup: discover areas, create zones, tag entities.

    Returns a summary dict with counts of what was created/tagged.
    """
    summary: dict[str, Any] = {
        "areas_found": 0,
        "zones_created": 0,
        "entities_tagged": 0,
        "entities_assigned": 0,
        "skipped_existing_zones": False,
    }

    ar = area_registry.async_get(hass)
    dr = device_registry.async_get(hass)
    er = entity_registry.async_get(hass)

    # -----------------------------------------------------------------------
    # 1. Check if zones already exist — skip zone creation if so
    # -----------------------------------------------------------------------
    existing_zones = await async_get_zones_v2(hass, entry.entry_id)
    if existing_zones:
        _LOGGER.info(
            "Auto-setup: %d Habitus zones already exist, skipping zone creation",
            len(existing_zones),
        )
        summary["skipped_existing_zones"] = True
    else:
        # -------------------------------------------------------------------
        # 2. Discover all HA areas and build zones
        # -------------------------------------------------------------------
        areas = sorted(
            ar.areas.values(),
            key=lambda a: (a.name or a.id or "").lower(),
        )
        summary["areas_found"] = len(areas)

        if not areas:
            _LOGGER.info("Auto-setup: no HA areas found, skipping zone creation")
        else:
            # Build a mapping: area_id -> list of (entity_id, RegistryEntry)
            area_entities: dict[str, list[tuple[str, entity_registry.RegistryEntry]]] = {
                a.id: [] for a in areas
            }
            for entity_id, ent_entry in er.entities.items():
                if ent_entry.disabled_by is not None:
                    continue
                eff_area = _get_entity_area_id(dr, ent_entry)
                if eff_area and eff_area in area_entities:
                    area_entities[eff_area].append((entity_id, ent_entry))

            new_zones: list[HabitusZoneV2] = []
            used_zone_ids: set[str] = set()

            for area in areas:
                area_name = area.name or area.id
                slug = _slugify(area_name)
                zone_id = f"zone:{slug}"

                # Ensure unique zone_id
                if zone_id in used_zone_ids:
                    counter = 2
                    while f"{zone_id}_{counter}" in used_zone_ids:
                        counter += 1
                    zone_id = f"{zone_id}_{counter}"
                used_zone_ids.add(zone_id)

                # Classify entities into roles
                role_entities: dict[str, list[str]] = {}
                all_entity_ids: list[str] = []
                for entity_id, ent_entry in area_entities.get(area.id, []):
                    role = _classify_entity_role(hass, ent_entry)
                    role_entities.setdefault(role, []).append(entity_id)
                    all_entity_ids.append(entity_id)

                if not all_entity_ids:
                    _LOGGER.debug(
                        "Auto-setup: area '%s' has no entities, skipping", area_name
                    )
                    continue

                # Sort entity lists for determinism
                for role_list in role_entities.values():
                    role_list.sort()
                all_entity_ids.sort()

                # Convert lists to tuples for the frozen dataclass
                entities_map: dict[str, tuple[str, ...]] = {
                    role: tuple(ents) for role, ents in role_entities.items() if ents
                }

                zone = HabitusZoneV2(
                    zone_id=zone_id,
                    name=area_name,
                    zone_type="room",
                    entity_ids=tuple(all_entity_ids),
                    entities=entities_map or None,
                    current_state="idle",
                    priority=0,
                    tags=(slug,),
                    metadata={"auto_setup": True, "ha_area_id": area.id},
                )
                new_zones.append(zone)
                summary["entities_assigned"] += len(all_entity_ids)

            if new_zones:
                await async_set_zones_v2(
                    hass, entry.entry_id, new_zones, validate=False
                )
                summary["zones_created"] = len(new_zones)
                _LOGGER.info(
                    "Auto-setup: created %d Habitus zones from HA areas (%d entities assigned)",
                    len(new_zones),
                    summary["entities_assigned"],
                )

    # -----------------------------------------------------------------------
    # 3. Auto-tag entities by domain using DOMAIN_TAG_MAP
    # -----------------------------------------------------------------------
    existing_tags = await async_get_entity_tags(hass)
    tags_modified = False

    # Collect all non-disabled entities grouped by domain
    domain_entities: dict[str, list[str]] = {}
    for entity_id, ent_entry in er.entities.items():
        if ent_entry.disabled_by is not None:
            continue
        domain = ent_entry.domain
        if domain in DOMAIN_TAG_MAP:
            domain_entities.setdefault(domain, []).append(entity_id)

    for domain, entity_ids in domain_entities.items():
        tag_id, tag_name, color, icon = DOMAIN_TAG_MAP[domain]

        # Merge with existing tag if present
        existing_tag = existing_tags.get(tag_id)
        if existing_tag:
            existing_set = set(existing_tag.entity_ids)
            new_entities = [eid for eid in entity_ids if eid not in existing_set]
            if not new_entities:
                continue
            merged = list(existing_tag.entity_ids) + sorted(new_entities)
            existing_tag.entity_ids = merged
            summary["entities_tagged"] += len(new_entities)
        else:
            sorted_ids = sorted(entity_ids)
            existing_tags[tag_id] = EntityTag(
                tag_id=tag_id,
                name=tag_name,
                entity_ids=sorted_ids,
                color=color,
                icon=icon,
            )
            summary["entities_tagged"] += len(sorted_ids)
        tags_modified = True

    if tags_modified:
        await async_save_entity_tags(hass, existing_tags)
        _LOGGER.info(
            "Auto-setup: tagged %d entities across %d domain tags",
            summary["entities_tagged"],
            len(domain_entities),
        )

    _LOGGER.info(
        "Auto-setup summary: areas=%d, zones_created=%d, entities_assigned=%d, entities_tagged=%d",
        summary["areas_found"],
        summary["zones_created"],
        summary["entities_assigned"],
        summary["entities_tagged"],
    )

    return summary
