from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_CONTEXT_ENTITIES_REFRESH

_LOGGER = logging.getLogger(__name__)
from .entity import CopilotBaseEntity
from .entity_profile import is_full_entity_profile
from .media_entities import MusicActiveBinarySensor, TvActiveBinarySensor
from .forwarder_quality_entities import EventsForwarderConnectedBinarySensor
from .mesh_monitoring import ZWaveMeshStatusBinarySensor, ZigbeeMeshStatusBinarySensor
from .camera_entities import (
    MotionDetectionCamera,
    PresenceCamera,
)
from .unifi_context_entities import build_unifi_binary_entities


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator") if isinstance(data, dict) else None
    if coordinator is None:
        _LOGGER.error("Coordinator not available for %s, skipping binary_sensor setup", entry.entry_id)
        return

    if not is_full_entity_profile(entry):
        async_add_entities([CopilotOnlineBinarySensor(coordinator)], True)
        return

    dynamic_context_unique_ids: set[str] = set()

    def _collect_dynamic_context_binaries() -> list[BinarySensorEntity]:
        entities_out: list[BinarySensorEntity] = []
        unifi_coordinator = data.get("unifi_context_coordinator") if isinstance(data, dict) else None
        if unifi_coordinator is None:
            return entities_out
        try:
            for entity in build_unifi_binary_entities(unifi_coordinator):
                unique_id = str(getattr(entity, "unique_id", "") or "")
                if unique_id and unique_id in dynamic_context_unique_ids:
                    continue
                if unique_id:
                    dynamic_context_unique_ids.add(unique_id)
                entities_out.append(entity)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Failed to create UniFi context binary entities")
        return entities_out

    entities = [CopilotOnlineBinarySensor(coordinator)]

    # Events Forwarder quality binary sensor (v0.1 kernel)
    if isinstance(data, dict) and data.get("events_forwarder_state") is not None:
        entities.append(EventsForwarderConnectedBinarySensor(coordinator, entry))

    media_coordinator = data.get("media_coordinator") if isinstance(data, dict) else None
    if media_coordinator is not None:
        entities.extend(
            [
                MusicActiveBinarySensor(media_coordinator),
                TvActiveBinarySensor(media_coordinator),
            ]
        )
    
    # Media Context v2 doesn't have binary sensor entities currently

    # Mesh Monitoring Binary Sensors (Z-Wave / Zigbee)
    entities.extend([
        ZWaveMeshStatusBinarySensor(hass, entry),
        ZigbeeMeshStatusBinarySensor(hass, entry),
    ])

    # UniFi context binary sensors
    entities.extend(_collect_dynamic_context_binaries())

    # Camera Context Binary Sensors (Habitus Camera Integration)
    # Auto-discover cameras from HA and create entities
    camera_entities = await _discover_camera_entities(hass)
    for cam_id, cam_name in camera_entities:
        entities.append(MotionDetectionCamera(coordinator, entry, cam_id, cam_name))
        entities.append(PresenceCamera(coordinator, entry, cam_id, cam_name))

    @callback
    def _async_handle_context_refresh(updated_entry_id: str) -> None:
        if str(updated_entry_id) != entry.entry_id:
            return
        new_entities = _collect_dynamic_context_binaries()
        if new_entities:
            async_add_entities(new_entities, True)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            SIGNAL_CONTEXT_ENTITIES_REFRESH,
            _async_handle_context_refresh,
        )
    )

    async_add_entities(entities, True)


async def _discover_camera_entities(hass: HomeAssistant) -> list[tuple[str, str]]:
    """Discover camera entities from Home Assistant."""
    from homeassistant.helpers import entity_registry
    er = entity_registry.async_get(hass)
    cameras = []
    
    for entity_id, entry in er.entities.items():
        if entry.domain == "camera":
            camera_name = entry.name or entry.original_name or entity_id.split(".")[-1]
            cameras.append((entity_id, camera_name))
    
    return cameras


class CopilotOnlineBinarySensor(CopilotBaseEntity, BinarySensorEntity):
    _attr_name = "Online"
    _attr_unique_id = "ai_home_copilot_online"
    _attr_icon = "mdi:robot"

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        if isinstance(self.coordinator.data, dict):
            ok = self.coordinator.data.get("ok")
            if ok is None:
                return None
            return bool(ok)
        # Defensive fallback for unexpected coordinator payload types.
        return bool(getattr(self.coordinator.data, "ok", False))
