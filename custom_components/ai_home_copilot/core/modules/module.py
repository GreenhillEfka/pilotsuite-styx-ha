"""Base Module Classes for PilotSuite HA Integration.

Defines the CopilotModule interface and ModuleContext for all integration modules.
"""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@dataclass
class ModuleContext:
    """Context passed to all module lifecycle methods.
    
    Provides access to HomeAssistant instance and the config entry
    that loaded this module.
    """
    hass: HomeAssistant
    entry: ConfigEntry
    
    @property
    def domain(self) -> str:
        """Get the domain from the config entry."""
        return self.entry.domain
    
    @property
    def entry_id(self) -> str:
        """Get the entry ID."""
        return self.entry.entry_id


class CopilotModule:
    """Base class for all PilotSuite modules.
    
    Modules should inherit from this class and implement the lifecycle methods.
    """
    
    @property
    def name(self) -> str:
        """Return the module name (should be overridden)."""
        raise NotImplementedError("Module must define a name property")
    
    @property
    def version(self) -> str:
        """Return the module version (optional)."""
        return "0.1"
    
    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the module for a config entry.
        
        Called when the config entry is set up. Modules should:
        - Initialize their data structures in hass.data
        - Register any services
        - Set up periodic tasks or event listeners
        """
        raise NotImplementedError("Module must implement async_setup_entry")
    
    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the module when the config entry is removed.
        
        Should return True if successful, False otherwise.
        """
        raise NotImplementedError("Module must implement async_unload_entry")
    
    async def async_reload_entry(self, ctx: ModuleContext) -> None:
        """Reload the module (optional).
        
        Called when the config entry is reloaded.
        Default implementation calls unload then setup.
        """
        await self.async_unload_entry(ctx)
        await self.async_setup_entry(ctx)
