"""Energy Context: Energy monitoring context for PilotSuite.

Provides:
- Energy snapshot coordinator (consumption, production, anomalies)
- Load shifting opportunities
- Energy sensor entities
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
class EnergySnapshot:
    """Energy snapshot data from Core Add-on."""
    timestamp: str
    total_consumption_today_kwh: float
    total_production_today_kwh: float
    current_power_watts: float
    peak_power_today_watts: float
    anomalies_detected: int
    shifting_opportunities: int
    baseline_kwh: float


@dataclass(frozen=True, slots=True)
class EnergyAnomaly:
    """Energy anomaly data."""
    id: str
    timestamp: str
    device_id: str | None
    device_type: str | None
    expected_value: float
    actual_value: float
    deviation_percent: float
    severity: str  # "low", "medium", "high", "critical"
    description: str


@dataclass(frozen=True, slots=True)
class EnergyShiftingOpportunity:
    """Load shifting opportunity data."""
    id: str
    timestamp: str
    device_type: str
    reason: str
    current_cost_eur: float
    optimal_cost_eur: float
    savings_estimate_eur: float
    suggested_window_start: str
    suggested_window_end: str
    confidence: float  # 0.0 - 1.0


class EnergyContextCoordinator(DataUpdateCoordinator[EnergySnapshot]):
    """Coordinator for Energy context from Core Add-on."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, token: str | None):
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-energy_context",
            update_interval=None,  # Event-driven via N3 forwarder
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

    async def _async_update_data(self) -> EnergySnapshot:
        """Fetch energy snapshot from Core Add-on."""
        try:
            session = await self._get_session()
            base_url = self._get_base_url()
            url = f"{base_url}/api/v1/energy"
            
            async with session.get(url, headers=self._get_headers()) as response:
                if response.status == 503:
                    raise Exception("Energy service not initialized in Core Add-on")
                if response.status == 401:
                    raise Exception("Invalid API token for Energy service")
                if not response.ok:
                    raise Exception(f"Energy API returned status {response.status}")
                
                data = await response.json()
                
                return EnergySnapshot(
                    timestamp=data.get("timestamp", datetime.now().isoformat()),
                    total_consumption_today_kwh=data.get("total_consumption_today_kwh", 0.0),
                    total_production_today_kwh=data.get("total_production_today_kwh", 0.0),
                    current_power_watts=data.get("current_power_watts", 0.0),
                    peak_power_today_watts=data.get("peak_power_today_watts", 0.0),
                    anomalies_detected=data.get("anomalies_detected", 0),
                    shifting_opportunities=data.get("shifting_opportunities", 0),
                    baseline_kwh=data.get("baselines", {}).get("daily_average", 0.0),
                )
        except aiohttp.ClientError as err:
            raise Exception(f"Connection error to Energy service: {err}") from err

    async def async_get_anomalies(self) -> list[EnergyAnomaly]:
        """Fetch energy anomalies from Core Add-on."""
        try:
            session = await self._get_session()
            base_url = self._get_base_url()
            url = f"{base_url}/api/v1/energy/anomalies"
            
            async with session.get(url, headers=self._get_headers()) as response:
                if not response.ok:
                    return []
                
                data = await response.json()
                return [
                    EnergyAnomaly(
                        id=a["id"],
                        timestamp=a.get("timestamp", ""),
                        device_id=a.get("device_id"),
                        device_type=a.get("device_type"),
                        expected_value=a.get("expected_value", 0.0),
                        actual_value=a.get("actual_value", 0.0),
                        deviation_percent=a.get("deviation_percent", 0.0),
                        severity=a.get("severity", "unknown"),
                        description=a.get("description", ""),
                    )
                    for a in data.get("anomalies", [])
                ]
        except Exception as err:
            _LOGGER.warning("Failed to fetch energy anomalies: %s", err)
            return []

    async def async_get_shifting_opportunities(self) -> list[EnergyShiftingOpportunity]:
        """Fetch load shifting opportunities from Core Add-on."""
        try:
            session = await self._get_session()
            base_url = self._get_base_url()
            url = f"{base_url}/api/v1/energy/shifting"
            
            async with session.get(url, headers=self._get_headers()) as response:
                if not response.ok:
                    return []
                
                data = await response.json()
                return [
                    EnergyShiftingOpportunity(
                        id=o["id"],
                        timestamp=o.get("timestamp", ""),
                        device_type=o.get("device_type", ""),
                        reason=o.get("reason", ""),
                        current_cost_eur=o.get("current_cost_eur", 0.0),
                        optimal_cost_eur=o.get("optimal_cost_eur", 0.0),
                        savings_estimate_eur=o.get("savings_estimate_eur", 0.0),
                        suggested_window_start=o.get("suggested_window_start", ""),
                        suggested_window_end=o.get("suggested_window_end", ""),
                        confidence=o.get("confidence", 0.0),
                    )
                    for o in data.get("opportunities", [])
                ]
        except Exception as err:
            _LOGGER.warning("Failed to fetch shifting opportunities: %s", err)
            return []

    async def async_explain_suggestion(self, suggestion_id: str) -> dict[str, Any]:
        """Get explanation for an energy suggestion."""
        try:
            session = await self._get_session()
            base_url = self._get_base_url()
            url = f"{base_url}/api/v1/energy/explain/{suggestion_id}"
            
            async with session.get(url, headers=self._get_headers()) as response:
                if not response.ok:
                    return {}
                
                return await response.json()
        except Exception as err:
            _LOGGER.warning("Failed to fetch suggestion explanation: %s", err)
            return {}


def create_energy_context(
    hass: HomeAssistant,
    host: str,
    port: int,
    token: str | None,
) -> EnergyContextCoordinator:
    """Factory function to create Energy context coordinator."""
    return EnergyContextCoordinator(hass=hass, host=host, port=port, token=token)
