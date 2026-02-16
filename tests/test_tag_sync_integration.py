"""Integration tests for tag-sync roundtrip: Core ↔ HA labels."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from custom_components.ai_home_copilot.tag_sync import (
    async_pull_tag_system_snapshot,
)
from custom_components.ai_home_copilot.tag_registry import (
    async_import_canonical_tags,
    async_replace_assignments_snapshot,
    async_sync_labels_now,
    SUPPORTED_SUBJECT_KINDS,
    _label_id_from_obj,
    _label_name_from_obj,
)
from custom_components.ai_home_copilot.const import DOMAIN


class MockLabel:
    """Mock HA label for testing."""

    def __init__(self, label_id: str, name: str, icon: str | None = None, color: str | None = None):
        self.label_id = label_id
        self.id = label_id
        self.name = name
        self.icon = icon
        self.color = color


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance for tag sync tests."""
    # Use a real dict for data to support setdefault properly
    hass = Mock()
    hass.data = {}  # Real dict, not MagicMock
    hass.config_entries = Mock()
    hass.config_entries.async_entries = Mock(return_value=[])
    hass.loop = Mock()
    hass.bus = Mock()
    hass.bus.async_listen = Mock()
    hass.helpers = Mock()
    hass.helpers.storage = Mock()
    
    # Mock Store for tag registry
    mock_store = Mock()
    mock_store.async_load = AsyncMock(return_value=None)
    mock_store.async_save = AsyncMock()
    
    # Create a mock Store class that returns our mock_store instance
    def mock_store_class(*args, **kwargs):
        return mock_store
    
    hass.helpers.storage.Store = mock_store_class
    
    return hass


# =============================================================================
# TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_label_helpers():
    """Test label extraction helpers."""
    label = MockLabel("label_123", "kitchen_light", icon="mdi:lightbulb")
    assert _label_id_from_obj(label) == "label_123"
    assert _label_name_from_obj(label) == "kitchen_light"

    dict_label = {"label_id": "label_456", "name": "bedroom"}
    assert _label_id_from_obj(dict_label) == "label_456"
    assert _label_name_from_obj(dict_label) == "bedroom"


@pytest.mark.asyncio
async def test_import_canonical_tags(mock_hass):
    """Test importing tags from Core registry."""
    tags = [
        {
            "id": "aicp.kind.light",
            "display": {"name": "Light Control", "names": {"de": "Lichtsteuerung"}},
            "icon": "mdi:lightbulb",
            "color": "yellow",
            "ha": {"materialize_as_label": True},
        },
        {
            "id": "aicp.role.safety_critical",
            "display": {"name": "Safety Critical"},
            "ha": {"materializes_in_ha": True},
        },
        {
            "id": "candidate.test",
            "display": {"name": "Candidate Tag"},
            "ha": {"materialize_as_label": False},  # not materialized in v0.1
        },
    ]

    # Mock storage for tag registry
    mock_store_data = {}
    mock_store = Mock()
    mock_store.async_load = AsyncMock(return_value=None)
    mock_store.async_save = AsyncMock()
    
    def mock_store_class(*args, **kwargs):
        return mock_store
    
    mock_hass.helpers.storage.Store = mock_store_class
    
    # Set up the global store in hass.data
    mock_hass.data[DOMAIN] = {
        "_global": {
            "tag_registry_store": mock_store,
        }
    }
    
    # Patch the Store used by tag_registry
    with patch("custom_components.ai_home_copilot.tag_registry.Store", mock_store_class):
        result = await async_import_canonical_tags(
            mock_hass,
            tags=tags,
            schema_version="0.1",
            fetched_at="2026-02-10T02:40:00Z",
        )

    assert result["tags_imported"] == 3


@pytest.mark.asyncio
async def test_replace_assignments_snapshot(mock_hass):
    """Test importing assignments snapshot from Core."""
    assignments = [
        {
            "assignment_id": "assign_001",
            "subject_kind": "entity",
            "subject_id": "light.kitchen",
            "tag_id": "aicp.kind.light",
            "materialized": False,
            "source": "core",
            "confidence": 0.95,
            "updated_at": "2026-02-10T02:40:00Z",
        },
        {
            "assignment_id": "assign_002",
            "subject_kind": "area",
            "subject_id": "kitchen",
            "tag_id": "aicp.role.important",
            "materialized": False,
            "source": "core",
            "confidence": 0.85,
        },
    ]

    # Mock storage for tag registry
    mock_store = Mock()
    mock_store.async_load = AsyncMock(return_value=None)
    mock_store.async_save = AsyncMock()
    
    def mock_store_class(*args, **kwargs):
        return mock_store
    
    mock_hass.helpers.storage.Store = mock_store_class
    
    # Set up the global store in hass.data
    mock_hass.data[DOMAIN] = {
        "_global": {
            "tag_registry_store": mock_store,
        }
    }
    
    # Patch the Store used by tag_registry
    with patch("custom_components.ai_home_copilot.tag_registry.Store", mock_store_class):
        result = await async_replace_assignments_snapshot(
            mock_hass,
            assignments=assignments,
            revision=42,
            fetched_at="2026-02-10T02:40:00Z",
        )

    assert result["subjects"] == 2
    assert result["assignments"] == 2


@pytest.mark.asyncio
async def test_sync_labels_now(mock_hass):
    """Test label materialization in HA."""
    # Pre-populate tags and assignments via Store mock
    initial_data = {
        "tags": {
            "aicp.kind.light": {"title": "Light", "status": "confirmed", "icon": "mdi:lightbulb"},
            "aicp.role.safety": {"title": "Safety", "status": "confirmed"},
            "candidate.pending": {"title": "Pending", "status": "pending"},  # won't materialize
        },
        "assignments": {
            "entity:light.kitchen": ["aicp.kind.light", "aicp.role.safety"],
            "entity:light.bedroom": ["aicp.kind.light"],
        },
        "ha_label_map": {},
        "user_aliases": {},
    }
    
    mock_store = Mock()
    mock_store.async_load = AsyncMock(return_value=initial_data)
    mock_store.async_save = AsyncMock()
    
    # Set up the global store in hass.data so _get_store returns our mock
    # This must happen before calling async_sync_labels_now
    mock_hass.data[DOMAIN] = {
        "_global": {
            "tag_registry_store": mock_store,
        }
    }

    # Mock label registry - async_list_labels is actually a sync function that returns a list
    mock_label_reg = Mock()
    mock_label_reg.async_list_labels = Mock(return_value=[])  # Sync, not async
    mock_label_reg.async_create = Mock(
        side_effect=lambda name, **kwargs: MockLabel(f"label_{name}", name, **kwargs)
    )

    # Mock entity registry updates - async_update_entity is SYNC, not async
    mock_entity_reg = Mock()
    mock_entity_reg.async_update_entity = Mock()

    # Mock config entries
    mock_config_entries = Mock()
    mock_config_entries.async_entries = Mock(return_value=[])
    
    mock_hass.config_entries = mock_config_entries

    with patch(
        "custom_components.ai_home_copilot.tag_registry.get_label_registry_sync",
        return_value=mock_label_reg,
    ), patch(
        "custom_components.ai_home_copilot.tag_registry._get_label_registry",
        return_value=mock_label_reg,
    ), patch(
        "homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_reg
    ):
        report = await async_sync_labels_now(mock_hass)

    # Should have created 2 labels (3 tags - 1 candidate)
    assert report.created_labels == 2
    # Should have applied labels to 2 entities
    assert report.updated_subjects == 2
    # Should have skipped 1 pending tag
    assert report.skipped_pending == 1
    # No errors
    assert report.errors is None


@pytest.mark.asyncio
async def test_pull_tag_system_snapshot_mocked(mock_hass):
    """Test pulling full tag system snapshot from Core."""
    # Create a minimal mock config entry (avoid real ConfigEntry dependency)
    mock_entry = Mock()
    mock_entry.entry_id = "test_entry"
    mock_entry.data = {"host": "localhost", "port": 8123, "token": "test_token"}
    mock_entry.options = {}
    
    # Mock config entries properly
    mock_config_entries = Mock()
    mock_config_entries.async_entries = Mock(return_value=[mock_entry])
    mock_hass.config_entries = mock_config_entries
    
    # Mock storage with stateful behavior (save then load returns saved data)
    stored_data = [None]  # Use list to allow modification in nested function
    
    async def mock_async_load():
        return stored_data[0]
    
    async def mock_async_save(data):
        stored_data[0] = data
    
    mock_store = Mock()
    mock_store.async_load = mock_async_load
    mock_store.async_save = mock_async_save
    
    # Set up hass.data with both global store and entry coordinator
    mock_hass.data[DOMAIN] = {
        "_global": {
            "tag_registry_store": mock_store,
        },
        "test_entry": {
            "coordinator": Mock(
                api=AsyncMock(
                    async_get=AsyncMock(
                        side_effect=lambda url: _mock_core_response(url)
                    )
                )
            )
        }
    }

    # Mock label registry - async_list_labels is actually a sync function that returns a list
    mock_label_reg = Mock()
    mock_label_reg.async_list_labels = Mock(return_value=[])  # Sync, not async
    mock_label_reg.async_create = Mock(
        side_effect=lambda name, **kwargs: MockLabel(f"label_{name}", name, **kwargs)
    )

    with patch(
        "custom_components.ai_home_copilot.tag_registry.get_label_registry_sync",
        return_value=mock_label_reg,
    ), patch(
        "custom_components.ai_home_copilot.tag_registry._get_label_registry",
        return_value=mock_label_reg,
    ):
        result = await async_pull_tag_system_snapshot(mock_hass, entry_id="test_entry", lang="de")

    assert result["entry_id"] == "test_entry"
    assert result["tags"]["tags_imported"] > 0
    assert result["assignments"]["assignments"] > 0
    assert result["label_sync"]["created_labels"] > 0


def _mock_core_response(url: str):
    """Mock Core API responses for tag-system endpoints."""
    if "/tag-system/tags" in url:
        return {
            "schema_version": "0.1",
            "tags": [
                {
                    "id": "aicp.kind.light",
                    "display": {"name": "Light", "names": {"de": "Licht"}},
                    "icon": "mdi:lightbulb",
                    "ha": {"materialize_as_label": True},
                },
                {
                    "id": "aicp.kind.sensor",
                    "display": {"name": "Sensor", "names": {"de": "Sensor"}},
                    "ha": {"materialize_as_label": True},
                },
            ],
        }
    if "/tag-system/assignments" in url:
        return {
            "revision": 1,
            "total": 2,
            "assignments": [
                {
                    "assignment_id": "a1",
                    "subject_kind": "entity",
                    "subject_id": "light.kitchen",
                    "tag_id": "aicp.kind.light",
                    "materialized": False,
                    "source": "core",
                },
                {
                    "assignment_id": "a2",
                    "subject_kind": "entity",
                    "subject_id": "sensor.temperature",
                    "tag_id": "aicp.kind.sensor",
                    "materialized": False,
                    "source": "core",
                },
            ],
        }
    return {}