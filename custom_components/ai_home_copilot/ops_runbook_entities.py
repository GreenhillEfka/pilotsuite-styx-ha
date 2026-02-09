"""Ops Runbook Entities - Home Assistant sensors and binary sensors."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .ops_runbook_store import OpsRunbookStore

_LOGGER = logging.getLogger(__name__)


class OpsRunbookStatusBinarySensor(BinarySensorEntity):
    """Binary sensor for ops runbook overall status."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the binary sensor."""
        self._hass = hass
        self._attr_name = "Ops Runbook Status"
        self._attr_unique_id = f"{DOMAIN}_ops_runbook_status"
        self._attr_device_class = "problem"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:book-check"

    @property
    def is_on(self) -> bool | None:
        """Return True if there are issues detected."""
        # Return True (problem) if last checks failed
        store = self._hass.data.get(DOMAIN, {}).get("ops_runbook_store")
        if not store:
            return None

        try:
            # Check if we can get the summary synchronously
            last_checks = getattr(store, "_data", {}).get("last_checks", {})
            
            for check_type, check_data in last_checks.items():
                status = check_data.get("status")
                if status in ["fail", "failed", "error"]:
                    return True  # Problem detected
            
            return False  # No problems
        except Exception as e:
            _LOGGER.error(f"Error getting ops runbook status: {e}")
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        store = self._hass.data.get(DOMAIN, {}).get("ops_runbook_store")
        if not store:
            return {}

        try:
            data = getattr(store, "_data", {})
            last_checks = data.get("last_checks", {})
            
            attributes = {}
            for check_type, check_data in last_checks.items():
                attributes[f"last_{check_type}_status"] = check_data.get("status", "unknown")
                attributes[f"last_{check_type}_time"] = check_data.get("timestamp", "never")
            
            attributes["action_count"] = len(data.get("action_history", []))
            attributes["checklist_count"] = len(data.get("checklist_history", []))
            
            return attributes
        except Exception as e:
            _LOGGER.error(f"Error getting extra attributes: {e}")
            return {}


class OpsRunbookLastCheckSensor(SensorEntity):
    """Sensor for the last check timestamp."""

    def __init__(self, hass: HomeAssistant, check_type: str) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._check_type = check_type
        self._attr_name = f"Ops Runbook Last {check_type.replace('_', ' ').title()}"
        self._attr_unique_id = f"{DOMAIN}_ops_runbook_last_{check_type}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:clock-outline"
        self._attr_device_class = "timestamp"

    @property
    def native_value(self) -> str | None:
        """Return the timestamp of the last check."""
        store = self._hass.data.get(DOMAIN, {}).get("ops_runbook_store")
        if not store:
            return None

        try:
            data = getattr(store, "_data", {})
            last_checks = data.get("last_checks", {})
            check_data = last_checks.get(self._check_type, {})
            
            timestamp_str = check_data.get("timestamp")
            if timestamp_str:
                # Convert to the format HA expects
                return timestamp_str
            
            return None
        except Exception as e:
            _LOGGER.error(f"Error getting last check time for {self._check_type}: {e}")
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        store = self._hass.data.get(DOMAIN, {}).get("ops_runbook_store")
        if not store:
            return {}

        try:
            data = getattr(store, "_data", {})
            last_checks = data.get("last_checks", {})
            check_data = last_checks.get(self._check_type, {})
            
            attributes = {
                "status": check_data.get("status", "never_run"),
                "check_type": self._check_type,
            }
            
            # Add specific result details
            results = check_data.get("results", {})
            if "duration_seconds" in results:
                attributes["duration_seconds"] = results["duration_seconds"]
            
            if "checks" in results:
                # Count passed/failed checks
                checks = results["checks"]
                passed = sum(1 for check in checks.values() if check.get("success"))
                failed = len(checks) - passed
                attributes["checks_passed"] = passed
                attributes["checks_failed"] = failed
                attributes["total_checks"] = len(checks)
            
            return attributes
        except Exception as e:
            _LOGGER.error(f"Error getting extra attributes for {self._check_type}: {e}")
            return {}


class OpsRunbookActionCountSensor(SensorEntity):
    """Sensor for the number of recent actions."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._attr_name = "Ops Runbook Actions Count"
        self._attr_unique_id = f"{DOMAIN}_ops_runbook_actions_count"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:counter"
        self._attr_native_unit_of_measurement = "actions"

    @property
    def native_value(self) -> int | None:
        """Return the number of recent actions."""
        store = self._hass.data.get(DOMAIN, {}).get("ops_runbook_store")
        if not store:
            return None

        try:
            data = getattr(store, "_data", {})
            return len(data.get("action_history", []))
        except Exception as e:
            _LOGGER.error(f"Error getting action count: {e}")
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        store = self._hass.data.get(DOMAIN, {}).get("ops_runbook_store")
        if not store:
            return {}

        try:
            data = getattr(store, "_data", {})
            action_history = data.get("action_history", [])
            
            # Get recent stats (last 24h)
            now = datetime.now(timezone.utc)
            recent_actions = []
            for action in action_history[-50:]:  # Last 50 actions max
                try:
                    action_time = datetime.fromisoformat(action["timestamp"].replace("Z", "+00:00"))
                    hours_ago = (now - action_time).total_seconds() / 3600
                    if hours_ago <= 24:
                        recent_actions.append(action)
                except ValueError:
                    continue
            
            successful = sum(1 for action in recent_actions if action.get("success"))
            failed = len(recent_actions) - successful
            
            attributes = {
                "recent_24h": len(recent_actions),
                "recent_successful": successful,
                "recent_failed": failed,
                "total_actions": len(action_history),
            }
            
            # Most recent action info
            if action_history:
                last_action = action_history[-1]
                attributes["last_action"] = last_action.get("action", "unknown")
                attributes["last_action_success"] = last_action.get("success", False)
                attributes["last_action_time"] = last_action.get("timestamp", "unknown")
            
            return attributes
        except Exception as e:
            _LOGGER.error(f"Error getting action attributes: {e}")
            return {}


class OpsRunbookChecklistStatusSensor(SensorEntity):
    """Sensor for checklist completion status."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._attr_name = "Ops Runbook Checklist Status"
        self._attr_unique_id = f"{DOMAIN}_ops_runbook_checklist_status"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:format-list-checks"

    @property
    def native_value(self) -> str | None:
        """Return the overall checklist status."""
        store = self._hass.data.get(DOMAIN, {}).get("ops_runbook_store")
        if not store:
            return "unknown"

        try:
            data = getattr(store, "_data", {})
            checklist_history = data.get("checklist_history", [])
            
            if not checklist_history:
                return "no_checklists"
            
            # Get the most recent checklist
            recent_checklist = checklist_history[-1]
            return recent_checklist.get("status", "unknown")
            
        except Exception as e:
            _LOGGER.error(f"Error getting checklist status: {e}")
            return "error"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        store = self._hass.data.get(DOMAIN, {}).get("ops_runbook_store")
        if not store:
            return {}

        try:
            data = getattr(store, "_data", {})
            checklist_history = data.get("checklist_history", [])
            
            attributes = {
                "total_checklists": len(checklist_history),
            }
            
            if checklist_history:
                recent_checklist = checklist_history[-1]
                attributes["last_checklist"] = recent_checklist.get("checklist", "unknown")
                attributes["last_checklist_time"] = recent_checklist.get("timestamp", "unknown")
                
                # Count items by status
                items = recent_checklist.get("items", [])
                status_counts = {}
                for item in items:
                    status = item.get("status", "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                attributes.update(status_counts)
                attributes["total_items"] = len(items)
            
            # Recent activity (last 7 days)
            now = datetime.now(timezone.utc)
            recent_activity = 0
            for checklist in checklist_history:
                try:
                    checklist_time = datetime.fromisoformat(checklist["timestamp"].replace("Z", "+00:00"))
                    days_ago = (now - checklist_time).total_seconds() / (24 * 3600)
                    if days_ago <= 7:
                        recent_activity += 1
                except ValueError:
                    continue
            
            attributes["recent_7d"] = recent_activity
            
            return attributes
        except Exception as e:
            _LOGGER.error(f"Error getting checklist attributes: {e}")
            return {}


async def async_setup_ops_runbook_entities(hass: HomeAssistant) -> list:
    """Set up ops runbook entities."""
    entities = [
        OpsRunbookStatusBinarySensor(hass),
        OpsRunbookLastCheckSensor(hass, "preflight"),
        OpsRunbookLastCheckSensor(hass, "smoke_test"),
        OpsRunbookActionCountSensor(hass),
        OpsRunbookChecklistStatusSensor(hass),
    ]
    
    _LOGGER.info(f"Setting up {len(entities)} ops runbook entities")
    return entities