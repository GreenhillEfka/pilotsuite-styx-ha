"""Dashboard Card Generator — Auto-generate Lovelace YAML cards (v5.6.0).

Generates Home Assistant Lovelace dashboard card configurations for:
- Energy overview (gauges for consumption, production, current power)
- Energy schedule (upcoming device schedule from Smart Schedule Planner)
- Sankey flow diagram (iframe embedding the SVG endpoint)
- Zone energy breakdown (per-zone power cards)
- Anomaly alerts (conditional card for active anomalies)
"""

from __future__ import annotations

import logging
from typing import Any

import yaml

_LOGGER = logging.getLogger(__name__)


def _yaml_dump(data: Any) -> str:
    """Dump data to YAML string with clean formatting."""
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


def generate_energy_overview_card(host: str, port: int) -> dict[str, Any]:
    """Generate energy overview gauge card."""
    return {
        "type": "vertical-stack",
        "title": "Energie-Uebersicht",
        "cards": [
            {
                "type": "horizontal-stack",
                "cards": [
                    {
                        "type": "gauge",
                        "entity": "sensor.pilotsuite_energy_consumption",
                        "name": "Verbrauch heute",
                        "unit": "kWh",
                        "min": 0,
                        "max": 50,
                        "severity": {
                            "green": 0,
                            "yellow": 20,
                            "red": 35,
                        },
                    },
                    {
                        "type": "gauge",
                        "entity": "sensor.pilotsuite_energy_production",
                        "name": "Erzeugung heute",
                        "unit": "kWh",
                        "min": 0,
                        "max": 30,
                        "severity": {
                            "red": 0,
                            "yellow": 5,
                            "green": 15,
                        },
                    },
                ],
            },
            {
                "type": "gauge",
                "entity": "sensor.pilotsuite_current_power",
                "name": "Aktuelle Leistung",
                "unit": "W",
                "min": 0,
                "max": 11000,
                "severity": {
                    "green": 0,
                    "yellow": 5000,
                    "red": 8000,
                },
            },
        ],
    }


def generate_schedule_card(host: str, port: int) -> dict[str, Any]:
    """Generate energy schedule card showing upcoming device runs."""
    return {
        "type": "vertical-stack",
        "title": "Geraete-Zeitplan",
        "cards": [
            {
                "type": "entity",
                "entity": "sensor.pilotsuite_energy_schedule",
                "name": "Naechstes Geraet",
                "icon": "mdi:calendar-clock",
            },
            {
                "type": "markdown",
                "content": (
                    "### Tagesplan\n"
                    "{% set sched = state_attr('sensor.pilotsuite_energy_schedule', 'schedule') %}\n"
                    "{% if sched %}\n"
                    "| Geraet | Zeit | Kosten | PV |\n"
                    "|--------|------|--------|----|{% for s in sched %}\n"
                    "| {{ s.device }} | {{ s.hours }} | {{ s.cost_eur }} EUR | {{ s.pv_pct }}% |{% endfor %}\n"
                    "\n**Gesamtkosten:** {{ state_attr('sensor.pilotsuite_energy_schedule', 'total_estimated_cost_eur') }} EUR\n"
                    "**PV-Abdeckung:** {{ state_attr('sensor.pilotsuite_energy_schedule', 'total_pv_coverage_percent') }}%\n"
                    "{% else %}\n"
                    "Kein Zeitplan verfuegbar.\n"
                    "{% endif %}"
                ),
            },
        ],
    }


def generate_sankey_card(host: str, port: int) -> dict[str, Any]:
    """Generate Sankey energy flow diagram card (iframe)."""
    return {
        "type": "iframe",
        "url": f"http://{host}:{port}/api/v1/energy/sankey.svg?theme=dark&width=700&height=400",
        "title": "Energiefluss",
        "aspect_ratio": "16:9",
    }


def generate_zone_cards(
    host: str, port: int, zones: list[dict[str, Any]]
) -> dict[str, Any]:
    """Generate per-zone energy breakdown cards."""
    if not zones:
        return {
            "type": "markdown",
            "title": "Zonen-Energie",
            "content": "Keine Energiezonen registriert.",
        }

    zone_cards = []
    for zone in zones:
        zone_cards.append(
            {
                "type": "entities",
                "title": zone.get("zone_name", zone.get("zone_id", "Zone")),
                "entities": [
                    {
                        "type": "attribute",
                        "entity": "sensor.pilotsuite_energy_sankey_flow",
                        "attribute": "total_consumption_kwh",
                        "name": "Verbrauch",
                        "suffix": "kWh",
                    },
                ],
                "footer": {
                    "type": "graph",
                    "entity": "sensor.pilotsuite_energy_sankey_flow",
                    "hours_to_show": 24,
                },
            }
        )

    return {
        "type": "vertical-stack",
        "title": "Zonen-Energie",
        "cards": zone_cards,
    }


def generate_anomaly_card() -> dict[str, Any]:
    """Generate conditional anomaly alert card."""
    return {
        "type": "conditional",
        "conditions": [
            {
                "entity": "sensor.pilotsuite_energy_consumption",
                "state_not": "unavailable",
            },
        ],
        "card": {
            "type": "markdown",
            "title": "Energie-Warnungen",
            "content": (
                "{% set anomalies = state_attr('sensor.pilotsuite_energy_consumption', 'anomalies_detected') %}\n"
                "{% if anomalies and anomalies > 0 %}\n"
                "⚠ **{{ anomalies }} Anomalie(n) erkannt**\n"
                "\nPruefen Sie den Energieverbrauch auf ungewoehnliche Muster.\n"
                "{% else %}\n"
                "✓ Keine Anomalien erkannt\n"
                "{% endif %}"
            ),
        },
    }


def generate_full_dashboard(
    host: str,
    port: int,
    zones: list[dict[str, Any]] | None = None,
    include_sankey: bool = True,
    include_schedule: bool = True,
    include_anomalies: bool = True,
) -> dict[str, Any]:
    """Generate complete energy dashboard view configuration."""
    cards: list[dict[str, Any]] = []

    # Energy overview always included
    cards.append(generate_energy_overview_card(host, port))

    if include_schedule:
        cards.append(generate_schedule_card(host, port))

    if include_sankey:
        cards.append(generate_sankey_card(host, port))

    if zones:
        cards.append(generate_zone_cards(host, port, zones))

    if include_anomalies:
        cards.append(generate_anomaly_card())

    return {
        "title": "PilotSuite Energie",
        "path": "pilotsuite-energy",
        "icon": "mdi:lightning-bolt",
        "badges": [],
        "cards": cards,
    }


def dashboard_to_yaml(
    host: str,
    port: int,
    zones: list[dict[str, Any]] | None = None,
) -> str:
    """Generate full dashboard as YAML string for Lovelace import."""
    dashboard = generate_full_dashboard(host, port, zones=zones)
    return _yaml_dump({"views": [dashboard]})
