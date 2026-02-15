"""
Energy Distribution Card
========================

Generates a Lovelace UI card for energy distribution visualization.
Shows:
- Current power consumption (W)
- Daily energy consumption (kWh)
- Energy sources breakdown (grid, solar, battery)
- Cost information
- Historical trends

Design: Simple gauge + bar chart visualization
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class EnergyData:
    """Energy distribution data."""
    total_consumption_w: float
    total_consumption_kwh_today: float
    grid_consumption_w: float | None = None
    solar_production_w: float | None = None
    battery_discharge_w: float | None = None
    battery_charge_w: float | None = None
    current_cost_eur: float | None = None
    today_cost_eur: float | None = None
    baseline_kwh: float | None = None
    savings_percent: float | None = None


def create_energy_distribution_card(
    hass: HomeAssistant,
    energy_data: EnergyData,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create an Energy Distribution Card YAML configuration.
    
    Args:
        hass: Home Assistant instance
        energy_data: Energy distribution data
        config: Optional configuration overrides
        
    Returns:
        Lovelace card configuration dict
    """
    card_config = {
        "type": "vertical-stack",
        "cards": [
            _create_energy_header_card(energy_data),
            _create_energy_gauge_card(energy_data),
            _create_energy_sources_card(energy_data),
            _create_energy_cost_card(energy_data),
        ],
    }
    
    # Apply custom configuration if provided
    if config:
        card_config.update(config)
        
    return card_config


def _create_energy_header_card(energy_data: EnergyData) -> dict[str, str]:
    """Create energy header card."""
    return {
        "type": "horizontal-stack",
        "cards": [
            {
                "type": "custom:hui-card",
                "title": "⚡ Energie",
                "icon": "mdi:flash",
            },
        ],
    }


def _create_energy_gauge_card(energy_data: EnergyData) -> dict[str, Any]:
    """Create energy consumption gauge card."""
    current_power = energy_data.total_consumption_w
    max_power = 5000  # Default max (5 kW)
    
    # Calculate percentage for gauge
    percentage = min(100, (current_power / max_power) * 100) if max_power > 0 else 0
    
    return {
        "type": "custom:hui-card",
        "title": "Stromverbrauch",
        "icon": "mdi:power-plug",
        "cards": [
            {
                "type": "gauge",
                "entity": "sensor.ai_home_copilot_energy_power",
                "name": "aktuell",
                "min": 0,
                "max": max_power,
                "severity": {
                    "green": 1000,
                    "yellow": 2500,
                    "red": 4000,
                },
                "needle": True,
            },
            {
                "type": "vertical-stack",
                "cards": [
                    {
                        "type": "sensor",
                        "entity": "sensor.ai_home_copilot_energy_power",
                        "name": "aktuell",
                        "unit": "W",
                    },
                    {
                        "type": "sensor",
                        "entity": "sensor.ai_home_copilot_energy_daily",
                        "name": "heute",
                        "unit": "kWh",
                    },
                ],
            },
        ],
    }


def _create_energy_sources_card(energy_data: EnergyData) -> dict[str, Any]:
    """Create energy sources breakdown card."""
    cards = []
    
    # Grid consumption
    if energy_data.grid_consumption_w is not None:
        cards.append({
            "type": "conditional",
            "conditions": [
                {
                    "entity": "sensor.ai_home_copilot_energy_grid",
                    "state_not": "unavailable",
                },
            ],
            "card": {
                "type": "sensor",
                "entity": "sensor.ai_home_copilot_energy_grid",
                "name": "Netz",
                "unit": "W",
                "icon": "mdi:transmission-tower",
            },
        })
        
    # Solar production
    if energy_data.solar_production_w is not None:
        cards.append({
            "type": "conditional",
            "conditions": [
                {
                    "entity": "sensor.ai_home_copilot_energy_solar",
                    "state_not": "unavailable",
                },
            ],
            "card": {
                "type": "sensor",
                "entity": "sensor.ai_home_copilot_energy_solar",
                "name": "Solar",
                "unit": "W",
                "icon": "mdi:solar-power",
            },
        })
        
    # Battery
    if (
        energy_data.battery_discharge_w is not None
        or energy_data.battery_charge_w is not None
    ):
        cards.append({
            "type": "conditional",
            "conditions": [
                {
                    "entity": "sensor.ai_home_copilot_energy_battery",
                    "state_not": "unavailable",
                },
            ],
            "card": {
                "type": "sensor",
                "entity": "sensor.ai_home_copilot_energy_battery",
                "name": "Batterie",
                "unit": "W",
                "icon": "mdi:battery-charging",
            },
        })
        
    return {
        "type": "custom:hui-card",
        "title": "Energiequellen",
        "icon": "mdi:source-branch",
        "cards": cards if cards else [
            {
                "type": "markdown",
                "content": "Daten zur Energieverteilung nicht verfügbar",
            },
        ],
    }


def _create_energy_cost_card(energy_data: EnergyData) -> dict[str, Any]:
    """Create energy cost card."""
    cards = []
    
    # Current cost
    if energy_data.current_cost_eur is not None:
        cards.append({
            "type": "sensor",
            "entity": "sensor.ai_home_copilot_energy_cost_current",
            "name": "aktuell",
            "unit": "€/h",
            "icon": "mdi:currency-eur",
        })
        
    # Today's cost
    if energy_data.today_cost_eur is not None:
        cards.append({
            "type": "sensor",
            "entity": "sensor.ai_home_copilot_energy_cost_daily",
            "name": "heute",
            "unit": "€",
            "icon": "mdi:currency-eur",
        })
        
    # Savings
    if energy_data.savings_percent is not None:
        cards.append({
            "type": "conditional",
            "conditions": [
                {
                    "entity": "sensor.ai_home_copilot_energy_savings",
                    "state_not": "unavailable",
                },
            ],
            "card": {
                "type": "gauge",
                "entity": "sensor.ai_home_copilot_energy_savings",
                "name": "Einsparung",
                "min": 0,
                "max": 100,
                "severity": {
                    "green": 20,
                    "yellow": 50,
                    "red": 80,
                },
            },
        })
        
    return {
        "type": "custom:hui-card",
        "title": "Kosten & Einsparungen",
        "icon": "mdi:cash-multiple",
        "cards": cards if cards else [
            {
                "type": "markdown",
                "content": "Kostendaten nicht verfügbar",
            },
        ],
    }


def get_energy_distribution_card_yaml(energy_data: EnergyData) -> str:
    """
    Get energy distribution card as YAML string.
    
    Args:
        energy_data: Energy distribution data
        
    Returns:
        YAML string for Lovelace configuration
    """
    card_dict = create_energy_distribution_card(None, energy_data)
    return _dict_to_yaml(card_dict)


def _dict_to_yaml(data: dict[str, Any], indent: int = 0) -> str:
    """Convert dict to YAML string (simple implementation)."""
    indent_str = "  " * indent
    lines = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{indent_str}- {key}:")
                lines.append(_dict_to_yaml(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{indent_str}- {key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(_dict_to_yaml(item, indent + 1))
                    else:
                        lines.append(f"{indent_str}  - {item}")
            else:
                lines.append(f"{indent_str}- {key}: {value}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                lines.append(_dict_to_yaml(item, indent))
            else:
                lines.append(f"{indent_str}- {item}")
    else:
        lines.append(f"{indent_str}{data}")
        
    return "\n".join(lines)
