"""Weather Context Entities for PilotSuite.

Provides sensor entities for weather-based PV forecasting and energy optimization.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .weather_context import (
    WeatherContextCoordinator,
    WeatherSnapshot,
    WeatherForecast,
    PVRecommendation,
)


async def async_setup_weather_entities(
    hass: HomeAssistant,
    coordinator: WeatherContextCoordinator,
) -> None:
    """Set up Weather Context entities."""
    entities = [
        WeatherConditionSensor(coordinator),
        WeatherTemperatureSensor(coordinator),
        WeatherCloudCoverSensor(coordinator),
        WeatherUVIndexSensor(coordinator),
        WeatherPVSolarForecastSensor(coordinator),
        WeatherPVRecommendationSensor(coordinator),
        WeatherPVSurplusSensor(coordinator),
    ]
    
    # Register entities with Home Assistant
    for entity in entities:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(
                hass.config_entries.ConfigEntry(domain=DOMAIN),
                "sensor",
                entity,
            )
        )


class WeatherConditionSensor(SensorEntity):
    """Sensor for current weather condition."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_name = "PilotSuite Weather Condition"
        self._attr_unique_id = f"{DOMAIN}_weather_condition"
        self._attr_icon = "mdi:weather-partly-cloudy"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = [
            "sunny",
            "clear",
            "partly_cloudy",
            "cloudy",
            "overcast",
            "rainy",
            "drizzle",
            "stormy",
            "snowy",
            "foggy",
            "windy",
        ]

    @property
    def native_value(self) -> StateType:
        """Return current weather condition."""
        if self.coordinator.data:
            return self.coordinator.data.condition
        return None


class WeatherTemperatureSensor(SensorEntity):
    """Sensor for current temperature."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_name = "PilotSuite Weather Temperature"
        self._attr_unique_id = f"{DOMAIN}_weather_temperature"
        self._attr_icon = "mdi:thermometer"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = "°C"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> StateType:
        """Return current temperature."""
        if self.coordinator.data:
            return self.coordinator.data.temperature_c
        return None


class WeatherCloudCoverSensor(SensorEntity):
    """Sensor for cloud cover percentage."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_name = "PilotSuite Weather Cloud Cover"
        self._attr_unique_id = f"{DOMAIN}_weather_cloud_cover"
        self._attr_icon = "mdi:weather-cloudy"
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> StateType:
        """Return cloud cover percentage."""
        if self.coordinator.data:
            return self.coordinator.data.cloud_cover_percent
        return None


class WeatherUVIndexSensor(SensorEntity):
    """Sensor for UV index."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_name = "PilotSuite Weather UV Index"
        self._attr_unique_id = f"{DOMAIN}_weather_uv_index"
        self._attr_icon = "mdi:weather-sunny-alert"
        self._attr_native_unit_of_measurement = "UV"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> StateType:
        """Return UV index."""
        if self.coordinator.data:
            return self.coordinator.data.uv_index
        return None


class WeatherPVSolarForecastSensor(SensorEntity):
    """Sensor for PV solar production forecast."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_name = "PilotSuite PV Solar Forecast Today"
        self._attr_unique_id = f"{DOMAIN}_pv_forecast_kwh"
        self._attr_icon = "mdi:solar-power"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> StateType:
        """Return PV production forecast for today."""
        if self.coordinator.data:
            return round(self.coordinator.data.forecast_pv_production_kwh, 2)
        return None


class WeatherPVRecommendationSensor(SensorEntity):
    """Sensor for weather-based PV energy recommendation."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_name = "PilotSuite PV Recommendation"
        self._attr_unique_id = f"{DOMAIN}_pv_recommendation"
        self._attr_icon = "mdi:lightbulb-group"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = [
            "optimal_charging",    # Great conditions for EV/home charging
            "moderate_usage",     # Normal conditions
            "grid_recommended",   # Poor PV conditions, grid recommended
            "export_surplus",     # Excess PV, export recommended
        ]

    @property
    def native_value(self) -> StateType:
        """Return current PV recommendation."""
        if self.coordinator.data:
            return self.coordinator.data.recommendation
        return None


class WeatherPVSurplusSensor(SensorEntity):
    """Sensor for expected PV surplus (after home consumption)."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_name = "PilotSuite PV Surplus Expected"
        self._attr_unique_id = f"{DOMAIN}_pv_surplus_kwh"
        self._attr_icon = "mdi:transmission-tower-export"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> StateType:
        """Return expected PV surplus after home consumption."""
        # This would be calculated from forecast + consumption data
        if self.coordinator.data:
            forecast = self.coordinator.data.forecast_pv_production_kwh
            # Placeholder: assume 60% self-consumption
            surplus = forecast * 0.4
            return round(surplus, 2)
        return None
