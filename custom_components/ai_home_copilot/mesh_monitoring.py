"""
Mesh Monitoring for Z-Wave and Zigbee networks.

Provides sensors and binary sensors for network health monitoring:
- Z-Wave: device count, mesh status, battery levels, latency
- Zigbee: device count, mesh status, link quality, battery alerts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .entity import CopilotBaseEntity


# Common entity prefixes
ZWAVE_ENTITY_PREFIXES = (
    "zwave_js.",
    "zwave.",
    "ozw.",
)

ZIGBEE_ENTITY_PREFIXES = (
    "zigbee2mqtt.",
    "deconz.",
    "zha.",
)


@dataclass
class MeshDeviceInfo:
    """Represents a mesh device."""
    entity_id: str
    name: str
    is_online: bool
    battery_level: int | None = None
    link_quality: int | None = None
    latency_ms: int | None = None


def _get_integration_prefixes(protocol: str) -> tuple[str, ...]:
    """Get entity prefixes for the given protocol."""
    if protocol == "zwave":
        return ZWAVE_ENTITY_PREFIXES
    elif protocol == "zigbee":
        return ZIGBEE_ENTITY_PREFIXES
    return ()


def _analyze_mesh_devices(hass: HomeAssistant, protocol: str) -> dict[str, Any]:
    """Analyze mesh devices for the given protocol."""
    prefixes = _get_integration_prefixes(protocol)
    if not prefixes:
        return {
            "total": 0,
            "online": 0,
            "offline": 0,
            "unavailable": 0,
            "battery_devices": [],
            "low_battery": [],
            "avg_latency_ms": None,
            "avg_link_quality": None,
        }
    
    all_states = hass.states.async_all()
    
    devices: list[MeshDeviceInfo] = []
    battery_devices: list[dict] = []
    low_battery: list[dict] = []
    latency_values: list[int] = []
    link_quality_values: list[int] = []
    
    for state in all_states:
        entity_id = state.entity_id
        
        # Check if entity belongs to this protocol
        if not any(entity_id.startswith(prefix) for prefix in prefixes):
            continue
        
        # Skip diagnostic entities
        if entity_id.endswith(("_info", "_status", "_statistics", "_health")):
            continue
        
        is_available = state.state not in ("unavailable", "unknown", "none")
        name = state.attributes.get("friendly_name", entity_id)
        
        # Extract battery level
        battery_level = state.attributes.get("battery_level")
        if battery_level is not None:
            try:
                battery_level = int(battery_level)
            except (ValueError, TypeError):
                battery_level = None
            
            if battery_level is not None and battery_level > 0:
                device_info = MeshDeviceInfo(
                    entity_id=entity_id,
                    name=name,
                    is_online=is_available,
                    battery_level=battery_level,
                )
                devices.append(device_info)
                battery_devices.append({
                    "entity_id": entity_id,
                    "name": name,
                    "battery_level": battery_level,
                })
                if battery_level < 20:
                    low_battery.append({
                        "entity_id": entity_id,
                        "name": name,
                        "battery_level": battery_level,
                    })
        
        # Extract latency (Z-Wave specific)
        if protocol == "zwave":
            latency = state.attributes.get("latency")
            if latency is not None:
                try:
                    latency = int(latency)
                    if latency > 0:
                        latency_values.append(latency)
                except (ValueError, TypeError):
                    pass
        
        # Extract link quality (Zigbee specific)
        if protocol == "zigbee":
            link_quality = state.attributes.get("linkquality") or state.attributes.get("link_quality")
            if link_quality is not None:
                try:
                    link_quality = int(link_quality)
                    if link_quality > 0:
                        link_quality_values.append(link_quality)
                except (ValueError, TypeError):
                    pass
        
        # Count all devices (not just battery)
        if battery_level is None:
            devices.append(MeshDeviceInfo(
                entity_id=entity_id,
                name=name,
                is_online=is_available,
            ))
    
    total = len(devices)
    online = sum(1 for d in devices if d.is_online)
    offline = sum(1 for d in devices if not d.is_online)
    unavailable = sum(1 for d in devices if d.state == "unavailable" if hasattr(d, 'state'))
    
    avg_latency = sum(latency_values) / len(latency_values) if latency_values else None
    avg_link_quality = sum(link_quality_values) / len(link_quality_values) if link_quality_values else None
    
    return {
        "total": total,
        "online": online,
        "offline": offline,
        "unavailable": unavailable,
        "battery_devices": battery_devices,
        "low_battery": low_battery,
        "avg_latency_ms": round(avg_latency, 1) if avg_latency else None,
        "avg_link_quality": round(avg_link_quality, 1) if avg_link_quality else None,
    }


async def async_setup_mesh_sensors(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up mesh monitoring sensors."""
    
    entities = [
        ZWaveNetworkHealthSensor(hass, entry),
        ZWaveDevicesOnlineSensor(hass, entry),
        ZigbeeNetworkHealthSensor(hass, entry),
        ZigbeeDevicesOnlineSensor(hass, entry),
    ]
    
    async_add_entities(entities, True)


async def async_setup_mesh_binary_sensors(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up mesh monitoring binary sensors."""
    
    entities = [
        ZWaveMeshStatusBinarySensor(hass, entry),
        ZigbeeMeshStatusBinarySensor(hass, entry),
    ]
    
    async_add_entities(entities, True)


class ZWaveNetworkHealthSensor(SensorEntity):
    """Sensor for Z-Wave network health status."""
    
    _attr_has_entity_name = False
    _attr_name = "Z-Wave Network Health"
    _attr_unique_id = "zwave_network_health"
    _attr_icon = "mdi:mesh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def native_value(self) -> str:
        data = _analyze_mesh_devices(self._hass, "zwave")
        
        if data["total"] == 0:
            return "not_found"
        
        # Calculate health score
        if data["unavailable"] > data["total"] * 0.5:
            return "critical"
        elif data["low_battery"]:
            return "degraded"
        elif data["avg_latency_ms"] and data["avg_latency_ms"] > 200:
            return "slow"
        elif data["online"] < data["total"]:
            return "degraded"
        
        return "healthy"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = _analyze_mesh_devices(self._hass, "zwave")
        return {
            "total_devices": data["total"],
            "online_devices": data["online"],
            "offline_devices": data["offline"],
            "unavailable_devices": data["unavailable"],
            "battery_devices": len(data["battery_devices"]),
            "low_battery_devices": len(data["low_battery"]),
            "avg_latency_ms": data["avg_latency_ms"],
        }


class ZWaveDevicesOnlineSensor(SensorEntity):
    """Sensor for count of online Z-Wave devices."""
    
    _attr_has_entity_name = False
    _attr_name = "Z-Wave Devices Online"
    _attr_unique_id = "zwave_devices_online"
    _attr_icon = "mdi:access_point"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def native_value(self) -> int:
        data = _analyze_mesh_devices(self._hass, "zwave")
        return data["online"]
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = _analyze_mesh_devices(self._hass, "zwave")
        return {
            "total": data["total"],
            "offline": data["offline"],
            "unavailable": data["unavailable"],
        }


class ZigbeeNetworkHealthSensor(SensorEntity):
    """Sensor for Zigbee network health status."""
    
    _attr_has_entity_name = False
    _attr_name = "Zigbee Network Health"
    _attr_unique_id = "zigbee_network_health"
    _attr_icon = "mdi:zigbee"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def native_value(self) -> str:
        data = _analyze_mesh_devices(self._hass, "zigbee")
        
        if data["total"] == 0:
            return "not_found"
        
        # Calculate health score based on link quality
        if data["unavailable"] > data["total"] * 0.5:
            return "critical"
        elif data["low_battery"]:
            return "degraded"
        elif data["avg_link_quality"] and data["avg_link_quality"] < 50:
            return "weak_signal"
        elif data["online"] < data["total"]:
            return "degraded"
        
        return "healthy"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = _analyze_mesh_devices(self._hass, "zigbee")
        return {
            "total_devices": data["total"],
            "online_devices": data["online"],
            "offline_devices": data["offline"],
            "unavailable_devices": data["unavailable"],
            "battery_devices": len(data["battery_devices"]),
            "low_battery_devices": len(data["low_battery"]),
            "avg_link_quality": data["avg_link_quality"],
        }


class ZigbeeDevicesOnlineSensor(SensorEntity):
    """Sensor for count of online Zigbee devices."""
    
    _attr_has_entity_name = False
    _attr_name = "Zigbee Devices Online"
    _attr_unique_id = "zigbee_devices_online"
    _attr_icon = "mdi:access_point_network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def native_value(self) -> int:
        data = _analyze_mesh_devices(self._hass, "zigbee")
        return data["online"]
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = _analyze_mesh_devices(self._hass, "zigbee")
        return {
            "total": data["total"],
            "offline": data["offline"],
            "unavailable": data["unavailable"],
        }


class ZWaveMeshStatusBinarySensor(BinarySensorEntity):
    """Binary sensor for Z-Wave mesh network status."""
    
    _attr_has_entity_name = False
    _attr_name = "Z-Wave Mesh Status"
    _attr_unique_id = "zwave_mesh_status"
    _attr_icon = "mdi:mesh_network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def is_on(self) -> bool:
        data = _analyze_mesh_devices(self._hass, "zwave")
        
        if data["total"] == 0:
            return False
        
        # Mesh is healthy if most devices are online
        if data["total"] > 0:
            online_ratio = data["online"] / data["total"]
            return online_ratio >= 0.8
        
        return False
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = _analyze_mesh_devices(self._hass, "zwave")
        return {
            "total_devices": data["total"],
            "online_devices": data["online"],
            "unavailable_devices": data["unavailable"],
            "low_battery_alerts": len(data["low_battery"]),
            "avg_latency_ms": data["avg_latency_ms"],
        }


class ZigbeeMeshStatusBinarySensor(BinarySensorEntity):
    """Binary sensor for Zigbee mesh network status."""
    
    _attr_has_entity_name = False
    _attr_name = "Zigbee Mesh Status"
    _attr_unique_id = "zigbee_mesh_status"
    _attr_icon = "mdi:mesh_network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def is_on(self) -> bool:
        data = _analyze_mesh_devices(self._hass, "zigbee")
        
        if data["total"] == 0:
            return False
        
        # Mesh is healthy if most devices are online and link quality is good
        if data["total"] > 0:
            online_ratio = data["online"] / data["total"]
            if online_ratio < 0.8:
                return False
            
            # Check average link quality
            if data["avg_link_quality"] and data["avg_link_quality"] < 40:
                return False
        
        return True
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = _analyze_mesh_devices(self._hass, "zigbee")
        return {
            "total_devices": data["total"],
            "online_devices": data["online"],
            "unavailable_devices": data["unavailable"],
            "low_battery_alerts": len(data["low_battery"]),
            "avg_link_quality": data["avg_link_quality"],
        }


# Battery overview sensors (additional utility)

class ZWaveBatteryOverviewSensor(SensorEntity):
    """Sensor for Z-Wave battery overview."""
    
    _attr_has_entity_name = False
    _attr_name = "Z-Wave Battery Overview"
    _attr_unique_id = "zwave_battery_overview"
    _attr_icon = "mdi:battery"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def native_value(self) -> str:
        data = _analyze_mesh_devices(self._hass, "zwave")
        
        low = len(data["low_battery"])
        total = len(data["battery_devices"])
        
        if total == 0:
            return "no_battery_devices"
        elif low > 0:
            return f"{low}/{total} low"
        return "ok"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = _analyze_mesh_devices(self._hass, "zwave")
        return {
            "total_battery_devices": len(data["battery_devices"]),
            "low_battery_devices": data["low_battery"],
        }


class ZigbeeBatteryOverviewSensor(SensorEntity):
    """Sensor for Zigbee battery overview."""
    
    _attr_has_entity_name = False
    _attr_name = "Zigbee Battery Overview"
    _attr_unique_id = "zigbee_battery_overview"
    _attr_icon = "mdi:battery"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
    
    @property
    def native_value(self) -> str:
        data = _analyze_mesh_devices(self._hass, "zigbee")
        
        low = len(data["low_battery"])
        total = len(data["battery_devices"])
        
        if total == 0:
            return "no_battery_devices"
        elif low > 0:
            return f"{low}/{total} low"
        return "ok"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = _analyze_mesh_devices(self._hass, "zigbee")
        return {
            "total_battery_devices": len(data["battery_devices"]),
            "low_battery_devices": data["low_battery"],
        }
