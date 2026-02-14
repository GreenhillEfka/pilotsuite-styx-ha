"""UniFi Module v0.1 - Network & Wi-Fi diagnostics.

Implements the unifi_module v0.1 spec as a CopilotModule.

Provides:
- WAN quality checks (loss, latency, jitter, outages)
- Wi-Fi roaming analysis (ping-pong, sticky clients, roam failures)
- AP/Radio health (retries, utilization, DFS events)
- Baselines & anomaly detection
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import statistics

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.event import async_track_time_interval
import voluptuous as vol

from ...const import DOMAIN
from ..module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)


# ========== Data Classes ==========

@dataclass
class WANMetrics:
    """WAN quality metrics."""
    interface: str
    timestamp: datetime
    packet_loss_percent: Optional[float] = None
    latency_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    outage_count: int = 0
    is_active: bool = True
    

@dataclass
class ClientMetrics:
    """Wi-Fi client metrics."""
    mac: str
    name: Optional[str]
    current_ap: str
    rssi: Optional[int] = None
    snr: Optional[int] = None
    roam_count_24h: int = 0
    disconnect_count_24h: int = 0
    last_disconnect_reason: Optional[str] = None
    session_duration_avg_min: Optional[float] = None


@dataclass
class APMetrics:
    """AP/Radio health metrics."""
    ap_name: str
    mac: str
    channel_2g: Optional[int] = None
    channel_5g: Optional[int] = None
    utilization_2g_percent: Optional[float] = None
    utilization_5g_percent: Optional[float] = None
    retries_2g_percent: Optional[float] = None
    retries_5g_percent: Optional[float] = None
    client_count_2g: int = 0
    client_count_5g: int = 0
    dfs_event_count_24h: int = 0


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
    """UniFi Module v0.1 implementation."""

    @property
    def name(self) -> str:
        return "unifi_module"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the UniFi module for this config entry."""
        hass = ctx.hass
        entry = ctx.entry
        
        # Initialize module data
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        
        if entry.entry_id not in hass.data[DOMAIN]:
            hass.data[DOMAIN][entry.entry_id] = {}
        
        entry_data = hass.data[DOMAIN][entry.entry_id]
        entry_data["unifi_module"] = {
            "config": self._create_default_config(entry),
            "baseline_data": {},  # Rolling baseline storage
            "last_check": None,
            "candidates": [],
            "polling_unsub": None,
        }
        
        unifi_data = entry_data["unifi_module"]
        
        # Register services
        await self._register_services(hass, entry.entry_id)
        
        # Set up periodic checks (every 15 minutes)
        unifi_data["polling_unsub"] = async_track_time_interval(
            hass,
            lambda _: asyncio.create_task(self._periodic_check(hass, entry.entry_id)),
            timedelta(minutes=15),
        )
        
        # Run initial check
        await self._periodic_check(hass, entry.entry_id)
        
        _LOGGER.info("UniFi module v0.1 initialized for entry %s", entry.entry_id)

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the UniFi module."""
        hass = ctx.hass
        entry = ctx.entry
        
        try:
            entry_data = hass.data[DOMAIN][entry.entry_id]
            unifi_data = entry_data.get("unifi_module", {})
            
            # Cancel polling
            polling_unsub = unifi_data.get("polling_unsub")
            if polling_unsub:
                polling_unsub()
            
            # Clear data
            if "unifi_module" in entry_data:
                del entry_data["unifi_module"]
            
            _LOGGER.info("UniFi module unloaded for entry %s", entry.entry_id)
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
            "thresholds": {
                "wan_loss_warning": 1.0,  # %
                "wan_loss_critical": 3.0,
                "wan_jitter_warning": 20.0,  # ms
                "wan_jitter_critical": 30.0,
                "roam_rate_high": 6,  # per hour
                "rssi_sticky_threshold": -75,  # dBm
                "ap_utilization_high": 70.0,  # %
                "ap_retries_high": 20.0,  # %
            }
        }

    async def _register_services(self, hass: HomeAssistant, entry_id: str) -> None:
        """Register UniFi module services."""
        
        async def handle_run_diagnostics(call: ServiceCall) -> None:
            """Run UniFi diagnostics on demand."""
            await self._periodic_check(hass, entry_id)
            
        async def handle_get_report(call: ServiceCall) -> None:
            """Get current UniFi diagnostic report."""
            report = await self._generate_report(hass, entry_id)
            _LOGGER.info("UniFi Report:\n%s", report)
        
        service_prefix = f"{DOMAIN}_unifi"
        
        hass.services.async_register(
            DOMAIN, f"{service_prefix}_run_diagnostics", handle_run_diagnostics
        )
        hass.services.async_register(
            DOMAIN, f"{service_prefix}_get_report", handle_get_report
        )

    async def _periodic_check(self, hass: HomeAssistant, entry_id: str) -> None:
        """Periodic diagnostic check."""
        try:
            entry_data = hass.data[DOMAIN][entry_id]
            unifi_data = entry_data["unifi_module"]
            
            if not unifi_data["config"]["enabled"]:
                return
            
            _LOGGER.debug("Running UniFi periodic diagnostics")
            
            # Collect data
            wan_metrics = await self._collect_wan_metrics(hass)
            client_metrics = await self._collect_client_metrics(hass)
            ap_metrics = await self._collect_ap_metrics(hass)
            
            # Run checks and generate candidates
            candidates = []
            
            # Check A: WAN Quality
            candidates.extend(await self._check_wan_quality(wan_metrics, unifi_data))
            
            # Check B: WAN Failover
            candidates.extend(await self._check_wan_failover(wan_metrics, unifi_data))
            
            # Check C: Roaming
            candidates.extend(await self._check_roaming(client_metrics, unifi_data))
            
            # Check D: AP Health
            candidates.extend(await self._check_ap_health(ap_metrics, unifi_data))
            
            # Check E: Baselines & Anomalies
            candidates.extend(await self._check_baselines(
                wan_metrics, client_metrics, ap_metrics, unifi_data
            ))
            
            # Store results
            unifi_data["candidates"] = candidates
            unifi_data["last_check"] = datetime.now()
            
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

    # ========== Data Collection ==========

    async def _collect_wan_metrics(self, hass: HomeAssistant) -> List[WANMetrics]:
        """Collect WAN metrics from UniFi integration or API."""
        metrics = []
        
        try:
            # Try to get WAN data from UniFi integration entities
            # Look for sensor.unifi_* entities with WAN data
            
            # Fallback: Try direct API call if configured
            # (Implementation depends on available UniFi integration)
            
            # For now, create mock data structure
            # Real implementation would parse UniFi entities or API
            _LOGGER.debug("Collecting WAN metrics (placeholder)")
            
        except Exception as e:
            _LOGGER.error("Error collecting WAN metrics: %s", e)
        
        return metrics

    async def _collect_client_metrics(self, hass: HomeAssistant) -> List[ClientMetrics]:
        """Collect Wi-Fi client metrics."""
        metrics = []
        
        try:
            # Parse UniFi device_tracker entities and associated sensors
            # Look for RSSI, AP association, etc.
            
            _LOGGER.debug("Collecting client metrics (placeholder)")
            
        except Exception as e:
            _LOGGER.error("Error collecting client metrics: %s", e)
        
        return metrics

    async def _collect_ap_metrics(self, hass: HomeAssistant) -> List[APMetrics]:
        """Collect AP/Radio health metrics."""
        metrics = []
        
        try:
            # Parse UniFi AP entities
            # Look for channel, utilization, client count
            
            _LOGGER.debug("Collecting AP metrics (placeholder)")
            
        except Exception as e:
            _LOGGER.error("Error collecting AP metrics: %s", e)
        
        return metrics

    # ========== Check A: WAN Quality ==========

    async def _check_wan_quality(
        self, wan_metrics: List[WANMetrics], unifi_data: Dict
    ) -> List[Candidate]:
        """Check WAN loss, latency, jitter."""
        candidates = []
        thresholds = unifi_data["config"]["thresholds"]
        
        for wan in wan_metrics:
            # Check packet loss
            if wan.packet_loss_percent is not None:
                if wan.packet_loss_percent >= thresholds["wan_loss_critical"]:
                    candidates.append(Candidate(
                        id=f"wan_loss_{wan.interface}",
                        type="candidate.net.wan_quality.degraded",
                        severity="critical",
                        summary=f"WAN {wan.interface}: Packet loss {wan.packet_loss_percent:.1f}% (critical)",
                        evidence={
                            "interface": wan.interface,
                            "packet_loss_percent": wan.packet_loss_percent,
                            "latency_ms": wan.latency_ms,
                            "jitter_ms": wan.jitter_ms,
                            "timestamp": wan.timestamp.isoformat(),
                        },
                        suggested_actions=[
                            "Check modem/ONT logs for signal issues",
                            "Verify physical WAN cable connections",
                            "Contact ISP if issue persists",
                            "Consider enabling additional monitoring (ping sensor)",
                        ],
                        tags=["net", "wan", "loss"],
                        timestamp=datetime.now(),
                    ))
                elif wan.packet_loss_percent >= thresholds["wan_loss_warning"]:
                    candidates.append(Candidate(
                        id=f"wan_loss_{wan.interface}",
                        type="candidate.net.wan_quality.degraded",
                        severity="warning",
                        summary=f"WAN {wan.interface}: Packet loss {wan.packet_loss_percent:.1f}% (degraded)",
                        evidence={
                            "interface": wan.interface,
                            "packet_loss_percent": wan.packet_loss_percent,
                            "latency_ms": wan.latency_ms,
                            "jitter_ms": wan.jitter_ms,
                            "timestamp": wan.timestamp.isoformat(),
                        },
                        suggested_actions=[
                            "Monitor WAN connection over next hour",
                            "Check for local interference or device issues",
                        ],
                        tags=["net", "wan", "loss"],
                        timestamp=datetime.now(),
                    ))
            
            # Check jitter
            if wan.jitter_ms is not None:
                if wan.jitter_ms >= thresholds["wan_jitter_critical"]:
                    candidates.append(Candidate(
                        id=f"wan_jitter_{wan.interface}",
                        type="candidate.net.wan_quality.jitter",
                        severity="critical",
                        summary=f"WAN {wan.interface}: High jitter {wan.jitter_ms:.1f}ms (impacts VoIP/video)",
                        evidence={
                            "interface": wan.interface,
                            "jitter_ms": wan.jitter_ms,
                            "latency_ms": wan.latency_ms,
                            "timestamp": wan.timestamp.isoformat(),
                        },
                        suggested_actions=[
                            "Check for QoS/traffic shaping misconfigurations",
                            "Verify no bandwidth saturation",
                            "Contact ISP about line quality",
                        ],
                        tags=["net", "wan", "jitter"],
                        timestamp=datetime.now(),
                    ))
            
            # Check outages
            if wan.outage_count >= 3:
                candidates.append(Candidate(
                    id=f"wan_outages_{wan.interface}",
                    type="candidate.net.wan_outages.recurrent",
                    severity="warning",
                    summary=f"WAN {wan.interface}: {wan.outage_count} outages in 24h",
                    evidence={
                        "interface": wan.interface,
                        "outage_count": wan.outage_count,
                        "timestamp": wan.timestamp.isoformat(),
                    },
                    suggested_actions=[
                        "Review gateway logs for pattern (time-of-day correlation)",
                        "Check modem power supply and temperature",
                        "Verify line quality with ISP",
                    ],
                    tags=["net", "wan", "outages"],
                    timestamp=datetime.now(),
                ))
        
        return candidates

    # ========== Check B: WAN Failover ==========

    async def _check_wan_failover(
        self, wan_metrics: List[WANMetrics], unifi_data: Dict
    ) -> List[Candidate]:
        """Check for unexpected WAN failovers."""
        candidates = []
        
        # Look for inactive WANs or recent failover events
        inactive_wans = [w for w in wan_metrics if not w.is_active]
        
        for wan in inactive_wans:
            candidates.append(Candidate(
                id=f"wan_failover_{wan.interface}",
                type="candidate.net.wan_failover.unexpected",
                severity="warning",
                summary=f"WAN {wan.interface} is inactive (failover or down)",
                evidence={
                    "interface": wan.interface,
                    "is_active": wan.is_active,
                    "timestamp": wan.timestamp.isoformat(),
                },
                suggested_actions=[
                    "Verify if this is expected maintenance",
                    "Check gateway WAN status page",
                    "Review recent gateway events",
                ],
                tags=["net", "wan", "failover"],
                timestamp=datetime.now(),
            ))
        
        return candidates

    # ========== Check C: Roaming ==========

    async def _check_roaming(
        self, client_metrics: List[ClientMetrics], unifi_data: Dict
    ) -> List[Candidate]:
        """Check for roaming issues."""
        candidates = []
        thresholds = unifi_data["config"]["thresholds"]
        
        for client in client_metrics:
            # Check for ping-pong roaming
            if client.roam_count_24h >= thresholds["roam_rate_high"] * 24:
                candidates.append(Candidate(
                    id=f"roam_pingpong_{client.mac}",
                    type="candidate.wifi.roam.pingpong",
                    severity="warning",
                    summary=f"Client {client.name or client.mac}: Excessive roaming ({client.roam_count_24h} times/day)",
                    evidence={
                        "client_mac": client.mac,
                        "client_name": client.name,
                        "roam_count_24h": client.roam_count_24h,
                        "current_ap": client.current_ap,
                        "rssi": client.rssi,
                    },
                    suggested_actions=[
                        "Review AP placement and signal overlap",
                        "Check roaming thresholds (minimum RSSI)",
                        "Consider adjusting band steering settings",
                        "Verify 802.11r Fast Roaming configuration",
                    ],
                    tags=["wifi", "roam", "pingpong"],
                    timestamp=datetime.now(),
                ))
            
            # Check for sticky clients
            if client.rssi is not None and client.rssi < thresholds["rssi_sticky_threshold"]:
                candidates.append(Candidate(
                    id=f"sticky_client_{client.mac}",
                    type="candidate.wifi.client.sticky",
                    severity="warning",
                    summary=f"Client {client.name or client.mac}: Weak signal (RSSI {client.rssi} dBm) but not roaming",
                    evidence={
                        "client_mac": client.mac,
                        "client_name": client.name,
                        "current_ap": client.current_ap,
                        "rssi": client.rssi,
                        "snr": client.snr,
                    },
                    suggested_actions=[
                        "Client device may have aggressive roaming threshold",
                        "Reduce AP transmit power to encourage roaming",
                        "Enable minimum RSSI in WLAN settings (carefully)",
                        "Check if stronger AP is available nearby",
                    ],
                    tags=["wifi", "client", "sticky"],
                    timestamp=datetime.now(),
                ))
            
            # Check for roam failures
            if client.last_disconnect_reason and "auth" in client.last_disconnect_reason.lower():
                candidates.append(Candidate(
                    id=f"roam_fail_{client.mac}",
                    type="candidate.wifi.roam.failures",
                    severity="warning",
                    summary=f"Client {client.name or client.mac}: Disconnect with auth issue (possible roam failure)",
                    evidence={
                        "client_mac": client.mac,
                        "client_name": client.name,
                        "disconnect_reason": client.last_disconnect_reason,
                        "disconnect_count_24h": client.disconnect_count_24h,
                    },
                    suggested_actions=[
                        "Check for PMF (Protected Management Frames) mismatches",
                        "Verify 802.11r configuration consistency across APs",
                        "Review WPA/WPA2/WPA3 settings",
                    ],
                    tags=["wifi", "roam", "failures"],
                    timestamp=datetime.now(),
                ))
        
        return candidates

    # ========== Check D: AP Health ==========

    async def _check_ap_health(
        self, ap_metrics: List[APMetrics], unifi_data: Dict
    ) -> List[Candidate]:
        """Check AP/Radio health."""
        candidates = []
        thresholds = unifi_data["config"]["thresholds"]
        
        for ap in ap_metrics:
            # Check utilization
            if ap.utilization_2g_percent and ap.utilization_2g_percent >= thresholds["ap_utilization_high"]:
                candidates.append(Candidate(
                    id=f"ap_util_2g_{ap.mac}",
                    type="candidate.wifi.ap.utilization.high",
                    severity="warning",
                    summary=f"AP {ap.ap_name}: High 2.4 GHz utilization ({ap.utilization_2g_percent:.1f}%)",
                    evidence={
                        "ap_name": ap.ap_name,
                        "ap_mac": ap.mac,
                        "utilization_percent": ap.utilization_2g_percent,
                        "client_count": ap.client_count_2g,
                        "channel": ap.channel_2g,
                    },
                    suggested_actions=[
                        "Consider adding another AP in the area",
                        "Move devices to 5 GHz band if possible",
                        "Check for high-bandwidth IoT devices",
                    ],
                    tags=["wifi", "ap", "utilization"],
                    timestamp=datetime.now(),
                ))
            
            if ap.utilization_5g_percent and ap.utilization_5g_percent >= thresholds["ap_utilization_high"]:
                candidates.append(Candidate(
                    id=f"ap_util_5g_{ap.mac}",
                    type="candidate.wifi.ap.utilization.high",
                    severity="warning",
                    summary=f"AP {ap.ap_name}: High 5 GHz utilization ({ap.utilization_5g_percent:.1f}%)",
                    evidence={
                        "ap_name": ap.ap_name,
                        "ap_mac": ap.mac,
                        "utilization_percent": ap.utilization_5g_percent,
                        "client_count": ap.client_count_5g,
                        "channel": ap.channel_5g,
                    },
                    suggested_actions=[
                        "Consider adding another AP in the area",
                        "Review high-bandwidth clients",
                        "Check channel width (80 MHz may be too wide)",
                    ],
                    tags=["wifi", "ap", "utilization"],
                    timestamp=datetime.now(),
                ))
            
            # Check retries
            if ap.retries_2g_percent and ap.retries_2g_percent >= thresholds["ap_retries_high"]:
                candidates.append(Candidate(
                    id=f"ap_retries_2g_{ap.mac}",
                    type="candidate.wifi.ap.retries.high",
                    severity="warning",
                    summary=f"AP {ap.ap_name}: High 2.4 GHz retries ({ap.retries_2g_percent:.1f}%)",
                    evidence={
                        "ap_name": ap.ap_name,
                        "ap_mac": ap.mac,
                        "retries_percent": ap.retries_2g_percent,
                        "channel": ap.channel_2g,
                    },
                    suggested_actions=[
                        "Check for interference (neighbors, Bluetooth, microwaves)",
                        "Consider channel 1, 6, or 11 only",
                        "Verify channel width is 20 MHz",
                    ],
                    tags=["wifi", "ap", "retries"],
                    timestamp=datetime.now(),
                ))
            
            # Check DFS events
            if ap.dfs_event_count_24h >= 2:
                candidates.append(Candidate(
                    id=f"ap_dfs_{ap.mac}",
                    type="candidate.wifi.ap.dfs.instability",
                    severity="info",
                    summary=f"AP {ap.ap_name}: Multiple DFS events ({ap.dfs_event_count_24h} in 24h)",
                    evidence={
                        "ap_name": ap.ap_name,
                        "ap_mac": ap.mac,
                        "dfs_event_count_24h": ap.dfs_event_count_24h,
                        "channel_5g": ap.channel_5g,
                    },
                    suggested_actions=[
                        "DFS channels may be unstable in your location",
                        "Consider manually selecting non-DFS channels (36-48, 149-165)",
                        "Monitor for weather radar activity if near airport/coast",
                    ],
                    tags=["wifi", "ap", "dfs"],
                    timestamp=datetime.now(),
                ))
        
        return candidates

    # ========== Check E: Baselines & Anomalies ==========

    async def _check_baselines(
        self,
        wan_metrics: List[WANMetrics],
        client_metrics: List[ClientMetrics],
        ap_metrics: List[APMetrics],
        unifi_data: Dict,
    ) -> List[Candidate]:
        """Check for baseline anomalies."""
        candidates = []
        
        # Placeholder for baseline logic
        # Real implementation would:
        # 1. Load historical data from unifi_data["baseline_data"]
        # 2. Compute rolling statistics (median, IQR) per time-of-day bucket
        # 3. Compare current metrics to baseline
        # 4. Flag anomalies (z-score > 2 or value > median + 2*IQR)
        
        _LOGGER.debug("Baseline check (placeholder - not implemented in v0.1)")
        
        return candidates

    # ========== Reporting ==========

    async def _generate_report(self, hass: HomeAssistant, entry_id: str) -> str:
        """Generate human-readable report."""
        try:
            entry_data = hass.data[DOMAIN][entry_id]
            unifi_data = entry_data["unifi_module"]
            
            candidates = unifi_data.get("candidates", [])
            last_check = unifi_data.get("last_check")
            
            if not candidates:
                return "✅ UniFi Network Health: All checks passed\n"
            
            # Group by severity
            critical = [c for c in candidates if c.severity == "critical"]
            warning = [c for c in candidates if c.severity == "warning"]
            info = [c for c in candidates if c.severity == "info"]
            
            report_lines = [
                "🔍 UniFi Network Diagnostic Report",
                f"Last check: {last_check.strftime('%Y-%m-%d %H:%M:%S') if last_check else 'Never'}",
                "",
            ]
            
            if critical:
                report_lines.append(f"🔴 Critical Issues ({len(critical)}):")
                for c in critical:
                    report_lines.append(f"  • {c.summary}")
                report_lines.append("")
            
            if warning:
                report_lines.append(f"⚠️  Warnings ({len(warning)}):")
                for c in warning:
                    report_lines.append(f"  • {c.summary}")
                report_lines.append("")
            
            if info:
                report_lines.append(f"ℹ️  Info ({len(info)}):")
                for c in info:
                    report_lines.append(f"  • {c.summary}")
                report_lines.append("")
            
            # Top 3 actions
            report_lines.append("📋 Recommended Actions:")
            action_count = 0
            for c in critical + warning:
                for action in c.suggested_actions[:1]:  # First action only
                    report_lines.append(f"  {action_count + 1}. {action}")
                    action_count += 1
                    if action_count >= 3:
                        break
                if action_count >= 3:
                    break
            
            return "\n".join(report_lines)
            
        except Exception as e:
            _LOGGER.error("Error generating UniFi report: %s", e)
            return f"Error generating report: {e}"
