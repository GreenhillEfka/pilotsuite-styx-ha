"""Helpers and constants for config flow modules."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

# Entity roles for zone configuration
ZONE_ENTITY_ROLES = {
    "motion": {"icon": "mdi:motion-sensor", "label": "Bewegung"},
    "lights": {"icon": "mdi:lightbulb", "label": "Lichter"},
    "sensors": {"icon": "mdi:thermometer", "label": "Sensoren"},
    "media": {"icon": "mdi:television", "label": "Media"},
    "climate": {"icon": "mdi:thermostat", "label": "Klima"},
    "covers": {"icon": "mdi:blinds", "label": "Jalousien"},
}

# Wizard step constants
STEP_DISCOVERY = "discovery"
STEP_ZONES = "zones"
STEP_ZONE_ENTITIES = "zone_entities"
STEP_ENTITIES = "entities"
STEP_FEATURES = "features"
STEP_NETWORK = "network"
STEP_REVIEW = "review"


def as_csv(value) -> str:
    """Convert a value to a comma-separated string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ",".join([v for v in value if isinstance(v, str)])
    return str(value)


def parse_csv(value: str) -> list[str]:
    """Parse a comma-separated string into a list of strings."""
    if not value:
        return []
    parts = [p.strip() for p in value.replace("\n", ",").split(",")]
    return [p for p in parts if p]


async def validate_input(hass: HomeAssistant, data: dict) -> None:
    """Validate config input. Light for MVP; coordinator marks unavailable on failures."""
    return
