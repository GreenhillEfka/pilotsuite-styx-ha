"""Tests for Conflict Resolution."""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime

from core.sharing.conflict import ConflictResolver, Conflict


@pytest.fixture
def resolver(tmp_path):
    """Create a conflict resolver with temporary storage."""
    storage_path = str(tmp_path / "conflicts.json")
    return ConflictResolver(home_id="test-home", storage_path=storage_path)


class TestConflictResolver:
    """Test cases for ConflictResolver."""

    @pytest.mark.asyncio
    async def test_init(self, resolver):
        """Test initialization."""
        assert resolver.home_id == "test-home"
        assert len(resolver._active_conflicts) == 0

    @pytest.mark.asyncio
    async def test_latest_wins_strategy(self, resolver):
        """Test latest-wins resolution strategy."""
        local = {
            "state": "on",
            "last_updated": "2024-01-01T10:00:00",
        }
        remote = {
            "state": "off",
            "last_updated": "2024-01-01T11:00:00",
        }
        
        result = resolver.resolve("light.test", local, remote, "latest-wins")
        
        # Remote is newer, should use remote
        assert result["state"] == "off"

    @pytest.mark.asyncio
    async def test_merge_strategy(self, resolver):
        """Test merge resolution strategy."""
        local = {
            "state": "on",
            "brightness": 100,
            "last_updated": "2024-01-01T10:00:00",
        }
        remote = {
            "state": "off",
            "color": "red",
            "last_updated": "2024-01-01T09:00:00",
        }
        
        result = resolver.resolve("light.test", local, remote, "merge")
        
        # Should merge values, using local brightness and remote state
        assert "brightness" in result
        assert "color" in result

    @pytest.mark.asyncio
    async def test_local_wins_strategy(self, resolver):
        """Test local-wins resolution strategy."""
        local = {"state": "on"}
        remote = {"state": "off"}
        
        result = resolver.resolve("light.test", local, remote, "local-wins")
        
        assert result["state"] == "on"

    @pytest.mark.asyncio
    async def test_remote_wins_strategy(self, resolver):
        """Test remote-wins resolution strategy."""
        local = {"state": "on"}
        remote = {"state": "off"}
        
        result = resolver.resolve("light.test", local, remote, "remote-wins")
        
        assert result["state"] == "off"

    @pytest.mark.asyncio
    async def test_custom_strategy(self, resolver):
        """Test custom resolution strategy."""
        def custom_strategy(local, remote):
            return {**local, **remote, "custom": True}
        
        resolver.register_strategy("custom", custom_strategy)
        
        local = {"state": "on"}
        remote = {"state": "off"}
        
        result = resolver.resolve("light.test", local, remote, "custom")
        
        assert result["custom"] is True

    @pytest.mark.asyncio
    async def test_callback_registration(self, resolver):
        """Test conflict detection callback."""
        callback = AsyncMock()
        resolver.register_conflict_callback(callback)
        
        local = {"state": "on"}
        remote = {"state": "off"}
        
        resolver.resolve("light.test", local, remote)
        
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_identical_versions(self, resolver):
        """Test handling of identical versions."""
        local = {"state": "on", "last_updated": "2024-01-01T10:00:00"}
        remote = {"state": "on", "last_updated": "2024-01-01T10:00:00"}
        
        # Should not create conflict for identical versions
        result = resolver.resolve("light.test", local, remote)
        
        assert result["state"] == "on"

    @pytest.mark.asyncio
    async def test_persistence(self, resolver, tmp_path):
        """Test conflict persistence."""
        local = {"state": "on"}
        remote = {"state": "off"}
        
        resolver.resolve("light.test", local, remote)
        
        # Create new resolver with same storage
        new_resolver = ConflictResolver(home_id="test-home", storage_path=resolver.storage_path)
        new_resolver._load()
        
        assert "light.test" in new_resolver._active_conflicts


class TestConflict:
    """Test cases for Conflict dataclass."""

    def test_conflict_record(self):
        """Test conflict record creation."""
        conflict = Conflict(
            entity_id="light.test",
            local_version={"state": "on"},
            remote_version={"state": "off"},
            resolution="latest-wins",
            resolved_by="test-home",
        )
        
        assert conflict.entity_id == "light.test"
        assert conflict.resolution == "latest-wins"
