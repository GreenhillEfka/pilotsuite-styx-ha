"""Energy Schedule Sensor for PilotSuite (v5.5.0).

Exposes the Smart Schedule Planner's daily device schedule as a HA sensor.
Shows next scheduled device, total daily cost estimate, and PV coverage.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)


class EnergyScheduleSensor(CopilotBaseEntity):
    """Sensor exposing daily energy schedule from Core."""

    _attr_name = "Energy Schedule"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._host}:{self._port}_energy_schedule"
        self._plan_data: dict[str, Any] | None = None

    @property
    def native_value(self) -> str | None:
        """Return next scheduled device as state."""
        if not self._plan_data or not self._plan_data.get("ok"):
            return "unavailable"

        schedules = self._plan_data.get("schedules", [])
        if not schedules:
            return "no devices scheduled"

        now = datetime.now(timezone.utc)
        upcoming = [
            s for s in schedules
            if datetime.fromisoformat(s["start"]) > now
        ]

        if upcoming:
            nxt = min(upcoming, key=lambda s: s["start"])
            return f"{nxt['device_type']} at {nxt['start_hour']}:00"

        return f"{len(schedules)} devices done"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return schedule details."""
        attrs: dict[str, Any] = {
            "schedule_url": (
                f"http://{self._host}:{self._port}"
                "/api/v1/predict/schedule/daily"
            ),
            "next_device_url": (
                f"http://{self._host}:{self._port}"
                "/api/v1/predict/schedule/next"
            ),
        }

        if self._plan_data and self._plan_data.get("ok"):
            attrs["date"] = self._plan_data.get("date")
            attrs["devices_scheduled"] = self._plan_data.get(
                "devices_scheduled", 0
            )
            attrs["unscheduled_devices"] = self._plan_data.get(
                "unscheduled_devices", []
            )
            attrs["total_estimated_cost_eur"] = self._plan_data.get(
                "total_estimated_cost_eur", 0
            )
            attrs["total_pv_coverage_percent"] = self._plan_data.get(
                "total_pv_coverage_percent", 0
            )
            attrs["peak_load_watts"] = self._plan_data.get(
                "peak_load_watts", 0
            )

            # Build per-device schedule list
            schedules = self._plan_data.get("schedules", [])
            attrs["schedule"] = [
                {
                    "device": s["device_type"],
                    "hours": f"{s['start_hour']}:00-{s['end_hour']}:00",
                    "cost_eur": s["estimated_cost_eur"],
                    "pv_pct": s["pv_coverage_percent"],
                }
                for s in schedules
            ]

        return attrs

    async def async_update(self) -> None:
        """Fetch daily schedule from Core API."""
        try:
            session = self.coordinator._session
            if session is None:
                return

            url = (
                f"http://{self._host}:{self._port}"
                "/api/v1/predict/schedule/daily"
            )
            headers = {}
            token = self.coordinator._config.get("token") or self.coordinator._config.get("auth_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
                headers["X-Auth-Token"] = token

            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    self._plan_data = await resp.json()
                else:
                    _LOGGER.debug("Schedule API returned %s", resp.status)
        except Exception as e:
            _LOGGER.debug("Failed to fetch schedule data: %s", e)
