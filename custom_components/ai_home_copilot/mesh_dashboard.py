"""
Mesh Network Dashboard Visualization.

Provides:
- Mesh Network Overview Sensor (JSON with all network data)
- Z-Wave Mesh Topology Sensor (visualization data)
- Zigbee Mesh Topology Sensor (visualization data)
- Dashboard Card YAML generation
- ESPHome/Node-RED integration support
"""

from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .mesh_monitoring import _analyze_mesh_devices

_LOGGER = logging.getLogger(__name__)


# === Mesh Network Overview Sensor ===

class MeshNetworkOverviewSensor(SensorEntity):
    """Sensor for complete mesh network overview (JSON)."""
    
    _attr_has_entity_name = False
    _attr_name = "Mesh Network Overview"
    _attr_unique_id = "mesh_network_overview"
    _attr_icon = "mdi:mesh_network"
    _attr_entity_category = "diagnostic"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def native_value(self) -> str:
        """Return JSON string with overview data."""
        data = self._get_overview_data()
        return json.dumps(data)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._get_overview_data()
    
    def _get_overview_data(self) -> dict[str, Any]:
        """Gather all mesh network data."""
        zwave = _analyze_mesh_devices(self._hass, "zwave")
        zigbee = _analyze_mesh_devices(self._hass, "zigbee")
        
        # Calculate combined health score
        health_score = self._calculate_health_score(zwave, zigbee)
        
        # All battery devices
        all_battery = zwave["battery_devices"] + zigbee["battery_devices"]
        low_battery = zwave["low_battery"] + zigbee["low_battery"]
        
        return {
            "health_score": health_score,
            "zwave": {
                "total_devices": zwave["total"],
                "online": zwave["online"],
                "offline": zwave["offline"],
                "unavailable": zwave["unavailable"],
                "battery_devices": len(zwave["battery_devices"]),
                "low_battery_count": len(zwave["low_battery"]),
                "avg_latency_ms": zwave["avg_latency_ms"],
            },
            "zigbee": {
                "total_devices": zigbee["total"],
                "online": zigbee["online"],
                "offline": zigbee["offline"],
                "unavailable": zigbee["unavailable"],
                "battery_devices": len(zigbee["battery_devices"]),
                "low_battery_count": len(zigbee["low_battery"]),
                "avg_link_quality": zigbee["avg_link_quality"],
            },
            "battery": {
                "total": len(all_battery),
                "low": len(low_battery),
                "devices": all_battery,
                "low_battery_devices": low_battery,
            },
            "total_devices": zwave["total"] + zigbee["total"],
            "total_online": zwave["online"] + zigbee["online"],
        }
    
    def _calculate_health_score(self, zwave: dict, zigbee: dict) -> int:
        """Calculate overall network health score (0-100)."""
        score = 100
        
        # Penalty for unavailable devices
        zwave_unavailable_ratio = zwave["total"] and zwave["unavailable"] / zwave["total"] or 0
        zigbee_unavailable_ratio = zigbee["total"] and zigbee["unavailable"] / zigbee["total"] or 0
        score -= int((zwave_unavailable_ratio + zigbee_unavailable_ratio) * 50)
        
        # Penalty for low battery
        zwave_battery_ratio = zwave["battery_devices"] and len(zwave["low_battery"]) / len(zwave["battery_devices"]) or 0
        zigbee_battery_ratio = zigbee["battery_devices"] and len(zigbee["low_battery"]) / len(zigbee["battery_devices"]) or 0
        score -= int((zwave_battery_ratio + zigbee_battery_ratio) * 20)
        
        # Penalty for high latency (Z-Wave)
        if zwave["avg_latency_ms"] and zwave["avg_latency_ms"] > 100:
            score -= int((zwave["avg_latency_ms"] - 100) / 10)
        
        # Penalty for poor link quality (Zigbee)
        if zigbee["avg_link_quality"] and zigbee["avg_link_quality"] < 50:
            score += int(zigbee["avg_link_quality"] - 50)
        
        return max(0, min(100, score))


# === Z-Wave Mesh Topology Sensor ===

class ZWaveMeshTopologySensor(SensorEntity):
    """Sensor for Z-Wave mesh topology visualization data."""
    
    _attr_has_entity_name = False
    _attr_name = "Z-Wave Mesh Topology"
    _attr_unique_id = "zwave_mesh_topology"
    _attr_icon = "mdi:tree"
    _attr_entity_category = "diagnostic"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def native_value(self) -> str:
        """Return JSON string with topology data."""
        data = self._get_topology_data()
        return json.dumps(data)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._get_topology_data()
    
    def _get_topology_data(self) -> dict[str, Any]:
        """Gather Z-Wave mesh topology data."""
        zwave = _analyze_mesh_devices(self._hass, "zwave")
        
        # Build topology structure
        nodes = []
        for device in zwave.get("battery_devices", []):
            nodes.append({
                "id": device["entity_id"],
                "name": device["name"],
                "type": "battery",
                "status": "online" if device.get("is_online", True) else "offline",
                "battery": device["battery_level"],
                "latency": device.get("latency_ms"),
            })
        
        # Add non-battery devices
        for state in self._hass.states.async_all():
            if not state.entity_id.startswith(("zwave_js.", "zwave.", "ozw.")):
                continue
            if state.entity_id.endswith(("_info", "_status", "_statistics", "_health")):
                continue
            if any(d["entity_id"] == state.entity_id for d in nodes):
                continue
            
            is_available = state.state not in ("unavailable", "unknown", "none")
            battery = state.attributes.get("battery_level")
            latency = state.attributes.get("latency")
            
            nodes.append({
                "id": state.entity_id,
                "name": state.attributes.get("friendly_name", state.entity_id),
                "type": "mains" if battery is None else "battery",
                "status": "online" if is_available else "offline",
                "battery": int(battery) if battery else None,
                "latency": int(latency) if latency else None,
            })
        
        # Calculate network stats
        online_count = sum(1 for n in nodes if n["status"] == "online")
        latency_values = [n["latency"] for n in nodes if n.get("latency")]
        
        return {
            "protocol": "zwave",
            "nodes": nodes,
            "node_count": len(nodes),
            "online_count": online_count,
            "offline_count": len(nodes) - online_count,
            "avg_latency_ms": round(sum(latency_values) / len(latency_values), 1) if latency_values else None,
            "max_latency_ms": max(latency_values) if latency_values else None,
            "mesh_health": "healthy" if online_count == len(nodes) else "degraded",
        }


# === Zigbee Mesh Topology Sensor ===

class ZigbeeMeshTopologySensor(SensorEntity):
    """Sensor for Zigbee mesh topology visualization data."""
    
    _attr_has_entity_name = False
    _attr_name = "Zigbee Mesh Topology"
    _attr_unique_id = "zigbee_mesh_topology"
    _attr_icon = "mdi:zigbee"
    _attr_entity_category = "diagnostic"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def native_value(self) -> str:
        """Return JSON string with topology data."""
        data = self._get_topology_data()
        return json.dumps(data)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._get_topology_data()
    
    def _get_topology_data(self) -> dict[str, Any]:
        """Gather Zigbee mesh topology data."""
        zigbee = _analyze_mesh_devices(self._hass, "zigbee")
        
        # Build topology structure with link quality
        nodes = []
        routers = []
        end_devices = []
        
        for device in zigbee.get("battery_devices", []):
            device_data = {
                "id": device["entity_id"],
                "name": device["name"],
                "type": "end_device",
                "status": "online" if device.get("is_online", True) else "offline",
                "battery": device["battery_level"],
                "link_quality": device.get("link_quality"),
            }
            nodes.append(device_data)
            end_devices.append(device_data)
        
        # Add non-battery devices (potential routers)
        for state in self._hass.states.async_all():
            if not state.entity_id.startswith(("zigbee2mqtt.", "deconz.", "zha.")):
                continue
            if state.entity_id.endswith(("_info", "_status", "_statistics", "_health")):
                continue
            if any(d["entity_id"] == state.entity_id for d in nodes):
                continue
            
            is_available = state.state not in ("unavailable", "unknown", "none")
            battery = state.attributes.get("battery_level")
            link_quality = state.attributes.get("linkquality") or state.attributes.get("link_quality")
            
            device_data = {
                "id": state.entity_id,
                "name": state.attributes.get("friendly_name", state.entity_id),
                "type": "router" if battery is None else "end_device",
                "status": "online" if is_available else "offline",
                "battery": int(battery) if battery else None,
                "link_quality": int(link_quality) if link_quality else None,
            }
            nodes.append(device_data)
            if device_data["type"] == "router":
                routers.append(device_data)
            else:
                end_devices.append(device_data)
        
        # Calculate network stats
        online_count = sum(1 for n in nodes if n["status"] == "online")
        lq_values = [n["link_quality"] for n in nodes if n.get("link_quality")]
        
        # Determine mesh health based on router count and link quality
        router_ratio = len(routers) / len(nodes) if nodes else 0
        avg_lq = sum(lq_values) / len(lq_values) if lq_values else 0
        
        if avg_lq < 40 or router_ratio < 0.2:
            mesh_health = "weak"
        elif avg_lq < 60 or router_ratio < 0.4:
            mesh_health = "degraded"
        else:
            mesh_health = "healthy"
        
        return {
            "protocol": "zigbee",
            "nodes": nodes,
            "routers": routers,
            "end_devices": end_devices,
            "node_count": len(nodes),
            "router_count": len(routers),
            "online_count": online_count,
            "offline_count": len(nodes) - online_count,
            "avg_link_quality": round(avg_lq, 1),
            "mesh_health": mesh_health,
        }


# === Dashboard YAML Generation ===

def generate_mesh_dashboard_yaml(
    zwave_entities: list[str] | None = None,
    zigbee_entities: list[str] | None = None,
) -> str:
    """Generate Lovelace YAML for mesh network dashboard card.
    
    Args:
        zwave_entities: List of Z-Wave entity IDs to display
        zigbee_entities: List of Zigbee entity IDs to display
    
    Returns:
        YAML string for Lovelace configuration
    """
    entities = zwave_entities or zigbee_entities or []
    
    yaml_lines = [
        "type: vertical-stack",
        "title: Mesh Network Overview",
        "cards:",
        "  - type: conditional",
        "    conditions:",
        "      - entity: sensor.mesh_network_overview",
        "        state_not: unknown",
        "    card:",
        "      type: entities",
        "      title: Network Status",
        "      show_header_toggle: false",
        "      entities:",
        "        - entity: sensor.mesh_network_overview",
        "          name: Overview",
        "          secondary_info: last-changed",
        "",
        "  - type: horizontal-stack",
        "    cards:",
        "      - type: conditional",
        "        conditions:",
        "          - entity: sensor.zwave_network_health",
        "            state_not: unknown",
        "        card:",
        "          type: entity",
        "          entity: sensor.zwave_network_health",
        "          name: Z-Wave Health",
        "          icon: mdi:mesh",
        "",
        "      - type: conditional",
        "        conditions:",
        "          - entity: sensor.zigbee_network_health",
        "            state_not: unknown",
        "        card:",
        "          type: entity",
        "          entity: sensor.zigbee_network_health",
        "          name: Zigbee Health",
        "          icon: mdi:zigbee",
        "",
        "  - type: horizontal-stack",
        "    cards:",
        "      - type: conditional",
        "        conditions:",
        "          - entity: sensor.zwave_devices_online",
        "            state_not: '0'",
        "        card:",
        "          type: entity",
        "          entity: sensor.zwave_devices_online",
        "          name: Z-Wave Online",
        "          icon: mdi:access-point",
        "",
        "      - type: conditional",
        "        conditions:",
        "          - entity: sensor.zigbee_devices_online",
        "            state_not: '0'",
        "        card:",
        "          type: entity",
        "          entity: sensor.zigbee_devices_online",
        "          name: Zigbee Online",
        "          icon: mdi:access-point-network",
        "",
        "  - type: conditional",
        "    conditions:",
        "      - entity: binary_sensor.zwave_mesh_status",
        "    card:",
        "      type: entity",
        "      entity: binary_sensor.zwave_mesh_status",
        "      name: Z-Wave Mesh Status",
        "      icon: mdi:mesh_network",
        "",
        "  - type: conditional",
        "    conditions:",
        "      - entity: binary_sensor.zigbee_mesh_status",
        "    card:",
        "      type: entity",
        "      entity: binary_sensor.zigbee_mesh_status",
        "      name: Zigbee Mesh Status",
        "      icon: mdi:mesh_network",
        "",
        "  - type: conditional",
        "    conditions:",
        "      - entity: sensor.zwave_battery_overview",
        "        state_not: no_battery_devices",
        "    card:",
        "      type: entity",
        "      entity: sensor.zwave_battery_overview",
        "      name: Z-Wave Battery",
        "      icon: mdi:battery",
        "",
        "  - type: conditional",
        "    conditions:",
        "      - entity: sensor.zigbee_battery_overview",
        "        state_not: no_battery_devices",
        "    card:",
        "      type: entity",
        "      entity: sensor.zigbee_battery_overview",
        "      name: Zigbee Battery",
        "      icon: mdi:battery",
    ]
    
    # Add custom topology cards if entities provided
    if entities:
        yaml_lines.extend([
            "",
            "  - type: conditional",
            "    conditions:",
            "      - entity: sensor.zwave_mesh_topology",
            "    card:",
            "      type: entity",
            "      entity: sensor.zwave_mesh_topology",
            "      name: Z-Wave Topology",
            "      icon: mdi:tree",
        ])
    
    return "\n".join(yaml_lines)


def generate_mesh_dashboard_yaml_v2() -> str:
    """Generate enhanced Lovelace YAML for mesh network dashboard."""
    return """type: vertical-stack
title: Mesh Network Overview
cards:
  # Health Score Card
  - type: conditional
    conditions:
      - entity: sensor.mesh_network_overview
        state_not: unknown
    card:
      type: gauge
      entity: sensor.mesh_network_overview
      name: Network Health Score
      min: 0
      max: 100
      unit: '%'
      severity:
        red: 0
        yellow: 50
        green: 80

  # Network Status Overview
  - type: entities
    title: Network Status
    show_header_toggle: false
    entities:
      - entity: sensor.mesh_network_overview
        name: Overview
        secondary_info: last-changed

  # Z-Wave Section
  - type: horizontal-stack
    cards:
      - type: conditional
        conditions:
          - entity: sensor.zwave_network_health
            state_not: unknown
        card:
          type: entity
          entity: sensor.zwave_network_health
          name: Z-Wave Health
          icon: mdi:mesh

      - type: conditional
        conditions:
          - entity: sensor.zwave_devices_online
            state_not: '0'
        card:
          type: entity
          entity: sensor.zwave_devices_online
          name: Z-Wave Online
          icon: mdi:access-point

      - type: conditional
        conditions:
          - entity: sensor.zwave_battery_overview
            state_not: no_battery_devices
        card:
          type: entity
          entity: sensor.zwave_battery_overview
          name: Z-Wave Battery
          icon: mdi:battery

  # Zigbee Section
  - type: horizontal-stack
    cards:
      - type: conditional
        conditions:
          - entity: sensor.zigbee_network_health
            state_not: unknown
        card:
          type: entity
          entity: sensor.zigbee_network_health
          name: Zigbee Health
          icon: mdi:zigbee

      - type: conditional
        conditions:
          - entity: sensor.zigbee_devices_online
            state_not: '0'
        card:
          type: entity
          entity: sensor.zigbee_devices_online
          name: Zigbee Online
          icon: mdi:access-point-network

      - type: conditional
        conditions:
          - entity: sensor.zigbee_battery_overview
            state_not: no_battery_devices
        card:
          type: entity
          entity: sensor.zigbee_battery_overview
          name: Zigbee Battery
          icon: mdi:battery

  # Mesh Status Binary Sensors
  - type: horizontal-stack
    cards:
      - type: conditional
        conditions:
          - entity: binary_sensor.zwave_mesh_status
        card:
          type: entity
          entity: binary_sensor.zwave_mesh_status
          name: Z-Wave Mesh
          icon: mdi:mesh_network

      - type: conditional
        conditions:
          - entity: binary_sensor.zigbee_mesh_status
        card:
          type: entity
          entity: binary_sensor.zigbee_mesh_status
          name: Zigbee Mesh
          icon: mdi:mesh_network

  # Topology JSON (for custom cards)
  - type: conditional
    conditions:
      - entity: sensor.zwave_mesh_topology
        state_not: unknown
    card:
      type: entity
      entity: sensor.zwave_mesh_topology
      name: Z-Wave Topology
      icon: mdi:tree

  - type: conditional
    conditions:
      - entity: sensor.zigbee_mesh_topology
        state_not: unknown
    card:
      type: entity
      entity: sensor.zigbee_mesh_topology
      name: Zigbee Topology
      icon: mdi:zigbee
"""


# === Node-RED Dashboard Integration ===

def generate_nodered_mesh_payload(mesh_data: dict[str, Any]) -> dict[str, Any]:
    """Generate Node-RED compatible payload for mesh data.
    
    Args:
        mesh_data: Mesh network data from the overview sensor
    
    Returns:
        Node-RED msg payload structure
    """
    return {
        "topic": "mesh/network",
        "payload": {
            "health_score": mesh_data.get("health_score"),
            "zwave": {
                "devices": mesh_data.get("zwave", {}).get("total_devices"),
                "online": mesh_data.get("zwave", {}).get("online"),
                "latency": mesh_data.get("zwave", {}).get("avg_latency_ms"),
            },
            "zigbee": {
                "devices": mesh_data.get("zigbee", {}).get("total_devices"),
                "online": mesh_data.get("zigbee", {}).get("online"),
                "link_quality": mesh_data.get("zigbee", {}).get("avg_link_quality"),
            },
            "battery": {
                "total": mesh_data.get("battery", {}).get("total"),
                "low": mesh_data.get("battery", {}).get("low"),
            },
        },
        "timestamp": mesh_data.get("last_updated"),
    }


# === ESPHome Integration ===

def generate_esphome_mesh_yaml(
    entity_name: str = "mesh_network",
    zwave_entity: str = "sensor.zwave_mesh_topology",
    zigbee_entity: str = "sensor.zigbee_mesh_topology",
) -> str:
    """Generate ESPHome YAML configuration for mesh network display.
    
    Args:
        entity_name: Name for the ESPHome sensor
        zwave_entity: Home Assistant entity for Z-Wave data
        zigbee_entity: Home Assistant entity for Zigbee data
    
    Returns:
        ESPHome YAML configuration
    """
    return f"""
# Mesh Network Dashboard - ESPHome Configuration
# Add to your ESPHome configuration.yaml

sensor:
  - name: {entity_name}_health
    id: mesh_health_score
    state_class: measurement
    unit_of_measurement: "%"
    accuracy_decimals: 0
    
  - name: {entity_name}_zwave_devices
    id: zwave_device_count
    state_class: measurement
    accuracy_decimals: 0
    
  - name: {entity_name}_zigbee_devices
    id: zigbee_device_count
    state_class: measurement
    accuracy_decimals: 0
    
  - name: {entity_name}_battery_low
    id: low_battery_count
    state_class: measurement
    unit_of_measurement: "devices"
    accuracy_decimals: 0

text_sensor:
  - name: {entity_name}_status
    id: mesh_status
    state_class: measurement
    
  - name: {entity_name}_zwave_health
    id: zwave_health
    state_class: measurement
    
  - name: {entity_name}_zigbee_health
    id: zigbee_health
    state_class: measurement

# Optional: Display on OLED/LCD
display:
  - platform: ssd1306_i2c
    # ... your display config ...
    lambda: |-
      it.printf(0, 0, id(mesh_font), "Mesh: %d%%", id(mesh_health_score).state);
      it.printf(0, 16, id(mesh_font), "Z-Wave: %d", id(zwave_device_count).state);
      it.printf(0, 32, id(mesh_font), "Zigbee: %d", id(zigbee_device_count).state);
      it.printf(0, 48, id(mesh_font), "Low Bat: %d", id(low_battery_count).state);
"""


# === Home Assistant Service for Dashboard Generation ===

async def async_setup_mesh_dashboard_services(hass: HomeAssistant):
    """Set up services for generating mesh dashboard configurations."""
    
    from homeassistant.core import ServiceCall
    from homeassistant.helpers import template
    
    async def generate_lovelace_yaml(call: ServiceCall) -> str:
        """Generate Lovelace YAML for mesh dashboard."""
        return generate_mesh_dashboard_yaml_v2()
    
    async def generate_esphome_yaml(call: ServiceCall) -> str:
        """Generate ESPHome YAML for mesh display."""
        return generate_esphome_yaml()
    
    hass.services.async_register(
        DOMAIN,
        "generate_mesh_dashboard",
        generate_lovelace_yaml,
    )
    
    hass.services.async_register(
        DOMAIN,
        "generate_mesh_esphome",
        generate_esphome_yaml,
    )
