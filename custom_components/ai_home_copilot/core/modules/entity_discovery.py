"""Entity Discovery Module — Auto-discover HA entities, areas, and push to Core.

Reads from HA's entity/device/area registries and pushes a full entity
inventory to Core's bulk import API (/api/v1/entities/bulk). This enables
the entity search dropdowns, zone mapping suggestions, and auto-tagging.

Flow:
  1. On setup: read all registries, build entity + area lists
  2. Push to Core API for searchable dropdowns
  3. Listen for HA state changes to keep cache fresh
  4. Periodic re-sync every 5 minutes
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers import entity_registry, device_registry, area_registry

from .module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)

RESYNC_INTERVAL = 300  # 5 minutes


class EntityDiscoveryModule(CopilotModule):
    """Module that discovers HA entities/areas and syncs them to Core."""

    @property
    def name(self) -> str:
        return "entity_discovery"

    @property
    def version(self) -> str:
        return "1.0.0"

    def __init__(self):
        self._hass: Optional[HomeAssistant] = None
        self._entry_id: Optional[str] = None
        self._unsub_state_listener: Optional[Any] = None
        self._unsub_timer: Optional[Any] = None
        self._last_sync: float = 0.0
        self._entity_count: int = 0
        self._area_count: int = 0

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up entity discovery and initial sync."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry_id

        # Store reference in hass.data
        ctx.hass.data.setdefault("ai_home_copilot", {})
        ctx.hass.data["ai_home_copilot"].setdefault(ctx.entry_id, {})
        ctx.hass.data["ai_home_copilot"][ctx.entry_id]["entity_discovery"] = self

        # Initial sync (delayed to let HA finish loading)
        async def _delayed_initial_sync(_now=None):
            await self.async_full_sync()

        ctx.hass.async_create_task(_delayed_initial_sync())

        # Periodic re-sync
        from homeassistant.helpers.event import async_track_time_interval
        import datetime

        self._unsub_timer = async_track_time_interval(
            ctx.hass,
            _delayed_initial_sync,
            datetime.timedelta(seconds=RESYNC_INTERVAL),
        )

        _LOGGER.info("EntityDiscoveryModule setup complete")

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        if self._unsub_timer:
            self._unsub_timer()
        entry_store = ctx.hass.data.get("ai_home_copilot", {}).get(ctx.entry_id, {})
        if isinstance(entry_store, dict):
            entry_store.pop("entity_discovery", None)
        return True

    async def async_full_sync(self) -> dict[str, Any]:
        """Read all HA registries and push to Core."""
        if not self._hass:
            return {"error": "no hass"}

        import time

        entities = await self._collect_entities()
        areas = await self._collect_areas()

        # Push to Core
        result = await self._push_to_core(entities, areas)

        self._last_sync = time.time()
        self._entity_count = len(entities)
        self._area_count = len(areas)

        _LOGGER.info(
            "Entity discovery sync: %d entities, %d areas → Core",
            len(entities), len(areas),
        )
        return result

    async def _collect_entities(self) -> list[dict[str, Any]]:
        """Collect all entities from HA registries with area resolution."""
        hass = self._hass
        if not hass:
            return []

        ent_reg = entity_registry.async_get(hass)
        dev_reg = device_registry.async_get(hass)

        entities = []
        for entity_id, reg_entry in ent_reg.entities.items():
            if reg_entry.disabled_by is not None:
                continue

            # Resolve area: entity → device → area
            area_id = reg_entry.area_id or ""
            if not area_id and reg_entry.device_id:
                device = dev_reg.async_get(reg_entry.device_id)
                if device:
                    area_id = device.area_id or ""

            # Get current state
            state_obj = hass.states.get(entity_id)
            state = state_obj.state if state_obj else "unavailable"
            attrs = state_obj.attributes if state_obj else {}

            entities.append({
                "entity_id": entity_id,
                "domain": reg_entry.domain,
                "state": state,
                "friendly_name": attrs.get("friendly_name", reg_entry.name or entity_id),
                "device_class": reg_entry.device_class or attrs.get("device_class", ""),
                "area_id": area_id,
                "icon": reg_entry.icon or attrs.get("icon", ""),
                "unit_of_measurement": reg_entry.unit_of_measurement or attrs.get("unit_of_measurement", ""),
                "platform": reg_entry.platform,
            })

        return entities

    async def _collect_areas(self) -> list[dict[str, Any]]:
        """Collect all HA areas."""
        hass = self._hass
        if not hass:
            return []

        ar = area_registry.async_get(hass)
        areas = []
        for area in ar.areas.values():
            areas.append({
                "area_id": area.id,
                "name": area.name,
            })
        return sorted(areas, key=lambda a: a["name"].lower())

    async def _push_to_core(
        self, entities: list[dict[str, Any]], areas: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Push entity/area data to Core's bulk import endpoint."""
        hass = self._hass
        if not hass:
            return {"error": "no hass"}

        from ...const import DOMAIN

        entry_data = hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        if not isinstance(entry_data, dict):
            _LOGGER.debug("No entry data for entity sync")
            return {"error": "no_entry_data"}
        coordinator = entry_data.get("coordinator")
        if not coordinator or not hasattr(coordinator, "api"):
            _LOGGER.debug("No coordinator/api available for entity sync")
            return {"error": "no_client"}

        client = coordinator.api

        payload = {
            "entities": entities,
            "areas": areas,
        }

        try:
            result = await client.async_post(
                "/api/v1/entities/bulk", payload
            )
            _LOGGER.debug(
                "Pushed %d entities + %d areas to Core: %s",
                len(entities), len(areas), result,
            )
            return result or {}
        except Exception:
            _LOGGER.debug("Entity bulk push to Core failed (non-blocking)")
            return {"error": "push_failed"}

    def get_summary(self) -> dict[str, Any]:
        """Summary for sensor attributes."""
        return {
            "entity_count": self._entity_count,
            "area_count": self._area_count,
            "last_sync": self._last_sync,
            "resync_interval": RESYNC_INTERVAL,
        }
