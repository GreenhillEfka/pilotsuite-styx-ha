"""Ops Runbook Store - Persistent storage for operations runbook data."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY_RUNBOOK = "ops_runbook"

# Store structure:
# {
#   "last_checks": {
#     "preflight": {"timestamp": "...", "status": "...", "results": {...}},
#     "smoke_test": {"timestamp": "...", "status": "...", "results": {...}},
#   },
#   "action_history": [
#     {"timestamp": "...", "action": "...", "success": bool, "output": "...", "error": "..."},
#     ...
#   ],
#   "checklist_history": [
#     {"timestamp": "...", "checklist": "...", "status": "...", "items": [...]},
#     ...
#   ],
#   "config": {
#     "retention_days": 30,
#     "auto_cleanup": true,
#   }
# }


class OpsRunbookStore:
    """Store for Ops Runbook data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the store."""
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{STORAGE_KEY_RUNBOOK}"
        )
        self._data: dict[str, Any] = {}

    async def async_load(self) -> None:
        """Load data from storage."""
        if stored_data := await self._store.async_load():
            self._data = stored_data
        else:
            self._data = {
                "last_checks": {},
                "action_history": [],
                "checklist_history": [],
                "config": {
                    "retention_days": 30,
                    "auto_cleanup": True,
                }
            }

    @callback
    def async_get_data(self) -> dict[str, Any]:
        """Get a copy of the current data."""
        return dict(self._data)

    async def async_store_check_result(self, check_type: str, result: dict[str, Any]) -> None:
        """Store the result of a check (preflight, smoke_test)."""
        if not self._data:
            await self.async_load()

        self._data["last_checks"][check_type] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": result.get("status", "unknown"),
            "results": result,
        }

        await self._store.async_save(self._data)
        _LOGGER.debug(f"Stored check result for {check_type}")

    async def async_store_action_result(self, action: str, result: dict[str, Any]) -> None:
        """Store the result of an action."""
        if not self._data:
            await self.async_load()

        action_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "success": result.get("success", False),
            "output": result.get("output", ""),
            "error": result.get("error", ""),
        }

        self._data["action_history"].append(action_record)

        # Clean up old records if auto_cleanup is enabled
        if self._data["config"].get("auto_cleanup", True):
            await self._async_cleanup_history("action_history")

        await self._store.async_save(self._data)
        _LOGGER.debug(f"Stored action result for {action}")

    async def async_store_checklist_result(self, checklist: str, result: dict[str, Any]) -> None:
        """Store the result of a checklist."""
        if not self._data:
            await self.async_load()

        checklist_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checklist": checklist,
            "status": result.get("status", "unknown"),
            "items": result.get("items", []),
        }

        self._data["checklist_history"].append(checklist_record)

        # Clean up old records if auto_cleanup is enabled
        if self._data["config"].get("auto_cleanup", True):
            await self._async_cleanup_history("checklist_history")

        await self._store.async_save(self._data)
        _LOGGER.debug(f"Stored checklist result for {checklist}")

    async def async_get_last_check(self, check_type: str) -> dict[str, Any] | None:
        """Get the last result for a specific check type."""
        if not self._data:
            await self.async_load()

        return self._data["last_checks"].get(check_type)

    async def async_get_action_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get action history with optional limit."""
        if not self._data:
            await self.async_load()

        return self._data["action_history"][-limit:] if limit else self._data["action_history"]

    async def async_get_checklist_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get checklist history with optional limit."""
        if not self._data:
            await self.async_load()

        return self._data["checklist_history"][-limit:] if limit else self._data["checklist_history"]

    async def async_get_summary(self) -> dict[str, Any]:
        """Get a summary of runbook status."""
        if not self._data:
            await self.async_load()

        summary = {
            "last_checks": {},
            "recent_actions": len(self._data.get("action_history", [])),
            "recent_checklists": len(self._data.get("checklist_history", [])),
            "config": self._data.get("config", {}),
        }

        # Include status of last checks
        for check_type, check_data in self._data.get("last_checks", {}).items():
            summary["last_checks"][check_type] = {
                "timestamp": check_data.get("timestamp"),
                "status": check_data.get("status"),
            }

        return summary

    async def _async_cleanup_history(self, history_key: str) -> None:
        """Clean up old history records based on retention policy."""
        retention_days = self._data["config"].get("retention_days", 30)
        cutoff_timestamp = datetime.now(timezone.utc).timestamp() - (retention_days * 24 * 60 * 60)

        original_count = len(self._data[history_key])
        
        self._data[history_key] = [
            record for record in self._data[history_key]
            if datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")).timestamp() > cutoff_timestamp
        ]

        cleaned_count = original_count - len(self._data[history_key])
        if cleaned_count > 0:
            _LOGGER.debug(f"Cleaned up {cleaned_count} old records from {history_key}")

    async def async_update_config(self, config_updates: dict[str, Any]) -> None:
        """Update configuration settings."""
        if not self._data:
            await self.async_load()

        self._data["config"].update(config_updates)
        await self._store.async_save(self._data)
        _LOGGER.debug(f"Updated config: {config_updates}")


# Helper functions for backwards compatibility and easy access

async def async_get_state(hass: HomeAssistant) -> dict[str, Any]:
    """Get the current ops runbook state."""
    store = hass.data.get(DOMAIN, {}).get("ops_runbook_store")
    if not store:
        return {}
    return await store.async_get_summary()


async def async_set_last_check(hass: HomeAssistant, check_type: str, result: dict[str, Any]) -> None:
    """Set the last check result."""
    store = hass.data.get(DOMAIN, {}).get("ops_runbook_store")
    if store:
        await store.async_store_check_result(check_type, result)


async def async_get_runbook_state(hass: HomeAssistant) -> dict[str, Any]:
    """Get the full runbook state (alias for async_get_state)."""
    return await async_get_state(hass)