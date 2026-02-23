"""Weather context entities for PilotSuite."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .weather_context import WeatherContextCoordinator


class _WeatherSensorBase(CoordinatorEntity[WeatherContextCoordinator], SensorEntity):
    """Base class for weather coordinator-backed sensors."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: WeatherContextCoordinator, key: str, name: str, icon: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_name = name
        self._attr_icon = icon


class WeatherConditionSensor(_WeatherSensorBase):
    """Current weather condition."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="weather_condition",
            name="PilotSuite Weather Condition",
            icon="mdi:weather-partly-cloudy",
        )
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
            "unknown",
        ]

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data:
            return self.coordinator.data.condition
        return "unknown"


class WeatherTemperatureSensor(_WeatherSensorBase):
    """Current temperature."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="weather_temperature",
            name="PilotSuite Weather Temperature",
            icon="mdi:thermometer",
        )
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = "°C"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data:
            return self.coordinator.data.temperature_c
        return None


class WeatherCloudCoverSensor(_WeatherSensorBase):
    """Current cloud cover."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="weather_cloud_cover",
            name="PilotSuite Weather Cloud Cover",
            icon="mdi:weather-cloudy",
        )
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data:
            return self.coordinator.data.cloud_cover_percent
        return None


class WeatherUVIndexSensor(_WeatherSensorBase):
    """Current UV index."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="weather_uv_index",
            name="PilotSuite Weather UV Index",
            icon="mdi:weather-sunny-alert",
        )
        self._attr_native_unit_of_measurement = "UV"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data:
            return self.coordinator.data.uv_index
        return None


class WeatherPVSolarForecastSensor(_WeatherSensorBase):
    """Forecasted PV production (today)."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="pv_forecast_kwh",
            name="PilotSuite PV Solar Forecast Today",
            icon="mdi:solar-power",
        )
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data:
            return round(self.coordinator.data.forecast_pv_production_kwh, 2)
        return None


class WeatherPVRecommendationSensor(_WeatherSensorBase):
    """PV usage recommendation."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="pv_recommendation",
            name="PilotSuite PV Recommendation",
            icon="mdi:lightbulb-group",
        )
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = [
            "optimal_charging",
            "moderate_usage",
            "grid_recommended",
            "export_surplus",
        ]

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data:
            return self.coordinator.data.recommendation
        return "moderate_usage"


class WeatherPVSurplusSensor(_WeatherSensorBase):
    """Expected PV surplus after household baseline usage."""

    def __init__(self, coordinator: WeatherContextCoordinator) -> None:
        super().__init__(
            coordinator,
            key="pv_surplus_kwh",
            name="PilotSuite PV Surplus Expected",
            icon="mdi:transmission-tower-export",
        )
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> StateType:
        if not self.coordinator.data:
            return None
        forecast = self.coordinator.data.forecast_pv_production_kwh
        surplus = forecast * 0.4
        return round(surplus, 2)


def build_weather_entities(coordinator: WeatherContextCoordinator) -> list[SensorEntity]:
    """Build weather sensors backed by a weather coordinator."""
    return [
        WeatherConditionSensor(coordinator),
        WeatherTemperatureSensor(coordinator),
        WeatherCloudCoverSensor(coordinator),
        WeatherUVIndexSensor(coordinator),
        WeatherPVSolarForecastSensor(coordinator),
        WeatherPVRecommendationSensor(coordinator),
        WeatherPVSurplusSensor(coordinator),
    ]
