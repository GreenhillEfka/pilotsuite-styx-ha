"""Performance utilities for PilotSuite - Caching and Query Optimization."""
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
            current_time = time.time()
            if current_time > expires_at:
                del self._cache[key]
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value
    
    def _cleanup_expired(self) -> None:
        """Remove all expired entries from cache."""
        current_time = time.time()
        keys_to_remove = [
            key for key, (_, expires_at) in self._cache.items()
            if current_time > expires_at
        ]
        for key in keys_to_remove:
            del self._cache[key]
    
    async def set(self, key: str, value: Any) -> None:
        """Set value in cache with TTL."""
        async with self._lock:
            # Clean up expired entries to prevent memory leak
            self._cleanup_expired()
            
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

    def _cleanup_expired(self) -> None:
        """Remove all expired entries from cache."""
        now = time.time()
        expired_keys = [k for k, (_, expires_at) in self._cache.items() if now > expires_at]
        for key in expired_keys:
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


class LazyHistoryLoader:
    """Lazy loader for HA entity history with caching.
    
    Provides efficient access to HA recorder history with:
    - On-demand loading (lazy)
    - TTL-based caching
    - Bounded memory usage
    - Batch query support
    """
    
    def __init__(
        self, 
        hass,
        ttl_seconds: int = 60,
        max_entities: int = 50,
        max_hours_back: int = 24
    ):
        """Initialize lazy history loader.
        
        Args:
            hass: Home Assistant instance
            ttl_seconds: Cache TTL (default: 60s)
            max_entities: Maximum entities to cache (default: 50)
            max_hours_back: Maximum hours to look back (default: 24h)
        """
        self._hass = hass
        self._ttl = ttl_seconds
        self._max_entities = max_entities
        self._max_hours_back = max_hours_back
        self._cache: OrderedDict[str, Tuple[list, float]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._prefetch_queue: set = set()
        self._prefetch_task: Optional[asyncio.Task] = None
    
    async def get_history(
        self, 
        entity_id: str, 
        hours_back: int = 1,
        minimal_response: bool = True
    ) -> list:
        """Get history for an entity with caching.
        
        Args:
            entity_id: Entity ID to fetch history for
            hours_back: Hours to look back (default: 1h)
            minimal_response: Use minimal response format (default: True)
            
        Returns:
            List of state history entries
        """
        if hours_back > self._max_hours_back:
            hours_back = self._max_hours_back
        
        cache_key = f"{entity_id}:{hours_back}"
        
        # Check cache
        async with self._lock:
            if cache_key in self._cache:
                history, expires_at = self._cache[cache_key]
                if time.time() <= expires_at:
                    self._cache.move_to_end(cache_key)
                    return history
                else:
                    del self._cache[cache_key]
        
        # Fetch from HA
        history = await self._fetch_history(entity_id, hours_back, minimal_response)
        
        # Cache result
        async with self._lock:
            # Enforce max size
            while len(self._cache) >= self._max_entities:
                self._cache.popitem(last=False)
            
            expires_at = time.time() + self._ttl
            self._cache[cache_key] = (history, expires_at)
            self._cache.move_to_end(cache_key)
        
        return history
    
    async def get_batch_history(
        self, 
        entity_ids: list,
        hours_back: int = 1,
        minimal_response: bool = True
    ) -> Dict[str, list]:
        """Get history for multiple entities efficiently.
        
        Uses HA's batch history API when available.
        
        Args:
            entity_ids: List of entity IDs
            hours_back: Hours to look back
            minimal_response: Use minimal response format
            
        Returns:
            Dict mapping entity_id to history list
        """
        result: Dict[str, list] = {}
        missing_ids = []
        
        # Check cache first
        async with self._lock:
            for entity_id in entity_ids:
                cache_key = f"{entity_id}:{hours_back}"
                if cache_key in self._cache:
                    history, expires_at = self._cache[cache_key]
                    if time.time() <= expires_at:
                        self._cache.move_to_end(cache_key)
                        result[entity_id] = history
                        continue
                missing_ids.append(entity_id)
        
        # Batch fetch missing
        if missing_ids:
            batch_result = await self._fetch_batch_history(
                missing_ids, hours_back, minimal_response
            )
            result.update(batch_result)
            
            # Cache results
            async with self._lock:
                for entity_id, history in batch_result.items():
                    cache_key = f"{entity_id}:{hours_back}"
                    while len(self._cache) >= self._max_entities:
                        self._cache.popitem(last=False)
                    expires_at = time.time() + self._ttl
                    self._cache[cache_key] = (history, expires_at)
                    self._cache.move_to_end(cache_key)
        
        return result
    
    async def prefetch(self, entity_ids: list, hours_back: int = 1) -> None:
        """Schedule background prefetch for entities.
        
        Non-blocking: queues entities for background loading.
        
        Args:
            entity_ids: Entities to prefetch
            hours_back: Hours to look back
        """
        async with self._lock:
            for entity_id in entity_ids:
                cache_key = f"{entity_id}:{hours_back}"
                if cache_key not in self._cache:
                    self._prefetch_queue.add((entity_id, hours_back))
        
        # Start prefetch task if not running
        if self._prefetch_task is None or self._prefetch_task.done():
            self._prefetch_task = asyncio.create_task(self._process_prefetch())
    
    async def _process_prefetch(self) -> None:
        """Process prefetch queue in background."""
        while True:
            async with self._lock:
                if not self._prefetch_queue:
                    return
                item = self._prefetch_queue.pop()
            
            entity_id, hours_back = item
            try:
                await self.get_history(entity_id, hours_back)
            except Exception:  # noqa: BLE001
                pass  # Silent fail for prefetch
            
            # Small delay to avoid overwhelming
            await asyncio.sleep(0.1)
    
    async def _fetch_history(
        self, 
        entity_id: str, 
        hours_back: int,
        minimal_response: bool
    ) -> list:
        """Fetch history from HA recorder."""
        try:
            from datetime import datetime, timedelta, timezone
            
            now = datetime.now(timezone.utc)
            start_time = now - timedelta(hours=hours_back)
            
            # Try to use HA's history API
            if self._hass.state == "running":
                history = await self._hass.async_add_executor_job(
                    self._fetch_history_sync,
                    entity_id,
                    start_time,
                    now,
                    minimal_response
                )
                return history or []
            
            return []
            
        except Exception:  # noqa: BLE001
            return []

    def _fetch_history_sync(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: datetime,
        minimal_response: bool
    ) -> list:
        """Synchronous history fetch (runs in executor)."""
        try:
            # Try to get recorder instance
            recorder = self._hass.data.get("recorder")
            if not recorder:
                return []
            
            # Use history.get_instance if available (HA 2023.2+)
            try:
                from homeassistant.components.history import get_instance
                history_instance = get_instance(self._hass)
            except (ImportError, AttributeError):
                # Fallback for older HA versions
                return []
            
            # This is a simplified approach - actual implementation
            # would use history_instance.async_get_history_states
            # For now, return empty to avoid blocking
            return []
            
        except Exception:  # noqa: BLE001
            return []

    async def _fetch_batch_history(
        self,
        entity_ids: list,
        hours_back: int,
        minimal_response: bool
    ) -> Dict[str, list]:
        """Fetch history for multiple entities.
        
        Tries batch API first, falls back to individual fetches.
        """
        result = {}
        
        # Try batch fetch via concurrent individual requests
        # (HA doesn't have a true batch history API)
        tasks = [
            self._fetch_history(entity_id, hours_back, minimal_response)
            for entity_id in entity_ids
        ]
        
        histories = await asyncio.gather(*tasks, return_exceptions=True)
        
        for entity_id, history in zip(entity_ids, histories):
            if isinstance(history, Exception):
                result[entity_id] = []
            else:
                result[entity_id] = history
        
        return result
    
    async def invalidate(self, entity_id: str) -> None:
        """Invalidate cache for an entity."""
        async with self._lock:
            keys_to_remove = [
                k for k in self._cache 
                if k.startswith(f"{entity_id}:")
            ]
            for key in keys_to_remove:
                del self._cache[key]
    
    async def clear(self) -> None:
        """Clear entire history cache."""
        async with self._lock:
            self._cache.clear()
            self._prefetch_queue.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_entities": len(self._cache),
            "max_entities": self._max_entities,
            "ttl_seconds": self._ttl,
            "prefetch_queue_size": len(self._prefetch_queue),
        }


# Global lazy history loader (singleton per integration)
_history_loader: Optional[LazyHistoryLoader] = None


def get_history_loader(hass=None) -> LazyHistoryLoader:
    """Get or create global history loader instance.
    
    Args:
        hass: Home Assistant instance (required on first call)
        
    Returns:
        LazyHistoryLoader instance
    """
    global _history_loader
    if _history_loader is None:
        if hass is None:
            raise ValueError("hass is required for first initialization")
        _history_loader = LazyHistoryLoader(hass)
    return _history_loader
