"""Integration test for Cross-Home Sharing."""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime
from pathlib import Path

from core.sharing.discovery import DiscoveryService
from core.sharing.sync import SyncProtocol
from core.sharing.registry import SharedRegistry
from core.sharing.conflict import ConflictResolver


@pytest.fixture
async def test_home_setup(tmp_path):
    """Set up test environment for cross-home scenario."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    
    config = {
        "home_id": "home-1",
        "instance_name": "TestHome1",
        "sync_port": 8765,
        "storage_path": str(storage_dir / "registry.json"),
        "conflict_path": str(storage_dir / "conflicts.json"),
    }
    
    yield config


class TestCrossHomeScenario:
    """Integration tests for cross-home sharing scenario."""

    @pytest.mark.asyncio
    async def test_full_scenario(self, test_home_setup):
        """Test full cross-home sharing scenario."""
        config = test_home_setup
        
        # Step 1: Setup Home 1
        registry1 = SharedRegistry(storage_path=config["storage_path"])
        discovery1 = DiscoveryService(home_id=config["home_id"], instance_name=config["instance_name"])
        sync1 = SyncProtocol(peer_id=config["home_id"], sync_port=config["sync_port"])
        conflict1 = ConflictResolver(home_id=config["home_id"])
        
        # Step 2: Register entities
        registry1.register("light.living_room", shared=True, home_id=config["home_id"])
        registry1.register("light.kitchen", shared=True, home_id=config["home_id"])
        
        # Step 3: Test discovery
        peer_info = discovery1.get_local_peer_info()
        assert "home_id" in peer_info
        assert peer_info["home_id"] == config["home_id"]
        
        # Step 4: Test entity update triggers
        update_called = False
        def on_update(entity_id, data):
            nonlocal update_called
            update_called = True
        
        registry1.register_callback(on_updated=on_update)
        
        # Step 5: Test conflict resolution
        local = {"state": "on", "last_updated": "2024-01-01T10:00:00"}
        remote = {"state": "off", "last_updated": "2024-01-01T11:00:00"}
        
        resolved = conflict1.resolve("light.test", local, remote, "latest-wins")
        assert resolved["state"] == "off"  # Remote is newer
        
        # Cleanup
        await discovery1.stop()

    @pytest.mark.asyncio
    async def test_multiple_homes_simulation(self, tmp_path):
        """Simulate multiple homes sharing entities."""
        storage_dir = tmp_path / "multi-home"
        storage_dir.mkdir()
        
        # Simulate Home 1
        registry1 = SharedRegistry(storage_path=str(storage_dir / "home1_registry.json"))
        registry1.register("light.main", shared=True, home_id="home-1")
        
        # Simulate Home 2
        registry2 = SharedRegistry(storage_path=str(storage_dir / "home2_registry.json"))
        registry2.register("light.main", shared=True, home_id="home-2")
        
        # Both homes should see the same entity
        assert "light.main" in registry1.get_shared()
        assert "light.main" in registry2.get_shared()

    @pytest.mark.asyncio
    async def test_conflict_resolution_strategies(self, tmp_path):
        """Test all conflict resolution strategies."""
        storage_dir = tmp_path / "conflict-test"
        storage_dir.mkdir()
        
        resolver = ConflictResolver(home_id="test-home", storage_path=str(storage_dir / "conflicts.json"))
        
        local = {"state": "on", "brightness": 100, "last_updated": "2024-01-01T10:00:00"}
        remote = {"state": "off", "color": "red", "last_updated": "2024-01-01T11:00:00"}
        
        # Test all strategies
        strategies = ["latest-wins", "merge", "local-wins", "remote-wins"]
        
        for strategy in strategies:
            result = resolver.resolve("light.test", local, remote, strategy)
            assert result is not None
            assert isinstance(result, dict)
            
            # Clean up for next test
            resolver.clear_conflict("light.test")


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_entity_update(self):
        """Test handling of empty entity updates."""
        resolver = ConflictResolver(home_id="test-home")
        
        local = {}
        remote = {"state": "on"}
        
        result = resolver.resolve("light.test", local, remote)
        assert result["state"] == "on"

    @pytest.mark.asyncio
    async def test_missing_timestamp(self):
        """Test handling of missing timestamps."""
        resolver = ConflictResolver(home_id="test-home")
        
        local = {"state": "on"}  # No timestamp
        remote = {"state": "off", "last_updated": "2024-01-01T11:00:00"}
        
        result = resolver.resolve("light.test", local, remote, "latest-wins")
        # Remote has timestamp, should use it (or default to remote)
        assert result is not None

    @pytest.mark.asyncio
    async def test_duplicate_registration(self):
        """Test handling of duplicate entity registration."""
        registry = SharedRegistry()
        
        # First registration
        entity1 = registry.register("light.test", shared=True)
        
        # Second registration (should update, not create duplicate)
        entity2 = registry.register("light.test", shared=False)
        
        assert entity1.entity_id == entity2.entity_id
        assert entity2.shared is False

    @pytest.mark.asyncio
    async def test_unregister_nonexistent(self):
        """Test unregistering a non-existent entity."""
        registry = SharedRegistry()
        
        # Should not raise exception
        registry.unregister("light.nonexistent")
