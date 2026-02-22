from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data.get("coordinator")
    if coordinator is None:
        _LOGGER.error("Coordinator not available for %s, skipping binary_sensor setup", entry.entry_id)
        return

    if not is_full_entity_profile(entry):
        async_add_entities([CopilotOnlineBinarySensor(coordinator)], True)
        return

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

    # Camera Context Binary Sensors (Habitus Camera Integration)
    # Auto-discover cameras from HA and create entities
    camera_entities = await _discover_camera_entities(hass)
    for cam_id, cam_name in camera_entities:
        entities.append(MotionDetectionCamera(coordinator, entry, cam_id, cam_name))
        entities.append(PresenceCamera(coordinator, entry, cam_id, cam_name))

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
