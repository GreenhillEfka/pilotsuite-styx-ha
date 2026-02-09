"""Ops Runbook Module v0.1 - Runtime module for operations runbook."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..base import CopilotModule
from ...ops_runbook import async_setup_ops_runbook
from ...ops_runbook_store import OpsRunbookStore
from ...ops_runbook_entities import async_setup_ops_runbook_entities

_LOGGER = logging.getLogger(__name__)


class OpsRunbookModule(CopilotModule):
    """Module for Ops Runbook v0.1 functionality."""

    def __init__(self) -> None:
        """Initialize the module."""
        super().__init__()
        self._store: OpsRunbookStore | None = None

    @property
    def name(self) -> str:
        """Return the module name."""
        return "ops_runbook"

    @property
    def version(self) -> str:
        """Return the module version."""
        return "0.1"

    async def async_setup(self, hass: HomeAssistant, entry: ConfigEntry) -> bool:
        """Set up the module."""
        _LOGGER.info("Setting up Ops Runbook module v0.1")
        
        try:
            # Initialize store
            self._store = OpsRunbookStore(hass)
            await self._store.async_load()
            
            # Set up the main runbook functionality
            await async_setup_ops_runbook(hass, {})
            
            # Set up entities
            entities = await async_setup_ops_runbook_entities(hass)
            
            # Store entities for platform registration
            if not hasattr(hass.data[self.domain], "ops_runbook_entities"):
                hass.data[self.domain]["ops_runbook_entities"] = entities
            
            _LOGGER.info(f"Ops Runbook module setup complete with {len(entities)} entities")
            return True
            
        except Exception as e:
            _LOGGER.exception("Failed to set up Ops Runbook module")
            return False

    async def async_unload(self, hass: HomeAssistant, entry: ConfigEntry) -> bool:
        """Unload the module."""
        _LOGGER.info("Unloading Ops Runbook module v0.1")
        
        # Clean up entities
        if hasattr(hass.data[self.domain], "ops_runbook_entities"):
            del hass.data[self.domain]["ops_runbook_entities"]
        
        # Clean up store reference
        if hasattr(hass.data[self.domain], "ops_runbook_store"):
            del hass.data[self.domain]["ops_runbook_store"]
        
        self._store = None
        return True

    async def async_get_status(self, hass: HomeAssistant) -> dict[str, Any]:
        """Get module status."""
        status = {
            "name": self.name,
            "version": self.version,
            "enabled": True,
            "store_loaded": self._store is not None,
        }
        
        if self._store:
            try:
                summary = await self._store.async_get_summary()
                status["last_checks"] = summary.get("last_checks", {})
                status["recent_actions"] = summary.get("recent_actions", 0)
                status["recent_checklists"] = summary.get("recent_checklists", 0)
            except Exception as e:
                _LOGGER.error(f"Error getting store status: {e}")
                status["store_error"] = str(e)
        
        return status

    async def async_run_preflight_check(self, hass: HomeAssistant) -> dict[str, Any]:
        """Run preflight check through the module."""
        from ...ops_runbook import async_run_preflight_check
        return await async_run_preflight_check(hass)

    async def async_run_smoke_test(self, hass: HomeAssistant) -> dict[str, Any]:
        """Run smoke test through the module."""
        from ...ops_runbook import async_run_smoke_test
        return await async_run_smoke_test(hass)

    async def async_execute_action(self, hass: HomeAssistant, action: str) -> dict[str, Any]:
        """Execute runbook action through the module."""
        from ...ops_runbook import async_execute_runbook_action
        return await async_execute_runbook_action(hass, action)

    async def async_run_checklist(self, hass: HomeAssistant, checklist: str) -> dict[str, Any]:
        """Run checklist through the module."""
        from ...ops_runbook import async_run_checklist
        return await async_run_checklist(hass, checklist)