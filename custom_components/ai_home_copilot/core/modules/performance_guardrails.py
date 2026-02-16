"""Performance Guardrails - Rate limiting and throttling"""

import time
import asyncio
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class RateLimit:
    """Rate limit configuration."""
    max_calls: int
    window_seconds: float
    
    _calls: list[float] = field(default_factory=list, repr=False)
    
    def is_allowed(self) -> bool:
        """Check if call is allowed."""
        now = time.time()
        # Remove old calls outside window
        self._calls = [t for t in self._calls if now - t < self.window_seconds]
        
        if len(self._calls) >= self.max_calls:
            return False
        
        self._calls.append(now)
        return True
    
    def time_until_reset(self) -> float:
        """Seconds until rate limit resets."""
        if not self._calls:
            return 0.0
        now = time.time()
        oldest = min(self._calls)
        return max(0.0, self.window_seconds - (now - oldest))


class PerformanceGuardrails:
    """Central performance guardrails."""
    
    # Default rate limits
    LIMITS = {
        "events": RateLimit(max_calls=200, window_seconds=60),    # 200/min
        "habitus": RateLimit(max_calls=100, window_seconds=60),   # 100/min
        "mood": RateLimit(max_calls=50, window_seconds=60),       # 50/min
        "suggestions": RateLimit(max_calls=30, window_seconds=60), # 30/min
        "api": RateLimit(max_calls=100, window_seconds=60),      # 100/min
    }
    
    def __init__(self):
        self._limits = {k: RateLimit(v.max_calls, v.window_seconds) 
                       for k, v in self.LIMITS.items()}
    
    def check(self, category: str) -> tuple[bool, Optional[float]]:
        """Check if action is allowed.
        
        Returns:
            (is_allowed, time_until_reset)
        """
        limit = self._limits.get(category)
        if not limit:
            return True, None
        
        if limit.is_allowed():
            return True, None
        
        return False, limit.time_until_reset()
    
    def get_status(self) -> dict[str, dict]:
        """Get status of all limits."""
        status = {}
        for name, limit in self._limits.items():
            now = time.time()
            recent = [t for t in limit._calls if now - t < limit.window_seconds]
            status[name] = {
                "used": len(recent),
                "max": limit.max_calls,
                "available": limit.max_calls - len(recent),
            }
        return status


# Global instance
_guardrails = PerformanceGuardrails()


def get_guardrails() -> PerformanceGuardrails:
    """Get global guardrails instance."""
    return _guardrails
