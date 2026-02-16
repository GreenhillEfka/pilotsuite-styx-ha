from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .debug import DebugModeSensor
from .entity import CopilotBaseEntity
from .media_entities import (
    MusicActiveCountSensor,
    MusicNowPlayingSensor,
    MusicPrimaryAreaSensor,
    TvActiveCountSensor,
    TvPrimaryAreaSensor,
    TvSourceSensor,
)
from .media_context_v2_entities import (
    ActiveModeSensor,
    ActiveTargetSensor,
    ActiveZoneSensor,
    ConfigValidationSensor,
    DebugInfoSensor,
)
# DEPRECATED: v1 - prefer v2
# from .habitus_zones_entities import HabitusZonesCountSensor
from .habitus_zones_entities_v2 import (
    HabitusZonesV2CountSensor,
    HabitusZonesV2StatesSensor,
    HabitusZonesV2HealthSensor,
)
# DEPRECATED: v1 - prefer v2
# from .habitus_zones_store import async_get_zones
from .habitus_zones_store_v2 import async_get_zones_v2
from .habitus_zone_aggregates import build_zone_average_sensors
from .core_v1_entities import CoreApiV1StatusSensor
from .systemhealth_entities import SystemHealthEntityCountSensor, SystemHealthSqliteDbSizeSensor
from .mesh_monitoring import (
    ZWaveNetworkHealthSensor,
    ZWaveDevicesOnlineSensor,
    ZWaveBatteryOverviewSensor,
    ZigbeeNetworkHealthSensor,
    ZigbeeDevicesOnlineSensor,
    ZigbeeBatteryOverviewSensor,
)
from .mesh_dashboard import (
    MeshNetworkOverviewSensor,
    ZWaveMeshTopologySensor,
    ZigbeeMeshTopologySensor,
)
from .forwarder_quality_entities import (
    EventsForwarderDroppedTotalSensor,
    EventsForwarderErrorStreakSensor,
    EventsForwarderQueueDepthSensor,
)
from .inventory_entities import CopilotInventoryLastRunSensor
from .habitus_miner_entities import (
    HabitusMinerRuleCountSensor,
    HabitusMinerStatusSensor, 
    HabitusMinerTopRuleSensor,
)
from .pipeline_health_entities import PipelineHealthSensor
from .sensors.mood_sensor import (
    MoodSensor,
    MoodConfidenceSensor,
    NeuronActivitySensor,
)
from .sensors.neuron_dashboard import (
    NeuronDashboardSensor,
    MoodHistorySensor,
    SuggestionSensor,
)
from .sensors.voice_context import (
    VoiceContextSensor,
    VoicePromptSensor,
)
from .sensors.energy_insights import (
    EnergyInsightSensor,
    EnergyRecommendationSensor,
)
from .sensors.habit_learning_v2 import (
    HabitLearningSensor,
    HabitPredictionSensor,
    SequencePredictionSensor,
)
from .sensors.anomaly_alert import (
    AnomalyAlertSensor,
    AlertHistorySensor,
)
from .sensors.predictive_automation import (
    PredictiveAutomationSensor,
    PredictiveAutomationDetailsSensor,
)
from .sensors.inspector_sensor import InspectorSensor
from .sensors.neurons_14 import (
    PresenceRoomSensor,
    PresencePersonSensor,
    ActivityLevelSensor,
    ActivityStillnessSensor,
    TimeOfDaySensor,
    DayTypeSensor,
    RoutineStabilitySensor,
    LightLevelSensor,
    NoiseLevelSensor,
    WeatherContextSensor,
    CalendarLoadSensor,
    AttentionLoadSensor,
    StressProxySensor,
    EnergyProxySensor,
    MediaActivitySensor,
    MediaIntensitySensor,
)
from .mood_dashboard import (
    MoodDashboardEntity,
    MoodHistoryEntity,
    MoodExplanationEntity,
)
from .calendar_context import CalendarContextEntity
from .suggestion_panel import SuggestionQueue
from .camera_entities import (
    CameraMotionHistorySensor,
    CameraPresenceHistorySensor,
    CameraActivityHistorySensor,
    CameraZoneActivitySensor,
    ActivityCamera,
    ZoneCamera,
)

# Mobile Dashboard Cards
from .mobile_dashboard_cards import (
    MobileDashboardSensor,
    MobileQuickActionsSensor,
    MobileEntityGridSensor,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = [
        CopilotVersionSensor(coordinator),
        CoreApiV1StatusSensor(coordinator, entry),
        HabitusZonesCountSensor(coordinator, entry),
        # v2 Sensors
        HabitusZonesV2CountSensor(coordinator, entry),
        HabitusZonesV2StatesSensor(coordinator, entry),
        HabitusZonesV2HealthSensor(coordinator, entry),
        SystemHealthEntityCountSensor(coordinator),
        SystemHealthSqliteDbSizeSensor(coordinator),
        # Mesh Monitoring (Z-Wave / Zigbee)
        ZWaveNetworkHealthSensor(hass, entry),
        ZWaveDevicesOnlineSensor(hass, entry),
        ZWaveBatteryOverviewSensor(hass, entry),
        ZigbeeNetworkHealthSensor(hass, entry),
        ZigbeeDevicesOnlineSensor(hass, entry),
        ZigbeeBatteryOverviewSensor(hass, entry),
        # Mesh Dashboard (Overview & Topology)
        MeshNetworkOverviewSensor(hass, entry),
        ZWaveMeshTopologySensor(hass, entry),
        ZigbeeMeshTopologySensor(hass, entry),
        CopilotInventoryLastRunSensor(coordinator),
        HabitusMinerRuleCountSensor(coordinator),
        HabitusMinerStatusSensor(coordinator),
        HabitusMinerTopRuleSensor(coordinator),
        PipelineHealthSensor(coordinator),
        DebugModeSensor(hass),
        # Mood Sensors (Neural System)
        MoodSensor(coordinator),
        MoodConfidenceSensor(coordinator),
        NeuronActivitySensor(coordinator),
        # Voice Context Sensors (HA Assist)
        VoiceContextSensor(coordinator),
        VoicePromptSensor(coordinator),
        # 14 Neuron Sensors (Original Plan)
        PresenceRoomSensor(coordinator, hass),
        PresencePersonSensor(coordinator, hass),
        ActivityLevelSensor(coordinator, hass),
        ActivityStillnessSensor(coordinator, hass),
        TimeOfDaySensor(coordinator),
        DayTypeSensor(coordinator, hass),
        RoutineStabilitySensor(coordinator, hass),
        LightLevelSensor(coordinator, hass),
        NoiseLevelSensor(coordinator, hass),
        WeatherContextSensor(coordinator, hass),
        CalendarLoadSensor(coordinator, hass),
        AttentionLoadSensor(coordinator, hass),
        StressProxySensor(coordinator, hass),
        EnergyProxySensor(coordinator, hass),
        MediaActivitySensor(coordinator, hass),
        MediaIntensitySensor(coordinator, hass),
        # Energy Insights (ML-based)
        EnergyInsightSensor(coordinator),
        EnergyRecommendationSensor(coordinator),
        # Habit Learning v2 (ML-based)
        HabitLearningSensor(coordinator),
        HabitPredictionSensor(coordinator),
        SequencePredictionSensor(coordinator),
        # Anomaly Detection (ML-based)
        AnomalyAlertSensor(coordinator),
        AlertHistorySensor(coordinator),
        # Predictive Automation (ML-based)
        PredictiveAutomationSensor(coordinator),
        PredictiveAutomationDetailsSensor(coordinator),
        # Inspector Sensors (internal state visibility)
        InspectorSensor(coordinator, "zones", "Habitus Zones", "mdi:floor-plan"),
        InspectorSensor(coordinator, "tags", "Active Tags", "mdi:tag-multiple"),
        InspectorSensor(coordinator, "character", "Character Profile", "mdi:account-cog"),
        InspectorSensor(coordinator, "mood", "Current Mood", "mdi:emoticon"),
    ]

    # Events Forwarder quality sensors (v0.1 kernel)
    if isinstance(data, dict) and data.get("events_forwarder_state") is not None:
        entities.extend(
            [
                EventsForwarderQueueDepthSensor(coordinator, entry),
                EventsForwarderDroppedTotalSensor(coordinator, entry),
                EventsForwarderErrorStreakSensor(coordinator, entry),
            ]
        )

    media_coordinator = data.get("media_coordinator") if isinstance(data, dict) else None
    if media_coordinator is not None:
        entities.extend(
            [
                MusicNowPlayingSensor(media_coordinator),
                MusicPrimaryAreaSensor(media_coordinator),
                TvPrimaryAreaSensor(media_coordinator),
                TvSourceSensor(media_coordinator),
                MusicActiveCountSensor(media_coordinator),
                TvActiveCountSensor(media_coordinator),
            ]
        )
    
    # Media Context v2 sensor entities
    media_coordinator_v2 = data.get("media_coordinator_v2") if isinstance(data, dict) else None
    if media_coordinator_v2 is not None:
        entities.extend(
            [
                ActiveModeSensor(media_coordinator_v2),
                ActiveTargetSensor(media_coordinator_v2),
                ActiveZoneSensor(media_coordinator_v2),
                ConfigValidationSensor(media_coordinator_v2),
                DebugInfoSensor(media_coordinator_v2),
            ]
        )

    # Add optional Habitus zone aggregate sensors (e.g., Temperatur Ø / Luftfeuchte Ø).
    try:
        zones = await async_get_zones_v2(hass, entry.entry_id)
        for z in zones:
            entities.extend(
                build_zone_average_sensors(
                    hass=hass,
                    coordinator=coordinator,
                    zone_id=z.zone_id,
                    zone_name=z.name,
                    entities_by_role=z.entities,
                )
            )
    except Exception:  # noqa: BLE001
        # Best-effort: never break setup because of aggregates.
        pass

    # User Preference sensors
    user_pref_data = data.get("user_preference_module", {}) if isinstance(data, dict) else {}
    if user_pref_data:
        entities.append(ZoneOccupancySensor(hass, entry, user_pref_data))
        entities.append(UserPresenceSensor(hass, entry, user_pref_data))
        # Add per-user sensors
        for user_id in user_pref_data.get("users", {}).keys():
            entities.append(UserPreferenceSensor(hass, entry, user_pref_data, user_id))

    # Mood Dashboard entities (Neural System)
    entities.extend([
        MoodDashboardEntity(entry.entry_id),
        MoodHistoryEntity(entry.entry_id),
        MoodExplanationEntity(entry.entry_id),
    ])

    # Calendar Context entity (Neural System)
    calendar_config = data.get("calendar_context", {}) if isinstance(data, dict) else {}
    if calendar_config.get("enabled", False):
        from .calendar_context import CalendarContextModule
        module = CalendarContextModule(hass, entry.entry_id, calendar_config)
        await module.async_setup()
        entities.append(CalendarContextEntity(entry.entry_id, module))
        data["calendar_context_module"] = module

    # Mobile Dashboard Cards (Mobile-optimized UI)
    entities.extend([
        MobileDashboardSensor(hass, entry),
        MobileQuickActionsSensor(hass, entry),
        MobileEntityGridSensor(hass, entry),
    ])

    # Camera Context Sensors (Habitus Camera Integration)
    entities.extend([
        CameraMotionHistorySensor(coordinator, entry),
        CameraPresenceHistorySensor(coordinator, entry),
        CameraActivityHistorySensor(coordinator, entry),
        CameraZoneActivitySensor(coordinator, entry),
    ])
    
    # Camera Activity and Zone Sensors (auto-discover cameras)
    camera_entities = await _discover_camera_entities_for_sensors(hass)
    for cam_id, cam_name in camera_entities:
        entities.append(ActivityCamera(coordinator, entry, cam_id, cam_name))
        entities.append(ZoneCamera(coordinator, entry, cam_id, cam_name))

    # Home Alerts Sensors (Battery, Climate, Presence, System alerts)
    from .core.modules.home_alerts_module import get_home_alerts_module
    home_alerts_module = get_home_alerts_module(hass, entry.entry_id)
    if home_alerts_module is not None:
        from .home_alerts_sensor import (
            HomeAlertsCountSensor,
            HomeHealthScoreSensor,
            HomeAlertsByCategorySensor,
        )
        entities.append(HomeAlertsCountSensor(hass, entry, home_alerts_module))
        entities.append(HomeHealthScoreSensor(hass, entry, home_alerts_module))
        for category in ["battery", "climate", "presence", "system"]:
            entities.append(HomeAlertsByCategorySensor(hass, entry, home_alerts_module, category))

    async_add_entities(entities, True)


async def _discover_camera_entities_for_sensors(hass: HomeAssistant) -> list[tuple[str, str]]:
    """Discover camera entities for sensors."""
    from homeassistant.helpers import entity_registry
    er = entity_registry.async_get(hass)
    cameras = []
    
    for entity_id, entry in er.entities.items():
        if entry.domain == "camera":
            camera_name = entry.name or entry.original_name or entity_id.split(".")[-1]
            cameras.append((entity_id, camera_name))
    
    return cameras


class CopilotVersionSensor(CopilotBaseEntity, SensorEntity):
    _attr_name = "Version"
    _attr_unique_id = "version"
    _attr_icon = "mdi:tag"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.version


class ZoneOccupancySensor(SensorEntity):
    """Sensor for zone occupancy tracking."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:home-account"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, user_pref_data: dict) -> None:
        self._hass = hass
        self._entry = entry
        self._user_pref_data = user_pref_data
        self._attr_unique_id = f"{entry.entry_id}_zone_occupancy"
        self._attr_name = "CoPilot Zone Occupancy"
    
    @property
    def native_value(self) -> str:
        active_users = self._user_pref_data.get("active_users", {})
        if not active_users:
            return "empty"
        return f"{len(active_users)} zones"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "zones": self._user_pref_data.get("active_users", {}),
            "primary_user": self._user_pref_data.get("primary_user"),
            "tracked_users": list(self._user_pref_data.get("users", {}).keys()),
        }


class UserPresenceSensor(SensorEntity):
    """Sensor for overall user presence."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:account-check"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, user_pref_data: dict) -> None:
        self._hass = hass
        self._entry = entry
        self._user_pref_data = user_pref_data
        self._attr_unique_id = f"{entry.entry_id}_user_presence"
        self._attr_name = "CoPilot User Presence"
    
    @property
    def native_value(self) -> str:
        users = self._user_pref_data.get("users", {})
        if not users:
            return "unknown"
        
        # Check if any user is home
        for user_id, user_data in users.items():
            if user_data.get("state") == "home":
                return "home"
        return "away"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        users = self._user_pref_data.get("users", {})
        return {
            "users_count": len(users),
            "learning_mode": self._user_pref_data.get("learning_mode", "passive"),
        }


class UserPreferenceSensor(SensorEntity):
    """Sensor for individual user preferences."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:account-cog"
    
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        user_pref_data: dict,
        user_id: str,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._user_pref_data = user_pref_data
        self._user_id = user_id
        self._attr_unique_id = f"{entry.entry_id}_user_pref_{user_id}"
        self._attr_name = f"CoPilot User {user_id}"
    
    @property
    def native_value(self) -> str:
        user_data = self._user_pref_data.get("users", {}).get(self._user_id, {})
        return user_data.get("state", "unknown")
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        user_data = self._user_pref_data.get("users", {}).get(self._user_id, {})
        return {
            "preferences": user_data.get("preferences", {}),
            "patterns_count": len(user_data.get("learned_patterns", [])),
            "mood_history_count": len(user_data.get("mood_history", [])),
        }


class SuggestionQueueSensor(SensorEntity):
    """Sensor for suggestion queue status."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:lightbulb-outline"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_suggestion_queue"
        self._attr_name = "CoPilot Suggestions"
        self._queue_data: dict[str, Any] = {}
    
    @property
    def native_value(self) -> int:
        return self._queue_data.get("pending_count", 0)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._queue_data
    
    def update_queue(self, queue_data: dict[str, Any]) -> None:
        self._queue_data = queue_data
        self.async_write_ha_state()
