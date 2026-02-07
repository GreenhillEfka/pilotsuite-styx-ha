from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .core.runtime import CopilotRuntime
from .core.modules.legacy import LegacyModule
from .core.modules.events_forwarder import EventsForwarderModule


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


def _get_runtime(hass: HomeAssistant) -> CopilotRuntime:
    runtime = CopilotRuntime.get(hass)
    # Register built-in modules (idempotent).
    if "legacy" not in runtime.registry.names():
        runtime.registry.register("legacy", LegacyModule)
    if "events_forwarder" not in runtime.registry.names():
        runtime.registry.register("events_forwarder", EventsForwarderModule)
    return runtime


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = _get_runtime(hass)
    await runtime.async_setup_entry(entry, modules=["legacy", "events_forwarder"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = _get_runtime(hass)
    return await runtime.async_unload_entry(entry, modules=["legacy", "events_forwarder"])
