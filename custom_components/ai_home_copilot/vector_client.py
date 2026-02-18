"""Vector Store Client for Home Assistant Integration.

Provides client for connecting to the Core Add-on Vector Store API.
Used for:
- Entity embedding synchronization
- User preference similarity matching
- Pattern-based recommendations

Design Doc: docs/MUPL_PHASE2.md
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional

import aiohttp
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN
from .multi_user_preferences import MultiUserPreferenceModule

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

# Default sync interval
DEFAULT_SYNC_INTERVAL = timedelta(hours=6)


@dataclass
class VectorStoreConfig:
    """Configuration for vector store client."""
    
    api_url: str = "http://localhost:8909"
    api_token: str | None = None
    sync_interval: timedelta = DEFAULT_SYNC_INTERVAL
    enabled: bool = True
    similarity_threshold: float = 0.7
    

@dataclass
class SimilarityResult:
    """Result of a similarity search."""
    
    id: str
    similarity: float
    entry_type: str
    metadata: dict[str, Any]
    

@dataclass
class EntityEmbedding:
    """Embedding for an entity."""
    
    entity_id: str
    domain: str | None = None
    area: str | None = None
    capabilities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    

@dataclass
class UserPreferenceEmbedding:
    """Embedding for user preferences."""
    
    user_id: str
    preferences: dict[str, Any] = field(default_factory=dict)
    

@dataclass
class PatternEmbedding:
    """Embedding for a pattern."""
    
    pattern_id: str
    pattern_type: str = "learned"
    entities: list[str] = field(default_factory=list)
    conditions: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


class VectorStoreClient:
    """Client for the Core Add-on Vector Store API.
    
    Features:
    - Entity embedding synchronization
    - User preference similarity matching
    - Pattern-based recommendations
    - Automatic periodic sync
    """
    
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        config: VectorStoreConfig | None = None,
    ) -> None:
        """Initialize the vector store client."""
        self.hass = hass
        self.config_entry = config_entry
        self.config = config or VectorStoreConfig()
        
        self._session: aiohttp.ClientSession | None = None
        self._unsub_trackers: list[Any] = []
        self._sync_task: asyncio.Task | None = None
        
    async def async_setup(self) -> None:
        """Set up the vector store client."""
        if not self.config.enabled:
            _LOGGER.info("Vector Store Client disabled")
            return
            
        _LOGGER.info("Setting up Vector Store Client")
        
        # Create HTTP session
        self._session = aiohttp.ClientSession(
            base_url=self.config.api_url,
            headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=30),
        )
        
        # Start periodic sync
        if self.config.sync_interval.total_seconds() > 0:
            unsub = async_track_time_interval(
                self.hass,
                self._async_sync_entities,
                self.config.sync_interval,
            )
            self._unsub_trackers.append(unsub)
            
        # Initial sync
        self.hass.async_create_task(self._async_sync_entities(None))
        
        _LOGGER.info("Vector Store Client initialized")
        
    async def async_unload(self) -> None:
        """Unload the vector store client."""
        for unsub in self._unsub_trackers:
            unsub()
        self._unsub_trackers.clear()
        
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            
        if self._session:
            await self._session.close()
            self._session = None
            
    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.config.api_token:
            headers["X-Auth-Token"] = self.config.api_token
        return headers
        
    async def _async_sync_entities(self, _now: datetime | None) -> None:
        """Sync entity embeddings to the vector store."""
        try:
            _LOGGER.debug("Starting entity sync to vector store")
            
            # Collect entity data
            entities = []
            for state in self.hass.states.async_all():
                if state.entity_id.startswith(("sensor.", "binary_sensor.", "input_")):
                    continue  # Skip sensors and inputs
                    
                entity_data = self._extract_entity_data(state)
                entities.append(entity_data)
                
            if not entities:
                _LOGGER.debug("No entities to sync")
                return
                
            # Bulk upload
            result = await self.bulk_create_embeddings(
                entities=entities,
            )
            
            _LOGGER.info(
                "Vector store sync complete: %d entities created, %d failed",
                result.get("entities", {}).get("created", 0),
                result.get("entities", {}).get("failed", 0),
            )
            
        except Exception as e:
            _LOGGER.error("Failed to sync entities to vector store: %s", e)
            
    def _extract_entity_data(self, state) -> dict[str, Any]:
        """Extract entity data for embedding."""
        entity_id = state.entity_id
        domain = entity_id.split(".")[0]
        
        # Get area from registry
        area = None
        entity_registry = self.hass.data.get("entity_registry")
        if entity_registry:
            entry = entity_registry.async_get(entity_id)
            if entry and entry.area_id:
                area_registry = self.hass.data.get("area_registry")
                if area_registry:
                    area = area_registry.async_get_area(entry.area_id)
                    if area:
                        area = area.name
                        
        # Get capabilities from state
        capabilities = []
        attrs = state.attributes
        if "brightness" in attrs:
            capabilities.append("brightness")
        if "color_temp" in attrs or "color_temp_kelvin" in attrs:
            capabilities.append("color_temp")
        if "rgb_color" in attrs or "hs_color" in attrs:
            capabilities.append("color")
        if "temperature" in attrs:
            capabilities.append("temperature")
        if "volume_level" in attrs:
            capabilities.append("volume")
            
        return {
            "id": entity_id,
            "domain": domain,
            "area": area,
            "capabilities": capabilities,
            "tags": [],
            "state": {
                "state": state.state,
                "attributes": dict(attrs),
            },
        }
        
    # ==================== API Methods ====================
    
    async def create_entity_embedding(
        self,
        entity: EntityEmbedding,
    ) -> dict[str, Any]:
        """Create embedding for an entity.
        
        Args:
            entity: Entity embedding data
            
        Returns:
            API response
        """
        if not self._session:
            raise RuntimeError("Vector Store Client not initialized")
            
        payload = {
            "type": "entity",
            "id": entity.entity_id,
            "domain": entity.domain,
            "area": entity.area,
            "capabilities": entity.capabilities,
            "tags": entity.tags,
            "state": entity.state,
        }
        
        async with self._session.post("/api/v1/vector/embeddings", json=payload) as resp:
            data = await resp.json()
            if resp.status not in (200, 201):
                raise RuntimeError(f"API error: {data.get('error', resp.status)}")
            return data
            
    async def create_user_preference_embedding(
        self,
        user_pref: UserPreferenceEmbedding,
    ) -> dict[str, Any]:
        """Create embedding for user preferences.
        
        Args:
            user_pref: User preference embedding data
            
        Returns:
            API response
        """
        if not self._session:
            raise RuntimeError("Vector Store Client not initialized")
            
        payload = {
            "type": "user_preference",
            "id": user_pref.user_id,
            "preferences": user_pref.preferences,
        }
        
        async with self._session.post("/api/v1/vector/embeddings", json=payload) as resp:
            data = await resp.json()
            if resp.status not in (200, 201):
                raise RuntimeError(f"API error: {data.get('error', resp.status)}")
            return data
            
    async def create_pattern_embedding(
        self,
        pattern: PatternEmbedding,
    ) -> dict[str, Any]:
        """Create embedding for a pattern.
        
        Args:
            pattern: Pattern embedding data
            
        Returns:
            API response
        """
        if not self._session:
            raise RuntimeError("Vector Store Client not initialized")
            
        payload = {
            "type": "pattern",
            "id": pattern.pattern_id,
            "pattern_type": pattern.pattern_type,
            "entities": pattern.entities,
            "conditions": pattern.conditions,
            "confidence": pattern.confidence,
        }
        
        async with self._session.post("/api/v1/vector/embeddings", json=payload) as resp:
            data = await resp.json()
            if resp.status not in (200, 201):
                raise RuntimeError(f"API error: {data.get('error', resp.status)}")
            return data
            
    async def bulk_create_embeddings(
        self,
        entities: list[dict[str, Any]] | None = None,
        user_preferences: list[dict[str, Any]] | None = None,
        patterns: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create multiple embeddings at once.
        
        Args:
            entities: List of entity embedding data
            user_preferences: List of user preference data
            patterns: List of pattern data
            
        Returns:
            API response with creation counts
        """
        if not self._session:
            raise RuntimeError("Vector Store Client not initialized")
            
        payload = {
            "entities": entities or [],
            "user_preferences": user_preferences or [],
            "patterns": patterns or [],
        }
        
        async with self._session.post("/api/v1/vector/embeddings/bulk", json=payload) as resp:
            data = await resp.json()
            if resp.status not in (200, 201):
                raise RuntimeError(f"API error: {data.get('error', resp.status)}")
            return data
            
    async def find_similar(
        self,
        entry_id: str,
        entry_type: str | None = None,
        limit: int = 10,
        threshold: float | None = None,
    ) -> list[SimilarityResult]:
        """Find similar entries.
        
        Args:
            entry_id: Entry ID to find similar for
            entry_type: Filter by type (entity, user_preference, pattern)
            limit: Maximum number of results
            threshold: Minimum similarity threshold
            
        Returns:
            List of SimilarityResult objects
        """
        if not self._session:
            raise RuntimeError("Vector Store Client not initialized")
            
        params = {"limit": str(limit)}
        if entry_type:
            params["type"] = entry_type
        if threshold is not None:
            params["threshold"] = str(threshold)
            
        async with self._session.get(
            f"/api/v1/vector/similar/{entry_id}",
            params=params,
        ) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise RuntimeError(f"API error: {data.get('error', resp.status)}")
                
        return [
            SimilarityResult(
                id=r["id"],
                similarity=r["similarity"],
                entry_type=r["type"],
                metadata=r.get("metadata", {}),
            )
            for r in data.get("results", [])
        ]
        
    async def find_similar_entities(
        self,
        entity_id: str,
        limit: int = 10,
        threshold: float | None = None,
    ) -> list[SimilarityResult]:
        """Find entities similar to a given entity.
        
        Args:
            entity_id: Entity ID to find similar for
            limit: Maximum number of results
            threshold: Minimum similarity threshold
            
        Returns:
            List of similar entities
        """
        return await self.find_similar(
            entry_id=entity_id,
            entry_type="entity",
            limit=limit,
            threshold=threshold,
        )
        
    async def find_similar_users(
        self,
        user_id: str,
        limit: int = 10,
        threshold: float | None = None,
    ) -> list[SimilarityResult]:
        """Find users with similar preferences.
        
        Args:
            user_id: User ID to find similar for
            limit: Maximum number of results
            threshold: Minimum similarity threshold
            
        Returns:
            List of similar users
        """
        return await self.find_similar(
            entry_id=f"user_pref:{user_id}",
            entry_type="user_preference",
            limit=limit,
            threshold=threshold,
        )
        
    async def get_similarity(
        self,
        id1: str,
        id2: str,
    ) -> float:
        """Get similarity between two entries.
        
        Args:
            id1: First entry ID
            id2: Second entry ID
            
        Returns:
            Similarity score (0.0 - 1.0)
        """
        if not self._session:
            raise RuntimeError("Vector Store Client not initialized")
            
        payload = {"id1": id1, "id2": id2}
        
        async with self._session.post("/api/v1/vector/similarity", json=payload) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise RuntimeError(f"API error: {data.get('error', resp.status)}")
                
        return data.get("similarity", 0.0)
        
    async def get_vector_stats(self) -> dict[str, Any]:
        """Get vector store statistics.
        
        Returns:
            Stats dict
        """
        if not self._session:
            raise RuntimeError("Vector Store Client not initialized")
            
        async with self._session.get("/api/v1/vector/stats") as resp:
            data = await resp.json()
            if resp.status != 200:
                raise RuntimeError(f"API error: {data.get('error', resp.status)}")
            return data.get("stats", {})
            
    async def delete_embedding(self, entry_id: str) -> bool:
        """Delete an embedding.
        
        Args:
            entry_id: Entry ID to delete
            
        Returns:
            True if deleted
        """
        if not self._session:
            raise RuntimeError("Vector Store Client not initialized")
            
        async with self._session.delete(f"/api/v1/vector/vectors/{entry_id}") as resp:
            data = await resp.json()
            if resp.status not in (200, 204):
                raise RuntimeError(f"API error: {data.get('error', resp.status)}")
            return data.get("ok", False)
            
    # ==================== Preference Learning Helpers ====================
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferences: dict[str, Any],
    ) -> dict[str, Any]:
        """Update user preferences in vector store.
        
        Args:
            user_id: User identifier
            preferences: Preference dict (brightness, temperature, volume, mood)
            
        Returns:
            API response
        """
        return await self.create_user_preference_embedding(
            UserPreferenceEmbedding(
                user_id=user_id,
                preferences=preferences,
            )
        )
        
    async def get_user_similarity_recommendations(
        self,
        user_id: str,
        entity_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Get recommendations based on similar users.
        
        Finds users with similar preferences and returns their
        settings for the given entity.
        
        Args:
            user_id: Current user ID
            entity_id: Entity to get recommendations for
            limit: Maximum recommendations
            
        Returns:
            List of recommendation dicts
        """
        try:
            # Get MUPL module for actual preference data
            mupl = get_mupl_module(self.hass)
            
            # Find similar users
            similar_users = await self.find_similar_users(
                user_id=user_id,
                limit=limit,
                threshold=0.6,
            )
            
            if not similar_users:
                return []
            
            # Get real preferences from similar users via MUPL
            recommendations = []
            
            if mupl:
                all_users = mupl.get_all_users()
                
                for result in similar_users:
                    similar_user_id = result.metadata.get("user_id", result.id)
                    if similar_user_id != user_id and similar_user_id in all_users:
                        user_prefs = all_users[similar_user_id].preferences
                        # Extract entity-specific preference if exists
                        entity_pref = user_prefs.get(entity_id) if user_prefs else None
                        
                        recommendations.append({
                            "similar_user": similar_user_id,
                            "similarity": result.similarity,
                            "entity": entity_id,
                            "preference": entity_pref,
                            "hint": f"User {similar_user_id} prefers {entity_pref} (similarity: {result.similarity:.2f})",
                        })
            else:
                # Fallback: return similarity-based hints
                for result in similar_users:
                    similar_user_id = result.metadata.get("user_id", result.id)
                    if similar_user_id != user_id:
                        recommendations.append({
                            "similar_user": similar_user_id,
                            "similarity": result.similarity,
                            "entity": entity_id,
                            "hint": f"User {similar_user_id} has similar preferences (similarity: {result.similarity:.2f})",
                        })
                    
            return recommendations
            
        except Exception as e:
            _LOGGER.warning("Failed to get user similarity recommendations: %s", e)
            return []


# ==================== Module Accessor ====================

_VECTOR_CLIENT_KEY = f"{DOMAIN}_vector_client"


def get_vector_client(hass: HomeAssistant) -> VectorStoreClient | None:
    """Get the vector store client from hass.data."""
    for entry_id, entry_data in hass.data.get(DOMAIN, {}).items():
        if isinstance(entry_data, dict) and _VECTOR_CLIENT_KEY in entry_data:
            return entry_data[_VECTOR_CLIENT_KEY]
    return None


def set_vector_client(
    hass: HomeAssistant,
    entry_id: str,
    client: VectorStoreClient,
) -> None:
    """Store the vector store client in hass.data."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if entry_id not in hass.data[DOMAIN]:
        hass.data[DOMAIN][entry_id] = {}
    hass.data[DOMAIN][entry_id][_VECTOR_CLIENT_KEY] = client

# ==================== MUPL Integration ====================

def get_mupl_module(hass: HomeAssistant) -> MultiUserPreferenceModule | None:
    """Get the MUPL module from hass.data."""
    from .multi_user_preferences import get_mupl_module as _get_mupl
    return _get_mupl(hass)
