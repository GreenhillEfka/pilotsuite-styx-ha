"""Habitus Zones v2 Entities für Home Assistant."""

from __future__ import annotations

import json
from typing import Any

import yaml

from homeassistant.components.button import ButtonEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.text import TextEntity
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .entity import CopilotBaseEntity
from .habitus_zones_store_v2 import (
    HabitusZoneV2,
    SIGNAL_HABITUS_ZONES_V2_UPDATED,
    SIGNAL_HABITUS_ZONE_STATE_CHANGED,
    async_get_zones_v2,
    async_set_zones_v2_from_raw,
    async_set_zone_state,
    async_persist_all_zone_states,
)


class HabitusZonesV2JsonText(CopilotBaseEntity, TextEntity):
    """Bulk editor for Zones v2 - YAML/JSON."""

    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = False
    _attr_name = "PilotSuite habitus zones v2 (bulk editor)"
    _attr_unique_id = "ai_home_copilot_habitus_zones_v2_json"
    _attr_icon = "mdi:layers-outline"
    _attr_mode = "text"  # multiline
    _attr_native_max = 65535

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._value: str = "[]"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self._reload_value()

    async def _reload_value(self) -> None:
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        raw = []
        for z in zones:
            item = {
                "id": z.zone_id,
                "name": z.name,
                "zone_type": z.zone_type,
                "entity_ids": list(z.entity_ids),
            }
            if isinstance(z.entities, dict) and z.entities:
                item["entities"] = {k: list(v) for k, v in z.entities.items()}
            if z.parent_zone_id:
                item["parent"] = z.parent_zone_id
            if z.child_zone_ids:
                item["child_zones"] = list(z.child_zone_ids)
            if z.floor:
                item["floor"] = z.floor
            if z.current_state != "idle":
                item["current_state"] = z.current_state
            if z.priority:
                item["priority"] = z.priority
            if z.tags:
                item["tags"] = list(z.tags)
            if z.metadata:
                item["metadata"] = z.metadata
            raw.append(item)

        # Prefer YAML for multiline editing
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
            except Exception:
                # Also accept YAML
                raw = yaml.safe_load(value)

            zones = await async_set_zones_v2_from_raw(self.hass, self._entry.entry_id, raw)
        except Exception as err:
            persistent_notification.async_create(
                self.hass,
                f"Invalid Habitus zones v2 YAML/JSON: {err}",
                title="PilotSuite Habitus zones v2",
                notification_id="ai_home_copilot_habitus_zones_v2",
            )
            return

        persistent_notification.async_create(
            self.hass,
            f"Saved {len(zones)} Habitus zones v2.",
            title="PilotSuite Habitus zones v2",
            notification_id="ai_home_copilot_habitus_zones_v2",
        )
        await self._reload_value()


class HabitusZonesV2CountSensor(CopilotBaseEntity, SensorEntity):
    """Count of configured zones v2."""

    _attr_has_entity_name = False
    _attr_name = "PilotSuite habitus zones v2 count"
    _attr_unique_id = "ai_home_copilot_habitus_zones_v2_count"
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._count: int = 0
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = async_dispatcher_connect(
            self.hass, SIGNAL_HABITUS_ZONES_V2_UPDATED, self._on_update
        )
        await self._refresh()

    async def async_will_remove_from_hass(self) -> None:
        if callable(self._unsub):
            self._unsub()
        self._unsub = None
        await super().async_will_remove_from_hass()

    async def _refresh(self) -> None:
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
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


class HabitusZonesV2ValidateButton(CopilotBaseEntity, ButtonEntity):
    """Validate zones v2 configuration."""

    _attr_has_entity_name = False
    _attr_name = "PilotSuite validate habitus zones v2"
    _attr_unique_id = "ai_home_copilot_validate_habitus_zones_v2"
    _attr_icon = "mdi:check-decagram"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)

        missing: list[str] = []
        total = 0

        # Requirement checks
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

        msg = [f"Zones v2: {len(zones)}", f"Entities referenced: {total}"]

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
            title="PilotSuite Habitus zones v2 validation",
            notification_id="habitus_zones_v2_validation",
        )


class HabitusZonesV2StatesSensor(CopilotBaseEntity, SensorEntity):
    """Aggregated zone states - v2 new entity."""

    _attr_has_entity_name = False
    _attr_name = "PilotSuite habitus zones v2 states"
    _attr_unique_id = "ai_home_copilot_habitus_zones_v2_states"
    _attr_icon = "mdi:state-machine"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = async_dispatcher_connect(
            self.hass, SIGNAL_HABITUS_ZONES_V2_UPDATED, self._on_update
        )
        await self._refresh()

    async def async_will_remove_from_hass(self) -> None:
        if callable(self._unsub):
            self._unsub()
        self._unsub = None
        await super().async_will_remove_from_hass()

    async def _refresh(self) -> None:
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)

        states = {"idle": 0, "active": 0, "transitioning": 0, "disabled": 0, "error": 0}
        for z in zones:
            state = z.current_state
            states[state] = states.get(state, 0) + 1

        # State = most common active state
        active_states = {k: v for k, v in states.items() if k in ("active", "transitioning")}
        most_common = max(active_states, key=active_states.get) if active_states else "idle"

        self._attr_native_value = most_common
        self._attr_extra_state_attributes = {
            "zones_total": len(zones),
            "zones_by_state": states,
            "active_zones": [z.name for z in zones if z.current_state == "active"],
            "error_zones": [z.name for z in zones if z.current_state == "error"],
        }
        self.async_write_ha_state()

    def _on_update(self, entry_id: str) -> None:
        if entry_id != self._entry.entry_id:
            return

        def _run() -> None:
            self.hass.async_create_task(self._refresh())

        self.hass.loop.call_soon_threadsafe(_run)


class HabitusZonesV2HealthSensor(CopilotBaseEntity, SensorEntity):
    """Health status for zones v2."""

    _attr_has_entity_name = False
    _attr_name = "PilotSuite habitus zones v2 health"
    _attr_unique_id = "ai_home_copilot_habitus_zones_v2_health"
    _attr_icon = "mdi:heart-pulse"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = async_dispatcher_connect(
            self.hass, SIGNAL_HABITUS_ZONES_V2_UPDATED, self._on_update
        )
        await self._refresh()

    async def async_will_remove_from_hass(self) -> None:
        if callable(self._unsub):
            self._unsub()
        self._unsub = None
        await super().async_will_remove_from_hass()

    async def _refresh(self) -> None:
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        
        total = len(zones)
        error_count = sum(1 for z in zones if z.current_state == "error")
        disabled_count = sum(1 for z in zones if z.current_state == "disabled")
        
        if total == 0:
            health = "unknown"
        elif error_count > 0:
            health = "critical"
        elif disabled_count > total / 2:
            health = "degraded"
        else:
            health = "healthy"

        self._attr_native_value = health
        self._attr_extra_state_attributes = {
            "total_zones": total,
            "error_count": error_count,
            "disabled_count": disabled_count,
            "healthy_count": total - error_count - disabled_count,
        }
        self.async_write_ha_state()

    def _on_update(self, entry_id: str) -> None:
        if entry_id != self._entry.entry_id:
            return

        def _run() -> None:
            self.hass.async_create_task(self._refresh())

        self.hass.loop.call_soon_threadsafe(_run)


class HabitusZonesV2GlobalStateSelect(CopilotBaseEntity, SelectEntity):
    """Global zone mode - v2 new entity."""

    _attr_has_entity_name = False
    _attr_name = "PilotSuite zones v2 global state"
    _attr_unique_id = "ai_home_copilot_habitus_zones_v2_global_state"
    _attr_icon = "mdi:cog-transfer"
    _attr_options = ["auto", "manual", "disabled"]
    _attr_current_option = "auto"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_select_option(self, option: str) -> None:
        """Set global state for all zones."""
        self._attr_current_option = option
        
        # Get all zones and update their state
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        
        if option == "disabled":
            target_state = "disabled"
        elif option == "manual":
            target_state = "idle"  # Keep idle, manual control
        else:  # auto
            target_state = "idle"
        
        # Update each zone's state using the persistence API
        for zone in zones:
            await async_set_zone_state(
                self.hass,
                self._entry.entry_id,
                zone.zone_id,
                target_state,
                fire_event=True
            )
        
        self.async_write_ha_state()


class HabitusZonesV2SyncGraphButton(CopilotBaseEntity, ButtonEntity):
    """Sync zones to Brain Graph - v2 new entity."""

    _attr_has_entity_name = False
    _attr_name = "PilotSuite sync zones v2 to brain graph"
    _attr_unique_id = "ai_home_copilot_habitus_zones_v2_sync_graph"
    _attr_icon = "mdi:graph-outline"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        """Sync all zones to Brain Graph."""
        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        
        # Try to sync via Brain Graph service if available
        results: list[dict] = []
        
        try:
            from .brain_graph_sync import sync_service
            for zone in zones:
                result = await sync_service.sync_zone_to_graph(zone)
                results.append({
                    "zone_id": zone.zone_id,
                    "success": result.success,
                    "nodes_created": result.nodes_created,
                    "edges_created": result.edges_created,
                })
        except ImportError:
            # Brain Graph service not available
            results = [{"error": "brain_graph_sync not available", "zones": len(zones)}]
        except Exception as e:
            results = [{"error": str(e), "zones": len(zones)}]

        success_count = sum(1 for r in results if r.get("success"))
        
        persistent_notification.async_create(
            self.hass,
            f"Brain Graph Sync:\n- Zones processed: {len(zones)}\n- Success: {success_count}\n- Failed: {len(zones) - success_count}",
            title="PilotSuite Zones v2 → Brain Graph Sync",
            notification_id="habitus_zones_v2_graph_sync",
        )


class HabitusZonesV2ReloadButton(CopilotBaseEntity, ButtonEntity):
    """Reload zones v2 - re-read from storage."""

    _attr_has_entity_name = False
    _attr_name = "PilotSuite reload zones v2"
    _attr_unique_id = "ai_home_copilot_habitus_zones_v2_reload"
    _attr_icon = "mdi:reload"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        """Reload zones from storage."""
        # Trigger re-dispatch to refresh all entities
        from .habitus_zones_store_v2 import SIGNAL_HABITUS_ZONES_V2_UPDATED
        from homeassistant.helpers.dispatcher import async_dispatcher_send
        
        # This will trigger all subscribers to refresh
        async_dispatcher_send(
            self.hass, 
            SIGNAL_HABITUS_ZONES_V2_UPDATED, 
            self._entry.entry_id
        )
        
        persistent_notification.async_create(
            self.hass,
            "Habitus Zones v2 reloaded successfully.",
            title="PilotSuite Zones v2",
            notification_id="habitus_zones_v2_reload",
        )


# Registry for entity creation
ENTITIES_V2 = [
    HabitusZonesV2JsonText,
    HabitusZonesV2CountSensor,
    HabitusZonesV2ValidateButton,
    HabitusZonesV2StatesSensor,
    HabitusZonesV2HealthSensor,
    HabitusZonesV2GlobalStateSelect,
    HabitusZonesV2SyncGraphButton,
    HabitusZonesV2ReloadButton,
]
