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
from .habitus_zones_entities_v2 import (
    HabitusZonesSensor,
    HabitusZonesV2CountSensor,
    HabitusZonesV2StatesSensor,
    HabitusZonesV2HealthSensor,
)
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

# Regional Sensors (v5.16.0+)
from .sensors.weather_warning_sensor import WeatherWarningSensor
from .sensors.fuel_price_sensor import FuelPriceSensor
from .sensors.tariff_sensor import TariffSensor
from .sensors.proactive_alert_sensor import ProactiveAlertSensor
from .sensors.energy_forecast_sensor import EnergyForecastSensor
from .sensors.agent_status_sensor import AgentStatusSensor
from .sensors.onboarding_sensor import OnboardingSensor
from .sensors.battery_optimizer_sensor import BatteryOptimizerSensor
from .sensors.heat_pump_sensor import HeatPumpSensor
from .sensors.ev_charging_sensor import EVChargingSensor
from .sensors.hub_dashboard_sensor import (
    HubDashboardSensor,
    HubPluginsSensor,
    HubMultiHomeSensor,
)
from .sensors.predictive_maintenance_sensor import PredictiveMaintenanceSensor
from .sensors.anomaly_detection_sensor import AnomalyDetectionSensor
from .sensors.gas_meter_sensor import GasMeterSensor
from .sensors.habitus_zone_sensor import HabitusZoneSensor
from .sensors.light_intelligence_sensor import LightIntelligenceSensor
from .sensors.zone_mode_sensor import ZoneModeSensor
from .sensors.media_follow_sensor import MediaFollowSensor
from .sensors.energy_advisor_sensor import EnergyAdvisorSensor
from .sensors.automation_template_sensor import AutomationTemplateSensor


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not isinstance(data, dict):
        return
    coordinator = data.get("coordinator")
    if coordinator is None:
        return

    entities = [
        CopilotVersionSensor(coordinator),
        CoreApiV1StatusSensor(coordinator, entry),
        # Habitus Zones
        HabitusZonesSensor(coordinator, entry),
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
    user_pref_module = data.get("user_preference_module")
    user_pref_data = {}
    if user_pref_module is not None:
        if isinstance(user_pref_module, dict):
            user_pref_data = user_pref_module
        elif hasattr(user_pref_module, "get_state"):
            user_pref_data = user_pref_module.get_state() or {}
    if user_pref_data:
        entities.append(ZoneOccupancySensor(hass, entry, user_pref_data))
        entities.append(UserPresenceSensor(hass, entry, user_pref_data))
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

    # Regional Sensors (v5.16.0+) — PV, prices, weather, alerts, forecast
    entities.extend([
        WeatherWarningSensor(coordinator),
        FuelPriceSensor(coordinator),
        TariffSensor(coordinator),
        ProactiveAlertSensor(coordinator),
        EnergyForecastSensor(coordinator),
        AgentStatusSensor(coordinator),
        OnboardingSensor(coordinator),
        BatteryOptimizerSensor(coordinator),
        HeatPumpSensor(coordinator),
        EVChargingSensor(coordinator),
        HubDashboardSensor(coordinator),
        HubPluginsSensor(coordinator),
        HubMultiHomeSensor(coordinator),
        PredictiveMaintenanceSensor(coordinator),
        AnomalyDetectionSensor(coordinator),
        GasMeterSensor(coordinator),
        HabitusZoneSensor(coordinator),
        LightIntelligenceSensor(coordinator),
        ZoneModeSensor(coordinator),
        MediaFollowSensor(coordinator),
        EnergyAdvisorSensor(coordinator),
        AutomationTemplateSensor(coordinator),
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

    # Waste Reminder sensors (v3.2.1)
    from .core.modules.waste_reminder_module import get_waste_reminder_module
    waste_mod = get_waste_reminder_module(hass, entry.entry_id)
    if waste_mod is not None:
        entities.extend([
            WasteNextCollectionSensor(hass, entry, waste_mod),
            WasteTodayCountSensor(hass, entry, waste_mod),
        ])

    # Birthday Reminder sensors (v3.2.1)
    from .core.modules.birthday_reminder_module import get_birthday_reminder_module
    birthday_mod = get_birthday_reminder_module(hass, entry.entry_id)
    if birthday_mod is not None:
        entities.extend([
            BirthdayTodayCountSensor(hass, entry, birthday_mod),
            BirthdayNextSensor(hass, entry, birthday_mod),
        ])

    # Character Preset sensor (v3.2.1)
    from .core.modules.character_module import get_character_module
    char_mod = get_character_module(hass, entry.entry_id)
    if char_mod is not None:
        entities.append(CharacterPresetSensor(hass, entry, char_mod))

    # Network Health sensor (v3.2.1)
    from .core.modules.unifi_context_module import get_network_module
    net_mod = get_network_module(hass, entry.entry_id)
    if net_mod is not None:
        entities.append(NetworkHealthSensor(hass, entry, net_mod))

    # Entity Tags sensor (v3.2.2)
    from .core.modules.entity_tags_module import get_entity_tags_module
    tags_mod = get_entity_tags_module(hass, entry.entry_id)
    if tags_mod is not None:
        entities.append(EntityTagsSensor(hass, entry, tags_mod))

    # Person Tracking sensor (v3.3.0)
    from .core.modules.person_tracking_module import get_person_tracking_module
    person_mod = get_person_tracking_module(hass, entry.entry_id)
    if person_mod is not None:
        entities.append(PersonsHomeSensor(hass, entry, person_mod))

    # Frigate Cameras sensor (v3.3.0)
    from .core.modules.frigate_bridge import get_frigate_bridge
    frigate_mod = get_frigate_bridge(hass, entry.entry_id)
    if frigate_mod is not None:
        entities.append(FrigateCamerasSensor(hass, entry, frigate_mod))

    # Scene Module sensor (v3.4.0)
    from .core.modules.scene_module import get_scene_module
    scene_mod = get_scene_module(hass, entry.entry_id)
    if scene_mod is not None:
        entities.append(ZoneScenesSensor(hass, entry, scene_mod))

    # HomeKit Bridge sensor (v3.4.0)
    from .core.modules.homekit_bridge import get_homekit_bridge
    homekit_mod = get_homekit_bridge(hass, entry.entry_id)
    if homekit_mod is not None:
        entities.append(HomeKitBridgeSensor(hass, entry, homekit_mod))

    # HomeKit per-zone toggle + QR entities (v4.0.0)
    from .homekit_entities import async_create_homekit_entities
    await async_create_homekit_entities(hass, entry, coordinator, async_add_entities)

    # Calendar Module sensor (v3.5.0)
    from .core.modules.calendar_module import get_calendar_module
    cal_mod = get_calendar_module(hass, entry.entry_id)
    if cal_mod is not None:
        entities.append(CalendarSensor(hass, entry, cal_mod))

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
    _attr_unique_id = "ai_home_copilot_version"
    _attr_icon = "mdi:tag"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("version", "unknown")


class ZoneOccupancySensor(SensorEntity):
    """Sensor for zone occupancy tracking."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:home-account"
    
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, user_pref_data: dict) -> None:
        self._hass = hass
        self._entry = entry
        self._user_pref_data = user_pref_data
        self._attr_unique_id = f"{entry.entry_id}_zone_occupancy"
        self._attr_name = "PilotSuite Zone Occupancy"
    
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
        self._attr_name = "PilotSuite User Presence"
    
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
        self._attr_name = f"PilotSuite User {user_id}"
    
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
        self._attr_name = "PilotSuite Suggestions"
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


# ---------------------------------------------------------------------------
# Waste Reminder Sensors (v3.2.1)
# ---------------------------------------------------------------------------

class WasteNextCollectionSensor(SensorEntity):
    """Next waste collection type and date."""

    _attr_icon = "mdi:trash-can-outline"
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, module) -> None:
        self._hass = hass
        self._entry = entry
        self._module = module
        self._attr_unique_id = f"{entry.entry_id}_waste_next_collection"
        self._attr_name = "PilotSuite Waste Next Collection"

    @property
    def native_value(self) -> str | None:
        if self._module is None:
            return None
        state = self._module.get_state()
        nc = state.next_collection
        return nc.waste_type if nc else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._module is None:
            return {}
        state = self._module.get_state()
        nc = state.next_collection
        return {
            "days_to": nc.days_to if nc else None,
            "next_date": nc.next_date if nc else None,
            "icon": nc.icon if nc else None,
            "today": [c.waste_type for c in state.today_collections],
            "tomorrow": [c.waste_type for c in state.tomorrow_collections],
            "all_collections": [
                {"type": c.waste_type, "days_to": c.days_to, "date": c.next_date}
                for c in state.collections
            ],
        }


class WasteTodayCountSensor(SensorEntity):
    """Number of waste collections scheduled for today."""

    _attr_icon = "mdi:trash-can"
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "collections"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, module) -> None:
        self._hass = hass
        self._entry = entry
        self._module = module
        self._attr_unique_id = f"{entry.entry_id}_waste_today_count"
        self._attr_name = "PilotSuite Waste Today Count"

    @property
    def native_value(self) -> int:
        if self._module is None:
            return 0
        return len(self._module.get_state().today_collections)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._module is None:
            return {}
        state = self._module.get_state()
        return {
            "today_types": [c.waste_type for c in state.today_collections],
            "tomorrow_types": [c.waste_type for c in state.tomorrow_collections],
            "last_scan": state.last_scan.isoformat() if state.last_scan else None,
        }


# ---------------------------------------------------------------------------
# Birthday Reminder Sensors (v3.2.1)
# ---------------------------------------------------------------------------

class BirthdayTodayCountSensor(SensorEntity):
    """Number of birthdays today."""

    _attr_icon = "mdi:cake-variant"
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "birthdays"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, module) -> None:
        self._hass = hass
        self._entry = entry
        self._module = module
        self._attr_unique_id = f"{entry.entry_id}_birthday_today_count"
        self._attr_name = "PilotSuite Birthday Today Count"

    @property
    def native_value(self) -> int:
        if self._module is None:
            return 0
        return len(self._module.get_state().today_birthdays)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._module is None:
            return {}
        state = self._module.get_state()
        today = state.today_birthdays
        upcoming = [b for b in state.upcoming_birthdays if b.days_until > 0]
        return {
            "today_names": [b.name for b in today],
            "today_details": [b.to_dict() for b in today],
            "upcoming": [b.to_dict() for b in upcoming[:10]],
            "last_scan": state.last_scan.isoformat() if state.last_scan else None,
        }


class BirthdayNextSensor(SensorEntity):
    """Next upcoming birthday name."""

    _attr_icon = "mdi:cake-variant-outline"
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, module) -> None:
        self._hass = hass
        self._entry = entry
        self._module = module
        self._attr_unique_id = f"{entry.entry_id}_birthday_next"
        self._attr_name = "PilotSuite Birthday Next"

    @property
    def native_value(self) -> str | None:
        if self._module is None:
            return None
        state = self._module.get_state()
        upcoming = sorted(state.upcoming_birthdays, key=lambda b: b.days_until)
        if upcoming:
            return upcoming[0].name
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._module is None:
            return {}
        state = self._module.get_state()
        upcoming = sorted(state.upcoming_birthdays, key=lambda b: b.days_until)
        if upcoming:
            nxt = upcoming[0]
            return {
                "days_until": nxt.days_until,
                "age": nxt.age,
                "date": nxt.date.strftime("%Y-%m-%d") if nxt.date else None,
                "calendar_entity": nxt.calendar_entity,
            }
        return {}


# ---------------------------------------------------------------------------
# Module-Sweep Sensors (v3.2.1)
# ---------------------------------------------------------------------------

class CharacterPresetSensor(SensorEntity):
    """Active character preset name."""

    _attr_icon = "mdi:drama-masks"
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, module) -> None:
        self._hass = hass
        self._entry = entry
        self._module = module
        self._attr_unique_id = f"{entry.entry_id}_character_preset"
        self._attr_name = "PilotSuite Character Preset"

    @property
    def native_value(self) -> str | None:
        try:
            preset = self._module.get_current_preset()
            return preset.name.value if hasattr(preset.name, "value") else str(preset.name)
        except Exception:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        try:
            preset = self._module.get_current_preset()
            return {
                "display_name": preset.display_name,
                "description": preset.description,
                "icon": preset.icon,
                "available_modes": [
                    m["mode"] for m in self._module.get_available_modes()
                ],
            }
        except Exception:
            return {}


class NetworkHealthSensor(SensorEntity):
    """UniFi network health status."""

    _attr_icon = "mdi:lan-check"
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, module) -> None:
        self._hass = hass
        self._entry = entry
        self._module = module
        self._attr_unique_id = f"{entry.entry_id}_network_health"
        self._attr_name = "PilotSuite Network Health"

    @property
    def native_value(self) -> str | None:
        try:
            return self._module.get_health_status()
        except Exception:
            return "unavailable"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        try:
            snapshot = self._module.get_snapshot()
            if not snapshot:
                return {}
            return {
                "wan_online": snapshot.get("wan_online"),
                "wan_latency_ms": snapshot.get("wan_latency_ms"),
                "wan_packet_loss_percent": snapshot.get("wan_packet_loss_percent"),
                "clients_online": snapshot.get("clients_online"),
                "clients_total": snapshot.get("clients_total"),
            }
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# Entity Tags Sensor (v3.2.2)
# ---------------------------------------------------------------------------

class EntityTagsSensor(SensorEntity):
    """Number of user-defined entity tags. Attributes: full tag list."""

    _attr_icon = "mdi:tag-multiple"
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "tags"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, module) -> None:
        self._hass = hass
        self._entry = entry
        self._module = module
        self._attr_unique_id = f"{entry.entry_id}_entity_tags"
        self._attr_name = "PilotSuite Entity Tags"

    @property
    def native_value(self) -> int:
        if self._module is None:
            return 0
        return self._module.get_tag_count()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        try:
            summary = self._module.get_summary()
            return {
                "total_tagged_entities": self._module.get_total_tagged_entities(),
                "tags": summary.get("tags", []),
            }
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# Person Tracking Sensor (v3.3.0)
# ---------------------------------------------------------------------------

class PersonsHomeSensor(SensorEntity):
    """Number of persons currently home."""

    _attr_icon = "mdi:account-group"
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "persons"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, module) -> None:
        self._hass = hass
        self._entry = entry
        self._module = module
        self._attr_unique_id = f"{entry.entry_id}_persons_home"
        self._attr_name = "PilotSuite Persons Home"

    @property
    def native_value(self) -> int:
        if self._module is None:
            return 0
        return self._module.get_person_count()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._module is None:
            return {}
        try:
            home = self._module.get_persons_home()
            away = self._module.get_persons_away()
            return {
                "persons_home": home,
                "persons_away": away,
                "total_tracked": len(home) + len(away),
                "presence_map": self._module.get_presence_map(),
            }
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# Frigate Cameras Sensor (v3.3.0)
# ---------------------------------------------------------------------------

class FrigateCamerasSensor(SensorEntity):
    """Number of discovered Frigate cameras."""

    _attr_icon = "mdi:cctv"
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "cameras"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, module) -> None:
        self._hass = hass
        self._entry = entry
        self._module = module
        self._attr_unique_id = f"{entry.entry_id}_frigate_cameras"
        self._attr_name = "PilotSuite Frigate Cameras"

    @property
    def native_value(self) -> int:
        if self._module is None:
            return 0
        cams = self._module.get_frigate_cameras()
        return len(cams) if cams else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._module is None:
            return {}
        try:
            cams = self._module.get_frigate_cameras()
            recent = self._module.get_recent_detections()
            return {
                "cameras": cams,
                "recent_detections": recent[:10] if recent else [],
                "enabled": self._module._enabled,
            }
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# Zone Scenes Sensor (v3.4.0)
# ---------------------------------------------------------------------------

class ZoneScenesSensor(SensorEntity):
    """Number of saved zone scenes."""

    _attr_icon = "mdi:palette-outline"
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "scenes"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, module) -> None:
        self._hass = hass
        self._entry = entry
        self._module = module
        self._attr_unique_id = f"{entry.entry_id}_zone_scenes"
        self._attr_name = "PilotSuite Zone Scenes"

    @property
    def native_value(self) -> int:
        if self._module is None:
            return 0
        return self._module.get_scene_count()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._module is None:
            return {}
        try:
            summary = self._module.get_summary()
            return {
                "zones_with_scenes": summary.get("zones_with_scenes", 0),
                "manual_count": summary.get("manual_count", 0),
                "learned_count": summary.get("learned_count", 0),
                "preset_count": summary.get("preset_count", 0),
                "popular": [s["name"] for s in self._module.get_popular_scenes(3)],
            }
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# HomeKit Bridge Sensor (v3.4.0)
# ---------------------------------------------------------------------------

class HomeKitBridgeSensor(SensorEntity):
    """Number of habitus zones exposed to HomeKit."""

    _attr_icon = "mdi:apple"
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "zones"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, module) -> None:
        self._hass = hass
        self._entry = entry
        self._module = module
        self._attr_unique_id = f"{entry.entry_id}_homekit_bridge"
        self._attr_name = "PilotSuite HomeKit Bridge"

    @property
    def native_value(self) -> int:
        if self._module is None:
            return 0
        return self._module.get_zone_count()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._module is None:
            return {}
        try:
            summary = self._module.get_summary()
            return {
                "total_exposed_entities": summary.get("total_exposed_entities", 0),
                "homekit_available": summary.get("homekit_available", False),
                "zones": summary.get("zones", []),
            }
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# Calendar Sensor (v3.5.0)
# ---------------------------------------------------------------------------

class CalendarSensor(SensorEntity):
    """Number of HA calendar entities integrated with PilotSuite."""

    _attr_icon = "mdi:calendar-month"
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "calendars"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, module) -> None:
        self._hass = hass
        self._entry = entry
        self._module = module
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_name = "PilotSuite Calendar"

    @property
    def native_value(self) -> int:
        if self._module is None:
            return 0
        return self._module.get_calendar_count()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._module is None:
            return {}
        try:
            summary = self._module.get_summary()
            return {
                "calendars": summary.get("calendars", []),
            }
        except Exception:
            return {}
