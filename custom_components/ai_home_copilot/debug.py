"""Debug mode sensor and services for HA Integration v0.9.

Features:
- Toggle debug mode via service
- Persistent debug state
- Detailed debug attributes
- Log level control
- Debug history buffer
"""
from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEBUG_MODE_ENTITY_ID = "sensor.ai_home_copilot_debug_mode_enabled"
DEBUG_HISTORY_SIZE = 50
DEBUG_STORAGE_KEY = "ai_home_copilot_debug_state"
DEBUG_STORAGE_VERSION = 1


class DebugBuffer:
    """Circular buffer for debug messages."""
    
    def __init__(self, max_size: int = DEBUG_HISTORY_SIZE):
        self._buffer: deque = deque(maxlen=max_size)
    
    def add(self, message: str, level: str = "debug", context: dict | None = None) -> None:
        """Add a debug message to the buffer."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "context": context or {},
        }
        self._buffer.append(entry)
    
    def get_all(self) -> list[dict]:
        """Get all buffered messages."""
        return list(self._buffer)
    
    def clear(self) -> None:
        """Clear the buffer."""
        self._buffer.clear()
    
    def get_recent(self, count: int = 10) -> list[dict]:
        """Get most recent messages."""
        return list(self._buffer)[-count:]


# Global debug buffer
_debug_buffer = DebugBuffer()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up debug mode sensor and services."""
    
    # Initialize debug state
    store = Store(hass, DEBUG_STORAGE_VERSION, DEBUG_STORAGE_KEY)
    stored = await store.async_load() or {}
    
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    
    hass.data[DOMAIN]["debug_mode"] = stored.get("enabled", False)
    hass.data[DOMAIN]["debug_store"] = store
    hass.data[DOMAIN]["debug_buffer"] = _debug_buffer
    hass.data[DOMAIN]["debug_log_level"] = stored.get("log_level", "INFO")
    
    # Add sensor
    async_add_entities([DebugModeSensor(hass)], update_before_add=True)
    
    # Register services
    async def async_enable_debug(call: ServiceCall) -> None:
        """Enable debug mode."""
        hass.data[DOMAIN]["debug_mode"] = True
        hass.data[DOMAIN]["debug_log_level"] = call.data.get("log_level", "DEBUG")
        
        # Store state
        store = hass.data[DOMAIN].get("debug_store")
        if store:
            await store.async_save({
                "enabled": True,
                "log_level": hass.data[DOMAIN]["debug_log_level"],
                "enabled_at": datetime.now(timezone.utc).isoformat(),
            })
        
        # Log to buffer
        _debug_buffer.add(
            "Debug mode enabled",
            level="info",
            context={"log_level": hass.data[DOMAIN]["debug_log_level"]},
        )
        
        _LOGGER.info("AI Home CoPilot debug mode enabled")
        
        # Fire event
        hass.bus.async_fire(f"{DOMAIN}_debug_mode_changed", {
            "enabled": True,
            "log_level": hass.data[DOMAIN]["debug_log_level"],
        })
    
    async def async_disable_debug(call: ServiceCall) -> None:
        """Disable debug mode."""
        hass.data[DOMAIN]["debug_mode"] = False
        hass.data[DOMAIN]["debug_log_level"] = "INFO"
        
        # Store state
        store = hass.data[DOMAIN].get("debug_store")
        if store:
            await store.async_save({
                "enabled": False,
                "log_level": "INFO",
                "disabled_at": datetime.now(timezone.utc).isoformat(),
            })
        
        # Log to buffer
        _debug_buffer.add("Debug mode disabled", level="info")
        
        _LOGGER.info("AI Home CoPilot debug mode disabled")
        
        # Fire event
        hass.bus.async_fire(f"{DOMAIN}_debug_mode_changed", {
            "enabled": False,
        })
    
    async def async_toggle_debug(call: ServiceCall) -> None:
        """Toggle debug mode."""
        if hass.data[DOMAIN].get("debug_mode", False):
            await async_disable_debug(call)
        else:
            await async_enable_debug(call)
    
    async def async_clear_debug_buffer(call: ServiceCall) -> None:
        """Clear debug buffer."""
        _debug_buffer.clear()
        _LOGGER.info("AI Home CoPilot debug buffer cleared")
    
    # Register services
    hass.services.async_register(DOMAIN, "enable_debug", async_enable_debug)
    hass.services.async_register(DOMAIN, "disable_debug", async_disable_debug)
    hass.services.async_register(DOMAIN, "toggle_debug", async_toggle_debug)
    hass.services.async_register(DOMAIN, "clear_debug_buffer", async_clear_debug_buffer)


class DebugModeSensor(SensorEntity):
    """Debug mode sensor for AI Home CoPilot with enhanced attributes."""

    _attr_name = "AI Home CoPilot Debug Mode"
    _attr_unique_id = f"{DOMAIN}_debug_mode_sensor"
    _attr_icon = "mdi:bug"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "ai_home_copilot")},
            "name": "PilotSuite",
            "manufacturer": "PilotSuite",
            "model": "HACS Integration",
        }

    @property
    def state(self) -> str:
        """Return the state."""
        debug_mode = self.hass.data.get(DOMAIN, {}).get("debug_mode", False)
        return STATE_ON if debug_mode else STATE_OFF

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        data = self.hass.data.get(DOMAIN, {})
        debug_mode = data.get("debug_mode", False)
        log_level = data.get("debug_log_level", "INFO")
        buffer = data.get("debug_buffer", _debug_buffer)
        
        # Get recent debug messages
        recent_messages = buffer.get_recent(10) if buffer else []
        
        # Count by level
        all_messages = buffer.get_all() if buffer else []
        level_counts = {}
        for msg in all_messages:
            level = msg.get("level", "unknown")
            level_counts[level] = level_counts.get(level, 0) + 1
        
        return {
            "enabled": debug_mode,
            "log_level": log_level,
            "buffer_size": len(all_messages),
            "level_counts": level_counts,
            "recent_messages": recent_messages,
            "services": {
                "enable": f"{DOMAIN}.enable_debug",
                "disable": f"{DOMAIN}.disable_debug",
                "toggle": f"{DOMAIN}.toggle_debug",
                "clear_buffer": f"{DOMAIN}.clear_debug_buffer",
            },
        }


def log_debug(message: str, context: dict | None = None) -> None:
    """Log a debug message if debug mode is enabled.
    
    Call this from other modules to add to the debug buffer.
    """
    _debug_buffer.add(message, level="debug", context=context)
    _LOGGER.debug("[CoPilot Debug] %s", message)


def log_info(message: str, context: dict | None = None) -> None:
    """Log an info message to the debug buffer."""
    _debug_buffer.add(message, level="info", context=context)
    _LOGGER.info("[CoPilot] %s", message)


def log_warning(message: str, context: dict | None = None) -> None:
    """Log a warning message to the debug buffer."""
    _debug_buffer.add(message, level="warning", context=context)
    _LOGGER.warning("[CoPilot Warning] %s", message)


def log_error(message: str, context: dict | None = None) -> None:
    """Log an error message to the debug buffer."""
    _debug_buffer.add(message, level="error", context=context)
    _LOGGER.error("[CoPilot Error] %s", message)