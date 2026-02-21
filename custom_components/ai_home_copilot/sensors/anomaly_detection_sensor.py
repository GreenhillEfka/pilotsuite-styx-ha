"""Anomaly Detection v2 Sensor for Home Assistant (v6.2.0)."""

from __future__ import annotations

import logging
from typing import Any

from ..entity import CopilotBaseEntity

logger = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 120  # 2 minutes


class AnomalyDetectionSensor(CopilotBaseEntity):
    """Sensor showing anomaly detection status."""

    _attr_icon = "mdi:alert-decagram-outline"
    _attr_name = "PilotSuite Anomaly Detection"
    _attr_unique_id = "pilotsuite_anomaly_detection"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._anomaly_data: dict[str, Any] = {}

    @property
    def state(self) -> str:
        total = self._anomaly_data.get("total_anomalies", 0)
        critical = self._anomaly_data.get("critical", 0)
        if critical > 0:
            return f"{critical} kritisch"
        if total > 0:
            return f"{total} Anomalien"
        return "Normal"

    @property
    def icon(self) -> str:
        critical = self._anomaly_data.get("critical", 0)
        warning = self._anomaly_data.get("warning", 0)
        if critical > 0:
            return "mdi:alert-octagon"
        if warning > 0:
            return "mdi:alert"
        return "mdi:check-decagram"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        types = self._anomaly_data.get("anomaly_types", {})
        top = self._anomaly_data.get("top_anomalies", [])
        return {
            "total_entities": self._anomaly_data.get("total_entities", 0),
            "total_anomalies": self._anomaly_data.get("total_anomalies", 0),
            "critical": self._anomaly_data.get("critical", 0),
            "warning": self._anomaly_data.get("warning", 0),
            "info": self._anomaly_data.get("info", 0),
            "anomaly_types": types,
            "top_anomalies": top[:5],
        }

    async def async_update(self) -> None:
        data = await self._fetch("/api/v1/hub/anomalies")
        if data:
            self._anomaly_data = data
