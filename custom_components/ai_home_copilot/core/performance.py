"""Performance utilities for AI Home CoPilot.

Provides caching and optimization utilities for improved response times.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, Union

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")
K = TypeVar("K")


@dataclass
class CacheEntry(Generic[T]):
    """A cache entry with TTL and access metadata."""
    value: T
    created_at: float
    expires_at: float
    hits: int = 0
    last_access: float = field(default_factory=time.time)


class TTLCache(Generic[K, T]):
    """Thread-safe TTL cache with LRU eviction.
    
    Features:
    - Time-to-live (TTL) for automatic expiration
    - LRU eviction when max_size is reached
    - Hit/miss statistics
    - Async-safe for Home Assistant
    
    Usage:
        cache = TTLCache(max_size=100, default_ttl_seconds=30)
        cache.set("key", value)
        value = cache.get("key")
    """
    
    def __init__(
        self, 
        max_size: int = 100,
        default_ttl_seconds: float = 30.0,
        cleanup_interval_seconds: float = 60.0
    ):
        self._max_size = max_size
        self._default_ttl = default_ttl_seconds
        self._cleanup_interval = cleanup_interval_seconds
        self._cache: OrderedDict[K, CacheEntry[T]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
        self._last_cleanup = time.time()
    
    async def get(self, key: K) -> Optional[T]:
        """Get a value from cache if it exists and hasn't expired."""
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            # Check expiration
            if time.time() > entry.expires_at:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Move to end for LRU (most recently used)
            self._cache.move_to_end(key)
            entry.hits += 1
            entry.last_access = time.time()
            self._hits += 1
            
            return entry.value
    
    async def set(
        self, 
        key: K, 
        value: T, 
        ttl_seconds: Optional[float] = None
    ) -> None:
        """Set a value in cache with optional custom TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        now = time.time()
        
        async with self._lock:
            # Remove if exists (to update position)
            if key in self._cache:
                del self._cache[key]
            
            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = CacheEntry(
                value=value,
                created_at=now,
                expires_at=now + ttl,
                hits=0,
                last_access=now
            )
            
            # Periodic cleanup
            if now - self._last_cleanup > self._cleanup_interval:
                await self._cleanup_expired()
    
    async def delete(self, key: K) -> bool:
        """Remove a key from cache. Returns True if key existed."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    async def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        now = time.time()
        self._last_cleanup = now
        
        expired = [
            k for k, v in self._cache.items()
            if now > v.expires_at
        ]
        
        for key in expired:
            del self._cache[key]
        
        if expired:
            _LOGGER.debug("Cleaned up %d expired cache entries", len(expired))
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "default_ttl_seconds": self._default_ttl
        }


class EntityStateCache:
    """Cache for Home Assistant entity states with efficient queries.
    
    Optimizes repeated state lookups by caching entity states
    and providing fast domain/area filtering.
    """
    
    def __init__(
        self,
        ttl_seconds: float = 10.0,
        max_entities: int = 500
    ):
        self._cache = TTLCache[str, Dict[str, Any]](
            max_size=max_entities,
            default_ttl_seconds=ttl_seconds
        )
        self._domain_index: Dict[str, set] = {}
        self._area_index: Dict[str, set] = {}
        self._last_full_refresh: float = 0
    
    async def get_state(
        self, 
        hass, 
        entity_id: str,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get cached entity state."""
        if not force_refresh:
            cached = await self._cache.get(entity_id)
            if cached is not None:
                return cached
        
        # Fetch from HA
        state = hass.states.get(entity_id)
        if state is None:
            return None
        
        state_dict = {
            "entity_id": entity_id,
            "state": state.state,
            "attributes": dict(state.attributes),
            "last_changed": state.last_changed.isoformat() if state.last_changed else None,
            "last_updated": state.last_updated.isoformat() if state.last_updated else None
        }
        
        await self._cache.set(entity_id, state_dict)
        return state_dict
    
    async def get_domain_states(
        self,
        hass,
        domain: str,
        force_refresh: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """Get all states for a domain efficiently."""
        # Get all entity IDs for domain
        entity_ids = hass.states.async_entity_ids(domain)
        result = {}
        
        for entity_id in entity_ids:
            state = await self.get_state(hass, entity_id, force_refresh)
            if state:
                result[entity_id] = state
        
        return result
    
    async def invalidate_entity(self, entity_id: str) -> None:
        """Invalidate cache for a specific entity."""
        await self._cache.delete(entity_id)
    
    async def invalidate_domain(self, domain: str) -> int:
        """Invalidate all entities in a domain. Returns count invalidated."""
        count = 0
        # Note: This would need access to hass to get entity IDs
        # For now, we rely on TTL expiration
        return count
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.stats()


class MoodScoreCache:
    """Specialized cache for mood scores with zone and time-based invalidation.
    
    Mood scores are relatively stable but should be recalculated
    when relevant entity states change.
    """
    
    def __init__(self, ttl_seconds: float = 30.0):
        self._cache = TTLCache[str, Dict[str, Any]](
            max_size=50,  # Limited zones
            default_ttl_seconds=ttl_seconds
        )
        self._entity_zone_map: Dict[str, set] = {}  # entity_id -> set of zones
    
    def _cache_key(self, zone_name: str, context: Optional[str] = None) -> str:
        """Generate cache key for zone mood."""
        return f"mood:{zone_name}:{context or 'default'}"
    
    async def get_mood(
        self, 
        zone_name: str,
        context: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached mood score for a zone."""
        key = self._cache_key(zone_name, context)
        return await self._cache.get(key)
    
    async def set_mood(
        self,
        zone_name: str,
        mood_data: Dict[str, Any],
        context: Optional[str] = None,
        ttl_seconds: Optional[float] = None
    ) -> None:
        """Cache mood score for a zone."""
        key = self._cache_key(zone_name, context)
        await self._cache.set(key, mood_data, ttl_seconds)
    
    async def invalidate_zone(self, zone_name: str) -> None:
        """Invalidate all cached moods for a zone."""
        prefix = f"mood:{zone_name}:"
        async with self._cache._lock:
            keys_to_delete = [
                k for k in self._cache._cache.keys()
                if k.startswith(prefix)
            ]
            for key in keys_to_delete:
                del self._cache._cache[key]
    
    async def invalidate_for_entity(self, entity_id: str) -> int:
        """Invalidate all zones affected by entity change. Returns count."""
        zones = self._entity_zone_map.get(entity_id, set())
        count = 0
        for zone in zones:
            await self.invalidate_zone(zone)
            count += 1
        return count
    
    def register_entity_zone(self, entity_id: str, zone_name: str) -> None:
        """Register that an entity belongs to a zone for invalidation."""
        if entity_id not in self._entity_zone_map:
            self._entity_zone_map[entity_id] = set()
        self._entity_zone_map[entity_id].add(zone_name)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self._cache.stats()
        stats["entity_zone_mappings"] = len(self._entity_zone_map)
        return stats


# Decorator for caching async function results
def cached_result(
    cache: TTLCache,
    key_func: Optional[Callable] = None,
    ttl_seconds: Optional[float] = None
):
    """Decorator to cache async function results.
    
    Usage:
        cache = TTLCache(max_size=100, default_ttl_seconds=30)
        
        @cached_result(cache, key_func=lambda zone: f"mood:{zone}")
        async def get_mood_score(zone: str) -> dict:
            # Expensive computation
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}:{args}:{kwargs}"
            
            # Check cache
            cached = await cache.get(key)
            if cached is not None:
                return cached
            
            # Compute and cache
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl_seconds)
            return result
        
        return wrapper
    return decorator


# Global cache instances
_entity_state_cache: Optional[EntityStateCache] = None
_mood_score_cache: Optional[MoodScoreCache] = None


def get_entity_state_cache() -> EntityStateCache:
    """Get or create the global entity state cache."""
    global _entity_state_cache
    if _entity_state_cache is None:
        _entity_state_cache = EntityStateCache()
    return _entity_state_cache


def get_mood_score_cache() -> MoodScoreCache:
    """Get or create the global mood score cache."""
    global _mood_score_cache
    if _mood_score_cache is None:
        _mood_score_cache = MoodScoreCache()
    return _mood_score_cache


async def invalidate_caches_for_entity(entity_id: str) -> Dict[str, int]:
    """Invalidate all caches for an entity. Returns invalidation counts."""
    entity_cache = get_entity_state_cache()
    mood_cache = get_mood_score_cache()
    
    results = {}
    
    # Invalidate entity state
    await entity_cache.invalidate_entity(entity_id)
    results["entity_state"] = 1
    
    # Invalidate affected mood scores
    mood_inval = await mood_cache.invalidate_for_entity(entity_id)
    results["mood_scores"] = mood_inval
    
    _LOGGER.debug("Invalidated caches for %s: %s", entity_id, results)
    return results


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches."""
    return {
        "entity_state_cache": get_entity_state_cache().stats(),
        "mood_score_cache": get_mood_score_cache().stats()
    }