"""Anomaly Alert Sensor for PilotSuite.

Shows real-time anomaly detection status from the ML anomaly detector.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class AnomalyAlertSensor(SensorEntity):
    """Sensor showing current anomaly detection status."""
    
    _attr_name = "PilotSuite Anomaly Alert"
    _attr_unique_id = "ai_copilot_anomaly_alert"
    _attr_icon = "mdi:alert-octagon"
    _attr_should_poll = False
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        """Initialize the anomaly alert sensor."""
        super().__init__()
        self.coordinator = coordinator
        self._attr_native_value = "idle"
        self._attr_extra_state_attributes = {}
    
    @property
    def native_value(self) -> str:
        """Return the current alert status."""
        if not self.coordinator.data:
            return "idle"
        
        anomaly_status = self.coordinator.data.get("anomaly_status", {})
        
        if anomaly_status.get("status") == "active":
            summary = anomaly_status.get("summary", {})
            if summary.get("count", 0) > 0:
                return "active"
            return "healthy"
        
        return "idle"
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return anomaly detection details."""
        if not self.coordinator.data:
            return {}
        
        anomaly_status = self.coordinator.data.get("anomaly_status", {})
        
        return {
            "status": anomaly_status.get("status", "unknown"),
            "features": anomaly_status.get("features", []),
            "last_anomaly": anomaly_status.get("summary", {}).get("last_anomaly"),
            "peak_score": anomaly_status.get("summary", {}).get("peak_score", 0),
            "anomaly_count": anomaly_status.get("summary", {}).get("count", 0),
        }
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class AlertHistorySensor(SensorEntity):
    """Sensor showing recent alert history."""
    
    _attr_name = "PilotSuite Alert History"
    _attr_unique_id = "ai_copilot_alert_history"
    _attr_icon = "mdi:history"
    _attr_should_poll = False
    
    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        """Initialize the alert history sensor."""
        super().__init__()
        self.coordinator = coordinator
        self._attr_native_value = "0"
        self._attr_extra_state_attributes = {}
    
    @property
    def native_value(self) -> str:
        """Return the count of recent alerts."""
        if not self.coordinator.data:
            return "0"
        
        alert_history = self.coordinator.data.get("alert_history", [])
        return str(len(alert_history))
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return recent alert history."""
        if not self.coordinator.data:
            return {}
        
        alert_history = self.coordinator.data.get("alert_history", [])
        
        return {
            "alerts": [
                {
                    "timestamp": a.get("timestamp", 0),
                    "score": a.get("score", 0),
                    "is_anomaly": a.get("is_anomaly", False),
                    "device_id": a.get("device_id", ""),
                }
                for a in alert_history[-50:]  # Last 50 alerts
            ],
            "count": len(alert_history),
            "recent_anomalies": sum(1 for a in alert_history[-50:] if a.get("is_anomaly", False)),
        }
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up anomaly alert sensors from a config entry."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("coordinator")
    if coordinator is None:
        return
    
    sensors = [
        AnomalyAlertSensor(coordinator),
        AlertHistorySensor(coordinator),
    ]
    
    async_add_entities(sensors)
    
    _LOGGER.info("Anomaly alert sensors set up for entry %s", entry.entry_id)
