"""Habitus Control Dashboard Cards -- Live controls for Habitus zones.

Generates Lovelace YAML cards for the Habitus Dashboard including:
- Override modes panel (toggle Party/Vacation/Sleep/Eco/Guest/Children Sleep)
- Musikwolke panel (volume, favorites, coordinator status, grouping)
- Light module panel (brightness ratio, circadian presets, threshold slider)
- Presence module panel (timeout config, sensor status)
- Zone automation panel (occupancy, subsystem evaluations)
- Heating panel (override target temp)
- Per-zone status overview

All cards reference entities from the ai_home_copilot integration.
"""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ai_home_copilot"


def _sensor_id(suffix: str) -> str:
    """Build sensor entity ID."""
    return f"sensor.pilotsuite_styx_{suffix}"


def _button_id(suffix: str) -> str:
    """Build button entity ID."""
    return f"button.pilotsuite_styx_{suffix}"


def generate_override_modes_card() -> dict[str, Any]:
    """Generate the Override Modes control panel card."""
    return {
        "type": "vertical-stack",
        "title": "Override-Modi",
        "cards": [
            {
                "type": "entities",
                "title": "Aktiver Modus",
                "entities": [
                    {
                        "entity": _sensor_id("override_mode"),
                        "name": "Aktiver Modus",
                        "icon": "mdi:toggle-switch",
                    },
                    {
                        "entity": _sensor_id("override_modes_active"),
                        "name": "Aktive Modi",
                        "icon": "mdi:counter",
                    },
                    {
                        "entity": _sensor_id("music_cloud_erlaubt"),
                        "name": "Musik erlaubt",
                    },
                    {
                        "entity": _sensor_id("licht_auto_erlaubt"),
                        "name": "Licht Auto erlaubt",
                    },
                    {
                        "entity": _sensor_id("heizung_override"),
                        "name": "Heizung Override",
                    },
                ],
            },
            {
                "type": "grid",
                "columns": 3,
                "square": True,
                "cards": [
                    {
                        "type": "button",
                        "name": "Party",
                        "icon": "mdi:party-popper",
                        "tap_action": {
                            "action": "call-service",
                            "service": "rest_command.pilotsuite_toggle_mode",
                            "service_data": {"mode_id": "party"},
                        },
                    },
                    {
                        "type": "button",
                        "name": "Urlaub",
                        "icon": "mdi:airplane",
                        "tap_action": {
                            "action": "call-service",
                            "service": "rest_command.pilotsuite_toggle_mode",
                            "service_data": {"mode_id": "vacation"},
                        },
                    },
                    {
                        "type": "button",
                        "name": "Schlaf",
                        "icon": "mdi:sleep",
                        "tap_action": {
                            "action": "call-service",
                            "service": "rest_command.pilotsuite_toggle_mode",
                            "service_data": {"mode_id": "sleep"},
                        },
                    },
                    {
                        "type": "button",
                        "name": "Kinder",
                        "icon": "mdi:baby-face-outline",
                        "tap_action": {
                            "action": "call-service",
                            "service": "rest_command.pilotsuite_toggle_mode",
                            "service_data": {"mode_id": "children_sleep"},
                        },
                    },
                    {
                        "type": "button",
                        "name": "Eco",
                        "icon": "mdi:leaf",
                        "tap_action": {
                            "action": "call-service",
                            "service": "rest_command.pilotsuite_toggle_mode",
                            "service_data": {"mode_id": "eco"},
                        },
                    },
                    {
                        "type": "button",
                        "name": "Gäste",
                        "icon": "mdi:account-group",
                        "tap_action": {
                            "action": "call-service",
                            "service": "rest_command.pilotsuite_toggle_mode",
                            "service_data": {"mode_id": "guest"},
                        },
                    },
                ],
            },
        ],
    }


def generate_musikwolke_card() -> dict[str, Any]:
    """Generate the Musikwolke (Music Cloud) control panel card."""
    return {
        "type": "vertical-stack",
        "title": "Musikwolke",
        "cards": [
            {
                "type": "entities",
                "title": "Status",
                "entities": [
                    {
                        "entity": _sensor_id("musikwolke_status"),
                        "name": "Musikwolke Status",
                        "icon": "mdi:cloud-outline",
                    },
                    {
                        "entity": _sensor_id("musikwolke_koordinator"),
                        "name": "Koordinator",
                        "icon": "mdi:speaker-group",
                    },
                    {
                        "entity": _sensor_id("volume_preset"),
                        "name": "Lautstärke Preset",
                        "icon": "mdi:volume-medium",
                    },
                    {
                        "entity": _sensor_id("music_cloud"),
                        "name": "Zonen-Following",
                        "icon": "mdi:music-circle",
                    },
                    {
                        "entity": _sensor_id("music_cloud_zones"),
                        "name": "Konfigurierte Zonen",
                        "icon": "mdi:speaker-multiple",
                    },
                ],
            },
            {
                "type": "markdown",
                "title": "Sonos Favoriten",
                "content": (
                    "{% set status = states('sensor.pilotsuite_styx_musikwolke_status') %}\n"
                    "{% if status == 'Deaktiviert' %}\n"
                    "Musikwolke ist **deaktiviert**.\n"
                    "{% elif 'Aktiv' in status %}\n"
                    "Musikwolke ist **aktiv** mit {{ status }}.\n"
                    "{% else %}\n"
                    "Musikwolke ist **bereit** und wartet auf Präsenzerkennung.\n"
                    "{% endif %}"
                ),
            },
        ],
    }


def generate_light_module_card() -> dict[str, Any]:
    """Generate the Light Module control panel card."""
    return {
        "type": "vertical-stack",
        "title": "Lichtsteuerung",
        "cards": [
            {
                "type": "entities",
                "title": "Adaptives Licht",
                "entities": [
                    {
                        "entity": _sensor_id("light_module"),
                        "name": "Lichtmodul Status",
                        "icon": "mdi:lightbulb-auto",
                    },
                    {
                        "entity": _sensor_id("light_module_zones"),
                        "name": "Konfigurierte Zonen",
                        "icon": "mdi:floor-plan",
                    },
                    {
                        "entity": _sensor_id("light_level"),
                        "name": "Lichtlevel",
                        "icon": "mdi:brightness-6",
                    },
                    {
                        "entity": _sensor_id("light_intelligence"),
                        "name": "Licht-Intelligenz",
                        "icon": "mdi:lightbulb-on",
                    },
                ],
            },
            {
                "type": "markdown",
                "title": "Circadian Presets",
                "content": (
                    "| Preset | Farbtemp | Helligkeit |\n"
                    "|--------|----------|------------|\n"
                    "| Nacht | 2200K | 15% |\n"
                    "| Abend | 2700K | 60% |\n"
                    "| Tag | 4500K | 100% |\n"
                    "| Fokus | 5500K | 100% |\n"
                    "| Film | 2400K | 10% |\n"
                    "| Entspannung | 3000K | 40% |"
                ),
            },
        ],
    }


def generate_presence_module_card() -> dict[str, Any]:
    """Generate the Presence Module control panel card."""
    return {
        "type": "vertical-stack",
        "title": "Präsenzerkennung",
        "cards": [
            {
                "type": "entities",
                "title": "Präsenz Status",
                "entities": [
                    {
                        "entity": _sensor_id("presence_room"),
                        "name": "Raum-Präsenz",
                        "icon": "mdi:motion-sensor",
                    },
                    {
                        "entity": _sensor_id("presence_person"),
                        "name": "Person-Tracking",
                        "icon": "mdi:account-circle",
                    },
                    {
                        "entity": _sensor_id("activity_level"),
                        "name": "Aktivitätslevel",
                        "icon": "mdi:run",
                    },
                    {
                        "entity": _sensor_id("activity_stillness"),
                        "name": "Stille-Erkennung",
                        "icon": "mdi:meditation",
                    },
                ],
            },
        ],
    }


def generate_zone_automation_card() -> dict[str, Any]:
    """Generate the Zone Automation overview card."""
    return {
        "type": "vertical-stack",
        "title": "Zonen-Automation",
        "cards": [
            {
                "type": "entities",
                "title": "Zonen Status",
                "entities": [
                    {
                        "entity": _sensor_id("zone_automation"),
                        "name": "Zone Automation",
                        "icon": "mdi:home-automation",
                    },
                    {
                        "entity": _sensor_id("belegte_zonen"),
                        "name": "Belegte Zonen",
                        "icon": "mdi:account-group",
                    },
                ],
            },
        ],
    }


def generate_zone_status_card(zone_name: str, zone_id: str) -> dict[str, Any]:
    """Generate a per-zone status card."""
    return {
        "type": "vertical-stack",
        "title": f"Zone: {zone_name}",
        "cards": [
            {
                "type": "markdown",
                "content": (
                    f"**Zone:** {zone_name}\n"
                    f"**ID:** `{zone_id}`\n\n"
                    "---\n"
                    "| Subsystem | Status |\n"
                    "|-----------|--------|\n"
                    "| Musikwolke | {{ states('sensor.pilotsuite_styx_musikwolke_status') }} |\n"
                    "| Licht | {{ states('sensor.pilotsuite_styx_light_module') }} |\n"
                    "| Präsenz | {{ states('sensor.pilotsuite_styx_presence_room') }} |\n"
                    "| Override | {{ states('sensor.pilotsuite_styx_override_mode') }} |\n"
                    "| Heizung | {{ states('sensor.pilotsuite_styx_heizung_override') }} |"
                ),
            },
        ],
    }


def generate_full_habitus_dashboard(zones: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Generate the complete Habitus Dashboard.

    Parameters
    ----------
    zones : list[dict], optional
        List of zone dicts with 'name' and 'zone_id' keys.
        If not provided, generates a generic dashboard without zone-specific cards.

    Returns
    -------
    dict
        Complete Lovelace dashboard configuration.
    """
    cards = [
        generate_override_modes_card(),
        generate_musikwolke_card(),
        generate_light_module_card(),
        generate_presence_module_card(),
        generate_zone_automation_card(),
    ]

    if zones:
        for zone in zones:
            name = zone.get("name", zone.get("zone_id", "Unbekannt"))
            zone_id = zone.get("zone_id", "")
            if zone_id:
                cards.append(generate_zone_status_card(name, zone_id))

    return {
        "title": "PilotSuite Habitus",
        "path": "pilotsuite-habitus",
        "icon": "mdi:home-automation",
        "type": "panel",
        "cards": [
            {
                "type": "vertical-stack",
                "cards": cards,
            }
        ],
    }
