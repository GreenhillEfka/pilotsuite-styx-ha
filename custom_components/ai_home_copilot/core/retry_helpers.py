"""Retry mechanisms and error recovery for AI Home CoPilot.

Provides:
- Exponential backoff retry decorator
- Circuit breaker pattern
- Fallback strategies
- API error handling utilities
"""
from __future__ import annotations

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

import aiohttp
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        retry_on_exceptions: tuple = (asyncio.TimeoutError, aiohttp.ClientError, ConnectionError),
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_on_exceptions = retry_on_exceptions


# Default retry configuration
DEFAULT_RETRY_CONFIG = RetryConfig()


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay with exponential backoff.
    
    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
    
    Returns:
        Delay in seconds
    """
    delay = min(
        config.base_delay * (config.exponential_base ** attempt),
        config.max_delay
    )
    # Add jitter (±10%)
    import random
    jitter = delay * 0.1 * (2 * random.random() - 1)
    return delay + jitter


async def async_retry(
    func: Callable[..., T],
    *args,
    config: RetryConfig = DEFAULT_RETRY_CONFIG,
    logger: Optional[logging.Logger] = None,
    **kwargs,
) -> T:
    """Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for the function
        config: Retry configuration
        logger: Optional logger for error messages
        **kwargs: Keyword arguments for the function
    
    Returns:
        Result of the function
    
    Raises:
        Last exception if all retries fail
    """
    log = logger or _LOGGER
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except config.retry_on_exceptions as e:
            last_exception = e
            if attempt < config.max_attempts - 1:
                delay = calculate_delay(attempt, config)
                log.warning(
                    "Retry attempt %d/%d after %.1fs: %s - %s",
                    attempt + 1,
                    config.max_attempts,
                    delay,
                    func.__name__,
                    str(e),
                )
                await asyncio.sleep(delay)
            else:
                log.error(
                    "All %d retry attempts failed for %s: %s",
                    config.max_attempts,
                    func.__name__,
                    str(e),
                )
    
    raise last_exception


def retry_sync(
    func: Callable[..., T],
    *args,
    config: RetryConfig = DEFAULT_RETRY_CONFIG,
    logger: Optional[logging.Logger] = None,
    **kwargs,
) -> T:
    """Retry a synchronous function with exponential backoff.
    
    Args:
        func: Function to retry
        *args: Positional arguments for the function
        config: Retry configuration
        logger: Optional logger for error messages
        **kwargs: Keyword arguments for the function
    
    Returns:
        Result of the function
    
    Raises:
        Last exception if all retries fail
    """
    import time
    log = logger or _LOGGER
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            return func(*args, **kwargs)
        except config.retry_on_exceptions as e:
            last_exception = e
            if attempt < config.max_attempts - 1:
                delay = calculate_delay(attempt, config)
                log.warning(
                    "Retry attempt %d/%d after %.1fs: %s - %s",
                    attempt + 1,
                    config.max_attempts,
                    delay,
                    func.__name__,
                    str(e),
                )
                time.sleep(delay)
            else:
                log.error(
                    "All %d retry attempts failed for %s: %s",
                    config.max_attempts,
                    func.__name__,
                    str(e),
                )
    
    raise last_exception


class CircuitBreaker:
    """Circuit breaker pattern implementation.
    
    Prevents repeated calls to failing services by "opening" the circuit
    after a threshold of failures.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"  # closed, open, half_open
    
    @property
    def state(self) -> str:
        """Get current circuit state."""
        if self._state == "open":
            # Check if we should transition to half-open
            if self._last_failure_time is not None:
                import time
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = "half_open"
        return self._state
    
    def record_success(self) -> None:
        """Record a successful call."""
        self._failure_count = 0
        self._state = "closed"
    
    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        import time
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            _LOGGER.warning(
                "Circuit breaker opened after %d failures",
                self._failure_count,
            )
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Result of the function
        
        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        if self.state == "open":
            raise CircuitBreakerOpen(
                f"Circuit breaker is open. Recovery timeout: {self.recovery_timeout}s"
            )
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exception as e:
            self.record_failure()
            raise


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class FallbackStrategy:
    """Provides fallback strategies when primary service fails."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self._logger = logger or _LOGGER
        self._fallbacks: Dict[str, Callable] = {}
    
    def register_fallback(self, name: str, func: Callable) -> None:
        """Register a fallback function.
        
        Args:
            name: Name of the fallback
            func: Fallback function to call
        """
        self._fallbacks[name] = func
    
    async def execute(
        self,
        primary_func: Callable,
        *args,
        fallback_name: Optional[str] = None,
        default_return: Any = None,
        **kwargs,
    ) -> Any:
        """Execute primary function with fallback support.
        
        Args:
            primary_func: Primary function to try first
            *args: Positional arguments
            fallback_name: Name of fallback to use on failure
            default_return: Default value if all fail
            **kwargs: Keyword arguments
        
        Returns:
            Result of primary or fallback function
        """
        try:
            return await primary_func(*args, **kwargs)
        except Exception as e:
            self._logger.warning(
                "Primary function failed: %s. Trying fallback...",
                str(e),
            )
            
            if fallback_name and fallback_name in self._fallbacks:
                try:
                    fallback_func = self._fallbacks[fallback_name]
                    return await fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    self._logger.error(
                        "Fallback %s also failed: %s",
                        fallback_name,
                        str(fallback_error),
                    )
            
            return default_return


class APIErrorHandler:
    """Handles API errors with retry and fallback support."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        name: str = "API",
        logger: Optional[logging.Logger] = None,
    ):
        self._hass = hass
        self._name = name
        self._logger = logger or _LOGGER
        
        # Create circuit breaker for this API
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
        )
        
        # Create fallback strategy
        self._fallback_strategy = FallbackStrategy(logger=self._logger)
    
    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get the circuit breaker."""
        return self._circuit_breaker
    
    @property
    def fallback_strategy(self) -> FallbackStrategy:
        """Get the fallback strategy."""
        return self._fallback_strategy
    
    async def call_with_retry(
        self,
        func: Callable,
        *args,
        use_circuit_breaker: bool = True,
        retry_config: Optional[RetryConfig] = None,
        **kwargs,
    ) -> Any:
        """Call function with retry and circuit breaker.
        
        Args:
            func: Function to call
            *args: Positional arguments
            use_circuit_breaker: Whether to use circuit breaker
            retry_config: Retry configuration
            **kwargs: Keyword arguments
        
        Returns:
            Result of the function
        """
        config = retry_config or DEFAULT_RETRY_CONFIG
        
        async def _call():
            if use_circuit_breaker:
                return await self._circuit_breaker.call(func, *args, **kwargs)
            return await func(*args, **kwargs)
        
        try:
            return await async_retry(_call, config=config, logger=self._logger)
        except Exception as e:
            self._logger.error(
                "API call to %s failed after retries: %s",
                self._name,
                str(e),
            )
            raise


# Decorator for easy retry usage
def async_retry_decorator(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
):
    """Decorator for adding retry logic to async functions.
    
    Usage:
        @async_retry_decorator(max_attempts=3)
        async def my_function():
            ...
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await async_retry(func, *args, config=config, **kwargs)
        return wrapper
    return decorator
