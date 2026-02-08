from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .blueprints import async_install_blueprints
from .core.runtime import CopilotRuntime
from .core.modules.legacy import LegacyModule
from .core.modules.events_forwarder import EventsForwarderModule
from .core.modules.dev_surface import DevSurfaceModule


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
    if "dev_surface" not in runtime.registry.names():
        runtime.registry.register("dev_surface", DevSurfaceModule)
    return runtime


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Install shipped blueprints (does not create automations).
    await async_install_blueprints(hass)

    runtime = _get_runtime(hass)
    await runtime.async_setup_entry(entry, modules=["legacy", "events_forwarder", "dev_surface"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = _get_runtime(hass)
    return await runtime.async_unload_entry(entry, modules=["legacy", "events_forwarder", "dev_surface"])
