"""Habitus Dashboard Cards module entities."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .entity import CopilotBaseEntity


class HabitusDashboardCardsStatusSensor(CopilotBaseEntity, SensorEntity):
    """Sensor showing habitus_dashboard_cards module status."""

    _attr_icon = "mdi:view-dashboard"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{DOMAIN}_habitus_dashboard_cards_status"
        self._attr_name = "Habitus Dashboard Cards Status"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        # Check if module is enabled via capabilities
        capabilities = self.coordinator.data.get("capabilities", {})
        modules = capabilities.get("modules", {})
        dashboard_cards = modules.get("habitus_dashboard_cards", {})
        
        if dashboard_cards.get("enabled"):
            return "Active"
        return "Inactive"

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        capabilities = self.coordinator.data.get("capabilities", {})
        modules = capabilities.get("modules", {})
        dashboard_cards = modules.get("habitus_dashboard_cards", {})
        
        return {
            "version": dashboard_cards.get("version", "unknown"),
            "description": dashboard_cards.get("description", ""),
            "api_endpoints": dashboard_cards.get("endpoints", []),
            "documentation": "/local/docs/module_specs/habitus_dashboard_cards_v0.1.md",
            "pattern_types": ["overview", "room", "energy", "sleep"],
            "focus": "Core-only Lovelace cards, trends, aggregates, drill-down patterns",
        }
