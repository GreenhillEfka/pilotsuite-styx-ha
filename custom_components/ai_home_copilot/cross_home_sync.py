"""
Cross-Home Sharing Integration for AI Home CoPilot.

Bridges HA Integration with the Core Add-on's Cross-Home Sharing API.
Enables entity sync, discovery, and conflict resolution across multiple homes.

Privacy-first: Only metadata and anonymized patterns are shared.
Security: All sync traffic encrypted via Core Add-on.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import aiohttp
from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers import entity_registry
from homeassistant.const import EVENT_STATE_CHANGED, EVENT_CALL_SERVICE

from .const import DOMAIN
from .core.error_helpers import log_error_with_context

_LOGGER = logging.getLogger(__name__)

SHARING_API_BASE = "/api/v1/sharing"


@dataclass
class SharedEntity:
    """Represents an entity shared with another home."""
    entity_id: str
    shared_with: Set[str]  # Set of home_ids
    shared_by: str  # Source home_id
    permissions: str  # "read" or "read_write"
    last_sync: float
    sync_status: str  # "synced", "pending", "conflict", "error"


class CrossHomeClient:
    """
    Client for Cross-Home Sharing via Core Add-on API.
    
    Communicates with the Core Add-on's sharing endpoints to:
    - Discover other CoPilot homes on the network
    - Register entities for sharing
    - Sync entity state changes
    - Receive updates from remote homes
    """
    
    def __init__(
        self,
        hass: HomeAssistant,
        home_id: str,
        home_name: str,
        api_base: str = "http://localhost:8123",
        api_token: Optional[str] = None,
    ):
        """
        Initialize Cross-Home Client.
        
        Args:
            hass: Home Assistant instance
            home_id: Unique identifier for this home
            home_name: Display name for this home
            api_base: Core Add-on API base URL
            api_token: API token for authentication
        """
        self.hass = hass
        self.home_id = home_id
        self.home_name = home_name
        self.api_base = api_base.rstrip("/")
        self.api_token = api_token
        
        self._session: aiohttp.ClientSession | None = None
        self._is_initialized = False
        
        # Shared entities registry
        self.shared_entities: Dict[str, SharedEntity] = {}
        
        # Discovered peers
        self.peers: Dict[str, Dict[str, Any]] = {}
        
        # Conflict queue
        self._conflict_queue: List[Dict[str, Any]] = []
        
    async def async_initialize(self) -> None:
        """Initialize the client and start background tasks."""
        self._session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
        )
        
        # Load shared entities from storage
        await self._load_shared_entities()
        
        # Subscribe to HA events for syncing
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._on_state_changed)
        
        self._is_initialized = True
        _LOGGER.info("Cross-Home Client initialized for %s", self.home_id)
        
    async def async_shutdown(self) -> None:
        """Shutdown the client."""
        if self._session:
            await self._session.close()
            self._session = None
            
        self._is_initialized = False
        
    async def _load_shared_entities(self) -> None:
        """Load shared entities from Core Add-on."""
        try:
            data = await self._api_get(f"{SHARING_API_BASE}/entities")
            for entity_data in data.get("entities", []):
                entity = SharedEntity(
                    entity_id=entity_data["entity_id"],
                    shared_with=set(entity_data.get("shared_with", [])),
                    shared_by=entity_data.get("shared_by", self.home_id),
                    permissions=entity_data.get("permissions", "read"),
                    last_sync=entity_data.get("last_sync", 0),
                    sync_status=entity_data.get("sync_status", "pending"),
                )
                self.shared_entities[entity.entity_id] = entity
                
            _LOGGER.info("Loaded %d shared entities", len(self.shared_entities))
            
        except Exception as err:
            _LOGGER.warning("Failed to load shared entities: %s", err)
            
    async def _api_get(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request to Core Add-on API."""
        if not self._session:
            raise RuntimeError("Client not initialized")
            
        url = f"{self.api_base}{endpoint}"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()
            
    async def _api_post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request to Core Add-on API."""
        if not self._session:
            raise RuntimeError("Client not initialized")
            
        url = f"{self.api_base}{endpoint}"
        async with self._session.post(url, json=data) as resp:
            resp.raise_for_status()
            return await resp.json()
            
    async def _api_put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make PUT request to Core Add-on API."""
        if not self._session:
            raise RuntimeError("Client not initialized")
            
        url = f"{self.api_base}{endpoint}"
        async with self._session.put(url, json=data) as resp:
            resp.raise_for_status()
            return await resp.json()
            
    @callback
    def _on_state_changed(self, event: Event) -> None:
        """Handle state changes for synced entities."""
        entity_id = event.data.get("entity_id")
        if not entity_id or entity_id not in self.shared_entities:
            return
            
        # Queue sync task
        self.hass.async_create_task(self._sync_entity_change(event.data))
        
    async def _sync_entity_change(self, event_data: Dict[str, Any]) -> None:
        """Sync entity change to remote homes."""
        entity_id = event_data.get("entity_id")
        new_state = event_data.get("new_state")
        
        if not entity_id or not new_state:
            return
            
        entity = self.shared_entities.get(entity_id)
        if not entity or entity.sync_status == "conflict":
            return
            
        try:
            await self._api_post(f"{SHARING_API_BASE}/sync", {
                "entity_id": entity_id,
                "state": new_state.state,
                "attributes": dict(new_state.attributes) if new_state.attributes else {},
                "source_home": self.home_id,
                "timestamp": time.time(),
            })
            
            entity.last_sync = time.time()
            entity.sync_status = "synced"
            _LOGGER.debug("Synced %s to remote homes", entity_id)
            
        except Exception as err:
            entity.sync_status = "error"
            _LOGGER.warning("Failed to sync %s: %s", entity_id, err)
            
    async def async_discover_peers(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover other CoPilot homes on the network.
        
        Returns:
            Dict mapping home_id to peer info
        """
        try:
            data = await self._api_get(f"{SHARING_API_BASE}/discover")
            self.peers = data.get("peers", {})
            
            _LOGGER.info("Discovered %d peer homes", len(self.peers))
            return self.peers
            
        except Exception as err:
            _LOGGER.warning("Failed to discover peers: %s", err)
            return {}
            
    async def async_share_entity(
        self,
        entity_id: str,
        target_home_id: str,
        permissions: str = "read",
    ) -> bool:
        """
        Share an entity with another home.
        
        Args:
            entity_id: Entity to share
            target_home_id: Target home ID
            permissions: "read" or "read_write"
            
        Returns:
            True if successful
        """
        try:
            await self._api_post(f"{SHARING_API_BASE}/share", {
                "entity_id": entity_id,
                "source_home": self.home_id,
                "target_home": target_home_id,
                "permissions": permissions,
            })
            
            # Update local registry
            if entity_id in self.shared_entities:
                self.shared_entities[entity_id].shared_with.add(target_home_id)
            else:
                self.shared_entities[entity_id] = SharedEntity(
                    entity_id=entity_id,
                    shared_with={target_home_id},
                    shared_by=self.home_id,
                    permissions=permissions,
                    last_sync=0,
                    sync_status="pending",
                )
                
            _LOGGER.info("Shared %s with %s", entity_id, target_home_id)
            return True
            
        except Exception as err:
            _LOGGER.warning("Failed to share %s: %s", entity_id, err)
            return False
            
    async def async_unshare_entity(
        self,
        entity_id: str,
        target_home_id: str,
    ) -> bool:
        """
        Stop sharing an entity with another home.
        
        Args:
            entity_id: Entity to unshare
            target_home_id: Target home ID
            
        Returns:
            True if successful
        """
        try:
            await self._api_post(f"{SHARING_API_BASE}/unshare", {
                "entity_id": entity_id,
                "source_home": self.home_id,
                "target_home": target_home_id,
            })
            
            # Update local registry
            if entity_id in self.shared_entities:
                self.shared_entities[entity_id].shared_with.discard(target_home_id)
                if not self.shared_entities[entity_id].shared_with:
                    del self.shared_entities[entity_id]
                    
            _LOGGER.info("Unshared %s from %s", entity_id, target_home_id)
            return True
            
        except Exception as err:
            _LOGGER.warning("Failed to unshare %s: %s", entity_id, err)
            return False
            
    async def async_get_remote_entities(
        self,
        source_home_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get entities shared by another home.
        
        Args:
            source_home_id: Source home ID
            
        Returns:
            List of shared entity data
        """
        try:
            data = await self._api_get(f"{SHARING_API_BASE}/remote/{source_home_id}")
            return data.get("entities", [])
            
        except Exception as err:
            _LOGGER.warning("Failed to get remote entities from %s: %s", source_home_id, err)
            return []
            
    async def async_resolve_conflict(
        self,
        entity_id: str,
        resolution: str,
    ) -> bool:
        """
        Resolve a sync conflict.
        
        Args:
            entity_id: Entity with conflict
            resolution: "local_wins", "remote_wins", or "merge"
            
        Returns:
            True if resolved successfully
        """
        try:
            await self._api_post(f"{SHARING_API_BASE}/resolve", {
                "entity_id": entity_id,
                "source_home": self.home_id,
                "resolution": resolution,
            })
            
            if entity_id in self.shared_entities:
                self.shared_entities[entity_id].sync_status = "synced"
                
            _LOGGER.info("Resolved conflict for %s: %s", entity_id, resolution)
            return True
            
        except Exception as err:
            _LOGGER.warning("Failed to resolve conflict for %s: %s", entity_id, err)
            return False
            
    def get_stats(self) -> Dict[str, Any]:
        """Get cross-home sharing statistics."""
        status_counts = {"synced": 0, "pending": 0, "conflict": 0, "error": 0}
        for entity in self.shared_entities.values():
            status_counts[entity.sync_status] = status_counts.get(entity.sync_status, 0) + 1
            
        return {
            "home_id": self.home_id,
            "home_name": self.home_name,
            "peers_discovered": len(self.peers),
            "entities_shared": len(self.shared_entities),
            "sync_status": status_counts,
            "conflicts_pending": len(self._conflict_queue),
        }


async def get_cross_home_client(
    hass: HomeAssistant,
    home_id: str,
    home_name: str,
    api_base: str = "http://localhost:8123",
    api_token: Optional[str] = None,
) -> CrossHomeClient:
    """
    Get or create Cross-Home Client instance.
    
    Args:
        hass: Home Assistant instance
        home_id: Unique home identifier
        home_name: Display name
        api_base: Core Add-on API URL
        api_token: API token
        
    Returns:
        CrossHomeClient instance
    """
    dom_data = hass.data.get(DOMAIN, {})
    
    if "cross_home_client" in dom_data:
        return dom_data["cross_home_client"]
        
    client = CrossHomeClient(hass, home_id, home_name, api_base, api_token)
    await client.async_initialize()
    
    dom_data["cross_home_client"] = client
    hass.data[DOMAIN] = dom_data
    
    return client