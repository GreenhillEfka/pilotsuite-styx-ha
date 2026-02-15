"""
Habitus Zones Entities v1 - DEPRECATED
=======================================
This module is DEPRECATED. Please use habitus_zones_entities_v2 instead.

Migration notes:
- v2 provides enhanced entity validation and better state management
- This module will be removed in a future release

To migrate:
    # Old (v1):
    from .habitus_zones_entities import HabitusZonesJsonText

    # New (v2):
    from .habitus_zones_entities_v2 import HabitusZonesV2JsonText
"""

from __future__ import annotations

import json
import logging
import warnings
from typing import Any

import yaml

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

_LOGGER = logging.getLogger(__name__)

# Issue deprecation warning
warnings.warn(
    "habitus_zones_entities is DEPRECATED. Use habitus_zones_entities_v2 instead. "
    "This module will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2
)


class HabitusZonesJsonText(CopilotBaseEntity, TextEntity):
    # Advanced / bulk editor; wizard is the primary UX.
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot habitus zones (bulk editor)"
    _attr_unique_id = "ai_home_copilot_habitus_zones_json"
    _attr_icon = "mdi:layers-outline"
    _attr_mode = "text"  # multiline
    # Remove the default 255-char limit.
    _attr_native_max = 65535

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._value: str = "[]"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._reload_value()

    async def _reload_value(self) -> None:
        zones = await async_get_zones(self.hass, self._entry.entry_id)
        raw = []
        for z in zones:
            item = {"id": z.zone_id, "name": z.name, "entity_ids": z.entity_ids}
            if isinstance(getattr(z, "entities", None), dict) and z.entities:
                item["entities"] = z.entities
            raw.append(item)

        # Prefer YAML for multiline/bulk editing.
        self._value = yaml.safe_dump(raw, allow_unicode=True, sort_keys=False)
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        return self._value

    async def async_set_value(self, value: str) -> None:
        value = (value or "").strip()
        if not value:
            value = "[]"

        try:
            try:
                raw = json.loads(value)
            except Exception:  # noqa: BLE001
                # Also accept YAML for better multiline UX.
                raw = yaml.safe_load(value)

            zones = await async_set_zones_from_raw(self.hass, self._entry.entry_id, raw)
        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Invalid Habitus zones YAML/JSON: {err}",
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

        def _run() -> None:
            self.hass.async_create_task(self._refresh())

        self.hass.loop.call_soon_threadsafe(_run)

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

        # Requirement checks (mirrors store policy).
        zones_missing_motion: list[str] = []
        zones_missing_light: list[str] = []

        def domain(eid: str) -> str:
            return eid.split(".", 1)[0] if "." in eid else ""

        def is_light(eid: str) -> bool:
            return domain(eid) == "light"

        def is_motion_or_presence(eid: str) -> bool:
            dom = domain(eid)
            if dom not in ("binary_sensor", "sensor"):
                return False
            st = self.hass.states.get(eid)
            device_class = st.attributes.get("device_class") if st else None
            if device_class in ("motion", "presence", "occupancy"):
                return True
            eid_l = eid.lower()
            return any(k in eid_l for k in ("motion", "presence", "occupancy"))

        for z in zones:
            has_motion = False
            has_light = False
            for eid in z.entity_ids:
                total += 1
                st = self.hass.states.get(eid)
                if st is None:
                    missing.append(f"{z.zone_id}: {eid}")
                    continue
                has_light = has_light or is_light(eid)
                has_motion = has_motion or is_motion_or_presence(eid)

            if not has_motion:
                zones_missing_motion.append(z.zone_id)
            if not has_light:
                zones_missing_light.append(z.zone_id)

        msg = [f"Zones: {len(zones)}", f"Entities referenced: {total}"]

        if zones_missing_motion or zones_missing_light:
            msg.append("")
            msg.append("Requirements (minimum signals):")
            msg.append("- motion/presence: REQUIRED")
            msg.append("- light: REQUIRED")
            if zones_missing_motion:
                msg.append(f"Missing motion/presence in: {', '.join(zones_missing_motion)}")
            if zones_missing_light:
                msg.append(f"Missing light in: {', '.join(zones_missing_light)}")

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
