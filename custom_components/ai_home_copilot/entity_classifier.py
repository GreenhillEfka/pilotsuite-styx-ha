"""ML-style entity classification for PilotSuite auto-tagging.

Classifies HA entities by analyzing:
- Entity ID patterns (domain.name)
- Device class attributes
- Unit of measurement
- Entity name keywords (DE + EN)
- Area assignment
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import area_registry, entity_registry

_LOGGER = logging.getLogger(__name__)


@dataclass
class EntityClassification:
    """Classification result for a single entity."""
    entity_id: str
    domain: str
    device_class: str | None = None
    role: str = "unknown"  # lights, presence, brightness, temperature, humidity, media, climate, covers, energy, camera
    zone_hint: str | None = None  # suggested zone from area
    confidence: float = 0.0
    tags: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


# Keyword patterns for role detection (DE + EN)
ROLE_KEYWORDS: dict[str, list[str]] = {
    "presence": ["motion", "bewegung", "presence", "anwesenheit", "occupancy", "pir", "radar"],
    "brightness": ["lux", "illuminance", "helligkeit", "brightness", "light_level"],
    "temperature": ["temperature", "temperatur", "temp", "thermometer"],
    "humidity": ["humidity", "feuchtigkeit", "feuchte", "luftfeuchte"],
    "co2": ["co2", "kohlendioxid", "carbon_dioxide", "air_quality", "luftqualität"],
    "noise": ["noise", "lärm", "geräusch", "sound", "dezibel", "db"],
    "energy": ["energy", "energie", "power", "leistung", "watt", "kwh", "strom", "verbrauch"],
    "door": ["door", "tür", "türe", "kontakt", "contact", "entry"],
    "window": ["window", "fenster", "fensterkontakt"],
    "smoke": ["smoke", "rauch", "rauchmelder", "fire"],
    "water": ["water", "wasser", "leak", "leck", "flood"],
    "battery": ["battery", "batterie", "akku"],
}

# Device class to role mapping
DEVICE_CLASS_ROLE_MAP: dict[str, str] = {
    # binary_sensor device classes
    "motion": "presence",
    "presence": "presence",
    "occupancy": "presence",
    "door": "door",
    "window": "window",
    "garage_door": "door",
    "opening": "door",
    "smoke": "smoke",
    "gas": "smoke",
    "moisture": "water",
    "heat": "temperature",
    "vibration": "presence",
    "sound": "noise",
    "battery": "battery",
    # sensor device classes
    "temperature": "temperature",
    "humidity": "humidity",
    "illuminance": "brightness",
    "pressure": "temperature",
    "carbon_dioxide": "co2",
    "carbon_monoxide": "smoke",
    "pm25": "co2",
    "pm10": "co2",
    "volatile_organic_compounds": "co2",
    "nitrogen_dioxide": "co2",
    "power": "energy",
    "energy": "energy",
    "current": "energy",
    "voltage": "energy",
    "frequency": "energy",
    "signal_strength": "network",
    "battery": "battery",
    "timestamp": "time",
    "duration": "time",
    "speed": "weather",
    "wind_speed": "weather",
    "precipitation": "weather",
    "precipitation_intensity": "weather",
}

# Unit of measurement to role mapping
UOM_ROLE_MAP: dict[str, str] = {
    "°C": "temperature",
    "°F": "temperature",
    "%": "humidity",  # often humidity, but could be battery
    "lx": "brightness",
    "lm": "brightness",
    "W": "energy",
    "kW": "energy",
    "kWh": "energy",
    "Wh": "energy",
    "ppm": "co2",
    "µg/m³": "co2",
    "dB": "noise",
    "dBA": "noise",
}


def classify_entity(
    entity_id: str,
    state: State | None = None,
    area_name: str | None = None,
    entry: Any = None,
) -> EntityClassification:
    """Classify a single entity based on all available signals."""
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
    entity_name = entity_id.split(".", 1)[1] if "." in entity_id else entity_id

    classification = EntityClassification(
        entity_id=entity_id,
        domain=domain,
        zone_hint=area_name,
    )

    # Signal 1: Domain-based base role
    domain_roles = {
        "light": "lights",
        "media_player": "media",
        "climate": "climate",
        "cover": "covers",
        "switch": "switches",
        "fan": "fans",
        "camera": "cameras",
        "lock": "locks",
        "person": "presence",
        "device_tracker": "presence",
        "weather": "weather",
        "vacuum": "appliance",
        "humidifier": "humidity",
        "water_heater": "climate",
    }
    base_role = domain_roles.get(domain, "unknown")
    base_confidence = 0.6

    # Signal 2: Device class (highest confidence)
    device_class = None
    if entry and hasattr(entry, "device_class") and entry.device_class:
        device_class = entry.device_class
    elif state and state.attributes.get("device_class"):
        device_class = state.attributes["device_class"]

    if device_class:
        classification.device_class = device_class
        dc_role = DEVICE_CLASS_ROLE_MAP.get(device_class)
        if dc_role:
            base_role = dc_role
            base_confidence = 0.9

    # Signal 3: Unit of measurement
    uom = None
    if state:
        uom = state.attributes.get("unit_of_measurement")
    if uom and base_confidence < 0.9:
        uom_role = UOM_ROLE_MAP.get(uom)
        if uom_role:
            # Only override if domain is sensor/binary_sensor (generic)
            if domain in ("sensor", "binary_sensor"):
                base_role = uom_role
                base_confidence = max(base_confidence, 0.8)

    # Signal 4: Entity name keyword matching
    name_lower = entity_name.lower()
    friendly_name = ""
    if state and state.attributes.get("friendly_name"):
        friendly_name = state.attributes["friendly_name"].lower()

    combined_name = f"{name_lower} {friendly_name}"

    for role, keywords in ROLE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in combined_name:
                if domain in ("sensor", "binary_sensor") and base_confidence < 0.85:
                    base_role = role
                    base_confidence = max(base_confidence, 0.75)
                classification.tags.append(role)
                break

    classification.role = base_role
    classification.confidence = base_confidence

    # Generate tags based on role + domain
    if domain and domain not in classification.tags:
        classification.tags.insert(0, domain)
    if base_role and base_role not in classification.tags:
        classification.tags.append(base_role)

    return classification


async def classify_all_entities(hass: HomeAssistant) -> list[EntityClassification]:
    """Classify all entities in the HA instance."""
    ent_reg = entity_registry.async_get(hass)
    area_reg = area_registry.async_get(hass)

    # Build area lookup
    area_names: dict[str, str] = {}
    for area_id, area in area_reg.areas.items():
        area_names[area_id] = area.name

    classifications: list[EntityClassification] = []

    for entity_id, entry in ent_reg.entities.items():
        # Skip PilotSuite's own entities
        if entity_id.startswith("sensor.pilotsuite") or entity_id.startswith("sensor.ai_home_copilot"):
            continue
        if entity_id.startswith("button.pilotsuite") or entity_id.startswith("button.ai_home_copilot"):
            continue

        # Skip disabled entities
        if entry.disabled_by:
            continue

        state = hass.states.get(entity_id)
        area_name = area_names.get(entry.area_id) if entry.area_id else None

        # Also check device area if entity has no direct area
        if not area_name and entry.device_id:
            from homeassistant.helpers import device_registry
            dev_reg = device_registry.async_get(hass)
            device = dev_reg.async_get(entry.device_id)
            if device and device.area_id:
                area_name = area_names.get(device.area_id)

        classification = classify_entity(
            entity_id=entity_id,
            state=state,
            area_name=area_name,
            entry=entry,
        )
        classifications.append(classification)

    _LOGGER.info(
        "Classified %d entities: %d with high confidence (>0.8)",
        len(classifications),
        sum(1 for c in classifications if c.confidence > 0.8),
    )
    return classifications


def group_by_zone(classifications: list[EntityClassification]) -> dict[str, list[EntityClassification]]:
    """Group classified entities by their zone hint (area name)."""
    zones: dict[str, list[EntityClassification]] = {}
    for c in classifications:
        zone = c.zone_hint or "_unassigned"
        zones.setdefault(zone, []).append(c)
    return zones


def suggest_zone_entities(
    classifications: list[EntityClassification],
    zone_name: str,
) -> dict[str, list[str]]:
    """For a given zone, suggest entity assignments by role."""
    zone_entities = [c for c in classifications if c.zone_hint == zone_name]

    roles: dict[str, list[str]] = {
        "lights": [],
        "presence": [],
        "brightness": [],
        "temperature": [],
        "humidity": [],
        "co2": [],
        "noise": [],
        "media": [],
        "climate": [],
        "covers": [],
        "energy": [],
        "cameras": [],
        "doors": [],
        "windows": [],
    }

    for entity in zone_entities:
        role = entity.role
        if role in roles:
            roles[role].append(entity.entity_id)
        elif role == "door":
            roles["doors"].append(entity.entity_id)
        elif role == "window":
            roles["windows"].append(entity.entity_id)
        elif role == "switches" and entity.domain == "switch":
            # Don't auto-assign switches, they could be anything
            pass
        elif entity.domain == "light":
            roles["lights"].append(entity.entity_id)
        elif entity.domain == "media_player":
            roles["media"].append(entity.entity_id)

    # Filter empty roles
    return {k: v for k, v in roles.items() if v}
