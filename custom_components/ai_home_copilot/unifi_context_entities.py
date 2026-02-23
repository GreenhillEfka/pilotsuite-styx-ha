"""UniFi context entities for PilotSuite."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .unifi_context import UnifiContextCoordinator


class _UnifiSensorBase(CoordinatorEntity[UnifiContextCoordinator], SensorEntity):
    """Base class for UniFi coordinator-backed sensors."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: UnifiContextCoordinator, key: str, name: str, icon: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_name = name
        self._attr_icon = icon


class _UnifiBinaryBase(CoordinatorEntity[UnifiContextCoordinator], BinarySensorEntity):
    """Base class for UniFi coordinator-backed binary sensors."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: UnifiContextCoordinator, key: str, name: str, icon: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_name = name
        self._attr_icon = icon


class UnifiClientsOnlineSensor(_UnifiSensorBase):
    """Number of online UniFi clients."""

    def __init__(self, coordinator: UnifiContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="unifi_clients_online",
            name="PilotSuite UniFi Clients Online",
            icon="mdi:devices",
        )

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data:
            return len([c for c in self.coordinator.data.clients if c.status == "online"])
        return 0


class UnifiWanLatencySensor(_UnifiSensorBase):
    """Current WAN latency."""

    _attr_native_unit_of_measurement = "ms"

    def __init__(self, coordinator: UnifiContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="unifi_wan_latency",
            name="PilotSuite UniFi WAN Latency",
            icon="mdi:timer-outline",
        )

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data and self.coordinator.data.wan:
            return round(self.coordinator.data.wan.latency_ms, 1)
        return 0.0


class UnifiPacketLossSensor(_UnifiSensorBase):
    """Current WAN packet loss."""

    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator: UnifiContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="unifi_packet_loss",
            name="PilotSuite UniFi Packet Loss",
            icon="mdi:packet-loss",
        )

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data and self.coordinator.data.wan:
            return round(self.coordinator.data.wan.packet_loss_percent, 2)
        return 0.0


class UnifiUptimeSensor(_UnifiSensorBase):
    """WAN uptime as compact readable string."""

    def __init__(self, coordinator: UnifiContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="unifi_wan_uptime",
            name="PilotSuite UniFi WAN Uptime",
            icon="mdi:clock-outline",
        )

    @property
    def native_value(self) -> StateType:
        if not self.coordinator.data or not self.coordinator.data.wan:
            return "0s"
        seconds = int(self.coordinator.data.wan.uptime_seconds)
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            return f"{seconds // 60}m"
        if seconds < 86400:
            return f"{seconds // 3600}h"
        return f"{seconds // 86400}d"


class UnifiWanOnlineBinarySensor(_UnifiBinaryBase):
    """WAN online state."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: UnifiContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="unifi_wan_online",
            name="PilotSuite UniFi WAN Online",
            icon="mdi:wan",
        )

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data and self.coordinator.data.wan:
            return self.coordinator.data.wan.online
        return None


class UnifiRoamingActivityBinarySensor(_UnifiBinaryBase):
    """Roaming activity indicator."""

    _attr_device_class = BinarySensorDeviceClass.MOTION

    def __init__(self, coordinator: UnifiContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="unifi_roaming",
            name="PilotSuite UniFi Roaming Activity",
            icon="mdi:swap-horizontal",
        )

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return False
        return any(bool(client.roaming) for client in self.coordinator.data.clients)


def build_unifi_sensor_entities(coordinator: UnifiContextCoordinator) -> list[SensorEntity]:
    """Build UniFi sensor entities backed by a UniFi coordinator."""
    return [
        UnifiClientsOnlineSensor(coordinator),
        UnifiWanLatencySensor(coordinator),
        UnifiPacketLossSensor(coordinator),
        UnifiUptimeSensor(coordinator),
    ]


def build_unifi_binary_entities(coordinator: UnifiContextCoordinator) -> list[BinarySensorEntity]:
    """Build UniFi binary entities backed by a UniFi coordinator."""
    return [
        UnifiWanOnlineBinarySensor(coordinator),
        UnifiRoamingActivityBinarySensor(coordinator),
    ]
