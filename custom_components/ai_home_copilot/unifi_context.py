"""UniFi Context: Network monitoring context for AI Home CoPilot.

Provides:
- UniFi snapshot coordinator (WAN status, clients, roaming events)
- Traffic baselines
- Network health sensors
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
class WanStatus:
    """WAN uplink status data."""
    online: bool
    latency_ms: float
    packet_loss_percent: float
    uptime_seconds: int
    ip_address: str | None
    gateway: str | None
    dns_servers: list[str]
    last_check: str


@dataclass(frozen=True, slots=True)
class UnifiClient:
    """Network client data."""
    mac: str
    name: str | None
    ip: str | None
    status: str  # "online", "offline", "roaming"
    device_type: str | None
    connected_ap: str | None
    signal_dbm: int | None
    roaming: bool
    last_seen: str | None


@dataclass(frozen=True, slots=True)
class RoamingEvent:
    """Client roaming event data."""
    client_mac: str
    client_name: str | None
    from_ap: str
    to_ap: str
    timestamp: str
    signal_strength: int | None


@dataclass(frozen=True, slots=True)
class TrafficBaselines:
    """Traffic baseline metrics."""
    period: str
    avg_upload_mbps: float
    avg_download_mbps: float
    peak_upload_mbps: float
    peak_download_mbps: float
    total_bytes_up: int
    total_bytes_down: int
    last_updated: str


@dataclass(frozen=True, slots=True)
class UnifiSnapshot:
    """Complete UniFi network snapshot."""
    timestamp: str
    wan: WanStatus
    clients: list[UnifiClient]
    roaming_events: list[RoamingEvent]
    baselines: TrafficBaselines
    suppress_suggestions: bool
    suppression_reason: str | None


class UnifiContextCoordinator(DataUpdateCoordinator[UnifiSnapshot]):
    """Coordinator for UniFi network context from Core Add-on."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, token: str | None):
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-unifi_context",
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

    async def _async_update_data(self) -> UnifiSnapshot:
        """Fetch UniFi snapshot from Core Add-on."""
        try:
            session = await self._get_session()
            base_url = self._get_base_url()
            url = f"{base_url}/api/v1/unifi"
            
            async with session.get(url, headers=self._get_headers()) as response:
                if response.status == 503:
                    raise Exception("UniFi service not initialized in Core Add-on")
                if response.status == 401:
                    raise Exception("Invalid API token for UniFi service")
                if not response.ok:
                    raise Exception(f"UniFi API returned status {response.status}")
                
                data = await response.json()
                
                wan_data = data.get("wan", {})
                baselines_data = data.get("baselines", {})
                
                return UnifiSnapshot(
                    timestamp=data.get("timestamp", datetime.now().isoformat()),
                    wan=WanStatus(
                        online=wan_data.get("online", False),
                        latency_ms=wan_data.get("latency_ms", 0.0),
                        packet_loss_percent=wan_data.get("packet_loss_percent", 0.0),
                        uptime_seconds=wan_data.get("uptime_seconds", 0),
                        ip_address=wan_data.get("ip_address"),
                        gateway=wan_data.get("gateway"),
                        dns_servers=wan_data.get("dns_servers", []),
                        last_check=wan_data.get("last_check", ""),
                    ),
                    clients=[
                        UnifiClient(
                            mac=c.get("mac", ""),
                            name=c.get("name"),
                            ip=c.get("ip"),
                            status=c.get("status", "unknown"),
                            device_type=c.get("device_type"),
                            connected_ap=c.get("connected_ap"),
                            signal_dbm=c.get("signal_dbm"),
                            roaming=c.get("roaming", False),
                            last_seen=c.get("last_seen"),
                        )
                        for c in data.get("clients", [])
                    ],
                    roaming_events=[
                        RoamingEvent(
                            client_mac=r.get("client_mac", ""),
                            client_name=r.get("client_name"),
                            from_ap=r.get("from_ap", ""),
                            to_ap=r.get("to_ap", ""),
                            timestamp=r.get("timestamp", ""),
                            signal_strength=r.get("signal_strength"),
                        )
                        for r in data.get("roaming_events", [])
                    ],
                    baselines=TrafficBaselines(
                        period=baselines_data.get("period", ""),
                        avg_upload_mbps=baselines_data.get("avg_upload_mbps", 0.0),
                        avg_download_mbps=baselines_data.get("avg_download_mbps", 0.0),
                        peak_upload_mbps=baselines_data.get("peak_upload_mbps", 0.0),
                        peak_download_mbps=baselines_data.get("peak_download_mbps", 0.0),
                        total_bytes_up=baselines_data.get("total_bytes_up", 0),
                        total_bytes_down=baselines_data.get("total_bytes_down", 0),
                        last_updated=baselines_data.get("last_updated", ""),
                    ),
                    suppress_suggestions=data.get("suppress_suggestions", False),
                    suppression_reason=data.get("suppression_reason"),
                )
        except aiohttp.ClientError as err:
            raise Exception(f"Connection error to UniFi service: {err}") from err

    async def async_get_wan_status(self) -> WanStatus | None:
        """Fetch WAN status from Core Add-on."""
        try:
            session = await self._get_session()
            base_url = self._get_base_url()
            url = f"{base_url}/api/v1/unifi/wan"
            
            async with session.get(url, headers=self._get_headers()) as response:
                if not response.ok:
                    return None
                
                data = await response.json()
                return WanStatus(
                    online=data.get("online", False),
                    latency_ms=data.get("latency_ms", 0.0),
                    packet_loss_percent=data.get("packet_loss_percent", 0.0),
                    uptime_seconds=data.get("uptime_seconds", 0),
                    ip_address=data.get("ip_address"),
                    gateway=data.get("gateway"),
                    dns_servers=data.get("dns_servers", []),
                    last_check=data.get("last_check", ""),
                )
        except Exception as err:
            _LOGGER.warning("Failed to fetch WAN status: %s", err)
            return None

    async def async_get_clients(self) -> list[UnifiClient]:
        """Fetch connected clients from Core Add-on."""
        try:
            session = await self._get_session()
            base_url = self._get_base_url()
            url = f"{base_url}/api/v1/unifi/clients"
            
            async with session.get(url, headers=self._get_headers()) as response:
                if not response.ok:
                    return []
                
                data = await response.json()
                return [
                    UnifiClient(
                        mac=c.get("mac", ""),
                        name=c.get("name"),
                        ip=c.get("ip"),
                        status=c.get("status", "unknown"),
                        device_type=c.get("device_type"),
                        connected_ap=c.get("connected_ap"),
                        signal_dbm=c.get("signal_dbm"),
                        roaming=c.get("roaming", False),
                        last_seen=c.get("last_seen"),
                    )
                    for c in data
                ]
        except Exception as err:
            _LOGGER.warning("Failed to fetch UniFi clients: %s", err)
            return []

    async def async_get_roaming_events(self) -> list[RoamingEvent]:
        """Fetch roaming events from Core Add-on."""
        try:
            session = await self._get_session()
            base_url = self._get_base_url()
            url = f"{base_url}/api/v1/unifi/roaming"
            
            async with session.get(url, headers=self._get_headers()) as response:
                if not response.ok:
                    return []
                
                data = await response.json()
                return [
                    RoamingEvent(
                        client_mac=r.get("client_mac", ""),
                        client_name=r.get("client_name"),
                        from_ap=r.get("from_ap", ""),
                        to_ap=r.get("to_ap", ""),
                        timestamp=r.get("timestamp", ""),
                        signal_strength=r.get("signal_strength"),
                    )
                    for r in data
                ]
        except Exception as err:
            _LOGGER.warning("Failed to fetch roaming events: %s", err)
            return []


def create_unifi_context(
    hass: HomeAssistant,
    host: str,
    port: int,
    token: str | None,
) -> UnifiContextCoordinator:
    """Factory function to create UniFi context coordinator."""
    return UnifiContextCoordinator(hass=hass, host=host, port=port, token=token)
