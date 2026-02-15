from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .blueprints import async_install_blueprints
from .core.runtime import CopilotRuntime

_LOGGER = logging.getLogger(__name__)
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
from .debug import DebugModeSensor
from .services_setup import async_register_all_services

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
    "media_context",
    "mood",
    "mood_context",
    "energy_context",
    "unifi_context",
    "weather_context",
    "knowledge_graph_sync",
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    async_register_all_services(hass)
    return True


def _get_runtime(hass: HomeAssistant) -> CopilotRuntime:
    runtime = CopilotRuntime.get(hass)
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
        "media_context": MediaContextModule,
        "mood": MoodModule,
        "mood_context": MoodContextModule,
        "energy_context": EnergyContextModule,
        "unifi_context": UnifiContextModule,
        "weather_context": WeatherContextModule,
        "knowledge_graph_sync": KnowledgeGraphSyncModule,
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