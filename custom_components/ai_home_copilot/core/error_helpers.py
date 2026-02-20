"""Enhanced error handling utilities for PilotSuite.

Provides structured error capture with privacy-safe traceback logging and
better error context for diagnostics.
"""
import logging
import traceback
import sys
from typing import Any, Optional
from datetime import datetime, timezone

_LOGGER = logging.getLogger(__name__)


def format_error_context(
    error: Exception,
    operation: str,
    context: Optional[dict[str, Any]] = None,
    include_traceback: bool = True,
    max_frames: int = 10
) -> dict[str, Any]:
    """Format error with context for structured logging and diagnostics.
    
    Args:
        error: The caught exception
        operation: Description of what was being attempted
        context: Additional context data (will be sanitized)
        include_traceback: Whether to include formatted traceback
        max_frames: Maximum number of traceback frames to include
        
    Returns:
        Structured error data suitable for logging and diagnostics
    """
    error_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": str(operation),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": _sanitize_context(context or {}),
    }
    
    if include_traceback:
        try:
            tb_lines = traceback.format_exception(
                type(error), error, error.__traceback__, limit=max_frames
            )
            # Remove sensitive paths and keep only relevant frames
            sanitized_tb = _sanitize_traceback(tb_lines)
            error_data["traceback"] = sanitized_tb
            error_data["traceback_summary"] = _extract_traceback_summary(sanitized_tb)
        except Exception:  # noqa: BLE001
            error_data["traceback"] = "Failed to extract traceback"
            
    return error_data


def _sanitize_context(context: dict[str, Any]) -> dict[str, Any]:
    """Sanitize context data to remove sensitive information."""
    sanitized = {}
    
    for key, value in context.items():
        if any(sensitive in key.lower() for sensitive in ["token", "password", "key", "secret"]):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str) and len(value) > 200:
            sanitized[key] = value[:200] + "...[truncated]"
        elif isinstance(value, (list, tuple)) and len(value) > 10:
            sanitized[key] = f"<{type(value).__name__} with {len(value)} items>"
        else:
            sanitized[key] = value
            
    return sanitized


def _sanitize_traceback(tb_lines: list[str]) -> list[str]:
    """Sanitize traceback lines to remove absolute paths and sensitive info."""
    sanitized = []
    
    for line in tb_lines:
        # Replace absolute paths with relative ones
        if "/config/.openclaw/workspace" in line:
            line = line.replace("/config/.openclaw/workspace", ".")
        
        # Remove other sensitive paths
        line = line.replace("/usr/lib/python", "[python]")
        line = line.replace("/home/", "[home]/")
        
        # Keep only PilotSuite frames and immediate neighbors
        if any(marker in line for marker in [
            "ai_home_copilot", "copilot_core", "custom_components",
            "File \"<", "Traceback", "Exception", "Error"
        ]):
            sanitized.append(line.rstrip())
    
    return sanitized


def _extract_traceback_summary(tb_lines: list[str]) -> str:
    """Extract a concise summary of the error location."""
    if not tb_lines:
        return "No traceback available"
        
    # Find the last frame in our code
    our_frames = []
    for line in tb_lines:
        if "ai_home_copilot" in line and "File " in line:
            # Extract file and line number
            try:
                file_part = line.split(", line ")[0].split("File ")[-1].strip('"')
                line_part = line.split(", line ")[1].split(",")[0]
                our_frames.append(f"{file_part}:{line_part}")
            except (IndexError, ValueError):
                continue
                
    if our_frames:
        return f"Last frame: {our_frames[-1]}"
    else:
        return "Error outside PilotSuite code"


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    operation: str,
    context: Optional[dict[str, Any]] = None,
    level: int = logging.ERROR
) -> None:
    """Log error with full context and structured data.
    
    Args:
        logger: Logger instance to use
        error: The caught exception
        operation: Description of what was being attempted
        context: Additional context data
        level: Logging level to use
    """
    error_data = format_error_context(
        error, operation, context, include_traceback=True
    )
    
    # Log main error message
    logger.log(level, "%s failed: %s", operation, error_data["error_message"])
    
    # Log context if available
    if error_data.get("context"):
        logger.debug("Error context: %s", error_data["context"])
        
    # Log traceback summary for easier debugging
    if error_data.get("traceback_summary"):
        logger.log(level, "Error location: %s", error_data["traceback_summary"])
        
    # Full traceback at debug level
    if error_data.get("traceback"):
        logger.debug("Full traceback:\n%s", "\n".join(error_data["traceback"]))


def capture_error_for_diagnostics(
    error: Exception,
    operation: str,
    context: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Capture error data for diagnostics (without logging).
    
    This is useful for collecting error data that will be included in
    diagnostics reports or error digest systems.
    """
    return format_error_context(
        error, operation, context, include_traceback=True, max_frames=5
    )