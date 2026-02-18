from __future__ import annotations

import logging
from collections.abc import Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, DATA_CORE, DATA_RUNTIME
from .module import CopilotModule, ModuleContext
from .registry import ModuleRegistry

_LOGGER = logging.getLogger(__name__)


class CopilotRuntime:
    """Runtime container that owns the module registry.

    For now we always run the legacy module to keep behavior unchanged.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.registry = ModuleRegistry()
        self._live_modules: dict[str, dict[str, CopilotModule]] = {}

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
        entry_modules: dict[str, CopilotModule] = {}
        for name in modules:
            try:
                mod = self.registry.create(name)
                await mod.async_setup_entry(ctx)
                entry_modules[name] = mod
            except Exception:
                _LOGGER.exception("Module %s failed to set up — skipping", name)
        self._live_modules[entry.entry_id] = entry_modules

    async def async_unload_entry(self, entry: ConfigEntry, modules: Iterable[str]) -> bool:
        ctx = ModuleContext(hass=self.hass, entry=entry)
        entry_modules = self._live_modules.pop(entry.entry_id, {})
        unload_ok = True
        for name in reversed(list(modules)):
            mod = entry_modules.get(name)
            if mod is None:
                _LOGGER.debug("Module %s was not loaded — skip unload", name)
                continue
            try:
                unload_ok = await mod.async_unload_entry(ctx) and unload_ok
            except Exception:
                _LOGGER.exception("Module %s failed to unload", name)
                unload_ok = False
        return unload_ok
