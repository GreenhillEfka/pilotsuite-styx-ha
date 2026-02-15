"""Tests for Shared Entity Registry."""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime

from core.sharing.registry import SharedRegistry, SharedEntity, get_registry


@pytest.fixture
def registry(tmp_path):
    """Create a registry with temporary storage."""
    storage_path = str(tmp_path / "registry.json")
    return SharedRegistry(storage_path=storage_path)


class TestSharedRegistry:
    """Test cases for SharedRegistry."""

    @pytest.mark.asyncio
    async def test_register_entity(self, registry):
        """Test registering an entity."""
        entity = registry.register("light.living_room", shared=True)
        
        assert entity.entity_id == "light.living_room"
        assert entity.shared is True
        assert entity.domain == "light"

    @pytest.mark.asyncio
    async def test_unregister_entity(self, registry):
        """Test unregistering an entity."""
        registry.register("light.living_room", shared=True)
        registry.unregister("light.living_room")
        
        assert registry.get("light.living_room") is None

    @pytest.mark.asyncio
    async def test_update_entity(self, registry):
        """Test updating an entity."""
        registry.register("light.living_room", shared=True)
        
        updated = registry.update("light.living_room", shared=False, custom_field="value")
        
        assert updated.shared is False
        assert updated.metadata.get("custom_field") == "value"

    @pytest.mark.asyncio
    async def test_get_entity(self, registry):
        """Test getting an entity."""
        registry.register("light.living_room", shared=True)
        
        entity = registry.get("light.living_room")
        assert entity is not None
        assert entity.entity_id == "light.living_room"

    @pytest.mark.asyncio
    async def test_get_all_entities(self, registry):
        """Test getting all entities."""
        registry.register("light.a", shared=True)
        registry.register("light.b", shared=False)
        
        all_entities = registry.get_all()
        assert len(all_entities) == 2

    @pytest.mark.asyncio
    async def test_get_shared_entities(self, registry):
        """Test getting only shared entities."""
        registry.register("light.shared", shared=True)
        registry.register("light.private", shared=False)
        
        shared = registry.get_shared()
        assert len(shared) == 1
        assert "light.shared" in shared

    @pytest.mark.asyncio
    async def test_share_with_home(self, registry):
        """Test sharing entity with another home."""
        registry.register("light.test", shared=True, home_id="home-1")
        registry.share_with("light.test", "home-2")
        
        shared_with = registry.get_shared_with("light.test")
        assert "home-2" in shared_with

    @pytest.mark.asyncio
    async def test_callback_registration(self, registry):
        """Test callback registration."""
        callback = AsyncMock()
        registry.register_callback(on_registered=callback)
        
        registry.register("light.test", shared=True)
        
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_persistence(self, registry, tmp_path):
        """Test registry persistence."""
        # Register an entity
        registry.register("light.test", shared=True)
        
        # Create new registry with same storage
        new_registry = SharedRegistry(storage_path=registry.storage_path)
        new_registry._load()
        
        assert "light.test" in new_registry.get_all()


class TestSharedEntity:
    """Test cases for SharedEntity dataclass."""

    def test_to_dict(self):
        """Test converting to dictionary."""
        entity = SharedEntity(
            entity_id="light.test",
            name="Test Light",
            domain="light",
            shared=True,
        )
        
        data = entity.to_dict()
        assert data["entity_id"] == "light.test"
        assert data["domain"] == "light"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "entity_id": "light.test",
            "name": "Test Light",
            "domain": "light",
            "shared": True,
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        entity = SharedEntity.from_dict(data)
        assert entity.entity_id == "light.test"
        assert entity.domain == "light"


class TestRegistryIntegration:
    """Integration tests for registry."""

    @pytest.mark.asyncio
    async def test_multiple_entities(self, registry):
        """Test managing multiple entities."""
        entities = [
            "light.living_room",
            "light.kitchen",
            "switch.socket",
            "binary_sensor.door",
        ]
        
        for entity_id in entities:
            registry.register(entity_id, shared=True)
        
        assert len(registry.get_all()) == len(entities)

    @pytest.mark.asyncio
    async def test_sharing_scenarios(self, registry):
        """Test various sharing scenarios."""
        # Home 1 registers entity
        registry.register("light.main", shared=True, home_id="home-1")
        
        # Home 1 shares with Home 2
        registry.share_with("light.main", "home-2")
        
        # Verify shared
        shared_with = registry.get_shared_with("light.main")
        assert "home-2" in shared_with
