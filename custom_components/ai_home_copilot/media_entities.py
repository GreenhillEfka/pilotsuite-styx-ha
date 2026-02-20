"""
Media Entities v1 - DEPRECATED
==============================
This module is DEPRECATED. Please use media_context_v2_entities instead.

Migration notes:
- v2 provides enhanced entity definitions
- This module will be removed in a future release
"""

from __future__ import annotations

import warnings

# Issue deprecation warning
warnings.warn(
    "media_entities is DEPRECATED. Use media_context_v2_entities instead. "
    "This module will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2
)

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .media_context import MediaContextCoordinator


class _MediaBase(CoordinatorEntity[MediaContextCoordinator]):
    _attr_has_entity_name = False

    def __init__(self, coordinator: MediaContextCoordinator, *, unique_id: str, name: str, icon: str | None = None):
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_name = name
        if icon:
            self._attr_icon = icon


class MusicActiveBinarySensor(_MediaBase, BinarySensorEntity):
    def __init__(self, coordinator: MediaContextCoordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_music_active",
            name="PilotSuite music active",
            icon="mdi:music",
        )

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.music_active if self.coordinator.data else None


class TvActiveBinarySensor(_MediaBase, BinarySensorEntity):
    def __init__(self, coordinator: MediaContextCoordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_tv_active",
            name="PilotSuite TV active",
            icon="mdi:television",
        )

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.tv_active if self.coordinator.data else None


class MusicNowPlayingSensor(_MediaBase, SensorEntity):
    def __init__(self, coordinator: MediaContextCoordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_music_now_playing",
            name="PilotSuite music now playing",
            icon="mdi:music-note",
        )

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.music_now_playing if self.coordinator.data else None


class MusicPrimaryAreaSensor(_MediaBase, SensorEntity):
    def __init__(self, coordinator: MediaContextCoordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_music_primary_area",
            name="PilotSuite music primary area",
            icon="mdi:map-marker",
        )

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.music_primary_area if self.coordinator.data else None


class TvPrimaryAreaSensor(_MediaBase, SensorEntity):
    def __init__(self, coordinator: MediaContextCoordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_tv_primary_area",
            name="PilotSuite TV primary area",
            icon="mdi:map-marker",
        )

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.tv_primary_area if self.coordinator.data else None


class TvSourceSensor(_MediaBase, SensorEntity):
    def __init__(self, coordinator: MediaContextCoordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_tv_source",
            name="PilotSuite TV source",
            icon="mdi:video-input-hdmi",
        )

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.tv_source if self.coordinator.data else None


class MusicActiveCountSensor(_MediaBase, SensorEntity):
    def __init__(self, coordinator: MediaContextCoordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_music_active_count",
            name="PilotSuite music active count",
            icon="mdi:counter",
        )

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.music_active_count if self.coordinator.data else None


class TvActiveCountSensor(_MediaBase, SensorEntity):
    def __init__(self, coordinator: MediaContextCoordinator):
        super().__init__(
            coordinator,
            unique_id="ai_home_copilot_tv_active_count",
            name="PilotSuite TV active count",
            icon="mdi:counter",
        )

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.tv_active_count if self.coordinator.data else None
