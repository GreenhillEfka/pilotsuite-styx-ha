"""PilotSuite 3-Tab Dashboard Generator.

Generates dynamic Lovelace dashboard YAML dicts from zones_config.json.
Three tabs:
  1. Habitus  -- Mood gauges, zone grid, persons, temperature history
  2. Hausverwaltung -- Energy, heating, security, devices, network, weather
  3. Styx    -- Neural pipeline, brain graph, mood history, suggestions

Usage:
    from .pilotsuite_3tab_generator import generate_full_dashboard
    dashboard = generate_full_dashboard()  # loads zones_config.json automatically

Path: custom_components/ai_home_copilot/dashboard_cards/pilotsuite_3tab_generator.py
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Zone-config loader
# ---------------------------------------------------------------------------

_ZONES_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "zones_config.json"
)


def _load_zones_config() -> list[dict[str, Any]]:
    """Load zones from data/zones_config.json."""
    try:
        with open(_ZONES_CONFIG_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("zones", [])
    except Exception:
        _LOGGER.warning("Could not load zones_config.json, returning empty list")
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first(entities: list[str] | None) -> str | None:
    """Return first entity or None."""
    if entities:
        return entities[0]
    return None


def _zone_entities(zone: dict[str, Any], role: str) -> list[str]:
    """Get entity list for a role from zone dict."""
    return zone.get("entities", {}).get(role, [])


def _tpl(entity_id: str) -> str:
    """Wrap entity_id in a Jinja2 states() template."""
    return "{{ states('" + entity_id + "') }}"


# ---------------------------------------------------------------------------
# TAB 1: HABITUS
# ---------------------------------------------------------------------------

def _build_mood_gauges() -> dict[str, Any]:
    """Mood gauge horizontal-stack (comfort / joy / frugality)."""
    return {
        "type": "horizontal-stack",
        "cards": [
            {
                "type": "gauge",
                "entity": "sensor.ai_home_copilot_mood_comfort",
                "name": "Komfort",
                "min": 0,
                "max": 100,
                "severity": {"green": 70, "yellow": 40, "red": 0},
            },
            {
                "type": "gauge",
                "entity": "sensor.ai_home_copilot_mood_joy",
                "name": "Freude",
                "min": 0,
                "max": 100,
                "severity": {"green": 60, "yellow": 30, "red": 0},
            },
            {
                "type": "gauge",
                "entity": "sensor.ai_home_copilot_mood_frugality",
                "name": "Sparsamkeit",
                "min": 0,
                "max": 100,
                "severity": {"green": 60, "yellow": 30, "red": 0},
            },
        ],
    }


def _build_zone_card(zone: dict[str, Any]) -> dict[str, Any]:
    """Build a single zone vertical-stack for the grid."""
    name = zone.get("name", zone.get("zone_id", "?"))
    entities_map = zone.get("entities", {})

    # --- Markdown header with sensor templates ---
    header_parts: list[str] = [f"## {name}"]

    temp = _first(_zone_entities(zone, "temperature"))
    humid = _first(_zone_entities(zone, "humidity"))
    co2 = _first(_zone_entities(zone, "co2"))
    brightness = _first(_zone_entities(zone, "brightness"))

    env_line_parts: list[str] = []
    if temp:
        env_line_parts.append(f"{_tpl(temp)}°C")
    if humid:
        env_line_parts.append(f"{_tpl(humid)}%")
    if co2:
        env_line_parts.append(f"CO2: {_tpl(co2)} ppm")
    if brightness and not co2:
        # Show brightness only when no CO2 sensor (to keep line concise)
        env_line_parts.append(f"{_tpl(brightness)} lux")

    if env_line_parts:
        header_parts.append(" | ".join(env_line_parts))

    markdown_content = "\n".join(header_parts) + "\n"

    # --- Entity rows: pick representative entities per role ---
    entity_rows: list[dict[str, Any]] = []

    # Priority order of roles to display
    role_display: list[tuple[str, str]] = [
        ("motion", "Anwesenheit"),
        ("media", "Sonos"),
        ("lights", "Licht"),
        ("heating", "Heizung"),
        ("cover", "Rollo"),
        ("window", "Fenster"),
        ("power", "Verbrauch"),
    ]

    for role, label in role_display:
        ents = _zone_entities(zone, role)
        if ents:
            first = ents[0]
            # For motion: use the first motion sensor
            # For others: use first entity
            entity_rows.append({"entity": first, "name": label})
        if len(entity_rows) >= 5:
            break

    cards: list[dict[str, Any]] = [
        {"type": "markdown", "content": markdown_content},
    ]

    if entity_rows:
        cards.append({
            "type": "entities",
            "entities": entity_rows,
        })

    return {"type": "vertical-stack", "cards": cards}


def _build_zone_grid(zones: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build zone grid cards, split into groups of up to 3 columns.

    Returns a list of grid cards (may be 1-3 grid cards depending on zone count).
    """
    zone_cards = [_build_zone_card(z) for z in zones]

    # Split into chunks: first 6 in one grid, remaining in another
    grids: list[dict[str, Any]] = []
    chunk_size = 6  # 2 rows of 3

    for i in range(0, len(zone_cards), chunk_size):
        chunk = zone_cards[i : i + chunk_size]
        grids.append({
            "type": "grid",
            "columns": 3,
            "cards": chunk,
        })

    return grids


def _build_persons_card() -> dict[str, Any]:
    """Persons entities card."""
    return {
        "type": "entities",
        "title": "Personen",
        "entities": [
            {"entity": "person.andreas", "name": "Andreas"},
            {"entity": "person.efka", "name": "Efka"},
            {"entity": "person.mira", "name": "Mira"},
            {"entity": "person.pauli", "name": "Pauli"},
            {"entity": "person.steffi", "name": "Steffi"},
        ],
    }


def _build_temperature_history(zones: list[dict[str, Any]]) -> dict[str, Any]:
    """Temperature history-graph using first temp sensor per zone."""
    entities: list[dict[str, Any]] = []

    for zone in zones:
        temp = _first(_zone_entities(zone, "temperature"))
        if temp:
            entities.append({
                "entity": temp,
                "name": zone.get("name", zone.get("zone_id", "")),
            })

    return {
        "type": "history-graph",
        "title": "Raumtemperaturen (24h)",
        "hours_to_show": 24,
        "entities": entities,
    }


def generate_habitus_tab(zones: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate Tab 1: Habitus -- Mood, Zones, Persons, Temperatures.

    Args:
        zones: List of zone dicts from zones_config.json.

    Returns:
        Lovelace view configuration dict.
    """
    cards: list[dict[str, Any]] = []

    # 1) Mood gauges
    cards.append(_build_mood_gauges())

    # 2) Zone grid(s) -- dynamically from zones
    cards.extend(_build_zone_grid(zones))

    # 3) Persons
    cards.append(_build_persons_card())

    # 4) Temperature history
    cards.append(_build_temperature_history(zones))

    return {
        "title": "Habitus",
        "path": "habitus",
        "icon": "mdi:home-heart",
        "badges": [],
        "cards": cards,
    }


# ---------------------------------------------------------------------------
# TAB 2: HAUSVERWALTUNG
# ---------------------------------------------------------------------------

def _build_energy_section() -> dict[str, Any]:
    """Energy section: consumption, PV, gas, history."""
    return {
        "type": "vertical-stack",
        "title": "Energie",
        "cards": [
            {
                "type": "grid",
                "columns": 3,
                "cards": [
                    {
                        "type": "entity",
                        "entity": "sensor.stromverbrauch_paradiesgarten_21_electric_consumption_w",
                        "name": "Verbrauch Gesamt",
                        "icon": "mdi:flash",
                        "unit": "W",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.stromverbrauch_paradiesgarten_21_electric_production_w",
                        "name": "PV Produktion",
                        "icon": "mdi:solar-power",
                        "unit": "W",
                    },
                    {
                        "type": "entity",
                        "entity": "counter.gaszahler",
                        "name": "Gaszaehler",
                        "icon": "mdi:fire",
                    },
                ],
            },
            {
                "type": "grid",
                "columns": 2,
                "cards": [
                    {
                        "type": "entity",
                        "entity": "sensor.ostausrichtung_estimated_energy_production_today",
                        "name": "PV Ost heute",
                        "icon": "mdi:weather-sunny",
                        "unit": "kWh",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.westausrichtung_geschatzte_energieerzeugung_heute",
                        "name": "PV West heute",
                        "icon": "mdi:weather-sunny",
                        "unit": "kWh",
                    },
                ],
            },
            {
                "type": "history-graph",
                "title": "Energiefluss (24h)",
                "hours_to_show": 24,
                "entities": [
                    {
                        "entity": "sensor.stromverbrauch_paradiesgarten_21_electric_consumption_w",
                        "name": "Verbrauch",
                    },
                    {
                        "entity": "sensor.stromverbrauch_paradiesgarten_21_electric_production_w",
                        "name": "Produktion",
                    },
                ],
            },
        ],
    }


def _build_heating_section() -> dict[str, Any]:
    """Heating section: Wolf CGB-2."""
    return {
        "type": "vertical-stack",
        "title": "Heizung (Wolf CGB-2)",
        "cards": [
            {
                "type": "grid",
                "columns": 3,
                "cards": [
                    {
                        "type": "entity",
                        "entity": "sensor.heat_generator_1_boiler_water_temperature",
                        "name": "Vorlauf",
                        "icon": "mdi:thermometer",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.heat_generator_1_return_temperature",
                        "name": "Ruecklauf",
                        "icon": "mdi:thermometer-low",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.heat_generator_1_system_pressure",
                        "name": "Druck",
                        "icon": "mdi:gauge",
                        "unit": "bar",
                    },
                ],
            },
            {
                "type": "entities",
                "entities": [
                    {
                        "entity": "sensor.heat_generator_1_burner_status",
                        "name": "Brenner Status",
                    },
                    {
                        "entity": "sensor.heat_generator_1_operating_mode",
                        "name": "Betriebsmodus",
                    },
                    {
                        "entity": "sensor.heat_generator_1_outside_temperature",
                        "name": "Aussentemperatur",
                    },
                    {
                        "entity": "input_select.heizmodus",
                        "name": "Heizmodus",
                    },
                ],
            },
        ],
    }


def _build_security_section() -> dict[str, Any]:
    """Security section: windows, smoke detectors, cameras."""
    return {
        "type": "vertical-stack",
        "title": "Sicherheit",
        "cards": [
            {
                "type": "entities",
                "title": "Tueren & Fenster",
                "entities": [
                    {
                        "entity": "binary_sensor.sensor_fenster_schlafzimmer_window_door_is_open",
                        "name": "Fenster Schlafzimmer",
                    },
                    {
                        "entity": "binary_sensor.sensor_fenster_rechts_window_door_is_open",
                        "name": "Fenster Mira rechts",
                    },
                    {
                        "entity": "binary_sensor.sensor_fenster_links_window_door_is_open",
                        "name": "Fenster Mira links",
                    },
                    {
                        "entity": "binary_sensor.sensor_dachfenster_window_door_is_open",
                        "name": "Dachfenster Paul",
                    },
                    {
                        "entity": "binary_sensor.spasskiste_offnung",
                        "name": "Spasskiste",
                    },
                ],
            },
            {
                "type": "entities",
                "title": "Rauchmelder",
                "entities": [
                    {
                        "entity": "binary_sensor.feuermelder_zimmer_mira_smoke_detected",
                        "name": "Zimmer Mira",
                    },
                    {
                        "entity": "binary_sensor.feuermelder_zimmer_paul_smoke_detected",
                        "name": "Zimmer Paul",
                    },
                    {
                        "entity": "binary_sensor.feuermelder_flur",
                        "name": "Flur",
                    },
                ],
            },
            {
                "type": "entities",
                "title": "Kameras",
                "entities": [
                    {
                        "entity": "camera.ai360",
                        "name": "AI360 (Kontrollraum)",
                    },
                    {
                        "entity": "camera.camera_hub_g3_2ed9",
                        "name": "G3 (Arbeitszimmer)",
                    },
                    {
                        "entity": "camera.doorbell_repeater_5851",
                        "name": "Doorbell (Terrasse)",
                    },
                ],
            },
        ],
    }


def _build_devices_section() -> dict[str, Any]:
    """Household devices section."""
    return {
        "type": "vertical-stack",
        "title": "Haushaltsgeraete",
        "cards": [
            {
                "type": "grid",
                "columns": 2,
                "cards": [
                    {
                        "type": "entities",
                        "title": "Kueche",
                        "entities": [
                            {"entity": "switch.kaffeemaschine", "name": "Kaffeemaschine"},
                            {"entity": "counter.kaffeemaschine_bezuge", "name": "Bezuege total"},
                            {"entity": "switch.spulmaschine", "name": "Spuelmaschine"},
                            {"entity": "switch.coca_cola_kuhlschrank", "name": "Kuehlschrank"},
                        ],
                    },
                    {
                        "type": "entities",
                        "title": "Reinigung & Waesche",
                        "entities": [
                            {"entity": "vacuum.saugi", "name": "Saugroboter"},
                            {"entity": "vacuum.wischi", "name": "Wischroboter"},
                            {"entity": "sensor.waschmaschine", "name": "Waschmaschine"},
                            {"entity": "sensor.waschmaschine_pre_state", "name": "WM Status"},
                        ],
                    },
                ],
            },
        ],
    }


def _build_network_section() -> dict[str, Any]:
    """Network and system monitoring section."""
    return {
        "type": "vertical-stack",
        "title": "Netzwerk & System",
        "cards": [
            {
                "type": "grid",
                "columns": 2,
                "cards": [
                    {
                        "type": "entities",
                        "title": "System",
                        "entities": [
                            {"entity": "sensor.system_monitor_prozessornutzung", "name": "CPU"},
                            {"entity": "sensor.system_monitor_arbeitsspeicherauslastung", "name": "RAM"},
                            {"entity": "sensor.system_monitor_massenspeicher_auslastung", "name": "Speicher"},
                            {"entity": "sensor.system_monitor_prozessortemperatur", "name": "CPU Temp"},
                        ],
                    },
                    {
                        "type": "entities",
                        "title": "NAS (DS1515)",
                        "entities": [
                            {"entity": "sensor.ds1515_cpu_auslastung_gesamt", "name": "NAS CPU"},
                            {"entity": "sensor.ds1515_volume_1_volume_nutzung", "name": "Vol 1"},
                            {"entity": "sensor.ds1515_volume_4_volume_nutzung", "name": "Vol 4"},
                            {"entity": "sensor.ds1515_laufwerk_3_status", "name": "Disk 3"},
                        ],
                    },
                ],
            },
            {
                "type": "entities",
                "title": "UniFi Dream Machine",
                "entities": [
                    {"entity": "sensor.dream_machine_special_edition_cpu_utilization", "name": "UDM CPU"},
                    {"entity": "sensor.dream_machine_special_edition_memory_utilization_2", "name": "UDM RAM"},
                    {"entity": "sensor.dream_machine_special_edition_google_wan_latency", "name": "WAN Latenz"},
                    {"entity": "sensor.dream_machine_special_edition_clients", "name": "Clients"},
                ],
            },
        ],
    }


def _build_weather_section() -> dict[str, Any]:
    """Weather forecast card."""
    return {
        "type": "weather-forecast",
        "entity": "weather.pirateweather",
        "show_forecast": True,
    }


def generate_hausverwaltung_tab() -> dict[str, Any]:
    """Generate Tab 2: Hausverwaltung.

    Covers energy, heating, security, devices, network, and weather.
    Entity-IDs are hardcoded (infrastructure entities not in zone config).

    Returns:
        Lovelace view configuration dict.
    """
    return {
        "title": "Hausverwaltung",
        "path": "hausverwaltung",
        "icon": "mdi:home-city",
        "badges": [],
        "cards": [
            _build_energy_section(),
            _build_heating_section(),
            _build_security_section(),
            _build_devices_section(),
            _build_network_section(),
            _build_weather_section(),
        ],
    }


# ---------------------------------------------------------------------------
# TAB 3: STYX
# ---------------------------------------------------------------------------

def _build_neural_pipeline_section() -> dict[str, Any]:
    """Neural pipeline status cards."""
    return {
        "type": "vertical-stack",
        "title": "Neural Pipeline",
        "cards": [
            {
                "type": "grid",
                "columns": 4,
                "cards": [
                    {
                        "type": "entity",
                        "entity": "sensor.ai_home_copilot_neuron_activity",
                        "name": "Neuronen",
                        "icon": "mdi:brain",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.ai_home_copilot_mood",
                        "name": "Stimmung",
                        "icon": "mdi:emoticon",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.ai_home_copilot_suggestion_queue",
                        "name": "Vorschlaege",
                        "icon": "mdi:lightbulb-on",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.ai_home_copilot_brain_graph_summary",
                        "name": "Brain Graph",
                        "icon": "mdi:graph",
                    },
                ],
            },
        ],
    }


def _build_brain_graph_iframe() -> dict[str, Any]:
    """Brain graph visualization iframe."""
    return {
        "type": "iframe",
        "url": "/api/ai_home_copilot/brain_graph/vis",
        "aspect_ratio": "16:9",
        "title": "Brain Graph",
    }


def _build_mood_history_section() -> dict[str, Any]:
    """Mood history graphs (comfort + joy)."""
    return {
        "type": "vertical-stack",
        "title": "Stimmung pro Zone",
        "cards": [
            {
                "type": "history-graph",
                "title": "Comfort (24h)",
                "hours_to_show": 24,
                "entities": [
                    {
                        "entity": "sensor.ai_home_copilot_mood_comfort",
                        "name": "Gesamt Comfort",
                    },
                ],
            },
            {
                "type": "history-graph",
                "title": "Joy (24h)",
                "hours_to_show": 24,
                "entities": [
                    {
                        "entity": "sensor.ai_home_copilot_mood_joy",
                        "name": "Gesamt Joy",
                    },
                ],
            },
        ],
    }


def _build_suggestions_section() -> dict[str, Any]:
    """Active suggestions and action buttons."""
    return {
        "type": "vertical-stack",
        "title": "Aktive Vorschlaege",
        "cards": [
            {
                "type": "entities",
                "entities": [
                    {
                        "entity": "sensor.ai_home_copilot_suggestion_queue",
                        "name": "Warteschlange",
                    },
                    {
                        "entity": "button.ai_home_copilot_generate_overview",
                        "name": "Uebersicht generieren",
                    },
                    {
                        "entity": "button.ai_home_copilot_demo_suggestion",
                        "name": "Demo-Vorschlag",
                    },
                ],
            },
        ],
    }


def _build_habitus_patterns_section() -> dict[str, Any]:
    """Habitus pattern summary."""
    return {
        "type": "vertical-stack",
        "title": "Habitus-Muster",
        "cards": [
            {
                "type": "entities",
                "entities": [
                    {
                        "entity": "sensor.ai_home_copilot_habit_summary",
                        "name": "Muster-Zusammenfassung",
                    },
                ],
            },
        ],
    }


def _build_actions_section() -> dict[str, Any]:
    """PilotSuite action buttons."""
    return {
        "type": "vertical-stack",
        "title": "PilotSuite Aktionen",
        "cards": [
            {
                "type": "grid",
                "columns": 2,
                "cards": [
                    {
                        "type": "button",
                        "entity": "button.ai_home_copilot_generate_overview",
                        "name": "Uebersicht",
                        "icon": "mdi:file-document",
                        "show_state": False,
                    },
                    {
                        "type": "button",
                        "entity": "button.ai_home_copilot_config_snapshot",
                        "name": "Snapshot",
                        "icon": "mdi:camera",
                        "show_state": False,
                    },
                    {
                        "type": "button",
                        "entity": "button.ai_home_copilot_log_analysis",
                        "name": "Log-Analyse",
                        "icon": "mdi:text-search",
                        "show_state": False,
                    },
                    {
                        "type": "button",
                        "entity": "button.ai_home_copilot_core_capabilities",
                        "name": "Capabilities",
                        "icon": "mdi:rocket-launch",
                        "show_state": False,
                    },
                ],
            },
        ],
    }


def _build_system_status_section() -> dict[str, Any]:
    """System status entities."""
    return {
        "type": "vertical-stack",
        "title": "System Status",
        "cards": [
            {
                "type": "entities",
                "entities": [
                    {
                        "entity": "sensor.ai_home_copilot_status",
                        "name": "PilotSuite Status",
                    },
                    {
                        "entity": "update.ai_home_copilot_update",
                        "name": "Update verfuegbar",
                    },
                    {
                        "entity": "sensor.ai_home_copilot_forwarder_status",
                        "name": "Event Forwarder",
                    },
                ],
            },
        ],
    }


def generate_styx_tab() -> dict[str, Any]:
    """Generate Tab 3: Styx -- Neural Intelligence.

    Includes pipeline status, brain graph, mood history,
    suggestions, patterns, action buttons, and system status.

    Returns:
        Lovelace view configuration dict.
    """
    return {
        "title": "Styx",
        "path": "styx",
        "icon": "mdi:brain",
        "badges": [],
        "cards": [
            _build_neural_pipeline_section(),
            _build_brain_graph_iframe(),
            _build_mood_history_section(),
            _build_suggestions_section(),
            _build_habitus_patterns_section(),
            _build_actions_section(),
            _build_system_status_section(),
        ],
    }


# ---------------------------------------------------------------------------
# FULL DASHBOARD
# ---------------------------------------------------------------------------

def generate_full_dashboard(
    zones: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate the complete 3-tab PilotSuite dashboard.

    Args:
        zones: Optional list of zone dicts. If None, zones_config.json
               is loaded automatically from data/.

    Returns:
        Complete Lovelace dashboard configuration dict with three views.
        Compatible with ``yaml.dump()`` for writing to a YAML file.
    """
    if zones is None:
        zones = _load_zones_config()

    return {
        "title": "PilotSuite",
        "views": [
            generate_habitus_tab(zones),
            generate_hausverwaltung_tab(),
            generate_styx_tab(),
        ],
    }


__all__ = [
    "generate_habitus_tab",
    "generate_hausverwaltung_tab",
    "generate_styx_tab",
    "generate_full_dashboard",
]
