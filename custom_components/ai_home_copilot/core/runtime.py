from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, DATA_CORE, DATA_RUNTIME
from .module import CopilotModule, ModuleContext
from .registry import ModuleRegistry

_LOGGER = logging.getLogger(__name__)


class ModuleStatus:
    """Lightweight status record for a single module."""

    __slots__ = ("name", "state", "setup_time", "error", "last_activity")

    def __init__(self, name: str) -> None:
        self.name = name
        self.state: str = "pending"  # pending | active | error | unloaded
        self.setup_time: float = 0.0
        self.error: str | None = None
        self.last_activity: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "setup_time_ms": round(self.setup_time * 1000, 1),
            "error": self.error,
            "last_activity": self.last_activity,
        }


class CopilotRuntime:
    """Runtime container that owns the module registry.

    For now we always run the legacy module to keep behavior unchanged.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.registry = ModuleRegistry()
        self._live_modules: dict[str, dict[str, CopilotModule]] = {}
        self.module_statuses: dict[str, dict[str, ModuleStatus]] = {}

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

    def get_module_statuses(self, entry_id: str) -> dict[str, ModuleStatus]:
        """Return module status dict for a config entry."""
        return self.module_statuses.get(entry_id, {})

    async def async_setup_entry(self, entry: ConfigEntry, modules: Iterable[str]) -> None:
        ctx = ModuleContext(hass=self.hass, entry=entry)
        entry_modules: dict[str, CopilotModule] = {}
        entry_statuses: dict[str, ModuleStatus] = {}
        for name in modules:
            status = ModuleStatus(name)
            t0 = time.monotonic()
            try:
                mod = self.registry.create(name)
                await mod.async_setup_entry(ctx)
                entry_modules[name] = mod
                status.state = "active"
                status.setup_time = time.monotonic() - t0
                status.last_activity = time.time()
            except Exception as exc:
                _LOGGER.exception("Module %s failed to set up — skipping", name)
                status.state = "error"
                status.setup_time = time.monotonic() - t0
                status.error = str(exc)[:200]
            entry_statuses[name] = status
        self._live_modules[entry.entry_id] = entry_modules
        self.module_statuses[entry.entry_id] = entry_statuses

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
                result = await mod.async_unload_entry(ctx)
                if not isinstance(result, bool):
                    _LOGGER.warning(
                        "Module %s returned non-bool unload result %r; coercing to bool",
                        name,
                        result,
                    )
                unload_ok = bool(result) and unload_ok
            except Exception:
                _LOGGER.exception("Module %s failed to unload", name)
                unload_ok = False
        return unload_ok
