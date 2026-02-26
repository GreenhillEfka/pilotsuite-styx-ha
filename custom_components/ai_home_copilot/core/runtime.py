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

    __slots__ = ("name", "tier", "state", "setup_time", "error", "last_activity", "last_heartbeat")

    def __init__(self, name: str, tier: int = 3) -> None:
        self.name = name
        self.tier: int = tier
        self.state: str = "pending"  # pending | active | error | unloaded
        self.setup_time: float = 0.0
        self.error: str | None = None
        self.last_activity: float = 0.0
        self.last_heartbeat: float = 0.0

    def mark_active(self, elapsed: float) -> None:
        """Mark module as successfully started."""
        self.state = "active"
        self.setup_time = elapsed
        self.last_activity = time.time()
        self.last_heartbeat = time.time()

    def mark_error(self, elapsed: float, exc: Exception) -> None:
        """Mark module as failed during setup."""
        self.state = "error"
        self.setup_time = elapsed
        self.error = str(exc)[:200]
        self.last_activity = time.time()

    def mark_unloaded(self) -> None:
        """Mark module as unloaded."""
        self.state = "unloaded"
        self.last_activity = time.time()

    def heartbeat(self) -> None:
        """Update the heartbeat timestamp (called by modules to signal liveness)."""
        self.last_heartbeat = time.time()

    @property
    def tier_label(self) -> str:
        """Human-readable tier name."""
        return {0: "kernel", 1: "brain", 2: "context", 3: "extension"}.get(self.tier, "unknown")

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tier": self.tier,
            "tier_label": self.tier_label,
            "state": self.state,
            "setup_time_ms": round(self.setup_time * 1000, 1),
            "error": self.error,
            "last_activity": self.last_activity,
            "last_heartbeat": self.last_heartbeat,
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
        # Resolve tier info for each module (import here to avoid circular).
        from .. import MODULE_TIERS

        ctx = ModuleContext(hass=self.hass, entry=entry)
        entry_modules: dict[str, CopilotModule] = {}
        entry_statuses: dict[str, ModuleStatus] = {}
        for name in modules:
            tier = MODULE_TIERS.get(name, 3)
            status = ModuleStatus(name, tier=tier)
            t0 = time.monotonic()
            try:
                mod = self.registry.create(name)
                await mod.async_setup_entry(ctx)
                entry_modules[name] = mod
                status.mark_active(time.monotonic() - t0)
            except Exception as exc:
                _LOGGER.exception("Module %s (tier %d) failed to set up — skipping", name, tier)
                status.mark_error(time.monotonic() - t0, exc)
            entry_statuses[name] = status

        self._live_modules[entry.entry_id] = entry_modules
        self.module_statuses[entry.entry_id] = entry_statuses

        # Log boot summary
        active = sum(1 for s in entry_statuses.values() if s.state == "active")
        errors = sum(1 for s in entry_statuses.values() if s.state == "error")
        total_ms = sum(s.setup_time for s in entry_statuses.values()) * 1000
        _LOGGER.info(
            "Module boot: %d/%d active (%d errors) in %.0f ms",
            active, len(entry_statuses), errors, total_ms,
        )

    async def async_unload_entry(self, entry: ConfigEntry, modules: Iterable[str]) -> bool:
        ctx = ModuleContext(hass=self.hass, entry=entry)
        entry_modules = self._live_modules.pop(entry.entry_id, {})
        entry_statuses = self.module_statuses.get(entry.entry_id, {})
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
                status = entry_statuses.get(name)
                if status:
                    status.mark_unloaded()
            except Exception:
                _LOGGER.exception("Module %s failed to unload", name)
                unload_ok = False
        self.module_statuses.pop(entry.entry_id, None)
        return unload_ok
