from __future__ import annotations

import json
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.text import TextEntity
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .entity import CopilotBaseEntity
from .habitus_zones_store import (
    HabitusZone,
    SIGNAL_HABITUS_ZONES_UPDATED,
    async_get_zones,
    async_set_zones_from_raw,
)


class HabitusZonesJsonText(CopilotBaseEntity, TextEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot habitus zones (json)"
    _attr_unique_id = "ai_home_copilot_habitus_zones_json"
    _attr_icon = "mdi:layers-outline"
    _attr_mode = "text"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._value: str = "[]"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._reload_value()

    async def _reload_value(self) -> None:
        zones = await async_get_zones(self.hass, self._entry.entry_id)
        raw = [
            {"id": z.zone_id, "name": z.name, "entity_ids": z.entity_ids} for z in zones
        ]
        self._value = json.dumps(raw, ensure_ascii=False, indent=2)
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        return self._value

    async def async_set_value(self, value: str) -> None:
        value = (value or "").strip()
        if not value:
            value = "[]"

        try:
            raw = json.loads(value)
            zones = await async_set_zones_from_raw(self.hass, self._entry.entry_id, raw)
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Invalid Habitus zones JSON: {err}",
                title="AI Home CoPilot Habitus zones",
                notification_id="ai_home_copilot_habitus_zones",
            )
            return

        persistent_notification.async_create(
            self.hass,
            f"Saved {len(zones)} Habitus zones.",
            title="AI Home CoPilot Habitus zones",
            notification_id="ai_home_copilot_habitus_zones",
        )
        await self._reload_value()


class HabitusZonesCountSensor(CopilotBaseEntity, SensorEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot habitus zones count"
    _attr_unique_id = "ai_home_copilot_habitus_zones_count"
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._count: int = 0
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = async_dispatcher_connect(
            self.hass, SIGNAL_HABITUS_ZONES_UPDATED, self._on_update
        )
        await self._refresh()

    async def async_will_remove_from_hass(self) -> None:
        if callable(self._unsub):
            self._unsub()
        self._unsub = None
        await super().async_will_remove_from_hass()

    async def _refresh(self) -> None:
        zones = await async_get_zones(self.hass, self._entry.entry_id)
        self._count = len(zones)
        self.async_write_ha_state()

    def _on_update(self, entry_id: str) -> None:
        if entry_id != self._entry.entry_id:
            return
        self.hass.async_create_task(self._refresh())

    @property
    def native_value(self) -> int | None:
        return self._count


class HabitusZonesValidateButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot validate habitus zones"
    _attr_unique_id = "ai_home_copilot_validate_habitus_zones"
    _attr_icon = "mdi:check-decagram"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        zones = await async_get_zones(self.hass, self._entry.entry_id)

        missing: list[str] = []
        total = 0
        for z in zones:
            for eid in z.entity_ids:
                total += 1
                if self.hass.states.get(eid) is None:
                    missing.append(f"{z.zone_id}: {eid}")

        msg = [f"Zones: {len(zones)}", f"Entities referenced: {total}"]
        if missing:
            msg.append("")
            msg.append(f"Missing entities: {len(missing)}")
            msg.extend(f"- {m}" for m in missing[:50])
            if len(missing) > 50:
                msg.append("- … (truncated)")
        else:
            msg.append("All referenced entities exist (by current state lookup).")

        persistent_notification.async_create(
            self.hass,
            "\n".join(msg),
            title="AI Home CoPilot Habitus zones validation",
            notification_id="ai_home_copilot_habitus_zones_validation",
        )
