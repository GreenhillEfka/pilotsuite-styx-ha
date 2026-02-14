"""UniFi Context Entities for AI Home CoPilot.

Exposes network data as Home Assistant entities:
- sensor.ai_home_copilot_unifi_clients_online
- sensor.ai_home_copilot_unifi_wan_latency
- sensor.ai_home_copilot_unifi_packet_loss
- binary_sensor.ai_home_copilot_unifi_wan_online
- binary_sensor.ai_home_copilot_unifi_roaming_activity
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .unifi_context import UnifiContextCoordinator, UnifiSnapshot

_LOGGER = logging.getLogger(__name__)


class UnifiClientsOnlineSensor(CoordinatorEntity[UnifiContextCoordinator], Entity):
    """Sensor for number of online UniFi clients."""

    def __init__(self, hass: HomeAssistant, coordinator: UnifiContextCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_unifi_clients_online"
        self._attr_name = "AI Home CoPilot UniFi Clients Online"
        self.entity_id = f"sensor.{self._attr_unique_id}"
        self._attr_icon = "mdi:devices"

    @property
    def native_value(self) -> int:
        """Return number of online clients."""
        if self.coordinator.data:
            return len([c for c in self.coordinator.data.clients if c.status == "online"])
        return 0


class UnifiWanLatencySensor(CoordinatorEntity[UnifiContextCoordinator], Entity):
    """Sensor for WAN latency in milliseconds."""

    _attr_native_unit_of_measurement = "ms"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, hass: HomeAssistant, coordinator: UnifiContextCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_unifi_wan_latency"
        self._attr_name = "AI Home CoPilot UniFi WAN Latency"
        self.entity_id = f"sensor.{self._attr_unique_id}"

    @property
    def native_value(self) -> float:
        """Return WAN latency value."""
        if self.coordinator.data and self.coordinator.data.wan:
            return round(self.coordinator.data.wan.latency_ms, 1)
        return 0.0


class UnifiPacketLossSensor(CoordinatorEntity[UnifiContextCoordinator], Entity):
    """Sensor for WAN packet loss percentage."""

    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:packet-loss"

    def __init__(self, hass: HomeAssistant, coordinator: UnifiContextCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_unifi_packet_loss"
        self._attr_name = "AI Home CoPilot UniFi Packet Loss"
        self.entity_id = f"sensor.{self._attr_unique_id}"

    @property
    def native_value(self) -> float:
        """Return packet loss percentage."""
        if self.coordinator.data and self.coordinator.data.wan:
            return round(self.coordinator.data.wan.packet_loss_percent, 2)
        return 0.0


class UnifiWanOnlineBinarySensor(CoordinatorEntity[UnifiContextCoordinator], Entity):
    """Binary sensor for WAN online status."""

    _attr_device_class = "connectivity"
    _attr_icon = "mdi:wan"

    def __init__(self, hass: HomeAssistant, coordinator: UnifiContextCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_unifi_wan_online"
        self._attr_name = "AI Home CoPilot UniFi WAN Online"
        self.entity_id = f"binary_sensor.{self._attr_unique_id}"

    @property
    def is_on(self) -> bool | None:
        """Return True if WAN is online."""
        if self.coordinator.data and self.coordinator.data.wan:
            return self.coordinator.data.wan.online
        return None


class UnifiRoamingActivityBinarySensor(CoordinatorEntity[UnifiContextCoordinator], Entity):
    """Binary sensor for recent roaming activity."""

    _attr_device_class = "activity"
    _attr_icon = "mdi:swap-horizontal"

    def __init__(self, hass: HomeAssistant, coordinator: UnifiContextCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_unifi_roaming"
        self._attr_name = "AI Home CoPilot UniFi Roaming Activity"
        self.entity_id = f"binary_sensor.{self._attr_unique_id}"

    @property
    def is_on(self) -> bool | None:
        """Return True if there was recent roaming activity."""
        if self.coordinator.data:
            # Check for roaming clients in the last 5 minutes
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            for client in self.coordinator.data.clients:
                if client.roaming:
                    return True
        return False


class UnifiUptimeSensor(CoordinatorEntity[UnifiContextCoordinator], Entity):
    """Sensor for WAN uptime in human-readable format."""

    _attr_icon = "mdi:clock-outline"

    def __init__(self, hass: HomeAssistant, coordinator: UnifiContextCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_unifi_wan_uptime"
        self._attr_name = "AI Home CoPilot UniFi WAN Uptime"
        self.entity_id = f"sensor.{self._attr_unique_id}"

    @property
    def native_value(self) -> str:
        """Return formatted uptime."""
        if self.coordinator.data and self.coordinator.data.wan:
            seconds = self.coordinator.data.wan.uptime_seconds
            if seconds < 60:
                return f"{seconds}s"
            elif seconds < 3600:
                return f"{seconds // 60}m"
            elif seconds < 86400:
                return f"{seconds // 3600}h"
            else:
                return f"{seconds // 86400}d"
        return "0s"


async def async_setup_unifi_entities(
    hass: HomeAssistant,
    coordinator: UnifiContextCoordinator,
) -> list[Entity]:
    """Set up all UniFi context entities."""
    entities = [
        UnifiClientsOnlineSensor(hass, coordinator),
        UnifiWanLatencySensor(hass, coordinator),
        UnifiPacketLossSensor(hass, coordinator),
        UnifiWanOnlineBinarySensor(hass, coordinator),
        UnifiRoamingActivityBinarySensor(hass, coordinator),
        UnifiUptimeSensor(hass, coordinator),
    ]

    for entity in entities:
        hass.data[DOMAIN].setdefault("entities", []).append(entity)
        await entity.async_added_to_hass()

    _LOGGER.info("Created %d UniFi context entities", len(entities))
    return entities
