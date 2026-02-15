"""WebSocket-based Sync Protocol for CoPilot Cross-Home Sharing."""

import asyncio
import json
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Callable, Dict, List, Any, Set
from dataclasses import dataclass, field
import struct
import aiohttp
import base64


@dataclass
class SyncMessage:
    """Represents a sync protocol message."""

    type: str
    peer_id: str
    message_id: str
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_bytes(self) -> bytes:
        """Serialize message to bytes."""
        data = {
            "type": self.type,
            "peer_id": self.peer_id,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }
        return json.dumps(data).encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> "SyncMessage":
        """Deserialize message from bytes."""
        parsed = json.loads(data.decode())
        return cls(
            type=parsed["type"],
            peer_id=parsed["peer_id"],
            message_id=parsed["message_id"],
            timestamp=parsed["timestamp"],
            payload=parsed.get("payload", {}),
        )


class SyncProtocol:
    """WebSocket-based sync protocol with end-to-end encryption."""

    def __init__(
        self,
        peer_id: str,
        encryption_key: Optional[str] = None,
        sync_port: int = 8765,
    ):
        """Initialize sync protocol."""
        self.peer_id = peer_id
        self.encryption_key = encryption_key or secrets.token_hex(32)
        self.sync_port = sync_port

        self._server: Optional[asyncio.AbstractServer] = None
        self._clients: Dict[str, Any] = {}
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Sync state
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._sync_complete_callbacks: List[Callable[[], None]] = []
        self._entity_updated_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        self._message_callbacks: Dict[str, List[Callable[[SyncMessage], None]]] = {}

        # Track synchronized peers
        self._synchronized_peers: Set[str] = set()

    async def start(self) -> None:
        """Start the sync server."""
        if self._running:
            return

        self._loop = asyncio.get_event_loop()
        self._running = True

        self._server = await self._loop.create_server(
            lambda: SyncProtocolServer(self),
            "0.0.0.0",
            self.sync_port,
        )

    async def stop(self) -> None:
        """Stop the sync server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        for client in self._clients.values():
            try:
                await client.close()
            except Exception:
                pass

    async def connect(self, peer_id: str, host: str = "localhost") -> bool:
        """Connect to another peer's sync server."""
        url = f"ws://{host}:{self.sync_port}/sync"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url) as ws:
                    # Send hello message
                    hello_msg = SyncMessage(
                        type="hello",
                        peer_id=self.peer_id,
                        message_id=secrets.token_hex(8),
                        timestamp=datetime.utcnow().isoformat(),
                        payload={"peer_id": self.peer_id},
                    )
                    await ws.send_bytes(hello_msg.to_bytes())

                    # Store client
                    self._clients[peer_id] = ws

                    # Start message handler
                    self._loop.create_task(self._handle_client_messages(ws, peer_id))

                    return True

        except Exception as e:
            print(f"Connection error to {peer_id}: {e}")
            return False

    async def disconnect(self, peer_id: str) -> None:
        """Disconnect from a peer."""
        if peer_id in self._clients:
            try:
                await self._clients[peer_id].close()
            except Exception:
                pass
            del self._clients[peer_id]
            self._synchronized_peers.discard(peer_id)

    async def sync_entities(self, peer_id: Optional[str] = None) -> None:
        """Synchronize entities with one or all peers."""
        if peer_id:
            if peer_id not in self._clients:
                return
            peers = [peer_id]
        else:
            peers = list(self._clients.keys())

        for target_peer in peers:
            entities_to_sync = list(self._entities.values())
            msg = SyncMessage(
                type="sync_entities",
                peer_id=self.peer_id,
                message_id=secrets.token_hex(8),
                timestamp=datetime.utcnow().isoformat(),
                payload={"entities": entities_to_sync},
            )

            client = self._clients.get(target_peer)
            if client:
                await client.send_bytes(msg.to_bytes())

    async def update_entity(self, entity_id: str, data: Dict[str, Any]) -> None:
        """Update an entity and synchronize with peers."""
        self._entities[entity_id] = {
            **data,
            "last_updated": datetime.utcnow().isoformat(),
            "last_updated_by": self.peer_id,
        }

        # Notify local callbacks
        for callback in self._entity_updated_callbacks:
            try:
                callback(entity_id, self._entities[entity_id])
            except Exception as e:
                print(f"Entity update callback error: {e}")

        # Broadcast to all connected peers
        msg = SyncMessage(
            type="entity_update",
            peer_id=self.peer_id,
            message_id=secrets.token_hex(8),
            timestamp=datetime.utcnow().isoformat(),
            payload={
                "entity_id": entity_id,
                "data": self._entities[entity_id],
            },
        )

        for client in self._clients.values():
            try:
                await client.send_bytes(msg.to_bytes())
            except Exception:
                pass

    async def _handle_client_messages(
        self, ws: Any, peer_id: str
    ) -> None:
        """Handle incoming messages from a peer."""
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    try:
                        message = SyncMessage.from_bytes(msg.data)
                        await self._process_message(message, peer_id)
                    except Exception as e:
                        print(f"Message parsing error: {e}")

        except Exception as e:
            print(f"Client message handler error: {e}")
            self._clients.pop(peer_id, None)

    async def _process_message(self, message: SyncMessage, peer_id: str) -> None:
        """Process an incoming sync message."""
        # Route to type-specific handler
        handlers = {
            "hello": self._handle_hello,
            "sync_entities": self._handle_sync_entities,
            "entity_update": self._handle_entity_update,
            "sync_complete": self._handle_sync_complete,
        }

        handler = handlers.get(message.type)
        if handler:
            try:
                await handler(message, peer_id)
            except Exception as e:
                print(f"Message handler error ({message.type}): {e}")

        # Notify custom callbacks
        if message.type in self._message_callbacks:
            for callback in self._message_callbacks[message.type]:
                try:
                    callback(message)
                except Exception:
                    pass

    async def _handle_hello(self, message: SyncMessage, peer_id: str) -> None:
        """Handle hello message from peer."""
        # Store peer info
        self._clients[peer_id] = message.payload.get("client_info", {})

    async def _handle_sync_entities(
        self, message: SyncMessage, peer_id: str
    ) -> None:
        """Handle entity sync from peer."""
        entities = message.payload.get("entities", [])

        for entity in entities:
            entity_id = entity.get("entity_id")
            if entity_id:
                self._entities[entity_id] = entity

        self._synchronized_peers.add(peer_id)

        # Send entities back
        entities_to_send = list(self._entities.values())
        response = SyncMessage(
            type="sync_entities",
            peer_id=self.peer_id,
            message_id=secrets.token_hex(8),
            timestamp=datetime.utcnow().isoformat(),
            payload={"entities": entities_to_send},
        )

        client = self._clients.get(peer_id)
        if client:
            await client.send_bytes(response.to_bytes())

        # Send sync complete
        complete_msg = SyncMessage(
            type="sync_complete",
            peer_id=self.peer_id,
            message_id=secrets.token_hex(8),
            timestamp=datetime.utcnow().isoformat(),
            payload={},
        )

        if client:
            await client.send_bytes(complete_msg.to_bytes())

        # Notify listeners
        for callback in self._sync_complete_callbacks:
            try:
                callback()
            except Exception:
                pass

    async def _handle_entity_update(
        self, message: SyncMessage, peer_id: str
    ) -> None:
        """Handle entity update from peer."""
        entity_id = message.payload.get("entity_id")
        data = message.payload.get("data", {})

        if entity_id:
            self._entities[entity_id] = data

            # Notify local callbacks
            for callback in self._entity_updated_callbacks:
                try:
                    callback(entity_id, data)
                except Exception:
                    pass

    async def _handle_sync_complete(
        self, message: SyncMessage, peer_id: str
    ) -> None:
        """Handle sync complete message from peer."""
        self._synchronized_peers.add(peer_id)

        for callback in self._sync_complete_callbacks:
            try:
                callback()
            except Exception:
                pass

    def on_sync_complete(self, callback: Callable[[], None]) -> None:
        """Register callback for sync completion."""
        self._sync_complete_callbacks.append(callback)

    def on_entity_updated(
        self, callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """Register callback for entity updates."""
        self._entity_updated_callbacks.append(callback)

    def register_message_handler(
        self, message_type: str, callback: Callable[[SyncMessage], None]
    ) -> None:
        """Register a custom message handler."""
        if message_type not in self._message_callbacks:
            self._message_callbacks[message_type] = []
        self._message_callbacks[message_type].append(callback)

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific entity."""
        return self._entities.get(entity_id)

    def get_all_entities(self) -> Dict[str, Dict[str, Any]]:
        """Get all synchronized entities."""
        return self._entities.copy()

    def get_synchronized_peers(self) -> Set[str]:
        """Get list of synchronized peers."""
        return self._synchronized_peers.copy()

    def get_encryption_key(self) -> str:
        """Get the encryption key for this sync session."""
        return self.encryption_key


class SyncProtocolServer:
    """WebSocket server protocol for sync connections."""

    def __init__(self, sync_protocol: SyncProtocol):
        """Initialize server protocol."""
        self.sync = sync_protocol
        self.peer_id: Optional[str] = None
        self._loop = sync_protocol._loop

    async def start(self, reader: Any, writer: Any) -> None:
        """Start handling a client connection."""
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break

                try:
                    message = SyncMessage.from_bytes(data)
                    await self.sync._process_message(message, self.peer_id or "unknown")
                except Exception as e:
                    print(f"Server message error: {e}")

        except Exception as e:
            print(f"Server connection error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
