from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .entity import CopilotBaseEntity


def _entry_data(hass, entry_id: str) -> dict[str, Any]:
    d = hass.data.get(DOMAIN, {}).get(entry_id)
    return d if isinstance(d, dict) else {}


class _ForwarderQualityBase(CopilotBaseEntity):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def _data(self) -> dict[str, Any]:
        return _entry_data(self.coordinator.hass, self._entry.entry_id)


class EventsForwarderQueueDepthSensor(_ForwarderQualityBase, SensorEntity):
    _attr_name = "Events Forwarder Queue Depth"
    _attr_icon = "mdi:tray"
    _attr_native_unit_of_measurement = "events"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_events_forwarder_queue_depth"

    @property
    def native_value(self) -> int | None:
        if self._data.get("events_forwarder_state") is None:
            return None
        return int(self._data.get("events_forwarder_queue_len") or 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        d = self._data
        if d.get("events_forwarder_state") is None:
            return None
        last = d.get("events_forwarder_last")
        if not isinstance(last, dict):
            last = None
        return {
            "persistent_enabled": bool(d.get("events_forwarder_persistent_enabled")),
            "last_status": (last or {}).get("status"),
            "last_time": (last or {}).get("time"),
            "last_success_at": d.get("events_forwarder_last_success_at"),
            "last_error_at": d.get("events_forwarder_last_error_at"),
        }


class EventsForwarderDroppedTotalSensor(_ForwarderQualityBase, SensorEntity):
    _attr_name = "Events Forwarder Dropped Total"
    _attr_icon = "mdi:delete-alert"
    _attr_native_unit_of_measurement = "events"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_events_forwarder_dropped_total"

    @property
    def native_value(self) -> int | None:
        if self._data.get("events_forwarder_state") is None:
            return None
        return int(self._data.get("events_forwarder_dropped_total") or 0)


class EventsForwarderErrorStreakSensor(_ForwarderQualityBase, SensorEntity):
    _attr_name = "Events Forwarder Error Streak"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_events_forwarder_error_streak"

    @property
    def native_value(self) -> int | None:
        if self._data.get("events_forwarder_state") is None:
            return None
        return int(self._data.get("events_forwarder_error_streak") or 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        d = self._data
        if d.get("events_forwarder_state") is None:
            return None
        return {
            "error_total": int(d.get("events_forwarder_error_total") or 0),
            "sent_total": int(d.get("events_forwarder_sent_total") or 0),
            "health": d.get("events_forwarder_health"),
        }


class EventsForwarderConnectedBinarySensor(_ForwarderQualityBase, BinarySensorEntity):
    _attr_name = "Events Forwarder Connected"
    _attr_icon = "mdi:lan-connect"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_events_forwarder_connected"

    @property
    def is_on(self) -> bool | None:
        d = self._data
        if d.get("events_forwarder_state") is None:
            return None

        last_success_ts = d.get("events_forwarder_last_success_ts")
        try:
            last_success_ts_f = float(last_success_ts) if last_success_ts is not None else None
        except (TypeError, ValueError):
            last_success_ts_f = None

        # Spec-aligned: connected when the last successful delivery is recent.
        if last_success_ts_f is not None:
            import time as _time

            return (_time.time() - last_success_ts_f) < 900  # 15 minutes

        # If no sends yet, fall back to core online status.
        if self.coordinator.data is None:
            return None
        return bool(getattr(self.coordinator.data, "ok", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        d = self._data
        if d.get("events_forwarder_state") is None:
            return None
        last = d.get("events_forwarder_last")
        if not isinstance(last, dict):
            last = None
        return {
            "queue_len": int(d.get("events_forwarder_queue_len") or 0),
            "dropped_total": int(d.get("events_forwarder_dropped_total") or 0),
            "error_streak": int(d.get("events_forwarder_error_streak") or 0),
            "last_status": (last or {}).get("status"),
            "last_time": (last or {}).get("time"),
        }
