from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .blueprints import async_install_blueprints
from .core.runtime import CopilotRuntime
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
from .core.modules.energy_context_module import EnergyContextModule
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
    "mood_context",
    "energy_context",
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
        "mood_context": MoodContextModule,
        "energy_context": EnergyContextModule,
    }
    for name, cls in _module_classes.items():
        if name not in runtime.registry.names():
            runtime.registry.register(name, cls)
    return runtime


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await async_install_blueprints(hass)
    runtime = _get_runtime(hass)
    await runtime.async_setup_entry(entry, modules=_MODULES)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = _get_runtime(hass)
    return await runtime.async_unload_entry(entry, modules=_MODULES)
