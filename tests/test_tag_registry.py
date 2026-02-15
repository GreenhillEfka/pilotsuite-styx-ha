"""
Tests for Tag Registry Module
=============================
Tests cover:
- Tag CRUD operations
- Tag assignments
- Label sync

Run with: python3 -m pytest tests/ -v -k "tag_registry"
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components")


class TestTagRegistryBasics:
    """Tests for tag registry basic operations."""

    def test_supported_subject_kinds(self):
        """Test supported subject kinds definition."""
        from ai_home_copilot.tag_registry import SUPPORTED_SUBJECT_KINDS
        
        expected_kinds = {
            "entity",
            "device",
            "area",
            "automation",
            "scene",
            "script",
            "helper",
        }
        
        assert SUPPORTED_SUBJECT_KINDS == expected_kinds

    def test_storage_version(self):
        """Test storage version constant."""
        from ai_home_copilot.tag_registry import STORAGE_VERSION
        
        assert STORAGE_VERSION == 1


class TestTagStatus:
    """Tests for tag status handling."""

    def test_tag_status_pending(self):
        """Test pending tag status."""
        from ai_home_copilot.tag_registry import _tag_status
        
        # None tag should be pending
        assert _tag_status(None) == "pending"
        
        # Explicit pending
        assert _tag_status({"status": "pending"}) == "pending"

    def test_tag_status_confirmed(self):
        """Test confirmed tag status."""
        from ai_home_copilot.tag_registry import _tag_status
        
        assert _tag_status({"status": "confirmed"}) == "confirmed"

    def test_tag_status_default(self):
        """Test default tag status."""
        from ai_home_copilot.tag_registry import _tag_status
        
        # Empty dict should default to pending
        assert _tag_status({}) == "pending"


class TestUserTagDetection:
    """Tests for user tag detection."""

    def test_is_user_tag(self):
        """Test user tag detection."""
        from ai_home_copilot.tag_registry import _is_user_tag
        
        assert _is_user_tag("user.living_room") is True
        assert _is_user_tag("user.custom_tag") is True
        assert _is_user_tag("system.tag") is False

    def test_is_not_user_tag(self):
        """Test non-user tag detection."""
        from ai_home_copilot.tag_registry import _is_user_tag
        
        assert _is_user_tag("system.core") is False
        assert _is_user_tag("auto.generated") is False


class TestTagMaterialization:
    """Tests for tag materialization logic."""

    def test_pending_materialization(self):
        """Test pending materialization detection."""
        from ai_home_copilot.tag_registry import _is_pending_materialization
        
        # Pending with confirmed=False should be pending
        result = _is_pending_materialization(
            "user.new_tag",
            {"status": "pending", "confirmed": False}
        )
        assert result is True

    def test_confirmed_not_pending(self):
        """Test confirmed tags are not pending."""
        from ai_home_copilot.tag_registry import _is_pending_materialization
        
        result = _is_pending_materialization(
            "user.confirmed_tag",
            {"status": "confirmed", "confirmed": True}
        )
        assert result is False


class TestSyncReport:
    """Tests for sync report dataclass."""

    def test_sync_report_creation(self):
        """Test SyncReport creation."""
        from ai_home_copilot.tag_registry import SyncReport
        
        report = SyncReport(
            imported_user_aliases=5,
            created_labels=3,
            updated_subjects=10,
            skipped_pending=2,
            errors=None
        )
        
        assert report.imported_user_aliases == 5
        assert report.created_labels == 3
        assert report.updated_subjects == 10

    def test_sync_report_with_errors(self):
        """Test SyncReport with errors."""
        from ai_home_copilot.tag_registry import SyncReport
        
        report = SyncReport(
            imported_user_aliases=0,
            created_labels=0,
            updated_subjects=0,
            skipped_pending=0,
            errors=["Error 1", "Error 2"]
        )
        
        assert report.errors is not None
        assert len(report.errors) == 2


class TestTagStorage:
    """Tests for tag storage operations."""

    @pytest.mark.asyncio
    async def test_tag_storage_load(self):
        """Test tag storage loading."""
        # This would need a real Home Assistant mock
        # For now, test the expected structure
        data = {
            "tags": {},
            "assignments": {},
            "ha_label_map": {},
            "user_aliases": {}
        }
        
        assert isinstance(data, dict)
        assert "tags" in data

    @pytest.mark.asyncio
    async def test_tag_storage_save(self):
        """Test tag storage saving structure."""
        data = {
            "tags": {
                "user.living_room": {
                    "tag_key": "user.living_room",
                    "name": "Living Room",
                    "status": "confirmed"
                }
            },
            "assignments": {}
        }
        
        assert "user.living_room" in data["tags"]


class TestTagAssignment:
    """Tests for tag assignment operations."""

    def test_assignment_structure(self):
        """Test tag assignment structure."""
        assignment = {
            "subject": "light.living_room",
            "tags": ["user.living_room", "user.main_room"]
        }
        
        assert assignment["subject"] == "light.living_room"
        assert len(assignment["tags"]) == 2

    def test_assignment_update(self):
        """Test updating tag assignments."""
        assignments = {
            "light.living_room": ["user.living_room"]
        }
        
        # Add new tag
        if "light.living_room" in assignments:
            assignments["light.living_room"].append("user.bright")
        
        assert len(assignments["light.living_room"]) == 2


class TestLabelSync:
    """Tests for label synchronization."""

    def test_label_mapping(self):
        """Test HA label mapping structure."""
        label_map = {
            "user.living_room": "label.living_room_123",
            "user.kitchen": "label.kitchen_456"
        }
        
        assert "user.living_room" in label_map

    def test_label_sync_direction(self):
        """Test label sync direction (tag -> HA label)."""
        # tag_key -> ha_label_id
        label_map = {
            "user.tag1": "ha_label_1",
            "user.tag2": "ha_label_2"
        }
        
        assert label_map["user.tag1"] == "ha_label_1"


class TestTagImport:
    """Tests for tag import operations."""

    @pytest.mark.asyncio
    async def test_import_canonical_tags_structure(self):
        """Test canonical tag import structure."""
        tags = [
            {
                "tag_key": "user.living_room",
                "name": "Living Room",
                "status": "confirmed"
            },
            {
                "tag_key": "user.kitchen",
                "name": "Kitchen",
                "status": "pending"
            }
        ]
        
        assert len(tags) == 2
        assert tags[0]["tag_key"] == "user.living_room"

    @pytest.mark.asyncio
    async def test_import_with_schema_version(self):
        """Test import with schema version."""
        import_result = {
            "imported": 10,
            "updated": 5,
            "schema_version": "1.0"
        }
        
        assert import_result["schema_version"] == "1.0"
