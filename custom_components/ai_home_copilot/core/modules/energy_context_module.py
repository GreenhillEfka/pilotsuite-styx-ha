"""N0 Energy Context v0.1 – Energy monitoring context module.

Provides energy data from Core Add-on for other CoPilot modules.
Exposes consumption, production, anomalies, and load shifting opportunities.

Privacy-first: only aggregated values, no device-level granularity unless user-approved.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ...const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN
from ..module import ModuleContext
from ...energy_context import EnergyContextCoordinator, create_energy_context
from ...energy_context_entities import async_setup_energy_entities

_LOGGER = logging.getLogger(__name__)


class EnergyContextModule:
    """Energy context provider for other CoPilot modules.

    Fetches energy data from Core Add-on and exposes it as entities.
    """

    name = "energy_context"

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._entry: ConfigEntry | None = None
        self._coordinator: EnergyContextCoordinator | None = None

    @property
    def coordinator(self) -> EnergyContextCoordinator | None:
        """Get the energy coordinator."""
        return self._coordinator

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up energy context tracking."""
        self._hass = ctx.hass
        self._entry = ctx.entry

        data = {**ctx.entry.data, **ctx.entry.options}

        host = data.get(CONF_HOST)
        port = data.get(CONF_PORT, 8909)
        token = data.get(CONF_TOKEN)

        if not host:
            _LOGGER.warning("EnergyContext: no host configured — module idle")
            return

        # Create coordinator
        self._coordinator = create_energy_context(
            hass=ctx.hass,
            host=host,
            port=port,
            token=token,
        )

        try:
            await self._coordinator.async_config_entry_first_refresh()
        except Exception as err:
            _LOGGER.warning(
                "EnergyContext: failed initial refresh (Core Add-on may be down): %s",
                err,
            )
            # Continue anyway - Core Add-on might not be running

        # Set up entities
        if self._coordinator:
            await async_setup_energy_entities(ctx.hass, self._coordinator)

        # Store reference for other modules
        domain_data = ctx.hass.data.setdefault(DOMAIN, {})
        entry_data = domain_data.setdefault(ctx.entry.entry_id, {})
        entry_data["energy_context_module"] = self

        _LOGGER.info("EnergyContext v0.1: initialized (host=%s:%s)", host, port)

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload energy context tracking."""
        domain_data = ctx.hass.data.get(DOMAIN, {})
        entry_data = domain_data.get(ctx.entry.entry_id, {})
        entry_data.pop("energy_context_module", None)

        self._coordinator = None
        self._hass = None
        self._entry = None

        _LOGGER.debug("EnergyContext: unloaded")
        return True

    def get_snapshot(self) -> dict[str, Any] | None:
        """Get current energy snapshot for other modules."""
        if not self._coordinator or not self._coordinator.data:
            return None

        data = self._coordinator.data
        return {
            "timestamp": data.timestamp,
            "consumption_today_kwh": data.total_consumption_today_kwh,
            "production_today_kwh": data.total_production_today_kwh,
            "current_power_watts": data.current_power_watts,
            "peak_power_today_watts": data.peak_power_today_watts,
            "anomalies_count": data.anomalies_detected,
            "shifting_opportunities": data.shifting_opportunities,
            "baseline_kwh": data.baseline_kwh,
        }
