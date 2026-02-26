"""Sensor entities for PilotSuite.

This module provides lazy loading of sensor modules for better performance.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

# Lazy loading pattern - import from submodules only when needed
# This reduces startup time by deferring imports of large modules

# Phase 5: Notification & Scene Intelligence sensors
if TYPE_CHECKING:
    from .notification_sensor import NotificationSensor
    from .scene_intelligence_sensor import SceneIntelligenceSensor

def __getattr__(name: str):
    """Lazy import sensor classes."""
    
    # Presence sensors
    if name == "PresenceRoomSensor":
        from .presence_sensors import PresenceRoomSensor
        return PresenceRoomSensor
    if name == "PresencePersonSensor":
        from .presence_sensors import PresencePersonSensor
        return PresencePersonSensor
    
    # Activity sensors
    if name == "ActivityLevelSensor":
        from .activity_sensors import ActivityLevelSensor
        return ActivityLevelSensor
    if name == "ActivityStillnessSensor":
        from .activity_sensors import ActivityStillnessSensor
        return ActivityStillnessSensor
    
    # Time sensors
    if name == "TimeOfDaySensor":
        from .time_sensors import TimeOfDaySensor
        return TimeOfDaySensor
    if name == "DayTypeSensor":
        from .time_sensors import DayTypeSensor
        return DayTypeSensor
    if name == "RoutineStabilitySensor":
        from .time_sensors import RoutineStabilitySensor
        return RoutineStabilitySensor
    
    # Environment sensors
    if name == "LightLevelSensor":
        from .environment_sensors import LightLevelSensor
        return LightLevelSensor
    if name == "NoiseLevelSensor":
        from .environment_sensors import NoiseLevelSensor
        return NoiseLevelSensor
    if name == "WeatherContextSensor":
        from .environment_sensors import WeatherContextSensor
        return WeatherContextSensor
    
    # Calendar sensors
    if name == "CalendarLoadSensor":
        from .calendar_sensors import CalendarLoadSensor
        return CalendarLoadSensor
    
    # Cognitive sensors
    if name == "AttentionLoadSensor":
        from .cognitive_sensors import AttentionLoadSensor
        return AttentionLoadSensor
    if name == "StressProxySensor":
        from .cognitive_sensors import StressProxySensor
        return StressProxySensor
    
    # Energy sensors
    if name == "EnergyProxySensor":
        from .energy_sensors import EnergyProxySensor
        return EnergyProxySensor
    
    # Media sensors
    if name == "MediaActivitySensor":
        from .media_sensors import MediaActivitySensor
        return MediaActivitySensor
    if name == "MediaIntensitySensor":
        from .media_sensors import MediaIntensitySensor
        return MediaIntensitySensor
    
    # Legacy imports (for backward compatibility)
    if name == "MoodSensor":
        from .mood_sensor import MoodSensor
        return MoodSensor
    if name == "MoodConfidenceSensor":
        from .mood_sensor import MoodConfidenceSensor
        return MoodConfidenceSensor
    if name == "NeuronActivitySensor":
        from .mood_sensor import NeuronActivitySensor
        return NeuronActivitySensor
    if name == "PredictiveAutomationSensor":
        from .predictive_automation import PredictiveAutomationSensor
        return PredictiveAutomationSensor
    if name == "PredictiveAutomationDetailsSensor":
        from .predictive_automation import PredictiveAutomationDetailsSensor
        return PredictiveAutomationDetailsSensor
    if name == "AnomalyAlertSensor":
        from .anomaly_alert import AnomalyAlertSensor
        return AnomalyAlertSensor
    if name == "AlertHistorySensor":
        from .anomaly_alert import AlertHistorySensor
        return AlertHistorySensor
    if name == "EnergyInsightSensor":
        from .energy_insights import EnergyInsightSensor
        return EnergyInsightSensor
    if name == "EnergyRecommendationSensor":
        from .energy_insights import EnergyRecommendationSensor
        return EnergyRecommendationSensor
    if name == "HabitLearningSensor":
        from .habit_learning_v2 import HabitLearningSensor
        return HabitLearningSensor
    if name == "HabitPredictionSensor":
        from .habit_learning_v2 import HabitPredictionSensor
        return HabitPredictionSensor
    if name == "SequencePredictionSensor":
        from .habit_learning_v2 import SequencePredictionSensor
        return SequencePredictionSensor
    
    # Phase 5: Notification & Scene Intelligence sensors
    if name == "NotificationSensor":
        from .notification_sensor import NotificationSensor
        return NotificationSensor
    if name == "SceneIntelligenceSensor":
        from .scene_intelligence_sensor import SceneIntelligenceSensor
        return SceneIntelligenceSensor
    
    # Music Cloud sensors (zone-following music)
    if name == "MusicCloudSensor":
        from .music_cloud_sensor import MusicCloudSensor
        return MusicCloudSensor
    if name == "MusicCloudZonesSensor":
        from .music_cloud_sensor import MusicCloudZonesSensor
        return MusicCloudZonesSensor

    # Light Module sensors (adaptive lighting)
    if name == "LightModuleSensor":
        from .light_module_sensor import LightModuleSensor
        return LightModuleSensor
    if name == "LightModuleZonesSensor":
        from .light_module_sensor import LightModuleZonesSensor
        return LightModuleZonesSensor

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Explicit exports for static analysis and IDE support
__all__ = [
    # Phase 5: Notification & Scene Intelligence sensors
    "NotificationSensor",
    "SceneIntelligenceSensor",
    # New neuron sensors (split modules)
    "PresenceRoomSensor",
    "PresencePersonSensor",
    "ActivityLevelSensor",
    "ActivityStillnessSensor",
    "TimeOfDaySensor",
    "DayTypeSensor",
    "RoutineStabilitySensor",
    "LightLevelSensor",
    "NoiseLevelSensor",
    "WeatherContextSensor",
    "CalendarLoadSensor",
    "AttentionLoadSensor",
    "StressProxySensor",
    "EnergyProxySensor",
    "MediaActivitySensor",
    "MediaIntensitySensor",
    # Legacy sensors
    "MoodSensor",
    "MoodConfidenceSensor",
    "NeuronActivitySensor",
    "PredictiveAutomationSensor",
    "PredictiveAutomationDetailsSensor",
    "AnomalyAlertSensor",
    "AlertHistorySensor",
    "EnergyInsightSensor",
    "EnergyRecommendationSensor",
    "HabitLearningSensor",
    "HabitPredictionSensor",
    "SequencePredictionSensor",
    # Music Cloud & Light Module
    "MusicCloudSensor",
    "MusicCloudZonesSensor",
    "LightModuleSensor",
    "LightModuleZonesSensor",
]
