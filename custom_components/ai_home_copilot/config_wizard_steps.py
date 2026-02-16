"""Wizard step handlers extracted from config_flow.py."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.helpers import selector

from .config_helpers import (
    ZONE_ENTITY_ROLES,
    STEP_DISCOVERY,
    STEP_ZONES,
    STEP_ZONE_ENTITIES,
    STEP_ENTITIES,
    STEP_FEATURES,
    STEP_NETWORK,
    STEP_REVIEW,
)
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_WATCHDOG_ENABLED,
    CONF_EVENTS_FORWARDER_ENABLED,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_WATCHDOG_ENABLED,
    DEFAULT_EVENTS_FORWARDER_ENABLED,
)
from .setup_wizard import (
    SCHEMA_FEATURES,
    SCHEMA_NETWORK,
    SCHEMA_REVIEW,
)


def build_discovery_form():
    """Return (step_id, data_schema, description_placeholders) for the discovery step."""
    return (
        "wizard_discovery",
        vol.Schema({
            vol.Optional("quick_start", default=True): bool,
            vol.Optional("auto_discover", default=True): bool,
        }),
        {
            "description": (
                "Quick Start uses intelligent defaults based on your HA setup. "
                "Auto-discovery will scan for compatible devices.\n\n"
                "Skip advanced configuration if you're experienced with OpenClaw."
            )
        },
    )


def build_zones_form(wizard):
    """Return (step_id, data_schema, description_placeholders) for the zones step."""
    zone_suggestions = wizard.get_zone_suggestions()
    zone_options = [
        (z["area_id"], f"{z['name']} ({z['entity_count']} entities)")
        for z in zone_suggestions
    ]

    if zone_options:
        zone_schema = vol.Schema({
            vol.Optional("selected_zones"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=v, label=l)
                        for v, l in zone_options
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        })
    else:
        zone_schema = vol.Schema({
            vol.Optional("selected_zones"): str,
        })

    return (
        "wizard_zones",
        zone_schema,
        {
            "found_zones": str(len(zone_suggestions)),
            "hint": "Select zones or skip with empty selection.",
        },
    )


def build_zone_entities_form(wizard, selected_zones):
    """Return (step_id, data_schema, description_placeholders) for zone entity config."""
    zone_entities_schema = {}
    for zone_id in selected_zones:
        zone_info = wizard.get_zone_info(zone_id)
        for role, config in ZONE_ENTITY_ROLES.items():
            key = f"{zone_id}_{role}"
            zone_entities_schema[vol.Optional(key)] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=[config.get("domain", "sensor")],
                    multiple=True,
                )
            )

    return (
        "wizard_zone_entities",
        vol.Schema(zone_entities_schema) if zone_entities_schema else vol.Schema({}),
        {
            "zone_count": str(len(selected_zones)),
            "hint": "Configure entities for each zone (optional).",
        },
    )


def build_entities_form(wizard):
    """Return (step_id, data_schema, description_placeholders) for entity selection."""
    suggestions = wizard.suggest_media_players()
    return (
        "wizard_entities",
        vol.Schema({
            vol.Optional("music_players", default=suggestions["music"]): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["media_player"],
                    multiple=True,
                )
            ),
            vol.Optional("tv_players", default=suggestions["tv"]): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["media_player"],
                    multiple=True,
                )
            ),
        }),
        None,
    )


def build_features_form():
    """Return (step_id, data_schema, description_placeholders) for feature selection."""
    return ("wizard_features", SCHEMA_FEATURES, None)


def build_network_form():
    """Return (step_id, data_schema, description_placeholders) for network config."""
    return ("wizard_network", SCHEMA_NETWORK, None)


def build_review_form(wizard_data: dict):
    """Return (step_id, data_schema, description_placeholders) for the review step."""
    network = wizard_data.get("network", {})
    entities = wizard_data.get("entities", {})
    features = wizard_data.get("features", [])
    zones = wizard_data.get("selected_zones", [])

    music_count = len(entities.get("music_players", [])) if isinstance(entities.get("music_players"), list) else 0
    tv_count = len(entities.get("tv_players", [])) if isinstance(entities.get("tv_players"), list) else 0

    summary = f"""
**Configuration Summary:**

**Network:**
- Host: {network.get(CONF_HOST, DEFAULT_HOST)}
- Port: {network.get(CONF_PORT, DEFAULT_PORT)}

**Selected Zones:** {len(zones) if zones else 'Auto-detected'}

**Media Players:**
- Music: {music_count} players
- TV: {tv_count} players

**Features:** {', '.join(features) if features else 'Basic'}
    """

    return (
        "wizard_review",
        SCHEMA_REVIEW,
        {"summary": summary},
    )


def process_discovery_input(user_input: dict, wizard, wizard_data: dict) -> str:
    """Process discovery step input. Returns next step name."""
    quick_start = user_input.get("quick_start", True)
    wizard_data["quick_start"] = quick_start

    if user_input.get("auto_discover", True):
        # discover_entities is async, but called from the async dispatcher
        wizard_data["_auto_discover"] = True

    if quick_start:
        suggestions = wizard.suggest_media_players()
        wizard_data["entities"] = {
            "music_players": suggestions.get("music", []),
            "tv_players": suggestions.get("tv", []),
        }
        wizard_data["features"] = ["basic", "media_control"]
        wizard_data["selected_zones"] = []
        wizard_data["network"] = {
            CONF_HOST: DEFAULT_HOST,
            CONF_PORT: DEFAULT_PORT,
            CONF_TOKEN: "",
        }
        return STEP_REVIEW
    return STEP_ZONES


def process_zones_input(user_input: dict, wizard_data: dict) -> str:
    """Process zones step input. Returns next step name."""
    wizard_data["selected_zones"] = user_input.get("selected_zones", [])
    return STEP_ZONE_ENTITIES


def process_zone_entities_input(user_input: dict, wizard_data: dict) -> str:
    """Process zone entities step input. Returns next step name."""
    zone_entities = {}
    for key, value in user_input.items():
        if value and isinstance(value, list):
            zone_entities[key] = value
    wizard_data["zone_entities"] = zone_entities
    return STEP_ENTITIES


def process_entities_input(user_input: dict, wizard_data: dict) -> str:
    """Process entities step input. Returns next step name."""
    wizard_data["entities"] = user_input
    return STEP_FEATURES


def process_features_input(user_input: dict, wizard_data: dict) -> str:
    """Process features step input. Returns next step name."""
    wizard_data["features"] = user_input.get("features", [])
    return STEP_NETWORK


def process_network_input(user_input: dict, wizard_data: dict) -> str:
    """Process network step input. Returns next step name."""
    wizard_data["network"] = user_input
    return STEP_REVIEW


def build_final_config(wizard_data: dict) -> tuple[dict, str]:
    """Build final config from wizard data. Returns (config_dict, title)."""
    final_config = {
        **wizard_data.get("network", {}),
        **wizard_data.get("entities", {}),
        "selected_zones": wizard_data.get("selected_zones", []),
        "features": wizard_data.get("features", []),
        CONF_WATCHDOG_ENABLED: DEFAULT_WATCHDOG_ENABLED,
        CONF_EVENTS_FORWARDER_ENABLED: DEFAULT_EVENTS_FORWARDER_ENABLED,
    }
    title = "AI Home CoPilot (Quick Start)" if wizard_data.get("quick_start") else "AI Home CoPilot"
    return final_config, title
