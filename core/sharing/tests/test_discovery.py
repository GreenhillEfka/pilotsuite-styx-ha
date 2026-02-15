"""Tests for mDNS Discovery service."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import socket

from core.sharing.discovery import DiscoveryService


@pytest.fixture
def event_loop():
    """Create an event loop for the tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def discovery_service():
    """Create a discovery service instance."""
    return DiscoveryService(home_id="test-home-123", instance_name="TestCoPilot")


class TestDiscoveryService:
    """Test cases for DiscoveryService."""

    @pytest.mark.asyncio
    async def test_init(self, discovery_service):
        """Test initialization of discovery service."""
        assert discovery_service.home_id == "test-home-123"
        assert discovery_service.instance_name == "TestCoPilot"
        assert discovery_service._running is False
        assert discovery_service._socket is None

    @pytest.mark.asyncio
    async def test_generate_peer_id(self, discovery_service):
        """Test peer ID generation."""
        peer_id = discovery_service._generate_peer_id()
        assert len(peer_id) == 16
        assert isinstance(peer_id, str)

    @pytest.mark.asyncio
    async def test_encode_service_info(self, discovery_service):
        """Test service info encoding."""
        info = discovery_service._encode_service_info()
        
        assert "home_id" in info
        assert "peer_id" in info
        assert "instance_name" in info
        assert "version" in info
        assert "capabilities" in info

    @pytest.mark.asyncio
    async def test_start_stop(self, discovery_service):
        """Test starting and stopping discovery service."""
        # Mock the socket creation
        with patch.object(discovery_service, '_create_socket') as mock_socket:
            mock_socket.return_value = MagicMock()
            await discovery_service.start()
            
            assert discovery_service._running is True
            assert discovery_service._socket is not None
            
            await discovery_service.stop()
            assert discovery_service._running is False

    @pytest.mark.asyncio
    async def test_publish(self, discovery_service):
        """Test publishing service."""
        # Mock socket and loop
        mock_socket = MagicMock()
        mock_socket.sendto = AsyncMock()
        
        with patch.object(discovery_service, '_create_socket', return_value=mock_socket):
            await discovery_service.start()
            await discovery_service.publish()
            
            # Should have sent to multicast group
            assert mock_socket.sendto.called

    @pytest.mark.asyncio
    async def test_discover_peers(self, discovery_service):
        """Test peer discovery."""
        peers = discovery_service.discover_peers(timeout=0.1)
        assert isinstance(peers, dict)

    @pytest.mark.asyncio
    async def test_peer_callbacks(self, discovery_service):
        """Test peer discovery callbacks."""
        callback = AsyncMock()
        discovery_service.on_peer_discovered(callback)
        
        peer_info = {"peer_id": "test-peer", "home_id": "test-home"}
        discovery_service._notify_peer_discovered(peer_info)
        
        # Callback should have been called
        callback.assert_called_once_with(peer_info)

    @pytest.mark.asyncio
    async def test_get_peers(self, discovery_service):
        """Test getting discovered peers."""
        peer_info = {"peer_id": "test-peer", "home_id": "test-home"}
        discovery_service._notify_peer_discovered(peer_info)
        
        peers = discovery_service.get_peers()
        assert "test-peer" in peers

    @pytest.mark.asyncio
    async def test_get_local_peer_info(self, discovery_service):
        """Test getting local peer information."""
        info = discovery_service.get_local_peer_info()
        
        assert "home_id" in info
        assert "peer_id" in info
        assert "version" in info
        assert "capabilities" in info


class TestDiscoveryIntegration:
    """Integration tests for discovery."""

    @pytest.mark.asyncio
    async def test_multi_peer_scenario(self):
        """Test scenario with multiple peers."""
        # Create multiple discovery services
        service1 = DiscoveryService(home_id="home-1", instance_name="Home1")
        service2 = DiscoveryService(home_id="home-2", instance_name="Home2")
        service3 = DiscoveryService(home_id="home-3", instance_name="Home3")

        try:
            # Start all services
            await service1.start()
            await service2.start()
            await service3.start()

            # Verify they're running
            assert service1._running
            assert service2._running
            assert service3._running

        finally:
            # Stop all services
            await service1.stop()
            await service2.stop()
            await service3.stop()
