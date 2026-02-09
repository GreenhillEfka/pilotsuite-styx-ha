"""Select platform for AI Home CoPilot integration."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .media_context_v2_entities import (
    ZoneSelectEntity,
    ManualTargetSelectEntity,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up select entities for the integration."""
    data = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Media Context v2 select entities
    media_coordinator_v2 = data.get("media_coordinator_v2") if isinstance(data, dict) else None
    if media_coordinator_v2 is not None:
        entities.extend([
            ZoneSelectEntity(media_coordinator_v2),
            ManualTargetSelectEntity(media_coordinator_v2),
        ])

    if entities:
        async_add_entities(entities, True)