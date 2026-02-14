"""
Brain Graph Sync Module for AI Home CoPilot Runtime.

Manages syncing HA state and relationships to Core Brain Graph module
via the /api/v1/graph endpoints. Creates a real-time knowledge graph
of HA entities, their relationships, and state transitions.
"""
import logging
from typing import Optional

from homeassistant.core import HomeAssistant

from ..module import ModuleContext
from ...brain_graph_sync import BrainGraphSync, async_setup_brain_graph_sync, async_unload_brain_graph_sync
from ...const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BrainGraphSyncModule:
    """Module for Brain Graph synchronization with Core."""

    name = "brain_graph_sync"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the Brain Graph sync module."""
        try:
            hass = ctx.hass
            entry = ctx.entry
            
            # Get Core connection details from config entry
            core_url = entry.data.get("core_url", "http://localhost:5000")
            access_token = entry.data.get("access_token", "")
            
            if not core_url or not access_token:
                _LOGGER.warning("Brain Graph sync disabled: missing core_url or access_token")
                return
            
            # Set up Brain Graph sync service
            brain_graph_sync = await async_setup_brain_graph_sync(
                hass, entry.data, core_url, access_token
            )
            
            if brain_graph_sync:
                # Store in hass.data for later access
                if entry.entry_id not in hass.data[DOMAIN]:
                    hass.data[DOMAIN][entry.entry_id] = {}
                hass.data[DOMAIN][entry.entry_id]["brain_graph_sync"] = brain_graph_sync
                
                _LOGGER.info("Brain Graph sync module started successfully")
            else:
                _LOGGER.error("Failed to start Brain Graph sync service")
                
        except Exception as err:
            _LOGGER.error("Brain Graph sync module setup failed: %s", err)

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the Brain Graph sync module."""
        try:
            hass = ctx.hass
            entry = ctx.entry
            
            brain_graph_sync = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("brain_graph_sync")
            if brain_graph_sync:
                await async_unload_brain_graph_sync(brain_graph_sync)
                
                # Remove from hass.data
                if (entry.entry_id in hass.data.get(DOMAIN, {}) and 
                    "brain_graph_sync" in hass.data[DOMAIN][entry.entry_id]):
                    del hass.data[DOMAIN][entry.entry_id]["brain_graph_sync"]
                
            _LOGGER.info("Brain Graph sync module unloaded")
            return True
            
        except Exception as err:
            _LOGGER.error("Brain Graph sync module unload failed: %s", err)
            return False