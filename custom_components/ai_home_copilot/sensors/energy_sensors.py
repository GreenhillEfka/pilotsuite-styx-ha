"""Energy sensor for AI Home CoPilot.

Sensor:
- EnergyProxySensor: Aggregated energy usage proxy with frugality scoring
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class EnergyUsageLevel(str, Enum):
    """Energy usage classification levels."""
    LOW: Final = "low"
    MODERATE: Final = "moderate"
    HIGH: Final = "high"
    VERY_HIGH: Final = "very_high"


# Thresholds in Watts
_POWER_THRESHOLD_LOW: Final = 100
_POWER_THRESHOLD_MODERATE: Final = 500
_POWER_THRESHOLD_HIGH: Final = 1500


@dataclass
class FrugalityScore:
    """Frugality mood factor based on energy consumption.
    
    Attributes:
        score: 0.0-1.0 where 1.0 = most frugal (low consumption)
        level: The usage level classification
        factors: Contributing factors for mood system
    """
    score: float
    level: EnergyUsageLevel
    factors: list[dict[str, Any]]


class EnergyProxySensor(CoordinatorEntity, SensorEntity):
    """Sensor for energy usage proxy with frugality scoring.
    
    Aggregates all power sensors in Home Assistant and calculates:
    - Total current power consumption
    - Number of active devices (lights, switches)
    - Frugality score for mood integration
    """
    
    _attr_name: str = "AI CoPilot Energy Proxy"
    _attr_unique_id: str = "ai_copilot_energy_proxy"
    _attr_icon: str = "mdi:lightning-bolt"
    _attr_native_unit_of_measurement: str = "W"
    _attr_should_poll: bool = True
    
    def __init__(
        self,
        coordinator: CopilotDataUpdateCoordinator,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(coordinator)
        self._hass: Final = hass
        self._frugality_score: FrugalityScore | None = None
    
    @property
    def frugality_score(self) -> FrugalityScore | None:
        """Get the current frugality score for mood integration."""
        return self._frugality_score
    
    @callback
    def _async_update_from_coordinator(self) -> None:
        """Update sensor state from coordinator data."""
        self._update_energy_data()
    
    async def async_update(self) -> None:
        """Calculate energy proxy from sensors."""
        self._update_energy_data()
    
    def _update_energy_data(self) -> None:
        """Calculate energy metrics from all power sensors."""
        # Get power sensors with device_class="power"
        power_sensors = [
            s for s in self._hass.states.async_all("sensor")
            if s.attributes.get("device_class") == "power"
        ]
        
        # Calculate total power consumption
        total_power: float = 0.0
        power_entities: list[dict[str, Any]] = []
        
        for sensor in power_sensors:
            try:
                value: float = float(sensor.state)
                if value > 0:
                    total_power += value
                    power_entities.append({
                        "entity_id": sensor.entity_id,
                        "power_w": value,
                    })
            except (ValueError, TypeError):
                continue
        
        # Count active devices
        light_states = self._hass.states.async_all("light")
        lights_on = sum(1 for l in light_states if l.state == "on")
        
        switch_states = self._hass.states.async_all("switch")
        switches_on = sum(1 for s in switch_states if s.state == "on")
        
        # Classify usage level
        usage_level = self._classify_usage(total_power)
        
        # Calculate frugality score (inverse of consumption)
        frugality_score = self._calculate_frugality(
            total_power=total_power,
            lights_on=lights_on,
            switches_on=switches_on,
        )
        
        # Update sensor state
        self._attr_native_value = usage_level.value
        self._attr_extra_state_attributes = {
            "total_power_w": round(total_power, 1),
            "lights_on": lights_on,
            "switches_on": switches_on,
            "power_entities_count": len(power_entities),
            "power_entities": power_entities[:10],  # Limit for state size
            "frugality_score": frugality_score.score,
            "usage_level": usage_level.value,
        }
        
        self._frugality_score = frugality_score
        
        _LOGGER.debug(
            "Energy updated: %.1fW (level=%s, frugality=%.2f)",
            total_power,
            usage_level.value,
            frugality_score.score,
        )
    
    def _classify_usage(self, total_power: float) -> EnergyUsageLevel:
        """Classify power consumption into usage level."""
        if total_power < _POWER_THRESHOLD_LOW:
            return EnergyUsageLevel.LOW
        elif total_power < _POWER_THRESHOLD_MODERATE:
            return EnergyUsageLevel.MODERATE
        elif total_power < _POWER_THRESHOLD_HIGH:
            return EnergyUsageLevel.HIGH
        else:
            return EnergyUsageLevel.VERY_HIGH
    
    def _calculate_frugality(
        self,
        total_power: float,
        lights_on: int,
        switches_on: int,
    ) -> FrugalityScore:
        """Calculate frugality score (0.0-1.0, higher = more frugal).
        
        Combines:
        - Power consumption (inverse relationship)
        - Active device count
        """
        # Normalize power to 0-1 scale (0 at 2000W, 1 at 0W)
        power_score = max(0.0, 1.0 - (total_power / 2000.0))
        
        # Device count penalty (more devices = less frugal)
        device_count = lights_on + switches_on
        device_score = max(0.0, 1.0 - (device_count / 20.0))
        
        # Weighted combination
        combined_score = (power_score * 0.7) + (device_score * 0.3)
        
        # Classify level
        usage_level = self._classify_usage(total_power)
        
        # Build factors for mood system
        factors: list[dict[str, Any]] = [
            {
                "entity": "sensor.energy_proxy",
                "weight": 0.7,
                "reason": f"power_consumption_{total_power:.0f}w",
                "value": total_power,
            },
            {
                "entity": "sensor.energy_proxy",
                "weight": 0.3,
                "reason": f"active_devices_{device_count}",
                "value": device_count,
            },
        ]
        
        return FrugalityScore(
            score=round(combined_score, 2),
            level=usage_level,
            factors=factors,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry_id: str,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up energy proxy sensor."""
    # This is called from __init__.py - coordinator is managed there
    # The actual entity creation happens via the module system
    pass
