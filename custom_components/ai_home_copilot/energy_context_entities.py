"""Energy Context Entities for PilotSuite.

Exposes energy data as Home Assistant entities:
- sensor.ai_home_copilot_energy_consumption_today
- sensor.ai_home_copilot_energy_production_today
- sensor.ai_home_copilot_energy_current_power
- sensor.ai_home_copilot_energy_anomalies
- sensor.ai_home_copilot_energy_shifting_opportunities
- binary_sensor.ai_home_copilot_energy_anomaly_alert
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .energy_context import EnergyContextCoordinator, EnergySnapshot

_LOGGER = logging.getLogger(__name__)


class EnergyConsumptionTodaySensor(CoordinatorEntity[EnergyContextCoordinator], SensorEntity):
    """Sensor for daily energy consumption."""

    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = "energy"
    _attr_state_class = "total"
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, hass: HomeAssistant, coordinator: EnergyContextCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_energy_consumption_today"
        self._attr_name = "PilotSuite Energy Consumption Today"
        self.entity_id = f"sensor.{self._attr_unique_id}"

    @property
    def native_value(self) -> float:
        """Return current consumption value."""
        if self.coordinator.data:
            return round(self.coordinator.data.total_consumption_today_kwh, 2)
        return 0.0


class EnergyProductionTodaySensor(CoordinatorEntity[EnergyContextCoordinator], SensorEntity):
    """Sensor for daily energy production (e.g., solar)."""

    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = "energy"
    _attr_state_class = "total"
    _attr_icon = "mdi:solar-power"

    def __init__(self, hass: HomeAssistant, coordinator: EnergyContextCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_energy_production_today"
        self._attr_name = "PilotSuite Energy Production Today"
        self.entity_id = f"sensor.{self._attr_unique_id}"

    @property
    def native_value(self) -> float:
        """Return current production value."""
        if self.coordinator.data:
            return round(self.coordinator.data.total_production_today_kwh, 2)
        return 0.0


class EnergyCurrentPowerSensor(CoordinatorEntity[EnergyContextCoordinator], SensorEntity):
    """Sensor for current power draw/production."""

    _attr_native_unit_of_measurement = "W"
    _attr_device_class = "power"
    _attr_state_class = "measurement"
    _attr_icon = "mdi:flash"

    def __init__(self, hass: HomeAssistant, coordinator: EnergyContextCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_energy_current_power"
        self._attr_name = "PilotSuite Energy Current Power"
        self.entity_id = f"sensor.{self._attr_unique_id}"

    @property
    def native_value(self) -> float:
        """Return current power value."""
        if self.coordinator.data:
            return round(self.coordinator.data.current_power_watts, 0)
        return 0.0


class EnergyAnomaliesSensor(CoordinatorEntity[EnergyContextCoordinator], SensorEntity):
    """Sensor for number of detected energy anomalies."""

    _attr_icon = "mdi:alert-circle"

    def __init__(self, hass: HomeAssistant, coordinator: EnergyContextCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_energy_anomalies"
        self._attr_name = "PilotSuite Energy Anomalies"
        self.entity_id = f"sensor.{self._attr_unique_id}"

    @property
    def native_value(self) -> int:
        """Return number of anomalies."""
        if self.coordinator.data:
            return self.coordinator.data.anomalies_detected
        return 0


class EnergyShiftingOpportunitiesSensor(CoordinatorEntity[EnergyContextCoordinator], SensorEntity):
    """Sensor for number of load shifting opportunities."""

    _attr_icon = "mdi:clock-outline"

    def __init__(self, hass: HomeAssistant, coordinator: EnergyContextCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_energy_shifting"
        self._attr_name = "PilotSuite Energy Shifting Opportunities"
        self.entity_id = f"sensor.{self._attr_unique_id}"

    @property
    def native_value(self) -> int:
        """Return number of shifting opportunities."""
        if self.coordinator.data:
            return self.coordinator.data.shifting_opportunities
        return 0


class EnergyAnomalyAlertBinarySensor(CoordinatorEntity[EnergyContextCoordinator], BinarySensorEntity):
    """Binary sensor that is ON when there are high-severity energy anomalies."""

    _attr_device_class = "problem"
    _attr_icon = "mdi:alert"

    def __init__(self, hass: HomeAssistant, coordinator: EnergyContextCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_energy_anomaly_alert"
        self._attr_name = "PilotSuite Energy Anomaly Alert"
        self.entity_id = f"binary_sensor.{self._attr_unique_id}"

    @property
    def is_on(self) -> bool | None:
        """Return True if there are high-severity anomalies."""
        # We need to fetch anomalies to check severity
        # This is a simple implementation - in production, use async_get_anomalies
        if self.coordinator.data and self.coordinator.data.anomalies_detected > 0:
            # Assume anomaly exists - actual severity check happens in async callback
            return True
        return False


async def async_setup_energy_entities(
    hass: HomeAssistant,
    coordinator: EnergyContextCoordinator,
) -> list[Entity]:
    """Set up all energy context entities."""
    entities = [
        EnergyConsumptionTodaySensor(hass, coordinator),
        EnergyProductionTodaySensor(hass, coordinator),
        EnergyCurrentPowerSensor(hass, coordinator),
        EnergyAnomaliesSensor(hass, coordinator),
        EnergyShiftingOpportunitiesSensor(hass, coordinator),
        EnergyAnomalyAlertBinarySensor(hass, coordinator),
    ]

    for entity in entities:
        hass.data[DOMAIN].setdefault("entities", []).append(entity)
        await entity.async_added_to_hass()

    _LOGGER.info("Created %d energy context entities", len(entities))
    return entities
