"""Setup Wizard for PilotSuite - Auto-Configuration for new users.

Provides a guided setup flow with:
- Auto-discovery of entities
- Zone selection
- Feature selection
- Network configuration
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import area_registry, device_registry, entity_registry
from homeassistant.helpers.selector import (
    selector,
    EntitySelectorConfig,
    AreaSelectorConfig,
    DeviceSelectorConfig,
)

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_WEBHOOK_URL,
    CONF_MEDIA_MUSIC_PLAYERS,
    CONF_MEDIA_TV_PLAYERS,
    CONF_WATCHDOG_ENABLED,
    CONF_EVENTS_FORWARDER_ENABLED,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_MEDIA_MUSIC_PLAYERS,
    DEFAULT_MEDIA_TV_PLAYERS,
    DEFAULT_WATCHDOG_ENABLED,
    DEFAULT_EVENTS_FORWARDER_ENABLED,
)

_LOGGER = logging.getLogger(__name__)

# Wizard steps
STEP_DISCOVERY = "discovery"
STEP_ZONES = "zones"
STEP_ENTITIES = "entities"
STEP_FEATURES = "features"
STEP_NETWORK = "network"
STEP_REVIEW = "review"

# Smart German zone templates for auto-suggestion
# Maps common German room names to expected entity roles and keywords
ZONE_TEMPLATES: dict[str, dict] = {
    "wohnbereich": {
        "name": "Wohnbereich",
        "icon": "mdi:sofa",
        "roles": ["lights", "media", "motion", "temperature", "brightness"],
        "keywords": ["wohn", "living", "lounge", "stube"],
        "priority": "high",
    },
    "schlafbereich": {
        "name": "Schlafbereich",
        "icon": "mdi:bed",
        "roles": ["lights", "motion", "temperature", "humidity", "cover"],
        "keywords": ["schlaf", "bed", "sleep", "schlafzimmer"],
        "priority": "high",
    },
    "kochbereich": {
        "name": "Kochbereich",
        "icon": "mdi:stove",
        "roles": ["lights", "motion", "temperature", "humidity", "co2", "power"],
        "keywords": ["kuch", "küch", "kitchen", "cook", "kochen"],
        "priority": "high",
    },
    "badbereich": {
        "name": "Badbereich",
        "icon": "mdi:shower",
        "roles": ["lights", "motion", "humidity", "temperature", "heating"],
        "keywords": ["bad", "bath", "dusch", "shower", "wc", "toilet"],
        "priority": "high",
    },
    "buero": {
        "name": "Büro / Arbeitsbereich",
        "icon": "mdi:desk",
        "roles": ["lights", "motion", "temperature", "brightness", "co2", "noise"],
        "keywords": ["büro", "buero", "office", "arbeit", "work", "desk"],
        "priority": "medium",
    },
    "flur": {
        "name": "Flurbereich",
        "icon": "mdi:door-open",
        "roles": ["lights", "motion", "door"],
        "keywords": ["flur", "hall", "corridor", "gang", "diele"],
        "priority": "medium",
    },
    "eingang": {
        "name": "Eingangsbereich",
        "icon": "mdi:door",
        "roles": ["lights", "motion", "camera", "lock", "door"],
        "keywords": ["eingang", "entrance", "entry", "haustür", "front"],
        "priority": "medium",
    },
    "garten": {
        "name": "Gartenbereich",
        "icon": "mdi:flower",
        "roles": ["lights", "motion", "camera", "temperature", "brightness"],
        "keywords": ["garten", "garden", "terrasse", "balkon", "outdoor", "aussen", "außen"],
        "priority": "low",
    },
    "keller": {
        "name": "Kellerbereich",
        "icon": "mdi:home-floor-negative-1",
        "roles": ["lights", "motion", "humidity", "temperature"],
        "keywords": ["keller", "basement", "cellar", "untergeschoss"],
        "priority": "low",
    },
    "kinderzimmer": {
        "name": "Kinderzimmer",
        "icon": "mdi:baby-face-outline",
        "roles": ["lights", "motion", "temperature", "humidity", "noise", "camera"],
        "keywords": ["kind", "child", "nursery", "spielzimmer", "kids"],
        "priority": "medium",
    },
    "esszimmer": {
        "name": "Essbereich",
        "icon": "mdi:silverware-fork-knife",
        "roles": ["lights", "motion", "temperature"],
        "keywords": ["ess", "dining", "speise"],
        "priority": "medium",
    },
    "garage": {
        "name": "Garage",
        "icon": "mdi:garage",
        "roles": ["lights", "motion", "camera", "cover", "door"],
        "keywords": ["garage", "carport", "stellplatz"],
        "priority": "low",
    },
}


class SetupWizard:
    """Manages the setup wizard flow."""
    
    def __init__(self, hass: HomeAssistant):
        self._hass = hass
        self._discovered_entities: Dict[str, List[Dict]] = {}
        self._selected_zones: List[str] = []
        self._selected_entities: Dict[str, List[str]] = {}
        self._selected_features: List[str] = []
    
    async def discover_entities(self) -> Dict[str, List[Dict]]:
        """Auto-discover relevant entities in HA."""
        discovered = {
            "media_players": [],
            "lights": [],
            "switches": [],
            "sensors": [],
            "binary_sensors": [],
            "persons": [],
            "zones": [],
            "weather": [],
            "calendar": [],
        }
        
        # Get entity registry
        ent_reg = entity_registry.async_get(self._hass)
        
        # Categorize entities
        for entity_id, entry in ent_reg.entities.items():
            domain = entry.domain
            
            if domain == "media_player":
                state = self._hass.states.get(entity_id)
                discovered["media_players"].append({
                    "entity_id": entity_id,
                    "name": entry.name or entity_id,
                    "state": state.state if state else "unknown",
                    "device_class": state.attributes.get("device_class") if state else None,
                })
            elif domain == "light":
                discovered["lights"].append({
                    "entity_id": entity_id,
                    "name": entry.name or entity_id,
                })
            elif domain == "switch":
                discovered["switches"].append({
                    "entity_id": entity_id,
                    "name": entry.name or entity_id,
                })
            elif domain == "sensor":
                discovered["sensors"].append({
                    "entity_id": entity_id,
                    "name": entry.name or entity_id,
                    "device_class": entry.device_class,
                })
            elif domain == "binary_sensor":
                discovered["binary_sensors"].append({
                    "entity_id": entity_id,
                    "name": entry.name or entity_id,
                    "device_class": entry.device_class,
                })
            elif domain == "person":
                discovered["persons"].append({
                    "entity_id": entity_id,
                    "name": entry.name or entity_id,
                })
            elif domain == "weather":
                discovered["weather"].append({
                    "entity_id": entity_id,
                    "name": entry.name or entity_id,
                })
            elif domain == "calendar":
                discovered["calendar"].append({
                    "entity_id": entity_id,
                    "name": entry.name or entity_id,
                })
        
        # Get areas/zones
        area_reg = area_registry.async_get(self._hass)
        for area_id, area in area_reg.areas.items():
            discovered["zones"].append({
                "area_id": area_id,
                "name": area.name,
                "icon": area.icon,
            })
        
        self._discovered_entities = discovered
        return discovered
    
    def get_zone_suggestions(self) -> List[Dict]:
        """Get suggested zones based on discovered areas with smart template matching."""
        zones = self._discovered_entities.get("zones", [])

        # Prioritize zones with entities and match to German templates
        prioritized = []
        ent_reg = entity_registry.async_get(self._hass)

        for zone in zones:
            entity_count = 0
            for entity_id, entry in ent_reg.entities.items():
                if entry.area_id == zone["area_id"]:
                    entity_count += 1

            # Match zone name to German templates
            zone_name_lower = (zone.get("name") or "").lower()
            matched_template = None
            for tpl_key, tpl in ZONE_TEMPLATES.items():
                if any(kw in zone_name_lower for kw in tpl["keywords"]):
                    matched_template = tpl
                    break

            tpl_priority = matched_template["priority"] if matched_template else "low"
            tpl_icon = matched_template["icon"] if matched_template else zone.get("icon", "mdi:home-circle")
            tpl_roles = matched_template["roles"] if matched_template else []

            # Compute combined priority score
            priority_scores = {"high": 3, "medium": 2, "low": 1}
            entity_score = 3 if entity_count > 5 else 2 if entity_count > 2 else 1
            combined_score = priority_scores.get(tpl_priority, 1) + entity_score

            prioritized.append({
                **zone,
                "entity_count": entity_count,
                "priority": "high" if combined_score >= 5 else "medium" if combined_score >= 3 else "low",
                "template": matched_template["name"] if matched_template else None,
                "suggested_roles": tpl_roles,
                "icon": tpl_icon,
            })

        # Sort by combined priority then entity count
        priority_order = {"high": 0, "medium": 1, "low": 2}
        prioritized.sort(key=lambda z: (priority_order.get(z["priority"], 3), -z["entity_count"]))
        return prioritized
    
    def get_zone_info(self, zone_id: str) -> Dict:
        """Get info for a specific zone."""
        zones = self._discovered_entities.get("zones", [])
        for zone in zones:
            if zone.get("area_id") == zone_id:
                return zone
        return {"area_id": zone_id, "name": zone_id, "entity_count": 0}
    
    def suggest_media_players(self) -> Dict[str, List[str]]:
        """Suggest media player configuration."""
        media_players = self._discovered_entities.get("media_players", [])
        
        music_players = []
        tv_players = []
        
        for player in media_players:
            device_class = player.get("device_class")
            
            if device_class == "tv":
                tv_players.append(player["entity_id"])
            elif device_class in ("speaker", "receiver", "speaker"):
                music_players.append(player["entity_id"])
            else:
                # Default: check name for hints
                name_lower = player["name"].lower()
                if any(x in name_lower for x in ["tv", "fernseher", "television"]):
                    tv_players.append(player["entity_id"])
                elif any(x in name_lower for x in ["speaker", "sonos", "audio", "musik"]):
                    music_players.append(player["entity_id"])
        
        return {
            "music": music_players[:5],  # Limit to 5
            "tv": tv_players[:5],
        }


async def generate_wizard_config(
    hass: HomeAssistant,
    selected_zones: List[str],
    selected_entities: Dict[str, List[str]],
    selected_features: List[str],
) -> Dict[str, Any]:
    """Generate final configuration from wizard selections."""
    
    wizard = SetupWizard(hass)
    await wizard.discover_entities()
    suggestions = wizard.suggest_media_players()
    
    config = {
        CONF_MEDIA_MUSIC_PLAYERS: selected_entities.get("music_players", suggestions["music"]),
        CONF_MEDIA_TV_PLAYERS: selected_entities.get("tv_players", suggestions["tv"]),
        CONF_WATCHDOG_ENABLED: DEFAULT_WATCHDOG_ENABLED,
        CONF_EVENTS_FORWARDER_ENABLED: DEFAULT_EVENTS_FORWARDER_ENABLED,
    }
    
    # Add feature-specific config
    if "energy_monitoring" in selected_features:
        # Would enable energy context
        pass
    
    if "presence_tracking" in selected_features:
        # Would configure presence tracking
        pass
    
    return config


# Discovery step schema
SCHEMA_DISCOVERY = vol.Schema({
    vol.Optional("auto_discover", default=True): bool,
})

# Zone selection schema (dynamic based on discovered areas)
def generate_zones_schema(zones: List[Dict]) -> vol.Schema:
    """Generate zone selection schema."""
    zone_options = [
        (z["area_id"], z["name"]) for z in zones
    ]
    
    return vol.Schema({
        vol.Required("selected_zones"): selector({
            "select": {
                "options": zone_options,
                "multiple": True,
                "mode": "list",
            }
        }),
    })

# Entity selection schema
SCHEMA_ENTITIES = vol.Schema({
    vol.Optional("music_players", default=[]): selector({
        "entity": {
            "filter": [{"domain": "media_player"}],
            "multiple": True,
        }
    }),
    vol.Optional("tv_players", default=[]): selector({
        "entity": {
            "filter": [{"domain": "media_player", "device_class": "tv"}],
            "multiple": True,
        }
    }),
    vol.Optional("lights", default=[]): selector({
        "entity": {
            "filter": [{"domain": "light"}],
            "multiple": True,
        }
    }),
})

# Features selection schema
SCHEMA_FEATURES = vol.Schema({
    vol.Required("features", default=["basic"]): selector({
        "select": {
            "options": [
                {"value": "basic", "label": "Basic - Core automation"},
                {"value": "energy_monitoring", "label": "Energy Monitoring"},
                {"value": "presence_tracking", "label": "Presence Tracking"},
                {"value": "media_control", "label": "Media Control"},
                {"value": "weather_integration", "label": "Weather Integration"},
                {"value": "calendar_integration", "label": "Calendar Integration"},
                {"value": "habitus_zones", "label": "Habitus Zones"},
                {"value": "mood_detection", "label": "Mood Detection"},
                {"value": "ml_automation", "label": "ML-Powered Automation"},
            ],
            "multiple": True,
            "mode": "list",
        }
    }),
})

# Network configuration schema
SCHEMA_NETWORK = vol.Schema({
    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    vol.Required(CONF_TOKEN): str,
})

# Review step schema
SCHEMA_REVIEW = vol.Schema({
    vol.Optional("confirm", default=True): bool,
})


# Export the wizard class
__all__ = [
    "SetupWizard",
    "generate_wizard_config",
]
