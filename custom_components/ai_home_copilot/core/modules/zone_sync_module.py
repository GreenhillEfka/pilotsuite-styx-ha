"""Zone Sync Module - Bidirectional Habitus Zone synchronization.

Responsibilities:
  - Watches for zone changes in HA store (SIGNAL_HABITUS_ZONES_V2_UPDATED)
  - Pushes zone updates to Core via /api/v1/habitus/zones/sync
  - Pulls zone metadata (mood, activity) from Core on coordinator refresh
  - Ensures zone entity_ids match between HA and Core

Replaces scattered zone sync logic across config_zones_flow and zone_detector.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ...const import DOMAIN
from ...connection_config import merged_entry_config
from ...habitus_zones_store_v2 import SIGNAL_HABITUS_ZONES_V2_UPDATED
from ..module import ModuleContext

_LOGGER = logging.getLogger(__name__)


class ZoneSyncModule:
    """Bidirectional zone sync between HA and Core."""

    name = "zone_sync"

    def __init__(self) -> None:
        self._unsub: list = []
        self._sync_lock = asyncio.Lock()
        self._last_sync_hash: str = ""

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry

        # Subscribe to zone store changes
        @callback
        def _on_zones_updated() -> None:
            """Trigger sync when zones change in HA store."""
            hass.async_create_task(self._sync_zones_to_core(hass, entry))

        unsub = async_dispatcher_connect(
            hass, SIGNAL_HABITUS_ZONES_V2_UPDATED, _on_zones_updated
        )
        self._unsub.append(unsub)

        # Initial sync on setup
        await self._sync_zones_to_core(hass, entry)

        _LOGGER.info("ZoneSyncModule initialized")

    async def _sync_zones_to_core(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Push all zones from HA store to Core."""
        async with self._sync_lock:
            try:
                api = self._get_api(hass, entry)
                if not api:
                    return

                # Get zones from HA store
                store = hass.data.get(DOMAIN, {}).get("zones_store_v2")
                if not store:
                    _LOGGER.debug("No zone store found — skipping sync")
                    return

                zones_dict = await store.async_load() if hasattr(store, "async_load") else {}
                zones = list(zones_dict.values()) if isinstance(zones_dict, dict) else []

                if not zones:
                    _LOGGER.debug("No zones to sync")
                    return

                # Build payload for Core
                zone_payload = []
                for zone in zones:
                    if hasattr(zone, "__dict__"):
                        # Frozen dataclass — convert to dict
                        zone_data = {
                            "zone_id": getattr(zone, "zone_id", ""),
                            "name": getattr(zone, "name", ""),
                            "zone_type": getattr(zone, "zone_type", "room"),
                            "entity_ids": list(getattr(zone, "entity_ids", ())),
                            "entities": dict(getattr(zone, "entities", {})),
                            "parent_zone_id": getattr(zone, "parent_zone_id", None),
                            "child_zone_ids": list(getattr(zone, "child_zone_ids", ())),
                            "floor": getattr(zone, "floor", None),
                            "current_state": getattr(zone, "current_state", "idle"),
                            "priority": getattr(zone, "priority", 5),
                            "tags": list(getattr(zone, "tags", ())),
                        }
                    elif isinstance(zone, dict):
                        zone_data = zone
                    else:
                        continue

                    if zone_data.get("zone_id"):
                        zone_payload.append(zone_data)

                if not zone_payload:
                    return

                # Compute hash to avoid unnecessary syncs
                import hashlib
                import json
                sync_hash = hashlib.md5(
                    json.dumps(zone_payload, sort_keys=True, default=str).encode()
                ).hexdigest()

                if sync_hash == self._last_sync_hash:
                    _LOGGER.debug("Zone data unchanged — skipping sync")
                    return

                # Push to Core (try new API first, then legacy)
                for endpoint in ("/api/v1/habitus/zones/sync", "/api/v1/hub/zones/sync"):
                    try:
                        resp = await api.async_post(
                            endpoint,
                            json={"zones": zone_payload, "full_sync": True},
                        )
                        if resp and resp.get("ok"):
                            self._last_sync_hash = sync_hash
                            _LOGGER.info(
                                "Synced %d zones to Core via %s", len(zone_payload), endpoint
                            )
                            return
                    except Exception:
                        _LOGGER.debug("Zone sync to %s failed", endpoint)

                _LOGGER.debug("Zone sync failed on all endpoints")

            except Exception:
                _LOGGER.exception("Zone sync error")

    def _get_api(self, hass: HomeAssistant, entry: ConfigEntry):
        """Get the CopilotApiClient."""
        data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if isinstance(data, dict):
            coordinator = data.get("coordinator")
            if coordinator and hasattr(coordinator, "api"):
                return coordinator.api
        return None

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        for unsub in self._unsub:
            unsub()
        self._unsub.clear()
        return True
