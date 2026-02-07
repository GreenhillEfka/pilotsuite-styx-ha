from __future__ import annotations

from collections.abc import Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, DATA_CORE, DATA_RUNTIME
from .module import ModuleContext
from .registry import ModuleRegistry


class CopilotRuntime:
    """Runtime container that owns the module registry.

    For now we always run the legacy module to keep behavior unchanged.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.registry = ModuleRegistry()

    @classmethod
    def get(cls, hass: HomeAssistant) -> "CopilotRuntime":
        hass.data.setdefault(DOMAIN, {})
        core = hass.data[DOMAIN].setdefault(DATA_CORE, {})
        runtime = core.get(DATA_RUNTIME)
        if isinstance(runtime, CopilotRuntime):
            return runtime

        runtime = CopilotRuntime(hass)
        core[DATA_RUNTIME] = runtime
        return runtime

    async def async_setup_entry(self, entry: ConfigEntry, modules: Iterable[str]) -> None:
        ctx = ModuleContext(hass=self.hass, entry=entry)
        for name in modules:
            mod = self.registry.create(name)
            await mod.async_setup_entry(ctx)

    async def async_unload_entry(self, entry: ConfigEntry, modules: Iterable[str]) -> bool:
        ctx = ModuleContext(hass=self.hass, entry=entry)
        # Unload in reverse order.
        unload_ok = True
        for name in reversed(list(modules)):
            mod = self.registry.create(name)
            unload_ok = await mod.async_unload_entry(ctx) and unload_ok
        return unload_ok
