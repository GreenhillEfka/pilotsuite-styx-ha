"""Energy sensor for AI Home CoPilot Neurons.

Sensor:
- EnergyProxySensor: Energy usage proxy
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class EnergyProxySensor(CoordinatorEntity, SensorEntity):
    """Sensor for energy usage proxy."""
    
    _attr_name = "AI CoPilot Energy Proxy"
    _attr_unique_id = "ai_copilot_energy_proxy"
    _attr_icon = "mdi:lightning-bolt"
    _attr_native_unit_of_measurement = "W"
    _attr_should_poll = True
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator, hass: HomeAssistant) -> None:
        super().__init__(coordinator)
        self._hass = hass
    
    async def async_update(self) -> None:
        """Calculate energy proxy from sensors."""
        # Get power sensors
        power_sensors = [
            s for s in self._hass.states.async_all("sensor")
            if s.attributes.get("device_class") == "power"
        ]
        
        total_power = 0
        for sensor in power_sensors:
            try:
                val = float(sensor.state)
                if val > 0:
                    total_power += val
            except (ValueError, TypeError):
                pass
        
        # Count high-power devices
        light_states = self._hass.states.async_all("light")
        lights_on = sum(1 for l in light_states if l.state == "on")
        
        switch_states = self._hass.states.async_all("switch")
        switches_on = sum(1 for s in switch_states if s.state == "on")
        
        # Classify
        if total_power < 100:
            usage = "low"
        elif total_power < 500:
            usage = "moderate"
        elif total_power < 1500:
            usage = "high"
        else:
            usage = "very_high"
        
        self._attr_native_value = usage
        self._attr_extra_state_attributes = {
            "total_power_w": round(total_power, 1),
            "lights_on": lights_on,
            "switches_on": switches_on,
        }
