"""Preference Input Card - User preference and delegation workflows.

Provides UI for:
- Preference input workflows
- Conflict resolution UI
- Schedule automation
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, EntityCategory

from ..const import DOMAIN

class PreferenceInputCard(Entity):
    """Card entity for preference input workflows.
    
    Provides UI for user preference input, conflict resolution,
    and schedule automation workflows.
    """
    
    _attr_has_entity_name = True
    _attr_name = "Preference Input"
    _attr_unique_id = "preference_input_card"
    _attr_icon = "mdi:heart-pulse"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    def __init__(self, hass: HomeAssistant, entry_id: str):
        """Initialize preference input card."""
        self._hass = hass
        self._entry_id = entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "CoPilot Core",
            "manufacturer": "PilotSuite",
            "model": "Core Add-on",
        }
    
    @property
    def state(self) -> str:
        """Return the state of the card."""
        return "idle"
    
    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return {
            "preference_workflows": 0,
            "active_conflicts": 0,
            "scheduled_automations": 0,
            "last_updated": None,
        }
    
    async def async_update(self) -> None:
        """Update card state."""
        # Fetch preference workflows
        preference_workflows = 0
        active_conflicts = 0
        scheduled_automations = 0
        
        # Update state
        self._attr_extra_state_attributes = {
            "preference_workflows": preference_workflows,
            "active_conflicts": active_conflicts,
            "scheduled_automations": scheduled_automations,
            "last_updated": None,
        }
