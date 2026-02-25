"""N0 Weather Context v0.1 – Weather data module for PV forecasting.

Provides weather data from Core Add-on for energy optimization.
Exposes current conditions, forecasts, and PV-based recommendations.

Privacy-first: only aggregated values, no location granularity unless user-approved.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from ...const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    DOMAIN,
    SIGNAL_CONTEXT_ENTITIES_REFRESH,
)
from ..module import ModuleContext
from ...weather_context import WeatherContextCoordinator, create_weather_context

_LOGGER = logging.getLogger(__name__)


class WeatherContextModule:
    """Weather context provider for PV forecasting and energy optimization.

    Fetches weather data from Core Add-on and exposes it as entities.
    Used by Energy module for PV production estimation.
    """

    name = "weather_context"

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._entry: ConfigEntry | None = None
        self._coordinator: WeatherContextCoordinator | None = None

    @property
    def coordinator(self) -> WeatherContextCoordinator | None:
        """Get the weather coordinator."""
        return self._coordinator

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up weather context tracking."""
        self._hass = ctx.hass
        self._entry = ctx.entry

        data = {**ctx.entry.data, **ctx.entry.options}

        host = data.get(CONF_HOST)
        port = data.get(CONF_PORT, 8909)
        token = data.get(CONF_TOKEN)

        if not host:
            _LOGGER.warning("WeatherContext: no host configured — module idle")
            return

        # Create coordinator
        self._coordinator = create_weather_context(
            hass=ctx.hass,
            host=host,
            port=port,
            token=token,
        )

        try:
            await self._coordinator.async_config_entry_first_refresh()
        except Exception as err:
            _LOGGER.warning(
                "WeatherContext: failed initial refresh (Core Add-on may be down): %s",
                err,
            )
            # Continue anyway - Core Add-on might not be running

        # Store reference for other modules and platform entities
        domain_data = ctx.hass.data.setdefault(DOMAIN, {})
        entry_data = domain_data.setdefault(ctx.entry.entry_id, {})
        entry_data["weather_context_module"] = self
        entry_data["weather_context_coordinator"] = self._coordinator
        async_dispatcher_send(ctx.hass, SIGNAL_CONTEXT_ENTITIES_REFRESH, ctx.entry.entry_id)

        _LOGGER.info("WeatherContext v0.1: initialized (host=%s:%s)", host, port)

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload weather context tracking."""
        domain_data = ctx.hass.data.get(DOMAIN, {})
        entry_data = domain_data.get(ctx.entry.entry_id, {})
        entry_data.pop("weather_context_module", None)
        entry_data.pop("weather_context_coordinator", None)

        self._coordinator = None
        self._hass = None
        self._entry = None

        _LOGGER.debug("WeatherContext: unloaded")
        return True

    def get_snapshot(self) -> dict[str, Any] | None:
        """Get current weather snapshot for other modules."""
        if not self._coordinator or not self._coordinator.data:
            return None

        data = self._coordinator.data
        return {
            "timestamp": data.timestamp,
            "condition": data.condition,
            "temperature_c": data.temperature_c,
            "humidity_percent": data.humidity_percent,
            "cloud_cover_percent": data.cloud_cover_percent,
            "uv_index": data.uv_index,
            "forecast_pv_kwh": data.forecast_pv_production_kwh,
            "recommendation": data.recommendation,
        }

    async def get_forecast(self, days: int = 3) -> list[dict[str, Any]]:
        """Get weather forecast for upcoming days."""
        if not self._coordinator:
            return []
        
        forecast = await self._coordinator.async_get_forecast(days)
        return [
            {
                "timestamp": f.timestamp,
                "condition": f.condition,
                "temp_high_c": f.temperature_high_c,
                "temp_low_c": f.temperature_low_c,
                "cloud_cover": f.cloud_cover_percent,
                "pv_factor": f.pv_production_factor,
            }
            for f in forecast
        ]

    async def get_pv_recommendations(self) -> list[dict[str, Any]]:
        """Get PV-based energy recommendations."""
        if not self._coordinator:
            return []
        
        recs = await self._coordinator.async_get_pv_recommendations()
        return [
            {
                "id": r.id,
                "type": r.recommendation_type,
                "reason": r.reason,
                "pv_surplus_kwh": r.pv_surplus_kwh,
                "confidence": r.confidence,
                "savings_eur": r.estimated_savings_eur,
            }
            for r in recs
        ]
