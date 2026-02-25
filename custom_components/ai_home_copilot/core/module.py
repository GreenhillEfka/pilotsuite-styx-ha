from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@dataclass(frozen=True, slots=True)
class ModuleContext:
    """Context passed to modules.

    Keep this small and stable; modules can always access hass/entry.
    """

    hass: HomeAssistant
    entry: ConfigEntry

    @property
    def domain(self) -> str:
        """Compatibility helper for modules expecting ctx.domain."""
        return self.entry.domain

    @property
    def entry_id(self) -> str:
        """Compatibility helper for modules expecting ctx.entry_id."""
        return self.entry.entry_id


@runtime_checkable
class CopilotModule(Protocol):
    """Minimal module interface.

    Modules are responsible for storing any entry-specific data under
    hass.data[DOMAIN][entry_id] as needed.
    """

    @property
    def name(self) -> str:
        ...

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        ...

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        ...
