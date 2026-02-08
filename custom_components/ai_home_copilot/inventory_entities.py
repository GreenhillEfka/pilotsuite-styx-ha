from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util

from .entity import CopilotBaseEntity
from .inventory_store import async_get_inventory_state


class CopilotInventoryLastRunSensor(CopilotBaseEntity, SensorEntity):
    """Diagnostic sensor: timestamp of last inventory generation."""

    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot inventory last run"
    _attr_unique_id = "ai_home_copilot_inventory_last_run"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clipboard-text-clock-outline"

    async def async_update(self) -> None:
        st = await async_get_inventory_state(self.hass)
        if not st.last_generated_at:
            self._attr_native_value = None
            return

        try:
            dt = dt_util.parse_datetime(st.last_generated_at)
            if dt is None:
                dt = datetime.fromisoformat(st.last_generated_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=dt_util.UTC)
            self._attr_native_value = dt
        except Exception:  # noqa: BLE001
            self._attr_native_value = None

    @property
    def available(self) -> bool:
        return True
