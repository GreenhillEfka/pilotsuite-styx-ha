"""Module Interface Standard - AI Home CoPilot

This defines the standard interface for all core modules.
All modules should follow this contract for consistency.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime


@dataclass
class ModuleState:
    """Standard module state."""
    module_id: str
    last_update: datetime
    data: dict[str, Any]
    error: Optional[str] = None


class ModuleInterface(ABC):
    """Base interface for all core modules."""
    
    @property
    @abstractmethod
    def module_id(self) -> str:
        """Unique module identifier."""
        pass
    
    @property
    @abstractmethod
    def state(self) -> ModuleState:
        """Current module state."""
        pass
    
    @abstractmethod
    async def async_init(self) -> None:
        """Initialize module."""
        pass
    
    @abstractmethod
    async def async_start(self) -> None:
        """Start module."""
        pass
    
    @abstractmethod
    async def async_stop(self) -> None:
        """Stop module."""
        pass


class DataModule(ModuleInterface):
    """Module that processes data and produces outputs."""
    
    @abstractmethod
    async def async_process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process input data and return results."""
        pass


class ContextModule(ModuleInterface):
    """Module that provides context to other modules."""
    
    @abstractmethod
    async def async_get_context(self) -> dict[str, Any]:
        """Get current context data."""
        pass


# Standard module outputs
MODULE_OUTPUT_TYPES = {
    "mood": dict,          # Mood data
    "presence": dict,       # Presence data
    "energy": dict,        # Energy data
    "suggestion": dict,    # Automation suggestions
    "state": dict,         # General state
}
