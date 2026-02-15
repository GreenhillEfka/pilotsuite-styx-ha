"""Habitus Miner sensor entities for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .entity import CopilotBaseEntity

if TYPE_CHECKING:
    from .coordinator import CopilotDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HabitusMinerRuleCountSensor(CopilotBaseEntity, SensorEntity):
    """Sensor tracking number of discovered behavioral rules."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:brain"

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_habitus_rules_count"
        self._attr_name = "Habitus Rules Count"
        self._rules_data: dict[str, Any] | None = None

    @property
    def native_value(self) -> int | None:
        """Return the number of discovered rules."""
        if self._rules_data and "total_rules" in self._rules_data:
            return self._rules_data["total_rules"]
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        if not self._rules_data:
            return None
        
        attrs = {}
        
        # Basic stats
        if "avg_confidence" in self._rules_data:
            attrs["average_confidence"] = self._rules_data["avg_confidence"]
        
        if "avg_lift" in self._rules_data:
            attrs["average_lift"] = self._rules_data["avg_lift"]
        
        # Top rules summary
        if "top_rules" in self._rules_data and self._rules_data["top_rules"]:
            top_rules = self._rules_data["top_rules"][:3]  # Top 3 rules
            attrs["top_rule_1"] = f"{top_rules[0]['A']} → {top_rules[0]['B']}" if len(top_rules) > 0 else None
            attrs["top_rule_1_confidence"] = top_rules[0].get("confidence") if len(top_rules) > 0 else None
            attrs["top_rule_2"] = f"{top_rules[1]['A']} → {top_rules[1]['B']}" if len(top_rules) > 1 else None
            attrs["top_rule_3"] = f"{top_rules[2]['A']} → {top_rules[2]['B']}" if len(top_rules) > 2 else None

        # Domain patterns summary
        if "domain_patterns" in self._rules_data:
            domain_count = len(self._rules_data["domain_patterns"])
            attrs["domain_patterns_count"] = domain_count
            
            # Top domain pattern
            if domain_count > 0:
                top_domain = max(
                    self._rules_data["domain_patterns"].items(),
                    key=lambda x: x[1]["count"]
                )
                attrs["top_domain_pattern"] = top_domain[0]
                attrs["top_domain_pattern_count"] = top_domain[1]["count"]

        # Storage stats
        if "storage_stats" in self._rules_data:
            storage = self._rules_data["storage_stats"]
            attrs["events_processed"] = storage.get("total_events_processed", 0)
            if storage.get("last_mining_ts"):
                from datetime import datetime
                attrs["last_mining"] = datetime.fromtimestamp(
                    storage["last_mining_ts"] / 1000
                ).isoformat()

        return attrs

    async def async_update(self) -> None:
        """Update the sensor data."""
        try:
            # Fetch rules summary from Core API
            result = await self.coordinator.api.get_with_auth("habitus/rules/summary")
            
            if result and result.get("status") == "ok":
                self._rules_data = result
                _LOGGER.debug("Updated habitus miner rules data")
            else:
                _LOGGER.debug("No habitus rules data available")
                self._rules_data = None
                
        except Exception as e:
            _LOGGER.debug("Error updating habitus miner sensor: %s", e)
            self._rules_data = None


class HabitusMinerStatusSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing overall Habitus Miner status."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:robot"

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_habitus_status"
        self._attr_name = "Habitus Miner Status"
        self._status_data: dict[str, Any] | None = None

    @property
    def native_value(self) -> str:
        """Return the status of the habitus miner."""
        if not self._status_data:
            return "unknown"
        
        status = self._status_data.get("status", "unknown")
        
        # Determine overall health
        if status == "ok":
            stats = self._status_data.get("statistics", {})
            rules_count = stats.get("total_rules", 0)
            
            if rules_count > 0:
                return "active"
            else:
                return "ready"
        
        return status

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional status attributes."""
        if not self._status_data:
            return None
        
        attrs = {}
        
        # Configuration
        if "config" in self._status_data:
            config = self._status_data["config"]
            attrs["min_confidence"] = config.get("min_confidence")
            attrs["min_lift"] = config.get("min_lift")
            attrs["max_rules"] = config.get("max_rules")
            attrs["time_windows"] = config.get("windows")

        # Statistics
        if "statistics" in self._status_data:
            stats = self._status_data["statistics"]
            attrs["total_rules"] = stats.get("total_rules", 0)
            attrs["events_processed"] = stats.get("total_events_processed", 0)
            
            if stats.get("last_mining_ts"):
                from datetime import datetime
                attrs["last_mining"] = datetime.fromtimestamp(
                    stats["last_mining_ts"] / 1000
                ).isoformat()
            
            # File status
            files_exist = stats.get("files_exist", {})
            attrs["has_rules_cache"] = files_exist.get("rules", False)
            attrs["has_events_cache"] = files_exist.get("events_cache", False)

        # Version info
        if "version" in self._status_data:
            attrs["version"] = self._status_data["version"]

        return attrs

    async def async_update(self) -> None:
        """Update the sensor data."""
        try:
            # Fetch status from Core API
            result = await self.coordinator.api.get_with_auth("habitus/status")
            
            if result:
                self._status_data = result
                _LOGGER.debug("Updated habitus miner status")
            else:
                _LOGGER.debug("No habitus status data available")
                self._status_data = None
                
        except Exception as e:
            _LOGGER.debug("Error updating habitus status sensor: %s", e)
            self._status_data = None


class HabitusMinerTopRuleSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing the top behavioral rule discovered."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:arrow-right-bold"

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_habitus_top_rule"
        self._attr_name = "Habitus Top Rule"
        self._rules_data: dict[str, Any] | None = None

    @property
    def native_value(self) -> str | None:
        """Return the top rule as a string."""
        if (
            self._rules_data 
            and "top_rules" in self._rules_data 
            and self._rules_data["top_rules"]
        ):
            top_rule = self._rules_data["top_rules"][0]
            return f"{top_rule['A']} → {top_rule['B']}"
        
        return "No rules discovered"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return attributes for the top rule."""
        if (
            not self._rules_data 
            or "top_rules" not in self._rules_data
            or not self._rules_data["top_rules"]
        ):
            return None
        
        top_rule = self._rules_data["top_rules"][0]
        
        return {
            "antecedent": top_rule.get("A"),
            "consequent": top_rule.get("B"), 
            "confidence": top_rule.get("confidence"),
            "lift": top_rule.get("lift"),
            "score": top_rule.get("score"),
            "window_seconds": top_rule.get("window_sec"),
            "rule_explanation": f"When {top_rule.get('A', '')} occurs, {top_rule.get('B', '')} follows within {top_rule.get('window_sec', 0)} seconds with {top_rule.get('confidence', 0):.1%} confidence",
        }

    async def async_update(self) -> None:
        """Update the sensor data."""
        try:
            # Fetch rules summary from Core API
            result = await self.coordinator.api.get_with_auth("habitus/rules/summary")
            
            if result and result.get("status") == "ok":
                self._rules_data = result
                _LOGGER.debug("Updated habitus top rule data")
            else:
                _LOGGER.debug("No habitus rules data available")
                self._rules_data = None
                
        except Exception as e:
            _LOGGER.debug("Error updating habitus top rule sensor: %s", e)
            self._rules_data = None