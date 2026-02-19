from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .blueprints import async_install_blueprints
from .core.runtime import CopilotRuntime

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .core.modules.legacy import LegacyModule
    from .core.modules.events_forwarder import EventsForwarderModule
    from .core.modules.dev_surface import DevSurfaceModule
    from .core.modules.performance_scaling import PerformanceScalingModule
    from .core.modules.habitus_miner import HabitusMinerModule
    from .core.modules.ops_runbook import OpsRunbookModule
    from .core.modules.unifi_module import UniFiModule
    from .core.modules.brain_graph_sync import BrainGraphSyncModule
    from .core.modules.candidate_poller import CandidatePollerModule
    from .core.modules.media_context_module import MediaContextModule
    from .core.modules.mood_context_module import MoodContextModule
    from .core.modules.mood_module import MoodModule
    from .core.modules.energy_context_module import EnergyContextModule
    from .core.modules.unifi_context_module import UnifiContextModule
    from .core.modules.weather_context_module import WeatherContextModule
    from .core.modules.knowledge_graph_sync import KnowledgeGraphSyncModule
    from .core.modules.ml_context_module import MLContextModule
    from .core.modules.camera_context_module import CameraContextModule
    from .core.modules.quick_search import QuickSearchModule
    from .core.modules.voice_context import VoiceContextModule
else:
    # Runtime imports - these are loaded lazily to avoid circular imports
    LegacyModule = None
    EventsForwarderModule = None
    DevSurfaceModule = None
    PerformanceScalingModule = None
    HabitusMinerModule = None
    OpsRunbookModule = None
    UniFiModule = None
    BrainGraphSyncModule = None
    CandidatePollerModule = None
    MediaContextModule = None
    MoodContextModule = None
    MoodModule = None
    EnergyContextModule = None
    UnifiContextModule = None
    WeatherContextModule = None
    KnowledgeGraphSyncModule = None
    MLContextModule = None
    CameraContextModule = None
    QuickSearchModule = None
    VoiceContextModule = None

from .debug import DebugModeSensor
from .services_setup import async_register_all_services
from .button import (
    CopilotToggleLightButton,
    CopilotCreateDemoSuggestionButton,
    CopilotAnalyzeLogsButton,
    CopilotRollbackLastFixButton,
    CopilotGenerateOverviewButton,
    CopilotDownloadOverviewButton,
    CopilotGenerateInventoryButton,
    CopilotSystemHealthReportButton,
    CopilotGenerateConfigSnapshotButton,
    CopilotDownloadConfigSnapshotButton,
    CopilotReloadConfigEntryButton,
    CopilotDevLogTestPushButton,
    CopilotDevLogPushLatestButton,
    CopilotDevLogsFetchButton,
    CopilotCoreCapabilitiesFetchButton,
    CopilotCoreEventsFetchButton,
    CopilotCoreGraphStateFetchButton,
    CopilotCoreGraphCandidatesPreviewButton,
    CopilotCoreGraphCandidatesOfferButton,
    CopilotPublishBrainGraphVizButton,
    CopilotPublishBrainGraphPanelButton,
    CopilotBrainDashboardSummaryButton,
    CopilotForwarderStatusButton,
    CopilotHaErrorsFetchButton,
    CopilotPingCoreButton,
    CopilotEnableDebug30mButton,
    CopilotDisableDebugButton,
    CopilotClearErrorDigestButton,
    CopilotClearAllLogsButton,
    CopilotSafetyBackupCreateButton,
    CopilotSafetyBackupStatusButton,
    CopilotGenerateHabitusDashboardButton,
    CopilotDownloadHabitusDashboardButton,
    CopilotGeneratePilotSuiteDashboardButton,
    CopilotDownloadPilotSuiteDashboardButton,
    VolumeUpButton,
    VolumeDownButton,
    VolumeMuteButton,
    ClearOverridesButton,
)

# Import remaining buttons from their respective files
from .button_camera import (
    CopilotGenerateCameraDashboardButton,
    CopilotDownloadCameraDashboardButton,
)

# DEPRECATED: v1 - now using v2 only
# v1 imports removed - use habitus_zones_entities_v2 instead
# v2 is now the primary implementation
from .habitus_zones_entities_v2 import (
    HabitusZonesV2ValidateButton,
    HabitusZonesV2SyncGraphButton,
    HabitusZonesV2ReloadButton,
)
from .button_tag_registry import CopilotTagRegistrySyncLabelsNowButton
from .button_update_rollback import CopilotUpdateRollbackReportButton

_MODULES = [
    "legacy",
    "performance_scaling",
    "events_forwarder",
    "dev_surface",
    "habitus_miner",
    "ops_runbook",
    "unifi_module",
    "brain_graph_sync",
    "candidate_poller",
    "media_zones",
    "mood",
    "mood_context",
    "energy_context",
    "network",
    "weather_context",
    "knowledge_graph_sync",
    "ml_context",
    "camera_context",
    "quick_search",
    "voice_context",
    "home_alerts",
    "character_module",
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    async_register_all_services(hass)
    
    # Register Quick Search services
    from .search_integration import async_register_services as register_search_services
    await register_search_services(hass)
    
    return True


def _get_runtime(hass: HomeAssistant) -> CopilotRuntime:
    runtime = CopilotRuntime.get(hass)
    
    # Import modules at runtime to avoid circular imports
    from .core.modules.legacy import LegacyModule
    from .core.modules.events_forwarder import EventsForwarderModule
    from .core.modules.dev_surface import DevSurfaceModule
    from .core.modules.performance_scaling import PerformanceScalingModule
    from .core.modules.habitus_miner import HabitusMinerModule
    from .core.modules.ops_runbook import OpsRunbookModule
    from .core.modules.unifi_module import UniFiModule
    from .core.modules.brain_graph_sync import BrainGraphSyncModule
    from .core.modules.candidate_poller import CandidatePollerModule
    from .core.modules.media_context_module import MediaContextModule
    from .core.modules.mood_context_module import MoodContextModule
    from .core.modules.mood_module import MoodModule
    from .core.modules.energy_context_module import EnergyContextModule
    from .core.modules.unifi_context_module import UnifiContextModule
    from .core.modules.weather_context_module import WeatherContextModule
    from .core.modules.knowledge_graph_sync import KnowledgeGraphSyncModule
    from .core.modules.ml_context_module import MLContextModule
    from .core.modules.camera_context_module import CameraContextModule
    from .core.modules.quick_search import QuickSearchModule
    from .core.modules.voice_context import VoiceContextModule
    from .core.modules.home_alerts_module import HomeAlertsModule
    from .core.modules.character_module import CharacterModule

    _module_classes = {
        "legacy": LegacyModule,
        "performance_scaling": PerformanceScalingModule,
        "events_forwarder": EventsForwarderModule,
        "dev_surface": DevSurfaceModule,
        "habitus_miner": HabitusMinerModule,
        "ops_runbook": OpsRunbookModule,
        "unifi_module": UniFiModule,
        "brain_graph_sync": BrainGraphSyncModule,
        "candidate_poller": CandidatePollerModule,
        "media_zones": MediaContextModule,
        "mood": MoodModule,
        "mood_context": MoodContextModule,
        "energy_context": EnergyContextModule,
        "network": UnifiContextModule,
        "weather_context": WeatherContextModule,
        "knowledge_graph_sync": KnowledgeGraphSyncModule,
        "ml_context": MLContextModule,
        "camera_context": CameraContextModule,
        "quick_search": QuickSearchModule,
        "voice_context": VoiceContextModule,
        "home_alerts": HomeAlertsModule,
        "character_module": CharacterModule,
    }
    for name, cls in _module_classes.items():
        if name not in runtime.registry.names():
            runtime.registry.register(name, cls)
    return runtime


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await async_install_blueprints(hass)
    runtime = _get_runtime(hass)
    await runtime.async_setup_entry(entry, modules=_MODULES)
    
    # Set up User Preference Module separately (not a CopilotModule)
    from .user_preference_module import UserPreferenceModule
    from .const import CONF_USER_PREFERENCE_ENABLED
    
    config = entry.options or entry.data
    if config.get(CONF_USER_PREFERENCE_ENABLED, False):
        user_pref_module = UserPreferenceModule(hass, entry)
        await user_pref_module.async_setup()
        
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        if entry.entry_id not in hass.data[DOMAIN]:
            hass.data[DOMAIN][entry.entry_id] = {}
        hass.data[DOMAIN][entry.entry_id]["user_preference_module"] = user_pref_module
    
    # Set up Multi-User Preference Learning Module (v0.8.0)
    from .multi_user_preferences import MultiUserPreferenceModule, set_mupl_module
    from .const import CONF_MUPL_ENABLED, DEFAULT_MUPL_ENABLED
    
    if config.get(CONF_MUPL_ENABLED, DEFAULT_MUPL_ENABLED):
        mupl_module = MultiUserPreferenceModule(hass, entry)
        await mupl_module.async_setup()
        set_mupl_module(hass, entry.entry_id, mupl_module)
        _LOGGER.info("Multi-User Preference Learning Module initialized")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = _get_runtime(hass)
    
    # Unload User Preference Module
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    user_pref_module = entry_data.get("user_preference_module")
    if user_pref_module:
        await user_pref_module.async_unload()
    
    # Unload Multi-User Preference Learning Module
    from .multi_user_preferences import _MUPL_MODULE_KEY
    mupl_module = entry_data.get(_MUPL_MODULE_KEY)
    if mupl_module:
        await mupl_module.async_unload()
    
    return await runtime.async_unload_entry(entry, modules=_MODULES)