"""UniFi Context Module v0.2 — Network monitoring context provider.

Connects Core Add-on UniFi Neuron to HA Integration.
Exposes WAN status, clients, roaming events, and traffic baselines.

v0.2 Changes:
- Enhanced Presence integration methods
- Better error handling and status reporting
- Improved data export methods for other modules
- Added AP-based room presence detection

Privacy-first: Only aggregated network data, no packet inspection.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ...const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN
from ..module import ModuleContext

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


class UnifiContextModule:
    """UniFi context provider for other CoPilot modules.

    Fetches network data from Core Add-on and exposes it as entities.
    Provides methods for Presence module to detect client locations.
    """

    name = "unifi_context"

    def __init__(self) -> None:
        self._hass: HomeAssistant | None = None
        self._entry: ConfigEntry | None = None
        self._entry_id: str | None = None
        self._coordinator: "UnifiContextCoordinator | None" = None
        self._ap_to_room_map: Dict[str, str] = {}

    @property
    def coordinator(self) -> "UnifiContextCoordinator | None":
        """Get the UniFi coordinator."""
        return self._coordinator

    @property
    def is_available(self) -> bool:
        """Check if UniFi context is available."""
        return (
            self._coordinator is not None
            and self._coordinator.data is not None
        )

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up UniFi context tracking."""
        self._hass = ctx.hass
        self._entry = ctx.entry
        self._entry_id = ctx.entry.entry_id

        data = {**ctx.entry.data, **ctx.entry.options}

        host = data.get(CONF_HOST)
        port = data.get(CONF_PORT, 8909)
        token = data.get(CONF_TOKEN)

        if not host:
            _LOGGER.warning("UnifiContext: no host configured — module idle")
            return

        # Import here to avoid circular imports
        from ...unifi_context import create_unifi_context

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

        # Build AP to room mapping from HA areas
        await self._build_ap_room_mapping()

        # Set up entities
        if self._coordinator:
            await self._setup_unifi_entities(ctx.hass)

        # Store reference for other modules
        domain_data = ctx.hass.data.setdefault(DOMAIN, {})
        entry_data = domain_data.setdefault(self._entry_id, {})
        entry_data["unifi_context_module"] = self

        _LOGGER.info("UnifiContext v0.2: initialized (host=%s:%s)", host, port)

    async def _build_ap_room_mapping(self) -> None:
        """Build mapping from AP names to room names.

        Uses HA areas to determine which room each AP serves.
        """
        self._ap_to_room_map = {}

        try:
            # Look for area entities that might contain AP info
            area_registry = self._hass.data.get("area_registry")
            if area_registry:
                areas = area_registry.areas
                for area_id, area in areas.items():
                    # Check if any device in this area is an AP
                    # This is a simplified mapping - can be enhanced
                    area_name = area.name.lower()
                    for ap_suffix in ["ap", "access point", "wifi"]:
                        if ap_suffix in area_name:
                            # Try to extract AP name
                            self._ap_to_room_map[area.name] = area.name
                            break
        except Exception as e:
            _LOGGER.debug("Could not build AP room mapping: %s", e)

    async def _setup_unifi_entities(self, hass: HomeAssistant) -> None:
        """Set up UniFi context entities."""
        try:
            from ...unifi_context_entities import async_setup_unifi_entities
            await async_setup_unifi_entities(hass, self._coordinator)
        except Exception as e:
            _LOGGER.warning("Could not set up UniFi entities: %s", e)

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload UniFi context tracking."""
        domain_data = ctx.hass.data.get(DOMAIN, {})
        entry_data = domain_data.get(self._entry_id, {})

        if "unifi_context_module" in entry_data:
            del entry_data["unifi_context_module"]

        self._coordinator = None
        self._hass = None
        self._entry = None
        self._entry_id = None

        _LOGGER.debug("UnifiContext: unloaded")
        return True

    # ========== Snapshot & Data Access ==========

    def get_snapshot(self) -> Optional[Dict[str, Any]]:
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

    # ========== Presence Integration ==========

    def get_clients_for_presence(self) -> List[Dict[str, Any]]:
        """Get client data formatted for Presence module.

        Returns:
            List of client dicts with presence-relevant fields.
        """
        if not self.is_available:
            return []

        snapshot = self._coordinator.data
        clients = []

        for client in snapshot.clients:
            if client.status != "online":
                continue

            # Determine room from AP
            room = self._get_room_for_ap(client.connected_ap)

            clients.append({
                "mac": client.mac,
                "name": client.name,
                "ip": client.ip,
                "device_type": client.device_type,
                "connected_ap": client.connected_ap,
                "room": room,
                "signal_dbm": client.signal_dbm,
                "signal_level": self._get_signal_level(client.signal_dbm),
                "is_online": client.status == "online",
                "last_seen": client.last_seen,
            })

        return clients

    def get_rooms_with_clients(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get clients grouped by room for presence detection.

        Returns:
            Dict mapping room name to list of clients in that room.
        """
        if not self.is_available:
            return {}

        clients_by_room: Dict[str, List[Dict[str, Any]]] = {}

        for client in self.get_clients_for_presence():
            room = client.get("room", "unknown")
            if room not in clients_by_room:
                clients_by_room[room] = []
            clients_by_room[room].append(client)

        return clients_by_room

    def get_clients_in_room(self, room: str) -> List[Dict[str, Any]]:
        """Get all clients in a specific room.

        Args:
            room: Room name to query.

        Returns:
            List of clients in the specified room.
        """
        rooms = self.get_rooms_with_clients()
        return rooms.get(room, [])

    def get_primary_room(self) -> str:
        """Get the room with the most active clients.

        Used for PresenceRoomSensor to determine primary presence location.
        """
        rooms = self.get_rooms_with_clients()

        if not rooms:
            return "none"

        # Find room with most clients
        primary_room = "none"
        max_clients = 0

        for room, clients in rooms.items():
            if room == "unknown":
                continue
            if len(clients) > max_clients:
                max_clients = len(clients)
                primary_room = room

        return primary_room

    def get_roaming_events_recent(self, minutes: int = 30) -> List[Dict[str, Any]]:
        """Get recent roaming events for activity detection.

        Roaming events can indicate movement between rooms/areas.

        Args:
            minutes: Number of minutes to look back.

        Returns:
            List of recent roaming events with room transition info.
        """
        if not self.is_available:
            return []

        snapshot = self._coordinator.data
        events = []

        try:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=minutes)

            for event in snapshot.roaming_events:
                event_time = datetime.fromisoformat(
                    event.timestamp.replace("Z", "+00:00")
                )
                if event_time >= cutoff:
                    # Determine room transitions
                    from_room = self._get_room_for_ap(event.from_ap)
                    to_room = self._get_room_for_ap(event.to_ap)

                    events.append({
                        "client_mac": event.client_mac,
                        "client_name": event.client_name,
                        "from_ap": event.from_ap,
                        "to_ap": event.to_ap,
                        "from_room": from_room,
                        "to_room": to_room,
                        "room_changed": from_room != to_room,
                        "timestamp": event.timestamp,
                        "signal_strength": event.signal_strength,
                    })
        except Exception as e:
            _LOGGER.debug("Error processing roaming events: %s", e)

        return events

    def has_recent_roaming(self, minutes: int = 5) -> bool:
        """Check if there was any recent roaming activity.

        Used for activity level detection.
        """
        return len(self.get_roaming_events_recent(minutes)) > 0

    def get_online_count(self) -> int:
        """Get number of online clients."""
        if not self.is_available:
            return 0
        return len([
            c for c in self._coordinator.data.clients
            if c.status == "online"
        ])

    # ========== Helper Methods ==========

    def _get_room_for_ap(self, ap_name: Optional[str]) -> str:
        """Map AP name to room name.

        Args:
            ap_name: Name of the AP.

        Returns:
            Room name or "unknown" if not mapped.
        """
        if not ap_name:
            return "unknown"

        # Check explicit mapping first
        if ap_name in self._ap_to_room_map:
            return self._ap_to_room_map[ap_name]

        # Try to infer from AP name (common UniFi naming patterns)
        ap_lower = ap_name.lower()

        # Common room indicators in AP names
        room_indicators = ["living", "bed", "bath", "kitchen", "office", "garage",
                          "garden", "basement", " attic", "hall", "dining"]

        for indicator in room_indicators:
            if indicator in ap_lower:
                # Capitalize for display
                return indicator.capitalize()

        # Return AP name as fallback
        return ap_name

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

    # ========== WAN Status ==========

    def get_wan_status(self) -> Optional[Dict[str, Any]]:
        """Get current WAN status for quick access."""
        if not self.is_available:
            return None

        wan = self._coordinator.data.wan
        return {
            "online": wan.online,
            "latency_ms": wan.latency_ms,
            "packet_loss_percent": wan.packet_loss_percent,
            "uptime_seconds": wan.uptime_seconds,
            "ip_address": wan.ip_address,
            "gateway": wan.gateway,
        }

    def is_wan_online(self) -> bool:
        """Quick check if WAN is online."""
        status = self.get_wan_status()
        return status.get("online", False) if status else False
