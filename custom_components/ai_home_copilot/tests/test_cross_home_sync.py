"""Tests for Cross-Home Sync module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, Mock


class TestCrossHomeClient:
    """Test cross-home sharing client."""
    
    def test_initialization(self):
        """Test CrossHomeClient initialization."""
        from custom_components.ai_home_copilot.cross_home_sync import CrossHomeClient
        
        hass = MagicMock()
        hass.data = {}
        
        client = CrossHomeClient(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
            api_base="http://localhost:8123",
            api_token="test_token",
        )
        
        assert client.home_id == "home_test"
        assert client.home_name == "Test Home"
        assert client.shared_entities == {}
        assert client.peers == {}
        assert client._session is None
        
    @pytest.mark.asyncio
    async def test_async_initialize(self):
        """Test async initialization."""
        from custom_components.ai_home_copilot.cross_home_sync import CrossHomeClient
        
        hass = MagicMock()
        hass.data = {}
        hass.bus = MagicMock()
        hass.bus.async_listen = Mock()
        
        client = CrossHomeClient(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
            api_base="http://localhost:8123",
        )
        
        # Mock the API calls
        with patch.object(client, '_load_shared_entities', new_callable=AsyncMock):
            await client.async_initialize()
            
            assert client._session is not None
            assert client._is_initialized is True
            hass.bus.async_listen.assert_called_once()
            
            # Cleanup
            await client.async_shutdown()
                
    @pytest.mark.asyncio
    async def test_discover_peers(self):
        """Test peer discovery."""
        from custom_components.ai_home_copilot.cross_home_sync import CrossHomeClient
        
        hass = MagicMock()
        hass.data = {}
        hass.bus = MagicMock()
        hass.bus.async_listen = Mock()
        
        client = CrossHomeClient(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
        )
        
        # Mock the _api_get method directly
        with patch.object(client, '_load_shared_entities', new_callable=AsyncMock):
            with patch.object(client, '_api_get', new_callable=AsyncMock) as mock_api_get:
                mock_api_get.return_value = {
                    "peers": {
                        "home_a": {"name": "Home A", "url": "http://192.168.1.100:8123"},
                        "home_b": {"name": "Home B", "url": "http://192.168.1.101:8123"},
                    }
                }
                
                await client.async_initialize()
                
                peers = await client.async_discover_peers()
                
                assert len(peers) == 2
                assert "home_a" in peers
                assert "home_b" in peers
                
                await client.async_shutdown()
            
    @pytest.mark.asyncio
    async def test_share_entity(self):
        """Test sharing an entity."""
        from custom_components.ai_home_copilot.cross_home_sync import CrossHomeClient
        
        hass = MagicMock()
        hass.data = {}
        hass.bus = MagicMock()
        hass.bus.async_listen = Mock()
        
        client = CrossHomeClient(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
        )
        
        # Mock the _api_post method directly
        with patch.object(client, '_load_shared_entities', new_callable=AsyncMock):
            with patch.object(client, '_api_post', new_callable=AsyncMock) as mock_api_post:
                mock_api_post.return_value = {"success": True}
                
                await client.async_initialize()
                
                result = await client.async_share_entity(
                    entity_id="light.living_room",
                    target_home_id="home_a",
                    permissions="read",
                )
                
                assert result is True
                assert "light.living_room" in client.shared_entities
                assert "home_a" in client.shared_entities["light.living_room"].shared_with
                
                await client.async_shutdown()
            
    @pytest.mark.asyncio
    async def test_unshare_entity(self):
        """Test unsharing an entity."""
        from custom_components.ai_home_copilot.cross_home_sync import (
            CrossHomeClient,
            SharedEntity,
        )
        
        hass = MagicMock()
        hass.data = {}
        hass.bus = MagicMock()
        hass.bus.async_listen = Mock()
        
        client = CrossHomeClient(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
        )
        
        # Pre-populate shared entity
        client.shared_entities["light.living_room"] = SharedEntity(
            entity_id="light.living_room",
            shared_with={"home_a", "home_b"},
            shared_by="home_test",
            permissions="read",
            last_sync=0,
            sync_status="synced",
        )
        
        # Mock the _api_post method directly
        with patch.object(client, '_load_shared_entities', new_callable=AsyncMock):
            with patch.object(client, '_api_post', new_callable=AsyncMock) as mock_api_post:
                mock_api_post.return_value = {"success": True}
                
                await client.async_initialize()
                
                result = await client.async_unshare_entity(
                    entity_id="light.living_room",
                    target_home_id="home_a",
                )
                
                assert result is True
                assert "home_a" not in client.shared_entities["light.living_room"].shared_with
                assert "home_b" in client.shared_entities["light.living_room"].shared_with
                
                await client.async_shutdown()
            
    @pytest.mark.asyncio
    async def test_get_remote_entities(self):
        """Test getting remote entities."""
        from custom_components.ai_home_copilot.cross_home_sync import CrossHomeClient
        
        hass = MagicMock()
        hass.data = {}
        hass.bus = MagicMock()
        hass.bus.async_listen = Mock()
        
        client = CrossHomeClient(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
        )
        
        # Mock the _api_get method directly
        with patch.object(client, '_load_shared_entities', new_callable=AsyncMock):
            with patch.object(client, '_api_get', new_callable=AsyncMock) as mock_api_get:
                mock_api_get.return_value = {
                    "entities": [
                        {"entity_id": "light.remote_light", "state": "on"},
                        {"entity_id": "sensor.remote_temp", "state": "22"},
                    ]
                }
                
                await client.async_initialize()
                
                entities = await client.async_get_remote_entities("home_a")
                
                assert len(entities) == 2
                assert entities[0]["entity_id"] == "light.remote_light"
                
                await client.async_shutdown()
            
    @pytest.mark.asyncio
    async def test_resolve_conflict(self):
        """Test conflict resolution."""
        from custom_components.ai_home_copilot.cross_home_sync import (
            CrossHomeClient,
            SharedEntity,
        )
        
        hass = MagicMock()
        hass.data = {}
        hass.bus = MagicMock()
        hass.bus.async_listen = Mock()
        
        client = CrossHomeClient(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
        )
        
        # Pre-populate conflict
        client.shared_entities["light.conflict"] = SharedEntity(
            entity_id="light.conflict",
            shared_with={"home_a"},
            shared_by="home_test",
            permissions="read_write",
            last_sync=0,
            sync_status="conflict",
        )
        
        # Mock the _api_post method directly
        with patch.object(client, '_load_shared_entities', new_callable=AsyncMock):
            with patch.object(client, '_api_post', new_callable=AsyncMock) as mock_api_post:
                mock_api_post.return_value = {"success": True}
                
                await client.async_initialize()
                
                result = await client.async_resolve_conflict(
                    entity_id="light.conflict",
                    resolution="local_wins",
                )
                
                assert result is True
                assert client.shared_entities["light.conflict"].sync_status == "synced"
                
                await client.async_shutdown()
            
    def test_get_stats(self):
        """Test statistics retrieval."""
        from custom_components.ai_home_copilot.cross_home_sync import (
            CrossHomeClient,
            SharedEntity,
        )
        
        hass = MagicMock()
        
        client = CrossHomeClient(
            hass=hass,
            home_id="home_test",
            home_name="Test Home",
        )
        
        # Add test entities
        client.shared_entities = {
            "light.synced": SharedEntity(
                entity_id="light.synced",
                shared_with={"home_a"},
                shared_by="home_test",
                permissions="read",
                last_sync=100,
                sync_status="synced",
            ),
            "light.pending": SharedEntity(
                entity_id="light.pending",
                shared_with={"home_a"},
                shared_by="home_test",
                permissions="read",
                last_sync=0,
                sync_status="pending",
            ),
            "light.conflict": SharedEntity(
                entity_id="light.conflict",
                shared_with={"home_a"},
                shared_by="home_test",
                permissions="read",
                last_sync=0,
                sync_status="conflict",
            ),
        }
        
        client.peers = {"home_a": {}, "home_b": {}}
        
        stats = client.get_stats()
        
        assert stats["home_id"] == "home_test"
        assert stats["peers_discovered"] == 2
        assert stats["entities_shared"] == 3
        assert stats["sync_status"]["synced"] == 1
        assert stats["sync_status"]["pending"] == 1
        assert stats["sync_status"]["conflict"] == 1


class TestSharedEntity:
    """Test SharedEntity dataclass."""
    
    def test_shared_entity_creation(self):
        """Test creating a SharedEntity."""
        from custom_components.ai_home_copilot.cross_home_sync import SharedEntity
        
        entity = SharedEntity(
            entity_id="light.test",
            shared_with={"home_a", "home_b"},
            shared_by="home_test",
            permissions="read_write",
            last_sync=123456,
            sync_status="synced",
        )
        
        assert entity.entity_id == "light.test"
        assert entity.shared_with == {"home_a", "home_b"}
        assert entity.permissions == "read_write"
        assert entity.sync_status == "synced"