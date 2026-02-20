from __future__ import annotations

import os

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfInformation
from homeassistant.helpers.entity import EntityCategory

from .entity import CopilotBaseEntity


class SystemHealthEntityCountSensor(CopilotBaseEntity, SensorEntity):
    _attr_has_entity_name = False
    _attr_name = "PilotSuite entities (total)"
    _attr_unique_id = "ai_home_copilot_systemhealth_entities_total"
    _attr_icon = "mdi:counter"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int:
        return len(self.hass.states.async_all())


class SystemHealthSqliteDbSizeSensor(CopilotBaseEntity, SensorEntity):
    _attr_has_entity_name = False
    _attr_name = "PilotSuite recorder db size (sqlite)"
    _attr_unique_id = "ai_home_copilot_systemhealth_sqlite_db_size"
    _attr_icon = "mdi:database"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = UnitOfInformation.BYTES
    _attr_device_class = "data_size"

    @property
    def native_value(self) -> int | None:
        # Default HA path; if absent, assume external DB.
        path = self.hass.config.path("home-assistant_v2.db")
        if not os.path.exists(path):
            return None
        try:
            return int(os.stat(path).st_size)
        except OSError:
            return None
