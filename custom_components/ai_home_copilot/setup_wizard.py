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
        """Get suggested zones based on discovered areas."""
        zones = self._discovered_entities.get("zones", [])
        
        # Prioritize zones with entities
        prioritized = []
        for zone in zones:
            entity_count = 0
            # Count entities in this zone
            ent_reg = entity_registry.async_get(self._hass)
            for entity_id, entry in ent_reg.entities.items():
                if entry.area_id == zone["area_id"]:
                    entity_count += 1
            
            prioritized.append({
                **zone,
                "entity_count": entity_count,
                "priority": "high" if entity_count > 5 else "medium" if entity_count > 2 else "low",
            })
        
        # Sort by entity count
        prioritized.sort(key=lambda z: z["entity_count"], reverse=True)
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


class AiHomeCopilotSetupWizard(config_entries.FlowHandler):
    """Config flow handler with setup wizard."""
    
    VERSION = 2  # New wizard version
    
    def __init__(self):
        self._wizard: Optional[SetupWizard] = None
        self._step = STEP_DISCOVERY
        self._data: Dict[str, Any] = {}
    
    async def async_step_init(self, user_input: Optional[Dict] = None) -> FlowResult:
        """Initialize the wizard."""
        self._wizard = SetupWizard(self.hass)
        return await self.async_step_discovery(user_input)
    
    async def async_step_discovery(self, user_input: Optional[Dict] = None) -> FlowResult:
        """Discovery step - find entities."""
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_DISCOVERY,
                data_schema=SCHEMA_DISCOVERY,
                description_placeholders={
                    "description": "This will scan your Home Assistant for compatible devices."
                }
            )
        
        # Perform auto-discovery
        discovered = await self._wizard.discover_entities()
        
        summary = {
            "media_players": len(discovered.get("media_players", [])),
            "lights": len(discovered.get("lights", [])),
            "persons": len(discovered.get("persons", [])),
            "zones": len(discovered.get("zones", [])),
            "weather": len(discovered.get("weather", [])),
        }
        
        self._data["discovery"] = discovered
        
        return self.async_show_form(
            step_id=STEP_ZONES,
            data_schema=generate_zones_schema(self._wizard.get_zone_suggestions()),
            description_placeholders={
                "summary": f"Found: {summary['media_players']} media players, {summary['zones']} zones"
            }
        )
    
    async def async_step_zones(self, user_input: Optional[Dict] = None) -> FlowResult:
        """Zone selection step."""
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_ZONES,
                data_schema=generate_zones_schema(self._wizard.get_zone_suggestions()),
            )
        
        self._data["selected_zones"] = user_input.get("selected_zones", [])
        return await self.async_step_entities(None)
    
    async def async_step_entities(self, user_input: Optional[Dict] = None) -> FlowResult:
        """Entity selection step."""
        # Get suggestions
        suggestions = self._wizard.suggest_media_players()
        
        # Create schema with suggested values
        schema = vol.Schema({
            vol.Optional("music_players", default=suggestions["music"]): selector({
                "entity": {
                    "filter": [{"domain": "media_player"}],
                    "multiple": True,
                }
            }),
            vol.Optional("tv_players", default=suggestions["tv"]): selector({
                "entity": {
                    "filter": [{"domain": "media_player", "device_class": "tv"}],
                    "multiple": True,
                }
            }),
        })
        
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_ENTITIES,
                data_schema=schema,
            )
        
        self._data["entities"] = user_input
        return await self.async_step_features(None)
    
    async def async_step_features(self, user_input: Optional[Dict] = None) -> FlowResult:
        """Feature selection step."""
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_FEATURES,
                data_schema=SCHEMA_FEATURES,
            )
        
        self._data["features"] = user_input.get("features", [])
        return await self.async_step_network(None)
    
    async def async_step_network(self, user_input: Optional[Dict] = None) -> FlowResult:
        """Network configuration step."""
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_NETWORK,
                data_schema=SCHEMA_NETWORK,
            )
        
        self._data["network"] = user_input
        return await self.async_step_review(None)
    
    async def async_step_review(self, user_input: Optional[Dict] = None) -> FlowResult:
        """Review and confirm configuration."""
        if user_input is None:
            # Generate summary
            network = self._data.get("network", {})
            entities = self._data.get("entities", {})
            features = self._data.get("features", [])
            zones = self._data.get("selected_zones", [])
            
            summary = f"""
**Configuration Summary:**

**Network:**
- Host: {network.get(CONF_HOST, DEFAULT_HOST)}
- Port: {network.get(CONF_PORT, DEFAULT_PORT)}

**Selected Zones:** {len(zones)} zones

**Media Players:**
- Music: {len(entities.get('music_players', []))} players
- TV: {len(entities.get('tv_players', []))} players

**Features:** {', '.join(features) if features else 'Basic'}
            """
            
            return self.async_show_form(
                step_id=STEP_REVIEW,
                data_schema=SCHEMA_REVIEW,
                description_placeholders={"summary": summary}
            )
        
        # Generate final configuration
        final_config = {
            **self._data.get("network", {}),
            **self._data.get("entities", {}),
            "selected_zones": self._data.get("selected_zones", []),
            "features": self._data.get("features", []),
        }
        
        return self.async_create_entry(
            title="PilotSuite",
            data=final_config,
        )


# Export the wizard class
__all__ = [
    "SetupWizard",
    "generate_wizard_config",
    "AiHomeCopilotSetupWizard",
]
