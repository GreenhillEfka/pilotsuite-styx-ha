"""
Zone Context Card
=================

Generates a Lovelace UI card for zone context visualization.
Shows:
- Current zone for each user
- Zone activity score
- Detected entities
- Zone history

Design: Simple zone status display with user indicators
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant

from .zone_detector import ZoneDetector, DetectedZone

_LOGGER = logging.getLogger(__name__)


@dataclass
class ZoneContextData:
    """Zone context data."""
    current_zones: dict[str, DetectedZone]  # user_id -> zone
    zone_summary: dict[str, list[str]]  # zone_id -> list of user_ids
    active_zones: list[str]  # zones with at least one user
    together_count: int  # number of users in same zone


def create_zone_context_card(
    hass: HomeAssistant,
    zone_data: ZoneContextData,
    zone_detector: ZoneDetector | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a Zone Context Card YAML configuration.
    
    Args:
        hass: Home Assistant instance
        zone_data: Zone context data
        zone_detector: Optional ZoneDetector instance
        config: Optional configuration overrides
        
    Returns:
        Lovelace card configuration dict
    """
    card_config = {
        "type": "vertical-stack",
        "cards": [
            _create_zone_header_card(zone_data),
            _create_zone_users_card(zone_data),
            _create_zone_activity_card(zone_data),
        ],
    }
    
    # Apply custom configuration if provided
    if config:
        card_config.update(config)
        
    return card_config


def _create_zone_header_card(zone_data: ZoneContextData) -> dict[str, str]:
    """Create zone header card."""
    return {
        "type": "horizontal-stack",
        "cards": [
            {
                "type": "custom:hui-card",
                "title": "🏠 Zonen",
                "icon": "mdi:home-map",
            },
        ],
    }


def _create_zone_users_card(zone_data: ZoneContextData) -> dict[str, Any]:
    """Create zone users card."""
    users_cards = []
    
    for user_id, zone in zone_data.current_zones.items():
        zone_name = zone.zone_name
        users_cards.append({
            "type": "custom:hui-entity-card",
            "entity": user_id,
            "name": f"🏠 {zone_name}",
            "icon": "mdi:account",
        })
        
    if not users_cards:
        users_cards.append({
            "type": "markdown",
            "content": "Keine Benutzer erkannt",
        })
        
    return {
        "type": "custom:hui-card",
        "title": "Benutzer in Zonen",
        "icon": "mdi:account-multiple",
        "cards": users_cards,
    }


def _create_zone_activity_card(zone_data: ZoneContextData) -> dict[str, Any]:
    """Create zone activity card."""
    activity_items = []
    
    for zone_id, user_list in zone_data.zone_summary.items():
        if user_list:
            activity_items.append({
                "type": "custom:hui-stat-card",
                "name": zone_id,
                "value": len(user_list),
                "unit": "Benutzer",
                "icon": "mdi:home",
            })
            
    if not activity_items:
        activity_items.append({
            "type": "markdown",
            "content": "Keine Zonenaktivität erkannt",
        })
        
    return {
        "type": "custom:hui-card",
        "title": "Zonenaktivität",
        "icon": "mdi:chart-bar",
        "cards": activity_items,
    }


def get_zone_context_card_yaml(zone_data: ZoneContextData) -> str:
    """
    Get zone context card as YAML string.
    
    Args:
        zone_data: Zone context data
        
    Returns:
        YAML string for Lovelace configuration
    """
    card_dict = create_zone_context_card(None, zone_data)
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
