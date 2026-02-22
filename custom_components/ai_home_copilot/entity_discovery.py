"""Entity Auto-Discovery for Zero-Config Setup.

Scans HA for known device types and suggests Habitus Zones accordingly.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Known media player domains with location hints
MEDIA_DEVICE_MAPPINGS = {
    "sonos": {
        "domain": "media_player",
        "platform": "sonos",
        "keywords": ["sonos", "play:", "woonzender", "living", "kitchen", "bedroom", "bath"],
        "icon": "mdi:speaker-wireless",
    },
    "apple_tv": {
        "domain": "media_player",
        "platform": "apple_tv",
        "keywords": ["apple", "tv", "atv", "living room", "bedroom"],
        "icon": "mdi:television-classic",
    },
    "smart_tv": {
        "domain": "media_player",
        "platform": ["lg_webos", "samsungtv", "firetv", "roku", "chromecast"],
        "keywords": ["tv", "smart", "living", "bedroom", "kitchen", "samsung", "lg", "panasonic"],
        "icon": "mdi:television",
    },
}

# Zone inference keywords
ZONE_KEYWORDS = {
    "living_room": ["living", "woonkamer", "salon", "livingroom", "lounge", "tv", "wohnzimmer"],
    "kitchen": ["kitchen", "keuken", "küche", "cook", "küche"],
    "bedroom": ["bedroom", "slaapkamer", "schlafzimmer", "bed", "night", "schlafzimmer"],
    "bathroom": ["bathroom", "badkamer", "badezimmer", "bath", "douche", "dusche"],
    "office": ["office", "kantoor", "büro", "work", "study", "arbeitszimmer"],
    "garage": ["garage", "garage", "werkplaats"],
    "garden": ["garden", "tuin", "garten", "terrace", "patio"],
}


def _normalize_entity_name(entity_id: str, state: Any) -> str:
    """Get a normalized display name for an entity."""
    if state and hasattr(state, "attributes"):
        name = state.attributes.get("friendly_name", "")
        if name:
            return name.lower()
    return entity_id.lower().replace("_", " ").replace(".", " ")


def infer_zone_from_entity(entity_id: str, state: Any) -> str | None:
    """Infer a Habitus zone from entity name/area."""
    name = _normalize_entity_name(entity_id, state)
    area_id = None
    
    if state and hasattr(state, "attributes"):
        area_id = state.attributes.get("area_id")
    
    # Check area_id first
    if area_id:
        area_lower = area_id.lower()
        for zone, keywords in ZONE_KEYWORDS.items():
            if any(kw in area_lower for kw in keywords):
                return zone
    
    # Fallback to entity name keywords
    for zone, keywords in ZONE_KEYWORDS.items():
        if any(kw in name for kw in keywords):
            return zone
    
    return None


async def discover_media_entities(hass: HomeAssistant) -> dict[str, list[dict]]:
    """Discover media players and group them by inferred zone.
    
    Returns:
        Dict mapping zone_name -> list of discovered entities
    """
    discovered: dict[str, list[dict]] = {}
    
    # Get all media_player entities
    states = hass.states.async_all("media_player")
    
    for state in states:
        entity_id = state.entity_id
        
        # Skip unavailable
        if state.state == "unavailable":
            continue
        
        # Infer zone
        zone = infer_zone_from_entity(entity_id, state) or "unassigned"
        
        # Determine device type
        device_type = "unknown"
        icon = "mdi:speaker"
        
        # Check platform/attributes
        if hasattr(state, "attributes"):
            attrs = state.attributes
            platform = attrs.get("platform", "")
            app = attrs.get("app_name", "").lower()
            
            # Sonos
            if "sonos" in platform.lower() or "sonos" in app:
                device_type = "sonos"
                icon = "mdi:speaker-wireless"
            # Apple TV
            elif "apple_tv" in platform.lower() or "apple" in app:
                device_type = "apple_tv"
                icon = "mdi:television-classic"
            # Smart TV
            elif any(tv in platform.lower() for tv in ["webos", "samsung", "firetv", "roku", "chromecast"]):
                device_type = "smart_tv"
                icon = "mdi:television"
        
        entity_info = {
            "entity_id": entity_id,
            "name": state.attributes.get("friendly_name", entity_id),
            "device_type": device_type,
            "icon": icon,
            "zone": zone,
        }
        
        if zone not in discovered:
            discovered[zone] = []
        discovered[zone].append(entity_info)
    
    _LOGGER.info("Discovered %d media entities across %d zones", 
                 sum(len(v) for v in discovered.values()), len(discovered))
    
    return discovered


async def discover_entities_for_zones(hass: HomeAssistant) -> dict[str, list[dict]]:
    """Full entity discovery for zone assignment.
    
    Returns:
        Dict mapping zone_name -> list of relevant entities
    """
    discovered: dict[str, list[dict]] = {}
    
    # Media players
    media_by_zone = await discover_media_entities(hass)
    for zone, entities in media_by_zone.items():
        if zone not in discovered:
            discovered[zone] = []
        discovered[zone].extend(entities)
    
    # Lights (for zone brightness context)
    light_states = hass.states.async_all("light")
    for state in light_states:
        if state.state == "unavailable":
            continue
        zone = infer_zone_from_entity(state.entity_id, state) or "unassigned"
        entity_info = {
            "entity_id": state.entity_id,
            "name": state.attributes.get("friendly_name", state.entity_id),
            "device_type": "light",
            "icon": "mdi:lightbulb",
            "zone": zone,
        }
        if zone not in discovered:
            discovered[zone] = []
        discovered[zone].append(entity_info)
    
    # Sensors for context
    sensor_types = ["temperature", "humidity", "motion"]
    for sensor in hass.states.async_all("sensor"):
        if sensor.state == "unavailable":
            continue
        attrs = sensor.attributes if hasattr(sensor, "attributes") else {}
        device_class = attrs.get("device_class", "")
        if device_class in sensor_types or any(t in sensor.entity_id for t in sensor_types):
            zone = infer_zone_from_entity(sensor.entity_id, sensor) or "unassigned"
            entity_info = {
                "entity_id": sensor.entity_id,
                "name": attrs.get("friendly_name", sensor.entity_id),
                "device_type": "sensor",
                "icon": "mdi:sensor",
                "zone": zone,
            }
            if zone not in discovered:
                discovered[zone] = []
            discovered[zone].append(entity_info)
    
    return discovered
