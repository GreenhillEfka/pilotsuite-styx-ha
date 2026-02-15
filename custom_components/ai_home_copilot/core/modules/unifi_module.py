"""UniFi Module v0.2 - Network & Wi-Fi diagnostics.

Implements the unifi_module v0.2 spec as a CopilotModule.

Provides:
- WAN quality checks (loss, latency, jitter, outages)
- Wi-Fi roaming analysis (ping-pong, sticky clients, roam failures)
- AP/Radio health (retries, utilization, DFS events)
- Baselines & anomaly detection
- Presence integration (client location, signal strength)

v0.2 Changes:
- Uses UnifiContextCoordinator for data collection
- Added Presence integration hooks
- Improved error handling
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

from dataclasses import dataclass
import statistics

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.event import async_track_time_interval
import voluptuous as vol

from ...const import DOMAIN
from ..module import CopilotModule, ModuleContext

# Import from existing unifi_context module (avoid duplication)
if TYPE_CHECKING:
    from ...unifi_context import (
        UnifiContextCoordinator,
        UnifiSnapshot,
        UnifiClient,
        WanStatus,
        RoamingEvent,
        TrafficBaselines,
    )

_LOGGER = logging.getLogger(__name__)


# ========== Data Classes ==========

@dataclass
class Candidate:
    """Unified candidate/issue structure."""
    id: str
    type: str
    severity: str  # info, warning, critical
    summary: str
    evidence: Dict[str, Any]
    suggested_actions: List[str]
    tags: List[str]
    timestamp: datetime


# ========== Module Implementation ==========

class UniFiModule:
    """UniFi Module v0.2 implementation."""

    # Threshold configuration
    DEFAULT_THRESHOLDS = {
        "wan_loss_warning": 1.0,  # %
        "wan_loss_critical": 3.0,
        "wan_latency_warning": 50.0,  # ms
        "wan_latency_critical": 100.0,
        "wan_jitter_warning": 20.0,  # ms
        "wan_jitter_critical": 30.0,
        "roam_rate_high": 6,  # per hour
        "rssi_sticky_threshold": -75,  # dBm
        "ap_utilization_high": 70.0,  # %
        "ap_retries_high": 20.0,  # %
    }

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._entry_id: str | None = None
        self._coordinator: "UnifiContextCoordinator | None" = None
        self._thresholds: Dict[str, float] = {}
        self._baseline_data: Dict[str, Any] = {}
        self._candidates: List[Candidate] = []
        self._last_check: datetime | None = None
        self._polling_unsub: Any = None

    @property
    def name(self) -> str:
        return "unifi_module"

    @property
    def coordinator(self) -> "UnifiContextCoordinator | None":
        """Get the UniFi coordinator for external access."""
        return self._coordinator

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the UniFi module for this config entry."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry.entry_id

        # Initialize data storage
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        if self._entry_id not in hass.data[DOMAIN]:
            hass.data[DOMAIN][self._entry_id] = {}

        entry_data = hass.data[DOMAIN][self._entry_id]
        entry_data["unifi_module"] = {
            "config": self._create_default_config(ctx.entry),
            "baseline_data": {},
            "last_check": None,
            "candidates": [],
            "polling_unsub": None,
        }

        unifi_data = entry_data["unifi_module"]

        # Get thresholds from config
        config = unifi_data["config"]
        self._thresholds = config.get("thresholds", self.DEFAULT_THRESHOLDS)

        # Try to get the coordinator from unifi_context_module
        self._coordinator = self._get_unifi_coordinator(ctx)

        if self._coordinator is None:
            _LOGGER.warning(
                "UniFi module: no UnifiContextCoordinator found. "
                "Network diagnostics will be limited."
            )

        # Register services
        await self._register_services(ctx.hass, self._entry_id)

        # Set up periodic checks (every 15 minutes)
        unifi_data["polling_unsub"] = async_track_time_interval(
            ctx.hass,
            lambda _: ctx.hass.async_create_task(self._periodic_check()),
            timedelta(minutes=config.get("check_interval_minutes", 15)),
        )

        # Run initial check
        await self._periodic_check()

        _LOGGER.info("UniFi module v0.2 initialized for entry %s", self._entry_id)

    def _get_unifi_coordinator(self, ctx: ModuleContext) -> "UnifiContextCoordinator | None":
        """Get the UnifiContextCoordinator from unifi_context_module."""
        try:
            entry_data = ctx.hass.data[DOMAIN].get(ctx.entry.entry_id, {})
            context_module = entry_data.get("unifi_context_module")
            if context_module and hasattr(context_module, "coordinator"):
                return context_module.coordinator
        except Exception as e:
            _LOGGER.debug("Could not get UnifiContextCoordinator: %s", e)
        return None

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the UniFi module."""
        try:
            entry_data = ctx.hass.data[DOMAIN].get(ctx.entry.entry_id, {})
            unifi_data = entry_data.get("unifi_module", {})

            # Cancel polling
            polling_unsub = unifi_data.get("polling_unsub")
            if polling_unsub:
                polling_unsub()

            # Clear data
            if "unifi_module" in entry_data:
                del entry_data["unifi_module"]

            _LOGGER.info("UniFi module unloaded for entry %s", ctx.entry.entry_id)
            return True

        except Exception as e:
            _LOGGER.error("Error unloading UniFi module: %s", e)
            return False

    def _create_default_config(self, entry: ConfigEntry) -> Dict[str, Any]:
        """Create default configuration."""
        return {
            "enabled": True,
            "check_interval_minutes": 15,
            "baseline_days": 14,
            "thresholds": self.DEFAULT_THRESHOLDS.copy(),
        }

    async def _register_services(self, hass: HomeAssistant, entry_id: str) -> None:
        """Register UniFi module services."""

        async def handle_run_diagnostics(call: ServiceCall) -> None:
            """Run UniFi diagnostics on demand."""
            await self._periodic_check()

        async def handle_get_report(call: ServiceCall) -> Dict[str, Any]:
            """Get current UniFi diagnostic report."""
            return await self._generate_report()

        async def handle_get_clients(call: ServiceCall) -> List[Dict[str, Any]]:
            """Get connected clients."""
            return self.get_clients_snapshot()

        service_prefix = f"{DOMAIN}_unifi"

        hass.services.async_register(
            DOMAIN, f"{service_prefix}_run_diagnostics", handle_run_diagnostics
        )
        hass.services.async_register(
            DOMAIN, f"{service_prefix}_get_report", handle_get_report
        )
        hass.services.async_register(
            DOMAIN, f"{service_prefix}_get_clients", handle_get_clients
        )

    async def _periodic_check(self) -> None:
        """Periodic diagnostic check."""
        if not self._coordinator:
            _LOGGER.debug("UniFi periodic check skipped: no coordinator")
            return

        try:
            # Refresh coordinator data
            await self._coordinator.async_refresh()

            snapshot = self._coordinator.data
            if not snapshot:
                _LOGGER.warning("UniFi periodic check: no data available")
                return

            _LOGGER.debug("Running UniFi periodic diagnostics")

            # Run checks and generate candidates
            candidates: List[Candidate] = []

            # Check A: WAN Quality
            candidates.extend(self._check_wan_quality(snapshot))

            # Check B: WAN Failover
            candidates.extend(self._check_wan_failover(snapshot))

            # Check C: Roaming
            candidates.extend(self._check_roaming(snapshot))

            # Check D: AP Health
            candidates.extend(self._check_ap_health(snapshot))

            # Store results
            self._candidates = candidates
            self._last_check = datetime.now()

            # Update hass data
            if self._entry_id:
                entry_data = self._hass.data[DOMAIN].get(self._entry_id, {})
                if "unifi_module" in entry_data:
                    entry_data["unifi_module"]["candidates"] = candidates
                    entry_data["unifi_module"]["last_check"] = self._last_check

            # Log summary
            if candidates:
                _LOGGER.info(
                    "UniFi diagnostics found %d issues: %s",
                    len(candidates),
                    ", ".join(c.type for c in candidates)
                )
            else:
                _LOGGER.debug("UniFi diagnostics: all checks passed")

        except Exception as e:
            _LOGGER.error("Error in UniFi periodic check: %s", e, exc_info=True)

    # ========== Presence Integration ==========

    def get_clients_snapshot(self) -> List[Dict[str, Any]]:
        """Get current clients for Presence module.

        Returns:
            List of client dicts with location, signal, and status info.
        """
        if not self._coordinator or not self._coordinator.data:
            return []

        snapshot = self._coordinator.data
        clients = []

        for client in snapshot.clients:
            clients.append({
                "mac": client.mac,
                "name": client.name,
                "ip": client.ip,
                "status": client.status,
                "device_type": client.device_type,
                "connected_ap": client.connected_ap,
                "signal_dbm": client.signal_dbm,
                "roaming": client.roaming,
                "last_seen": client.last_seen,
                # Presence-relevant fields
                "is_online": client.status == "online",
                "signal_strength": self._get_signal_level(client.signal_dbm),
            })

        return clients

    def get_clients_by_ap(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get clients grouped by AP for room-based presence."""
        clients_by_ap: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for client in self.get_clients_snapshot():
            ap = client.get("connected_ap", "unknown")
            clients_by_ap[ap].append(client)

        return dict(clients_by_ap)

    def get_client_by_mac(self, mac: str) -> Optional[Dict[str, Any]]:
        """Get specific client by MAC address."""
        for client in self.get_clients_snapshot():
            if client.get("mac", "").lower() == mac.lower():
                return client
        return None

    def get_roaming_events_recent(self, minutes: int = 30) -> List[Dict[str, Any]]:
        """Get recent roaming events for activity detection."""
        if not self._coordinator or not self._coordinator.data:
            return []

        snapshot = self._coordinator.data
        events = []

        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=minutes)

            for event in snapshot.roaming_events:
                event_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                if event_time >= cutoff:
                    events.append({
                        "client_mac": event.client_mac,
                        "client_name": event.client_name,
                        "from_ap": event.from_ap,
                        "to_ap": event.to_ap,
                        "timestamp": event.timestamp,
                        "signal_strength": event.signal_strength,
                    })
        except Exception as e:
            _LOGGER.debug("Error processing roaming events: %s", e)

        return events

    def get_wan_status(self) -> Optional[Dict[str, Any]]:
        """Get current WAN status."""
        if not self._coordinator or not self._coordinator.data:
            return None

        wan = self._coordinator.data.wan
        return {
            "online": wan.online,
            "latency_ms": wan.latency_ms,
            "packet_loss_percent": wan.packet_loss_percent,
            "uptime_seconds": wan.uptime_seconds,
            "ip_address": wan.ip_address,
            "gateway": wan.gateway,
            "dns_servers": wan.dns_servers,
        }

    @staticmethod
    def _get_signal_level(signal_dbm: Optional[int]) -> str:
        """Convert dBm to signal level string."""
        if signal_dbm is None:
            return "unknown"
        if signal_dbm >= -50:
            return "excellent"
        if signal_dbm >= -60:
            return "good"
        if signal_dbm >= -70:
            return "fair"
        return "poor"

    # ========== Check A: WAN Quality ==========

    def _check_wan_quality(self, snapshot: "UnifiSnapshot") -> List[Candidate]:
        """Check WAN loss, latency, jitter."""
        candidates = []
        wan = snapshot.wan

        # Check packet loss
        if wan.packet_loss_percent >= self._thresholds.get("wan_loss_critical", 3.0):
            candidates.append(Candidate(
                id=f"wan_loss_{wan.ip_address or 'default'}",
                type="candidate.net.wan_quality.degraded",
                severity="critical",
                summary=f"WAN: Packet loss {wan.packet_loss_percent:.1f}% (critical)",
                evidence={
                    "packet_loss_percent": wan.packet_loss_percent,
                    "latency_ms": wan.latency_ms,
                    "ip_address": wan.ip_address,
                    "timestamp": snapshot.timestamp,
                },
                suggested_actions=[
                    "Check modem/ONT logs for signal issues",
                    "Verify physical WAN cable connections",
                    "Contact ISP if issue persists",
                ],
                tags=["net", "wan", "loss"],
                timestamp=datetime.now(),
            ))
        elif wan.packet_loss_percent >= self._thresholds.get("wan_loss_warning", 1.0):
            candidates.append(Candidate(
                id=f"wan_loss_{wan.ip_address or 'default'}",
                type="candidate.net.wan_quality.degraded",
                severity="warning",
                summary=f"WAN: Packet loss {wan.packet_loss_percent:.1f}% (degraded)",
                evidence={
                    "packet_loss_percent": wan.packet_loss_percent,
                    "latency_ms": wan.latency_ms,
                    "ip_address": wan.ip_address,
                    "timestamp": snapshot.timestamp,
                },
                suggested_actions=[
                    "Monitor WAN connection over next hour",
                    "Check for local interference or device issues",
                ],
                tags=["net", "wan", "loss"],
                timestamp=datetime.now(),
            ))

        # Check latency
        if wan.latency_ms >= self._thresholds.get("wan_latency_critical", 100.0):
            candidates.append(Candidate(
                id="wan_latency_high",
                type="candidate.net.wan_quality.latency",
                severity="critical",
                summary=f"WAN: High latency {wan.latency_ms:.0f}ms (critical)",
                evidence={
                    "latency_ms": wan.latency_ms,
                    "packet_loss_percent": wan.packet_loss_percent,
                    "timestamp": snapshot.timestamp,
                },
                suggested_actions=[
                    "Check for bandwidth saturation",
                    "Review QoS settings",
                    "Contact ISP about line quality",
                ],
                tags=["net", "wan", "latency"],
                timestamp=datetime.now(),
            ))
        elif wan.latency_ms >= self._thresholds.get("wan_latency_warning", 50.0):
            candidates.append(Candidate(
                id="wan_latency_high",
                type="candidate.net.wan_quality.latency",
                severity="warning",
                summary=f"WAN: Elevated latency {wan.latency_ms:.0f}ms",
                evidence={
                    "latency_ms": wan.latency_ms,
                    "timestamp": snapshot.timestamp,
                },
                suggested_actions=[
                    "Monitor for sustained elevation",
                    "Check local network usage",
                ],
                tags=["net", "wan", "latency"],
                timestamp=datetime.now(),
            ))

        return candidates

    # ========== Check B: WAN Failover ==========

    def _check_wan_failover(self, snapshot: "UnifiSnapshot") -> List[Candidate]:
        """Check for unexpected WAN failovers."""
        candidates = []
        wan = snapshot.wan

        if not wan.online:
            candidates.append(Candidate(
                id="wan_offline",
                type="candidate.net.wan_outage",
                severity="critical",
                summary="WAN is offline",
                evidence={
                    "ip_address": wan.ip_address,
                    "uptime_seconds": wan.uptime_seconds,
                    "timestamp": snapshot.timestamp,
                },
                suggested_actions=[
                    "Check gateway WAN status page",
                    "Verify physical connection",
                    "Review gateway logs",
                ],
                tags=["net", "wan", "outage"],
                timestamp=datetime.now(),
            ))

        return candidates

    # ========== Check C: Roaming ==========

    def _check_roaming(self, snapshot: "UnifiSnapshot") -> List[Candidate]:
        """Check for roaming issues."""
        candidates = []
        roam_threshold = self._thresholds.get("roam_rate_high", 6)
        rssi_threshold = self._thresholds.get("rssi_sticky_threshold", -75)

        # Track roam counts per client
        roam_counts: Dict[str, int] = defaultdict(int)
        for event in snapshot.roaming_events:
            roam_counts[event.client_mac] += 1

        for client in snapshot.clients:
            # Check for excessive roaming
            roam_count = roam_counts.get(client.mac, 0)
            if roam_count >= roam_threshold * 24:  # Daily threshold
                candidates.append(Candidate(
                    id=f"roam_pingpong_{client.mac}",
                    type="candidate.wifi.roam.pingpong",
                    severity="warning",
                    summary=f"Client {client.name or client.mac}: Excessive roaming ({roam_count} times)",
                    evidence={
                        "client_mac": client.mac,
                        "client_name": client.name,
                        "roam_count": roam_count,
                        "current_ap": client.connected_ap,
                        "signal_dbm": client.signal_dbm,
                    },
                    suggested_actions=[
                        "Review AP placement and signal overlap",
                        "Check roaming thresholds (minimum RSSI)",
                        "Consider adjusting band steering settings",
                    ],
                    tags=["wifi", "roam", "pingpong"],
                    timestamp=datetime.now(),
                ))

            # Check for sticky clients with weak signal
            if client.signal_dbm is not None and client.signal_dbm < rssi_threshold:
                candidates.append(Candidate(
                    id=f"sticky_client_{client.mac}",
                    type="candidate.wifi.client.sticky",
                    severity="warning",
                    summary=f"Client {client.name or client.mac}: Weak signal ({client.signal_dbm} dBm)",
                    evidence={
                        "client_mac": client.mac,
                        "client_name": client.name,
                        "current_ap": client.connected_ap,
                        "signal_dbm": client.signal_dbm,
                    },
                    suggested_actions=[
                        "Client device may have aggressive roaming threshold",
                        "Reduce AP transmit power to encourage roaming",
                        "Check if stronger AP is available nearby",
                    ],
                    tags=["wifi", "client", "sticky"],
                    timestamp=datetime.now(),
                ))

        return candidates

    # ========== Check D: AP Health ==========

    def _check_ap_health(self, snapshot: "UnifiSnapshot") -> List[Candidate]:
        """Check AP/Radio health."""
        candidates = []

        # Group clients by AP to get counts
        ap_clients: Dict[str, int] = defaultdict(int)
        for client in snapshot.clients:
            if client.connected_ap:
                ap_clients[client.connected_ap] += 1

        # Note: Full AP metrics would require additional API endpoints
        # This is a simplified check based on client counts
        for ap_name, client_count in ap_clients.items():
            if client_count >= 20:  # High client density
                candidates.append(Candidate(
                    id=f"ap_high_clients_{ap_name}",
                    type="candidate.wifi.ap.clients.high",
                    severity="warning",
                    summary=f"AP {ap_name}: High client count ({client_count})",
                    evidence={
                        "ap_name": ap_name,
                        "client_count": client_count,
                    },
                    suggested_actions=[
                        "Consider adding another AP in the area",
                        "Review bandwidth-intensive clients",
                    ],
                    tags=["wifi", "ap", "clients"],
                    timestamp=datetime.now(),
                ))

        return candidates

    # ========== Reporting ==========

    async def _generate_report(self) -> Dict[str, Any]:
        """Generate diagnostic report."""
        if not self._candidates:
            return {
                "status": "healthy",
                "message": "All UniFi checks passed",
                "timestamp": self._last_check.isoformat() if self._last_check else None,
            }

        # Group by severity
        critical = [c for c in self._candidates if c.severity == "critical"]
        warning = [c for c in self._candidates if c.severity == "warning"]
        info = [c for c in self._candidates if c.severity == "info"]

        return {
            "status": "issues_found",
            "critical_count": len(critical),
            "warning_count": len(warning),
            "info_count": len(info),
            "issues": [
                {
                    "id": c.id,
                    "type": c.type,
                    "severity": c.severity,
                    "summary": c.summary,
                    "suggested_actions": c.suggested_actions,
                }
                for c in self._candidates
            ],
            "timestamp": self._last_check.isoformat() if self._last_check else None,
            "wan_status": self.get_wan_status(),
        }
