"""UniFi Context Module — Network monitoring context provider.

Connects Core Add-on UniFi Neuron to HA Integration.
Exposes WAN status, clients, roaming events, and traffic baselines.

Privacy-first: Only aggregated network data, no packet inspection.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ...const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN
from ..module import ModuleContext
from ...unifi_context import UnifiContextCoordinator, create_unifi_context
from ...unifi_context_entities import async_setup_unifi_entities

_LOGGER = logging.getLogger(__name__)


class UnifiContextModule:
    """UniFi context provider for other CoPilot modules.

    Fetches network data from Core Add-on and exposes it as entities.
    """

    name = "unifi_context"

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._entry: ConfigEntry | None = None
        self._coordinator: UnifiContextCoordinator | None = None

    @property
    def coordinator(self) -> UnifiContextCoordinator | None:
        """Get the UniFi coordinator."""
        return self._coordinator

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up UniFi context tracking."""
        self._hass = ctx.hass
        self._entry = ctx.entry

        data = {**ctx.entry.data, **ctx.entry.options}

        host = data.get(CONF_HOST)
        port = data.get(CONF_PORT, 8909)
        token = data.get(CONF_TOKEN)

        if not host:
            _LOGGER.warning("UnifiContext: no host configured — module idle")
            return

        # Create coordinator
        self._coordinator = create_unifi_context(
            hass=ctx.hass,
            host=host,
            port=port,
            token=token,
        )

        try:
            await self._coordinator.async_config_entry_first_refresh()
        except Exception as err:
            _LOGGER.warning(
                "UnifiContext: failed initial refresh (Core Add-on may be down): %s",
                err,
            )
            # Continue anyway - Core Add-on might not be running

        # Set up entities
        if self._coordinator:
            await async_setup_unifi_entities(ctx.hass, self._coordinator)

        # Store reference for other modules
        domain_data = ctx.hass.data.setdefault(DOMAIN, {})
        entry_data = domain_data.setdefault(ctx.entry.entry_id, {})
        entry_data["unifi_context_module"] = self

        _LOGGER.info("UnifiContext v0.1: initialized (host=%s:%s)", host, port)

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload UniFi context tracking."""
        domain_data = ctx.hass.data.get(DOMAIN, {})
        entry_data = domain_data.get(ctx.entry.entry_id, {})
        entry_data.pop("unifi_context_module", None)

        self._coordinator = None
        self._hass = None
        self._entry = None

        _LOGGER.debug("UnifiContext: unloaded")
        return True

    def get_snapshot(self) -> dict[str, Any] | None:
        """Get current UniFi snapshot for other modules."""
        if not self._coordinator or not self._coordinator.data:
            return None

        data = self._coordinator.data
        return {
            "timestamp": data.timestamp,
            "wan_online": data.wan.online,
            "wan_latency_ms": data.wan.latency_ms,
            "wan_packet_loss_percent": data.wan.packet_loss_percent,
            "wan_uptime_seconds": data.wan.uptime_seconds,
            "clients_online": len([c for c in data.clients if c.status == "online"]),
            "clients_total": len(data.clients),
            "roaming_events_count": len(data.roaming_events),
            "baselines": {
                "period": data.baselines.period,
                "avg_upload_mbps": data.baselines.avg_upload_mbps,
                "avg_download_mbps": data.baselines.avg_download_mbps,
            },
        }
