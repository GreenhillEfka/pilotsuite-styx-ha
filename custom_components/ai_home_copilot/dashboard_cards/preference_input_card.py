"""Preference Input Card — Conflict Resolution UI.

Surfaces multi-user preference conflicts and resolution strategy
via HA entity attributes. Dashboard cards can render this data.

Attributes exposed:
- active_conflicts: count of detected conflicts
- resolution_strategy: weighted | compromise | override
- conflict_details: list of per-axis divergences
- resolved_mood: final blended mood after resolution
- users_involved: list of active users in conflict
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, EntityCategory

from ..const import DOMAIN
from ..entity import build_main_device_identifiers

_LOGGER = logging.getLogger(__name__)


class PreferenceInputCard(Entity):
    """Card entity for preference conflict resolution.

    Reads from the ConflictResolver stored in hass.data and
    exposes conflict state as entity attributes.
    """

    _attr_has_entity_name = True
    _attr_name = "Conflict Resolution"
    _attr_unique_id = "preference_input_card"
    _attr_icon = "mdi:account-group"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._entry_id = entry_id
        self._conflict_data: dict[str, Any] = {}
        entry_data = hass.data.get(DOMAIN, {}).get(entry_id, {})
        coordinator = entry_data.get("coordinator") if isinstance(entry_data, dict) else None
        cfg = getattr(coordinator, "_config", {}) if coordinator is not None else {}
        self._attr_device_info = {
            "identifiers": build_main_device_identifiers(cfg),
            "name": "PilotSuite Core",
            "manufacturer": "PilotSuite",
            "model": "Core Add-on",
        }

    @property
    def state(self) -> str:
        if self._conflict_data.get("active"):
            return "conflict"
        return "ok"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self._conflict_data
        return {
            "active_conflicts": data.get("conflict_count", 0),
            "resolution_strategy": data.get("resolution", "weighted"),
            "users_involved": data.get("users_involved", []),
            "resolved_mood": data.get("resolved_mood", {}),
            "conflict_details": data.get("details", []),
            "override_user": data.get("override_user"),
            "last_evaluated": datetime.now(timezone.utc).isoformat(),
        }

    async def async_update(self) -> None:
        """Pull conflict state from hass.data."""
        global_data = self._hass.data.get(DOMAIN, {}).get("_global", {})
        resolver = global_data.get("conflict_resolver")
        if resolver is not None:
            self._conflict_data = resolver.state.to_dict()
        else:
            self._conflict_data = {}
