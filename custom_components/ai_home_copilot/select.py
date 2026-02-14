"""Select platform for AI Home CoPilot integration."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DEBUG_LEVELS,
    DEBUG_LEVEL_FULL,
    DEBUG_LEVEL_LIGHT,
    DEBUG_LEVEL_OFF,
    DEFAULT_DEBUG_LEVEL,
    DOMAIN,
)
from .entity import CopilotBaseEntity
from .media_context_v2_entities import (
    ZoneSelectEntity,
    ManualTargetSelectEntity,
)


class DiagnosticLevelSelectEntity(CopilotBaseEntity, SelectEntity):
    """Select entity to control debug/diagnostic level."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Debug Level"
    _attr_unique_id = "debug_level_select"
    _attr_icon = "mdi:bug-check"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_options = DEBUG_LEVELS
        self._attr_current_option = DEFAULT_DEBUG_LEVEL

    async def async_select_option(self, option: str) -> None:
        """Set the debug level."""
        if option not in DEBUG_LEVELS:
            return

        self._attr_current_option = option

        # Call service to update state
        await self.hass.services.async_call(
            DOMAIN,
            "set_debug_level",
            {"entry_id": self._entry_id, "level": option},
            blocking=False,
        )

        # Log the change
        kernel = self.coordinator.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get("dev_surface")
        if isinstance(kernel, dict) and "devlog" in kernel:
            kernel["devlog"].add(
                level="info",
                typ="debug_level",
                msg=f"Debug level changed to {option}",
                data={"level": option},
            )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up select entities for the integration."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data.get("coordinator")
    
    entities = [
        DiagnosticLevelSelectEntity(coordinator, entry.entry_id),
    ]
    
    # Media Context v2 select entities
    media_coordinator_v2 = data.get("media_coordinator_v2") if isinstance(data, dict) else None
    if media_coordinator_v2 is not None:
        entities.extend([
            ZoneSelectEntity(media_coordinator_v2),
            ManualTargetSelectEntity(media_coordinator_v2),
        ])

    if entities:
        async_add_entities(entities, True)