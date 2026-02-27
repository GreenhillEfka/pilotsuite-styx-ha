"""Zone Bootstrap Module - Laedt zones_config.json in den HabitusZoneStore V2.

Beim Setup wird die statische Zonen-Konfiguration aus data/zones_config.json gelesen
und in den persistenten HabitusZoneStore V2 geschrieben, sofern noch keine Zonen
vorhanden sind. Ein HA-Service erlaubt manuelles Neuladen.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.dispatcher import async_dispatcher_send

from ...const import DOMAIN
from ...habitus_zones_store_v2 import (
    SIGNAL_HABITUS_ZONES_V2_UPDATED,
    async_get_zones_v2,
    async_set_zones_v2_from_raw,
)
from ..module import ModuleContext

_LOGGER = logging.getLogger(__name__)

SERVICE_RELOAD = "zone_bootstrap_reload"

# Path to the bundled zones_config.json (data/ directory next to this package)
_ZONES_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "zones_config.json"
)


class ZoneBootstrapModule:
    """Loads zones_config.json into the HabitusZoneStore V2 on first setup."""

    name = "zone_bootstrap"

    def __init__(self) -> None:
        self._entry_id: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up zone bootstrap for a config entry."""
        hass: HomeAssistant = ctx.hass
        entry: ConfigEntry = ctx.entry
        self._entry_id = entry.entry_id

        # Check whether zones already exist in the store
        existing = await async_get_zones_v2(hass, entry.entry_id)

        if existing:
            _LOGGER.info(
                "ZoneBootstrap: %d zones already in store — skipping initial load",
                len(existing),
            )
        else:
            await self._load_and_persist(hass, entry.entry_id)

        # Register reload service
        async def _handle_reload(call: ServiceCall) -> None:
            """Reload zones from zones_config.json (forced)."""
            _LOGGER.info("ZoneBootstrap: reload requested via service call")
            await self._load_and_persist(hass, entry.entry_id, forced=True)

        hass.services.async_register(DOMAIN, SERVICE_RELOAD, _handle_reload)

        _LOGGER.info("ZoneBootstrapModule initialized")

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the module — remove the service."""
        ctx.hass.services.async_remove(DOMAIN, SERVICE_RELOAD)
        _LOGGER.debug("ZoneBootstrapModule unloaded")
        return True

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _load_and_persist(
        self,
        hass: HomeAssistant,
        entry_id: str,
        *,
        forced: bool = False,
    ) -> None:
        """Read zones_config.json and write into the HabitusZoneStore V2."""
        action = "force-reload" if forced else "initial load"
        _LOGGER.info("ZoneBootstrap: %s from %s", action, _ZONES_CONFIG_PATH)

        raw = await hass.async_add_executor_job(self._read_config_file)
        if raw is None:
            return

        zones_raw: list[dict[str, Any]] | Any = raw
        # The file wraps zones under a top-level "zones" key — async_set_zones_v2_from_raw
        # handles both list and {"zones": [...]} forms, so we can pass the raw dict directly.
        if isinstance(raw, dict):
            zones_raw = raw

        try:
            zones = await async_set_zones_v2_from_raw(
                hass, entry_id, zones_raw, validate=False
            )
            _LOGGER.info(
                "ZoneBootstrap: persisted %d zones into store (entry=%s)",
                len(zones),
                entry_id,
            )
        except Exception:
            _LOGGER.exception("ZoneBootstrap: failed to persist zones")
            return

        # Fire update signal so other modules (e.g. ZoneSyncModule) pick up the change
        async_dispatcher_send(hass, SIGNAL_HABITUS_ZONES_V2_UPDATED, entry_id)

    @staticmethod
    def _read_config_file() -> dict[str, Any] | None:
        """Read and parse zones_config.json (runs in executor)."""
        try:
            with open(_ZONES_CONFIG_PATH, encoding="utf-8") as fh:
                data = json.load(fh)
            _LOGGER.debug(
                "ZoneBootstrap: read %d bytes from zones_config.json",
                _ZONES_CONFIG_PATH.stat().st_size,
            )
            return data
        except FileNotFoundError:
            _LOGGER.error(
                "ZoneBootstrap: zones_config.json not found at %s",
                _ZONES_CONFIG_PATH,
            )
        except json.JSONDecodeError as exc:
            _LOGGER.error(
                "ZoneBootstrap: invalid JSON in zones_config.json — %s", exc
            )
        except Exception:
            _LOGGER.exception("ZoneBootstrap: unexpected error reading config")
        return None
