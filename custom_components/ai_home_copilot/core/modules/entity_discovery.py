"""Entity Discovery Module v2 — Full HA registry sync to Core.

Reads from HA's entity/device/area/floor registries, enriches entities
with device manufacturer/model info and HA labels, and pushes a full
inventory to Core's bulk import API (/api/v1/entities/bulk).

This enables:
- Searchable entity dropdowns in the React backend
- Zone mapping suggestions based on area names
- Auto-tagging via the entity tag system
- Device grouping by manufacturer/model

Data flow:
  1. On setup: read all registries, build enriched entity + area + device lists
  2. Push to Core API for searchable dropdowns
  3. Periodic re-sync every 5 minutes
  4. On sync response: process zone suggestions for auto-tagging

API reference (per HA docs):
  - REST: /api/states (entity states with attributes)
  - REST: /api/config (HA config)
  - WebSocket: config/entity_registry/list (entity → area_id, device_id, labels)
  - WebSocket: config/device_registry/list (device → manufacturer, model, area_id)
  - WebSocket: config/area_registry/list (area → name, floor_id)
  - WebSocket: config/floor_registry/list (floor → name, level)
  - WebSocket: config/label_registry/list (labels)

  Note: area_id is NOT in /api/states — it comes from the entity/device registries.
  The integration accesses registries directly via HA helpers (no WebSocket needed).
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
    """Module that discovers HA entities/areas/devices and syncs them to Core."""

    @property
    def name(self) -> str:
        return "entity_discovery"

    @property
    def version(self) -> str:
        return "2.1.0"

    def __init__(self):
        self._hass: Optional[HomeAssistant] = None
        self._entry_id: Optional[str] = None
        self._unsub_timer: Optional[Any] = None
        self._last_sync: float = 0.0
        self._entity_count: int = 0
        self._area_count: int = 0
        self._device_count: int = 0
        self._last_classification_count: int = 0
        self._last_high_confidence_count: int = 0

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

        _LOGGER.info("EntityDiscoveryModule v2 setup complete")

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        if self._unsub_timer:
            self._unsub_timer()
        entry_store = ctx.hass.data.get("ai_home_copilot", {}).get(ctx.entry_id, {})
        if isinstance(entry_store, dict):
            entry_store.pop("entity_discovery", None)
        return True

    async def async_full_sync(self) -> dict[str, Any]:
        """Read all HA registries and push enriched data to Core."""
        if not self._hass:
            return {"error": "no hass"}

        import time

        entities = self._collect_entities()
        areas = self._collect_areas()
        devices = self._collect_devices()

        # Push to Core
        result = await self._push_to_core(entities, areas, devices)

        self._last_sync = time.time()
        self._entity_count = len(entities)
        self._area_count = len(areas)
        self._device_count = len(devices)

        _LOGGER.info(
            "Entity discovery sync: %d entities, %d areas, %d devices → Core",
            len(entities), len(areas), len(devices),
        )

        # Process zone suggestions from Core response for auto-tagging
        zone_suggestions = []
        if isinstance(result, dict):
            zone_suggestions = result.get("zone_suggestions", [])
        if zone_suggestions:
            await self._auto_tag_zone_suggestions(zone_suggestions)

        # Run ML-style entity classification for enhanced auto-tagging
        await self.async_classify_entities()

        return result

    def _collect_entities(self) -> list[dict[str, Any]]:
        """Collect all entities from HA registries with area + device resolution."""
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
            device_id = reg_entry.device_id or ""
            if not area_id and device_id:
                device = dev_reg.async_get(device_id)
                if device:
                    area_id = device.area_id or ""

            # Get current state
            state_obj = hass.states.get(entity_id)
            state = state_obj.state if state_obj else "unavailable"
            attrs = state_obj.attributes if state_obj else {}

            # Device info enrichment
            device_info = {}
            if device_id:
                device = dev_reg.async_get(device_id)
                if device:
                    device_info = {
                        "device_id": device_id,
                        "device_name": device.name_by_user or device.name or "",
                        "manufacturer": device.manufacturer or "",
                        "model": device.model or "",
                        "sw_version": device.sw_version or "",
                    }

            # HA labels (available since HA 2024.x)
            labels = []
            if hasattr(reg_entry, "labels"):
                labels = list(reg_entry.labels) if reg_entry.labels else []

            entity = {
                "entity_id": entity_id,
                "domain": reg_entry.domain,
                "state": state,
                "friendly_name": attrs.get("friendly_name", reg_entry.name or entity_id),
                "device_class": reg_entry.device_class or attrs.get("device_class", ""),
                "area_id": area_id,
                "icon": reg_entry.icon or attrs.get("icon", ""),
                "unit_of_measurement": (
                    reg_entry.unit_of_measurement
                    or attrs.get("unit_of_measurement", "")
                ),
                "platform": reg_entry.platform,
                "labels": labels,
                "device": device_info,
            }

            # Domain-specific extras
            if reg_entry.domain == "media_player":
                entity["source_list"] = attrs.get("source_list", [])
                entity["supported_features"] = attrs.get("supported_features", 0)
            elif reg_entry.domain == "climate":
                entity["hvac_modes"] = attrs.get("hvac_modes", [])
                entity["current_temperature"] = attrs.get("current_temperature")
            elif reg_entry.domain == "light":
                entity["supported_color_modes"] = attrs.get("supported_color_modes", [])
                entity["brightness"] = attrs.get("brightness")
            elif reg_entry.domain == "cover":
                entity["current_position"] = attrs.get("current_position")
                entity["supported_features"] = attrs.get("supported_features", 0)

            entities.append(entity)

        return entities

    def _collect_areas(self) -> list[dict[str, Any]]:
        """Collect all HA areas with floor info."""
        hass = self._hass
        if not hass:
            return []

        ar = area_registry.async_get(hass)
        areas = []
        for area in ar.areas.values():
            area_data: dict[str, Any] = {
                "area_id": area.id,
                "name": area.name,
            }
            # Floor info (HA 2024.x+)
            if hasattr(area, "floor_id"):
                area_data["floor_id"] = area.floor_id or ""
            # Labels (HA 2024.x+)
            if hasattr(area, "labels"):
                area_data["labels"] = list(area.labels) if area.labels else []
            # Icon
            if hasattr(area, "icon"):
                area_data["icon"] = area.icon or ""
            # Aliases
            if hasattr(area, "aliases"):
                area_data["aliases"] = list(area.aliases) if area.aliases else []
            areas.append(area_data)

        return sorted(areas, key=lambda a: a["name"].lower())

    def _collect_devices(self) -> list[dict[str, Any]]:
        """Collect all HA devices with manufacturer/model info."""
        hass = self._hass
        if not hass:
            return []

        dev_reg = device_registry.async_get(hass)
        devices = []
        for device in dev_reg.devices.values():
            if device.disabled_by is not None:
                continue

            labels = []
            if hasattr(device, "labels"):
                labels = list(device.labels) if device.labels else []

            devices.append({
                "device_id": device.id,
                "name": device.name_by_user or device.name or "",
                "manufacturer": device.manufacturer or "",
                "model": device.model or "",
                "sw_version": device.sw_version or "",
                "area_id": device.area_id or "",
                "labels": labels,
            })

        return devices

    async def _push_to_core(
        self,
        entities: list[dict[str, Any]],
        areas: list[dict[str, Any]],
        devices: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Push entity/area/device data to Core's bulk import endpoint."""
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
            "devices": devices,
        }

        try:
            result = await client.async_post(
                "/api/v1/entities/bulk", payload
            )
            _LOGGER.debug(
                "Pushed %d entities + %d areas + %d devices to Core",
                len(entities), len(areas), len(devices),
            )
            return result or {}
        except Exception:
            _LOGGER.debug("Entity bulk push to Core failed (non-blocking)")
            return {"error": "push_failed"}

    async def _auto_tag_zone_suggestions(
        self, zone_suggestions: list[dict[str, Any]]
    ) -> None:
        """Process zone suggestions from Core response and auto-tag entities."""
        if not self._hass or not self._entry_id or not zone_suggestions:
            return

        try:
            from .entity_tags_module import get_entity_tags_module
            tags_mod = get_entity_tags_module(self._hass, self._entry_id)
            if tags_mod:
                count = await tags_mod.async_auto_tag_from_zone_suggestions(
                    zone_suggestions
                )
                if count > 0:
                    _LOGGER.info(
                        "Auto-tagged %d entities from %d zone suggestions",
                        count, len(zone_suggestions),
                    )
        except Exception:
            _LOGGER.debug("Zone auto-tagging failed (non-blocking)")

    async def async_classify_entities(self) -> list[dict[str, Any]]:
        """Run ML-style classification on all HA entities.

        Uses the entity_classifier module to analyze entity ID patterns,
        device classes, units of measurement, and name keywords (DE + EN)
        to determine each entity's role and suggest zone assignments.

        Returns a list of classification result dicts for downstream consumers.
        """
        if not self._hass:
            return []

        try:
            from ...entity_classifier import (
                classify_all_entities,
                group_by_zone,
                suggest_zone_entities,
            )

            classifications = await classify_all_entities(self._hass)

            self._last_classification_count = len(classifications)
            self._last_high_confidence_count = sum(
                1 for c in classifications if c.confidence > 0.8
            )

            # Auto-tag high-confidence classifications via entity_tags_module
            try:
                from .entity_tags_module import get_entity_tags_module
                tags_mod = get_entity_tags_module(self._hass, self._entry_id) if self._entry_id else None
                if tags_mod:
                    # Group by zone and auto-tag zone entities
                    zones = group_by_zone(classifications)
                    for zone_name, zone_classifications in zones.items():
                        if zone_name == "_unassigned":
                            continue
                        zone_entity_ids = [
                            c.entity_id for c in zone_classifications
                            if c.confidence >= 0.7
                        ]
                        if zone_entity_ids:
                            zone_id = f"zone:{zone_name.lower().replace(' ', '_')}"
                            await tags_mod.async_auto_tag_zone_entities(
                                zone_id, zone_name, zone_entity_ids,
                            )

                    # Auto-tag by classified role using domain tag map
                    from ...const import DOMAIN_TAG_MAP
                    role_entities: dict[str, list[str]] = {}
                    for c in classifications:
                        if c.confidence >= 0.7 and c.role != "unknown":
                            role_entities.setdefault(c.role, []).append(c.entity_id)

                    for role, entity_ids in role_entities.items():
                        # Find matching domain tag from DOMAIN_TAG_MAP
                        for domain, (tag_id, tag_name, color, icon) in DOMAIN_TAG_MAP.items():
                            if tag_id == role or tag_name.lower() == role:
                                await tags_mod.async_auto_tag_by_domain(
                                    domain, tag_id, tag_name, color, icon,
                                )
                                break

            except Exception:  # noqa: BLE001
                _LOGGER.debug("Classification auto-tagging failed (non-blocking)")

            _LOGGER.info(
                "Entity classification complete: %d total, %d high confidence",
                self._last_classification_count,
                self._last_high_confidence_count,
            )

            # Return serializable dicts for API consumers
            return [
                {
                    "entity_id": c.entity_id,
                    "domain": c.domain,
                    "device_class": c.device_class,
                    "role": c.role,
                    "zone_hint": c.zone_hint,
                    "confidence": c.confidence,
                    "tags": c.tags,
                }
                for c in classifications
            ]

        except Exception:  # noqa: BLE001
            _LOGGER.debug("Entity classification failed (non-blocking)")
            return []

    def get_summary(self) -> dict[str, Any]:
        """Summary for sensor attributes."""
        return {
            "entity_count": self._entity_count,
            "area_count": self._area_count,
            "device_count": self._device_count,
            "last_sync": self._last_sync,
            "resync_interval": RESYNC_INTERVAL,
            "classification_count": self._last_classification_count,
            "high_confidence_count": self._last_high_confidence_count,
        }
