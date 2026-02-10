"""Integration tests for tag-sync roundtrip: Core ↔ HA labels."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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


class MockLabel:
    """Mock HA label for testing."""

    def __init__(self, label_id: str, name: str, icon: str | None = None, color: str | None = None):
        self.label_id = label_id
        self.id = label_id
        self.name = name
        self.icon = icon
        self.color = color


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
async def test_import_canonical_tags(hass):
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

    result = await async_import_canonical_tags(
        hass,
        tags=tags,
        schema_version="0.1",
        fetched_at="2026-02-10T02:40:00Z",
    )

    assert result["tags_imported"] == 3

    # Verify storage loaded correctly
    from homeassistant.helpers.storage import Store

    store = Store(hass, 1, "ai_home_copilot.tag_registry")
    data = await store.async_load()
    assert "aicp.kind.light" in data["tags"]
    assert data["tags"]["aicp.kind.light"]["status"] == "confirmed"
    assert data["tags"]["aicp.kind.light"]["icon"] == "mdi:lightbulb"
    assert "aicp.role.safety_critical" in data["tags"]
    assert data["registry_schema_version"] == "0.1"


@pytest.mark.asyncio
async def test_replace_assignments_snapshot(hass):
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

    result = await async_replace_assignments_snapshot(
        hass,
        assignments=assignments,
        revision=42,
        fetched_at="2026-02-10T02:40:00Z",
    )

    assert result["subjects"] == 2
    assert result["assignments"] == 2

    from homeassistant.helpers.storage import Store

    store = Store(hass, 1, "ai_home_copilot.tag_registry")
    data = await store.async_load()
    assert "entity:light.kitchen" in data["assignments"]
    assert "aicp.kind.light" in data["assignments"]["entity:light.kitchen"]
    assert data["assignments_revision"] == 42


@pytest.mark.asyncio
async def test_sync_labels_now(hass):
    """Test label materialization in HA."""
    # Pre-populate tags and assignments
    from homeassistant.helpers.storage import Store

    store = Store(hass, 1, "ai_home_copilot.tag_registry")
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
    await store.async_save(initial_data)

    # Mock label registry
    mock_label_reg = AsyncMock()
    mock_label_reg.async_list_labels = AsyncMock(return_value=[])
    mock_label_reg.async_create = AsyncMock(
        side_effect=lambda name, **kwargs: MockLabel(f"label_{name}", name, **kwargs)
    )

    # Mock entity registry updates
    mock_entity_reg = AsyncMock()
    mock_entity_reg.async_update_entity = AsyncMock()

    with patch(
        "custom_components.ai_home_copilot.tag_registry.async_get_label_registry",
        return_value=mock_label_reg,
    ), patch(
        "homeassistant.helpers.entity_registry.async_get", return_value=mock_entity_reg
    ):
        report = await async_sync_labels_now(hass)

    # Should have created 2 labels (3 tags - 1 candidate)
    assert report.created_labels == 2
    # Should have applied labels to 2 entities
    assert report.updated_subjects == 2
    # Should have skipped 1 pending tag
    assert report.skipped_pending == 1
    # No errors
    assert report.errors is None

    # Verify entity registry was updated
    assert mock_entity_reg.async_update_entity.call_count == 2


@pytest.mark.asyncio
async def test_pull_tag_system_snapshot_mocked(hass):
    """Test pulling full tag system snapshot from Core."""
    # Mock the config entry and coordinator
    from homeassistant.config_entries import ConfigEntry
    from custom_components.ai_home_copilot.const import DOMAIN

    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="AI Home CoPilot",
        data={"host": "localhost", "port": 8123, "token": "test_token"},
        options={},
        entry_id="test_entry",
    )
    hass.config_entries._entries = [entry]
    hass.data[DOMAIN] = {
        "test_entry": {
            "coordinator": MagicMock(
                api=AsyncMock(
                    async_get=AsyncMock(
                        side_effect=lambda url: _mock_core_response(url)
                    )
                )
            )
        }
    }

    # Mock label registry
    mock_label_reg = AsyncMock()
    mock_label_reg.async_list_labels = AsyncMock(return_value=[])
    mock_label_reg.async_create = AsyncMock(
        side_effect=lambda name, **kwargs: MockLabel(f"label_{name}", name, **kwargs)
    )

    with patch(
        "custom_components.ai_home_copilot.tag_registry.async_get_label_registry",
        return_value=mock_label_reg,
    ):
        result = await async_pull_tag_system_snapshot(hass, entry_id="test_entry", lang="de")

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
