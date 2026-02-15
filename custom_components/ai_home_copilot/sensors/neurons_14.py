"""Neuron sensors for AI Home CoPilot - 14 Neurons from Original Plan.

This module is a lazy-loading facade that imports sensor classes from
individual modules for better code organization and maintainability.

Implements the missing neurons:
- presence.room, presence.person
- activity.level, activity.stillness
- time.of_day, day.type, routine.stability
- light.level, noise.level, weather.context
- calendar.load, attention.load, stress.proxy
- energy.proxy, media.activity, media.intensity
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

# Lazy imports - import from split modules
from .presence_sensors import PresenceRoomSensor, PresencePersonSensor
from .activity_sensors import ActivityLevelSensor, ActivityStillnessSensor
from .time_sensors import TimeOfDaySensor, DayTypeSensor, RoutineStabilitySensor
from .environment_sensors import LightLevelSensor, NoiseLevelSensor, WeatherContextSensor
from .calendar_sensors import CalendarLoadSensor
from .cognitive_sensors import AttentionLoadSensor, StressProxySensor
from .energy_sensors import EnergyProxySensor
from .media_sensors import MediaActivitySensor, MediaIntensitySensor

_LOGGER = logging.getLogger(__name__)

# Re-export all sensor classes
__all__ = [
    # Presence
    "PresenceRoomSensor",
    "PresencePersonSensor",
    # Activity
    "ActivityLevelSensor",
    "ActivityStillnessSensor",
    # Time
    "TimeOfDaySensor",
    "DayTypeSensor",
    "RoutineStabilitySensor",
    # Environment
    "LightLevelSensor",
    "NoiseLevelSensor",
    "WeatherContextSensor",
    # Calendar
    "CalendarLoadSensor",
    # Cognitive
    "AttentionLoadSensor",
    "StressProxySensor",
    # Energy
    "EnergyProxySensor",
    # Media
    "MediaActivitySensor",
    "MediaIntensitySensor",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the 14 neuron sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    entities = [
        PresenceRoomSensor(coordinator, hass),
        PresencePersonSensor(coordinator, hass),
        ActivityLevelSensor(coordinator, hass),
        ActivityStillnessSensor(coordinator, hass),
        TimeOfDaySensor(coordinator),
        DayTypeSensor(coordinator, hass),
        RoutineStabilitySensor(coordinator, hass),
        LightLevelSensor(coordinator, hass),
        NoiseLevelSensor(coordinator, hass),
        WeatherContextSensor(coordinator, hass),
        CalendarLoadSensor(coordinator, hass),
        AttentionLoadSensor(coordinator, hass),
        StressProxySensor(coordinator, hass),
        EnergyProxySensor(coordinator, hass),
        MediaActivitySensor(coordinator, hass),
        MediaIntensitySensor(coordinator, hass),
    ]
    
    async_add_entities(entities)
    
    _LOGGER.info("Created %d neuron sensors", len(entities))


# Import HomeAssistant type for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
