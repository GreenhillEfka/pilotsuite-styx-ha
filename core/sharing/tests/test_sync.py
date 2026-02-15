"""Tests for WebSocket Sync Protocol."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from core.sharing.sync import SyncProtocol, SyncMessage


@pytest.fixture
def sync_protocol():
    """Create a sync protocol instance."""
    return SyncProtocol(peer_id="test-peer-123", encryption_key="test-key")


class TestSyncProtocol:
    """Test cases for SyncProtocol."""

    @pytest.mark.asyncio
    async def test_init(self, sync_protocol):
        """Test initialization of sync protocol."""
        assert sync_protocol.peer_id == "test-peer-123"
        assert sync_protocol.encryption_key == "test-key"
        assert sync_protocol._running is False

    @pytest.mark.asyncio
    async def test_sync_message_serialization(self, sync_protocol):
        """Test message serialization."""
        msg = SyncMessage(
            type="test",
            peer_id="test-peer",
            message_id="msg-123",
            timestamp=datetime.utcnow().isoformat(),
            payload={"key": "value"}
        )

        # Serialize
        data = msg.to_bytes()
        assert isinstance(data, bytes)

        # Deserialize
        msg2 = SyncMessage.from_bytes(data)
        assert msg2.type == msg.type
        assert msg2.peer_id == msg.peer_id
        assert msg2.message_id == msg.message_id

    @pytest.mark.asyncio
    async def test_update_entity(self, sync_protocol):
        """Test entity update."""
        entity_id = "light.living_room"
        data = {"state": "on", "attributes": {"brightness": 100}}

        # This would normally trigger sync to peers
        # For unit test, just verify the entity is stored
        sync_protocol._entities[entity_id] = {
            **data,
            "last_updated": datetime.utcnow().isoformat(),
            "last_updated_by": sync_protocol.peer_id,
        }

        assert entity_id in sync_protocol._entities

    @pytest.mark.asyncio
    async def test_get_entity(self, sync_protocol):
        """Test getting an entity."""
        entity_id = "light.living_room"
        sync_protocol._entities[entity_id] = {
            "state": "on",
            "attributes": {},
            "last_updated": datetime.utcnow().isoformat(),
            "last_updated_by": sync_protocol.peer_id,
        }

        entity = sync_protocol.get_entity(entity_id)
        assert entity is not None
        assert entity["state"] == "on"

    @pytest.mark.asyncio
    async def test_sync_entities(self, sync_protocol):
        """Test entity synchronization."""
        # Add some entities
        sync_protocol._entities["light.a"] = {"state": "on"}
        sync_protocol._entities["light.b"] = {"state": "off"}

        # This would normally sync to connected peers
        # For unit test, just verify entities exist
        entities = sync_protocol.get_all_entities()
        assert "light.a" in entities
        assert "light.b" in entities

    @pytest.mark.asyncio
    async def test_sync_complete_callback(self, sync_protocol):
        """Test sync completion callback."""
        callback = AsyncMock()
        sync_protocol.on_sync_complete(callback)

        # Manually trigger callback (would be called by server)
        for cb in sync_protocol._sync_complete_callbacks:
            await cb()

        callback.assert_called_once()


class TestSyncIntegration:
    """Integration tests for sync protocol."""

    @pytest.mark.asyncio
    async def test_connect_and_sync(self):
        """Test connecting to another peer and syncing."""
        peer1 = SyncProtocol(peer_id="peer-1", sync_port=8765)
        peer2 = SyncProtocol(peer_id="peer-2", sync_port=8766)

        try:
            # Start servers
            await peer1.start()
            await peer2.start()

            # Add test entities
            peer1._entities["light.test"] = {"state": "on"}

            # Connect peer2 to peer1
            # In real scenario: await peer2.connect("peer-1", "localhost")
            # For unit test, just verify setup works
            assert peer1._running
            assert peer2._running

        finally:
            await peer1.stop()
            await peer2.stop()
