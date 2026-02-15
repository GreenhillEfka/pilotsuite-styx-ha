"""Performance utilities for AI Home CoPilot - Caching and Query Optimization."""
import asyncio
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Tuple


class TTLCache:
    """Thread-safe TTL cache with automatic expiration."""
    
    def __init__(self, ttl_seconds: int = 30, max_size: int = 100):
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self._lock:
            if key not in self._cache:
                return None
            
            value, expires_at = self._cache[key]
            if time.time() > expires_at:
                del self._cache[key]
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value
    
    async def set(self, key: str, value: Any) -> None:
        """Set value in cache with TTL."""
        async with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            
            expires_at = time.time() + self._ttl
            self._cache[key] = (value, expires_at)
            self._cache.move_to_end(key)
    
    async def invalidate(self, key: str) -> None:
        """Invalidate a specific key."""
        async with self._lock:
            self._cache.pop(key, None)
    
    async def clear(self) -> None:
        """Clear entire cache."""
        async with self._lock:
            self._cache.clear()
    
    async def invalidate_prefix(self, prefix: str) -> None:
        """Invalidate all keys starting with prefix."""
        async with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._cache[key]


class EntityStateCache:
    """Cache for HA entity states to reduce repeated queries."""
    
    def __init__(self, ttl_seconds: int = 5, max_entities: int = 200):
        self._cache = TTLCache(ttl_seconds=ttl_seconds, max_size=max_entities)
    
    async def get_entity(self, hass, entity_id: str) -> Optional[Any]:
        """Get entity state from cache or HA."""
        cached = await self._cache.get(entity_id)
        if cached is not None:
            return cached
        
        # Fetch from HA
        state = hass.states.get(entity_id)
        if state:
            await self._cache.set(entity_id, state)
        return state
    
    async def get_entities(self, hass, entity_ids: list) -> Dict[str, Any]:
        """Get multiple entities, batch-fetching unknown ones."""
        result = {}
        missing_ids = []
        
        # Check cache first
        for entity_id in entity_ids:
            cached = await self._cache.get(entity_id)
            if cached is not None:
                result[entity_id] = cached
            else:
                missing_ids.append(entity_id)
        
        # Batch fetch missing from HA
        if missing_ids:
            all_states = hass.states.async_all()
            state_map = {s.entity_id: s for s in all_states}
            
            for entity_id in missing_ids:
                if entity_id in state_map:
                    state = state_map[entity_id]
                    result[entity_id] = state
                    await self._cache.set(entity_id, state)
                else:
                    result[entity_id] = None
        
        return result
    
    async def invalidate(self, entity_id: str) -> None:
        """Invalidate cache for entity."""
        await self._cache.invalidate(entity_id)
    
    async def invalidate_prefix(self, prefix: str) -> None:
        """Invalidate all entities starting with prefix."""
        await self._cache.invalidate_prefix(prefix)


class DomainFilter:
    """Helper for efficient domain-filtered state queries."""
    
    @staticmethod
    def get_entities_by_domain(hass, domains: list) -> Dict[str, Any]:
        """Get all entities for given domains in one pass."""
        all_states = hass.states.async_all()
        result = {}
        
        for state in all_states:
            domain = state.entity_id.split('.')[0]
            if domain in domains:
                result[state.entity_id] = state
        
        return result


# Global cache instances (singleton per integration)
_mood_cache: Optional[TTLCache] = None
_entity_cache: Optional[EntityStateCache] = None


def get_mood_cache() -> TTLCache:
    """Get or create global mood cache instance."""
    global _mood_cache
    if _mood_cache is None:
        _mood_cache = TTLCache(ttl_seconds=30, max_size=50)
    return _mood_cache


def get_entity_cache() -> EntityStateCache:
    """Get or create global entity state cache instance."""
    global _entity_cache
    if _entity_cache is None:
        _entity_cache = EntityStateCache(ttl_seconds=5, max_entities=200)
    return _entity_cache
