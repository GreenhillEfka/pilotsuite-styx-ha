"""Weather Context: Weather data for PV forecasting and energy optimization.

Provides:
- Weather snapshot coordinator (current conditions + forecast)
- PV production estimation
- Weather-based energy recommendations
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

import aiohttp
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WeatherSnapshot:
    """Weather snapshot data from weather API or Core Add-on."""
    timestamp: str
    condition: str  # "sunny", "cloudy", "rainy", "stormy", "clear", "partly_cloudy"
    temperature_c: float
    humidity_percent: float
    cloud_cover_percent: float
    uv_index: float
    sunrise: str
    sunset: str
    forecast_pv_production_kwh: float  # Estimated PV production today
    recommendation: str  # "optimal_charging", "moderate_usage", "grid_recommended"


@dataclass(frozen=True, slots=True)
class WeatherForecast:
    """Weather forecast data."""
    timestamp: str
    condition: str
    temperature_high_c: float
    temperature_low_c: float
    cloud_cover_percent: float
    precipitation_probability: float
    pv_production_factor: float  # 0.0 - 1.0, 1.0 = optimal


@dataclass(frozen=True, slots=True)
class PVRecommendation:
    """PV-based energy recommendation."""
    id: str
    timestamp: str
    recommendation_type: str  # "charge_ev", "run_hvac", "defer_load", "grid_optimal"
    reason: str
    pv_surplus_kwh: float
    confidence: float  # 0.0 - 1.0
    suggested_action: str
    estimated_savings_eur: float


class WeatherContextCoordinator(DataUpdateCoordinator[WeatherSnapshot]):
    """Coordinator for Weather context from Core Add-on."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, token: str | None):
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-weather_context",
            update_interval=None,  # Event-driven or polling (e.g., 15 min)
        )
        self._host = host
        self._port = port
        self._token = token
        self._session: aiohttp.ClientSession | None = None

    def _get_base_url(self) -> str:
        """Build base URL for Core Add-on API."""
        host = self._host.strip().rstrip("/")
        # If host already has scheme, use it; otherwise default to http
        if host.startswith(("http://", "https://")):
            parsed = urlsplit(host)
            # Use provided scheme but construct proper URL with port
            scheme = parsed.scheme
            netloc = parsed.netloc
            if ":" not in netloc:  # No port in URL
                netloc = f"{netloc}:{self._port}"
            return f"{scheme}://{netloc}"
        # No scheme provided, default to http
        return f"http://{host}:{self._port}"

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with auth token."""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None:
            self._session = async_get_clientsession(self.hass)
        return self._session

    async def _async_update_data(self) -> WeatherSnapshot:
        """Fetch weather snapshot from Core Add-on."""
        try:
            session = await self._get_session()
            base_url = self._get_base_url()
            # Updated endpoint path for Core Add-on v0.4.28
            url = f"{base_url}/api/v1/weather"
            
            async with session.get(url, headers=self._get_headers()) as response:
                if response.status == 503:
                    raise Exception("Weather service not initialized in Core Add-on")
                if response.status == 401:
                    raise Exception("Invalid API token for Weather service")
                if not response.ok:
                    raise Exception(f"Weather API returned status {response.status}")
                
                data = await response.json()
                
                # Handle wrapped response from Core API
                if "data" in data:
                    data = data["data"]
                
                return WeatherSnapshot(
                    timestamp=data.get("timestamp", datetime.now().isoformat()),
                    condition=data.get("condition", "unknown"),
                    temperature_c=data.get("temperature_c", 0.0),
                    humidity_percent=data.get("humidity_percent", 0.0),
                    cloud_cover_percent=data.get("cloud_cover_percent", 0.0),
                    uv_index=data.get("uv_index", 0.0),
                    sunrise=data.get("sunrise", ""),
                    sunset=data.get("sunset", ""),
                    forecast_pv_production_kwh=data.get("forecast_pv_production_kwh", 0.0),
                    recommendation=data.get("recommendation", "moderate_usage"),
                )
        except aiohttp.ClientError as err:
            raise Exception(f"Connection error to Weather service: {err}") from err

    async def async_get_forecast(self, days: int = 3) -> list[WeatherForecast]:
        """Fetch weather forecast from Core Add-on."""
        try:
            session = await self._get_session()
            base_url = self._get_base_url()
            url = f"{base_url}/api/v1/weather/forecast?days={days}"
            
            async with session.get(url, headers=self._get_headers()) as response:
                if not response.ok:
                    return []
                
                data = await response.json()
                
                # Handle wrapped response from Core API
                if "data" in data:
                    data = data["data"]
                return [
                    WeatherForecast(
                        timestamp=f.get("timestamp", ""),
                        condition=f.get("condition", "unknown"),
                        temperature_high_c=f.get("temperature_high_c", 0.0),
                        temperature_low_c=f.get("temperature_low_c", 0.0),
                        cloud_cover_percent=f.get("cloud_cover_percent", 0.0),
                        precipitation_probability=f.get("precipitation_probability", 0.0),
                        pv_production_factor=f.get("pv_production_factor", 0.5),
                    )
                    for f in data.get("forecast", [])
                ]
        except Exception as err:
            _LOGGER.warning("Failed to fetch weather forecast: %s", err)
            return []

    async def async_get_pv_recommendations(self) -> list[PVRecommendation]:
        """Fetch PV-based energy recommendations."""
        try:
            session = await self._get_session()
            base_url = self._get_base_url()
            url = f"{base_url}/api/v1/weather/pv-recommendations"
            
            async with session.get(url, headers=self._get_headers()) as response:
                if not response.ok:
                    return []
                
                data = await response.json()
                
                # Handle wrapped response from Core API
                if "data" in data:
                    data = data["data"]
                return [
                    PVRecommendation(
                        id=r["id"],
                        timestamp=r.get("timestamp", ""),
                        recommendation_type=r.get("recommendation_type", "grid_optimal"),
                        reason=r.get("reason", ""),
                        pv_surplus_kwh=r.get("pv_surplus_kwh", 0.0),
                        confidence=r.get("confidence", 0.5),
                        suggested_action=r.get("suggested_action", ""),
                        estimated_savings_eur=r.get("estimated_savings_eur", 0.0),
                    )
                    for r in data.get("recommendations", [])
                ]
        except Exception as err:
            _LOGGER.warning("Failed to fetch PV recommendations: %s", err)
            return []


def create_weather_context(
    hass: HomeAssistant,
    host: str,
    port: int,
    token: str | None,
) -> WeatherContextCoordinator:
    """Factory function to create Weather context coordinator."""
    return WeatherContextCoordinator(hass=hass, host=host, port=port, token=token)
