"""mDNS/Bonjour Discovery for CoPilot Cross-Home Sharing."""

import asyncio
import socket
import json
import hashlib
from datetime import datetime
from typing import Optional, Callable, Dict, List, Any
import struct


class DiscoveryService:
    """Auto-discovery service using mDNS/Bonjour protocol."""

    MDNS_GROUP = "224.0.0.251"
    MDNS_PORT = 5353

    def __init__(self, home_id: str, instance_name: str = "CoPilot"):
        """Initialize discovery service."""
        self.home_id = home_id
        self.instance_name = instance_name
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._peers: Dict[str, Dict[str, Any]] = {}
        self._discovery_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._peer_updated_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._peer_id = self._generate_peer_id()

    def _generate_peer_id(self) -> str:
        """Generate unique peer ID from home_id."""
        return hashlib.sha256(self.home_id.encode()).hexdigest()[:16]

    def _create_socket(self) -> socket.socket:
        """Create and configure mDNS socket."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to all interfaces
        sock.bind(("", self.MDNS_PORT))

        # Join multicast group
        group = socket.inet_aton(self.MDNS_GROUP)
        sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, group + b"\x00\x00\x00\x00"
        )

        # Set TTL for multicast packets
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)

        return sock

    def _encode_service_info(self) -> Dict[str, Any]:
        """Encode service information for discovery."""
        return {
            "home_id": self.home_id,
            "peer_id": self._peer_id,
            "instance_name": self.instance_name,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "0.5.0",
            "capabilities": ["sync", "encryption", "shared_entities"],
        }

    def _encode_dns_packet(self, service_info: Dict[str, Any]) -> bytes:
        """Encode service info as DNS-SD packet."""
        # Basic DNS-SD format for mDNS
        data = b"\x00\x00"  # Transaction ID
        data += b"\x00\x00"  # Flags
        data += b"\x00\x01"  # Question count
        data += b"\x00\x00"  # Answer count
        data += b"\x00\x00"  # Authority count
        data += b"\x00\x00"  # Additional count

        # Service name: _copilot._tcp.local
        service_name = "_copilot._tcp.local"
        for part in service_name.split("."):
            data += bytes([len(part)]) + part.encode()
        data += b"\x00"  # End of name

        # Query type: PTR (16), class: IN (1)
        data += b"\x00\x10\x00\x01"

        return data

    async def start(self) -> None:
        """Start the discovery service."""
        if self._running:
            return

        self._loop = asyncio.get_event_loop()
        self._socket = self._create_socket()
        self._running = True

        # Start listening for incoming queries
        self._loop.create_task(self._listen())

    async def stop(self) -> None:
        """Stop the discovery service."""
        self._running = False
        if self._socket:
            self._socket.close()
            self._socket = None

    async def _listen(self) -> None:
        """Listen for incoming mDNS queries and respond."""
        while self._running:
            try:
                data, addr = await self._loop.sock_recvfrom(self._socket, 512)

                # Parse query and send response
                if self._is_discovery_query(data):
                    service_info = self._encode_service_info()
                    response = self._build_discovery_response(service_info)
                    await self._loop.sock_sendto(self._socket, response, addr)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    print(f"Discovery listen error: {e}")

    def _is_discovery_query(self, data: bytes) -> bool:
        """Check if packet is a service discovery query."""
        if len(data) < 12:
            return False

        # Check for PTR query for _copilot._tcp.local
        try:
            # Look for _copilot in the query
            return b"_copilot" in data
        except Exception:
            return False

    def _build_discovery_response(self, service_info: Dict[str, Any]) -> bytes:
        """Build mDNS response packet."""
        # Simple response format
        data = b"\x00\x00\x84\x00"  # Transaction ID, Flags (response)
        data += b"\x00\x00"  # Question count
        data += b"\x00\x01"  # Answer count
        data += b"\x00\x00"  # Authority count
        data += b"\x00\x00"  # Additional count

        # Answer: _copilot._tcp.local PTR
        data += b"\x0c" + b"\x08" + b"_copilot" + b"\x04" + b"_tcp" + b"\x05" + b"local"
        data += b"\x00"  # End of name

        # PTR record
        data += b"\x00\x10\x00\x01"  # Type: PTR, Class: IN
        data += b"\x00\x00\x0e\xx10"  # TTL: 120s
        data += b"\x00\x12"  # Data length

        # Target: instance name
        instance_name = f"{self.instance_name}.{self._peer_id}._copilot._tcp.local"
        for part in instance_name.split("."):
            data += bytes([len(part)]) + part.encode()
        data += b"\x00"

        # Additional: SRV record
        data += b"\x0c" + b"\x08" + b"_copilot" + b"\x04" + b"_tcp" + b"\x05" + b"local"
        data += b"\x00"  # End of name

        data += b"\x00\x21\x00\x01"  # Type: SRV, Class: IN
        data += b"\x00\x00\x0e\x10"  # TTL: 120s
        data += b"\x00\x0f"  # Data length

        # Priority, Weight, Port, Target
        data += b"\x00\x00\x00\x00"  # Priority, Weight
        data += b"\x1f\x91"  # Port: 8081
        data += (
            b"\x0c"
            + b"\x08"
            + b"_copilot"
            + b"\x04"
            + b"_tcp"
            + b"\x05"
            + b"local"
            + b"\x00"
        )

        return data

    async def publish(self) -> None:
        """Publish our service for discovery."""
        if not self._socket:
            return

        service_info = self._encode_service_info()
        response = self._build_discovery_response(service_info)

        # Send to mDNS multicast group
        addr = (self.MDNS_GROUP, self.MDNS_PORT)

        # Send multiple times for reliability
        for _ in range(3):
            try:
                await self._loop.sock_sendto(self._socket, response, addr)
            except Exception as e:
                print(f"Publish error: {e}")

            await asyncio.sleep(0.1)

    def discover_peers(self, timeout: float = 3.0) -> Dict[str, Dict[str, Any]]:
        """Discover other CoPilot instances on the network."""
        peers = {}

        # In a real implementation, this would:
        # 1. Send a query packet
        # 2. Wait for responses
        # 3. Parse responses and extract peer info

        return peers

    def on_peer_discovered(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for peer discovery events."""
        self._discovery_callbacks.append(callback)

    def on_peer_updated(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for peer update events."""
        self._peer_updated_callbacks.append(callback)

    def _notify_peer_discovered(self, peer_info: Dict[str, Any]) -> None:
        """Notify listeners of discovered peer."""
        self._peers[peer_info["peer_id"]] = peer_info

        for callback in self._discovery_callbacks:
            try:
                callback(peer_info)
            except Exception as e:
                print(f"Discovery callback error: {e}")

    def _notify_peer_updated(self, peer_info: Dict[str, Any]) -> None:
        """Notify listeners of updated peer."""
        self._peers[peer_info["peer_id"]] = peer_info

        for callback in self._peer_updated_callbacks:
            try:
                callback(peer_info)
            except Exception as e:
                print(f"Peer update callback error: {e}")

    def get_peers(self) -> Dict[str, Dict[str, Any]]:
        """Get all discovered peers."""
        return self._peers.copy()

    def get_local_peer_info(self) -> Dict[str, Any]:
        """Get local peer information."""
        return {
            "home_id": self.home_id,
            "peer_id": self._peer_id,
            "instance_name": self.instance_name,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "0.5.0",
            "capabilities": ["sync", "encryption", "shared_entities"],
        }
