"""Select platform for PilotSuite integration."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

_LOGGER = logging.getLogger(__name__)

from .const import (
    CONF_ENTITY_PROFILE,
    DEBUG_LEVELS,
    DEBUG_LEVEL_FULL,
    DEBUG_LEVEL_LIGHT,
    DEBUG_LEVEL_OFF,
    DEFAULT_DEBUG_LEVEL,
    DEFAULT_ENTITY_PROFILE,
    DOMAIN,
    ENTITY_PROFILES,
)
from .entity import CopilotBaseEntity
from .entity_profile import get_entity_profile
from .media_context_v2_entities import (
    ZoneSelectEntity,
    ManualTargetSelectEntity,
)
from .habitus_zones_entities_v2 import HabitusZonesV2GlobalStateSelect


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


class EntityProfileSelectEntity(CopilotBaseEntity, SelectEntity):
    """Select entity to switch between core/full entity profile at runtime."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Entity Profile"
    _attr_unique_id = "ai_home_copilot_entity_profile_select"
    _attr_icon = "mdi:tune-variant"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_options = list(ENTITY_PROFILES)
        self._attr_current_option = get_entity_profile(entry)

    async def async_select_option(self, option: str) -> None:
        if option not in ENTITY_PROFILES:
            return
        self._attr_current_option = option
        new_options = {**self._entry.options, CONF_ENTITY_PROFILE: option}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.async_write_ha_state()
        _LOGGER.info("Entity profile changed to %s — reload integration to apply", option)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up select entities for the integration."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not isinstance(data, dict):
        _LOGGER.error("Entry data not available for %s, skipping select setup", entry.entry_id)
        return
    coordinator = data.get("coordinator")
    if coordinator is None:
        _LOGGER.error("Coordinator not available for %s, skipping select setup", entry.entry_id)
        return
    
    entities = [
        DiagnosticLevelSelectEntity(coordinator, entry.entry_id),
        EntityProfileSelectEntity(coordinator, entry),
        # v2 Select
        HabitusZonesV2GlobalStateSelect(coordinator, entry),
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