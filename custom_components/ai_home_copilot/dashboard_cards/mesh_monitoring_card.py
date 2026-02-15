"""
Mesh Monitoring Dashboard Cards
================================

Lovelace UI card generators for:
- Network Health Card (Z-Wave & Zigbee mesh status)
- Battery Overview Card (battery levels)

These cards integrate with the habitus_dashboard.py infrastructure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class MeshNetworkData:
    """Mesh network monitoring data."""
    zwave_total: int = 0
    zwave_online: int = 0
    zwave_health: str = "not_found"
    zwave_latency_ms: float | None = None
    zwave_battery_devices: int = 0
    zwave_low_battery: int = 0
    
    zigbee_total: int = 0
    zigbee_online: int = 0
    zigbee_health: str = "not_found"
    zigbee_link_quality: float | None = None
    zigbee_battery_devices: int = 0
    zigbee_low_battery: int = 0


def create_mesh_network_health_card(
    hass: HomeAssistant,
    mesh_data: MeshNetworkData,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a Mesh Network Health Card YAML configuration.
    
    Shows:
    - Z-Wave mesh status (healthy/degraded/critical/not_found)
    - Zigbee mesh status
    - Device counts
    - Latency / Link Quality
    
    Args:
        hass: Home Assistant instance
        mesh_data: Mesh network data
        config: Optional configuration overrides
        
    Returns:
        Lovelace card configuration dict
    """
    # Determine status colors
    zwave_color = _get_health_color(mesh_data.zwave_health)
    zigbee_color = _get_health_color(mesh_data.zigbee_health)
    
    card_config = {
        "type": "vertical-stack",
        "cards": [
            {
                "type": "horizontal-stack",
                "cards": [
                    {
                        "type": "entity",
                        "entity": "sensor.zwave_network_health",
                        "name": "Z-Wave",
                        "icon": "mdi:mesh",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.zigbee_network_health",
                        "name": "Zigbee",
                        "icon": "mdi:zigbee",
                    },
                ],
            },
            {
                "type": "horizontal-stack",
                "cards": [
                    {
                        "type": "entity",
                        "entity": "sensor.zwave_devices_online",
                        "name": "Z-Wave Devices",
                        "icon": "mdi:access_point",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.zigbee_devices_online",
                        "name": "Zigbee Devices",
                        "icon": "mdi:access_point_network",
                    },
                ],
            },
            {
                "type": "horizontal-stack",
                "cards": [
                    {
                        "type": "entity",
                        "entity": "binary_sensor.zwave_mesh_status",
                        "name": "Z-Wave Mesh",
                        "icon": "mdi:mesh_network",
                    },
                    {
                        "type": "entity",
                        "entity": "binary_sensor.zigbee_mesh_status",
                        "name": "Zigbee Mesh",
                        "icon": "mdi:mesh_network",
                    },
                ],
            },
        ],
    }
    
    if config:
        card_config.update(config)
    
    return card_config


def create_battery_overview_card(
    hass: HomeAssistant,
    mesh_data: MeshNetworkData,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a Battery Overview Card YAML configuration.
    
    Shows:
    - Z-Wave battery status
    - Zigbee battery status
    - Low battery alerts
    
    Args:
        hass: Home Assistant instance
        mesh_data: Mesh network data
        config: Optional configuration overrides
        
    Returns:
        Lovelace card configuration dict
    """
    card_config = {
        "type": "vertical-stack",
        "cards": [
            {
                "type": "horizontal-stack",
                "cards": [
                    {
                        "type": "entity",
                        "entity": "sensor.zwave_battery_overview",
                        "name": "Z-Wave",
                        "icon": "mdi:battery",
                    },
                    {
                        "type": "entity",
                        "entity": "sensor.zigbee_battery_overview",
                        "name": "Zigbee",
                        "icon": "mdi:battery",
                    },
                ],
            },
            {
                "type": "conditional",
                "conditions": [
                    {
                        "entity": "sensor.zwave_battery_overview",
                        "state_not": "ok",
                    }
                ],
                "card": {
                    "type": "entities",
                    "title": "⚠️ Low Battery Alerts",
                    "show_header_toggle": False,
                    "entities": [
                        "sensor.zwave_battery_overview",
                        "sensor.zigbee_battery_overview",
                    ],
                },
            },
        ],
    }
    
    if config:
        card_config.update(config)
    
    return card_config


def _get_health_color(health: str) -> str:
    """Get color based on health status."""
    colors = {
        "healthy": "green",
        "ok": "green",
        "degraded": "yellow",
        "slow": "orange",
        "weak_signal": "orange",
        "critical": "red",
        "not_found": "grey",
    }
    return colors.get(health, "grey")


def get_mesh_data_from_hass(hass: HomeAssistant) -> MeshNetworkData:
    """Extract mesh network data from Home Assistant states."""
    from .mesh_monitoring import _analyze_mesh_devices
    
    zwave_data = _analyze_mesh_devices(hass, "zwave")
    zigbee_data = _analyze_mesh_devices(hass, "zigbee")
    
    return MeshNetworkData(
        zwave_total=zwave_data.get("total", 0),
        zwave_online=zwave_data.get("online", 0),
        zwave_health=_calculate_health(zwave_data),
        zwave_latency_ms=zwave_data.get("avg_latency_ms"),
        zwave_battery_devices=len(zwave_data.get("battery_devices", [])),
        zwave_low_battery=len(zwave_data.get("low_battery", [])),
        
        zigbee_total=zigbee_data.get("total", 0),
        zigbee_online=zigbee_data.get("online", 0),
        zigbee_health=_calculate_health(zigbee_data),
        zigbee_link_quality=zigbee_data.get("avg_link_quality"),
        zigbee_battery_devices=len(zigbee_data.get("battery_devices", [])),
        zigbee_low_battery=len(zigbee_data.get("low_battery", [])),
    )


def _calculate_health(data: dict[str, Any]) -> str:
    """Calculate health status from mesh data."""
    total = data.get("total", 0)
    if total == 0:
        return "not_found"
    
    unavailable = data.get("unavailable", 0)
    low_battery = data.get("low_battery", [])
    avg_latency = data.get("avg_latency_ms")
    avg_link_quality = data.get("avg_link_quality")
    
    if unavailable > total * 0.5:
        return "critical"
    elif low_battery:
        return "degraded"
    elif avg_latency and avg_latency > 200:
        return "slow"
    elif avg_link_quality and avg_link_quality < 50:
        return "weak_signal"
    elif data.get("online", 0) < total:
        return "degraded"
    
    return "healthy"
