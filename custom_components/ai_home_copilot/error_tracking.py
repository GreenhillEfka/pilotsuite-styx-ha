"""Convenience module for error tracking and diagnostics.

Provides easy-to-use functions for tracking errors across the integration
with automatic integration into the dev_surface error digest system.
"""
import logging
from typing import Any, Optional
from homeassistant.core import HomeAssistant

from .core.error_helpers import log_error_with_context, capture_error_for_diagnostics
from .core.modules.dev_surface import _get_kernel


def track_error(
    hass: HomeAssistant,
    entry_id: str,
    error: Exception,
    operation: str,
    context: Optional[dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """Track an error in both logging and dev_surface error digest.
    
    This is a convenience function that handles both logging with context
    and recording in the error digest for diagnostics.
    
    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID for this integration instance
        error: The caught exception
        operation: Description of what was being attempted
        context: Additional context data
        logger: Logger to use (if None, no logging is performed)
    """
    
    # Log the error with context if logger provided
    if logger is not None:
        log_error_with_context(logger, error, operation, context)
    
    # Record in dev_surface error digest for diagnostics
    try:
        kernel = _get_kernel(hass, entry_id)
        error_digest = kernel.get("errors")
        if error_digest and hasattr(error_digest, "record_exception"):
            error_digest.record_exception(error, operation, context)
    except Exception:  # noqa: BLE001
        # Don't let error tracking break the main flow
        pass


def get_error_summary(hass: HomeAssistant, entry_id: str) -> Optional[dict[str, Any]]:
    """Get current error summary for diagnostics.
    
    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID for this integration instance
        
    Returns:
        Error summary dict or None if not available
    """
    try:
        kernel = _get_kernel(hass, entry_id)
        error_digest = kernel.get("errors")
        if error_digest and hasattr(error_digest, "as_dict"):
            return error_digest.as_dict()
    except Exception:  # noqa: BLE001
        pass
    
    return None


def clear_errors(hass: HomeAssistant, entry_id: str) -> bool:
    """Clear all tracked errors for this integration instance.
    
    Args:
        hass: HomeAssistant instance
        entry_id: Config entry ID for this integration instance
        
    Returns:
        True if errors were cleared, False if error digest not available
    """
    try:
        kernel = _get_kernel(hass, entry_id)
        error_digest = kernel.get("errors")
        if error_digest and hasattr(error_digest, "clear"):
            error_digest.clear()
            return True
    except Exception:  # noqa: BLE001
        pass
    
    return False