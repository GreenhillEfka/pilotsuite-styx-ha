"""
Tests for Entity Validation Module
===================================
Tests cover:
- Zone entity validation
- Entity registry operations
- State validation

Run with: python3 -m pytest tests/ -v -k "entity"
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestZoneEntityValidation:
    """Tests for zone entity validation."""

    def test_zone_validation_v2_basic(self):
        """Test basic zone validation."""
        # Test with valid zone data
        from ai_home_copilot.habitus_zones_store_v2 import _validate_zone_v2, HabitusZoneV2
        
        mock_hass = Mock()
        
        valid_zone = HabitusZoneV2(
            zone_id="zone_1",
            name="Living Room",
            floor="ground_floor",
            entity_ids=["light.living_room", "sensor.temperature"],
            entities={
                "lights": ["light.living_room"],
                "sensors": ["sensor.temperature"]
            }
        )
        
        # Should not raise
        _validate_zone_v2(mock_hass, valid_zone)

    def test_zone_validation_v2_empty_name(self):
        """Test validation fails with empty name."""
        from ai_home_copilot.habitus_zones_store_v2 import _validate_zone_v2, HabitusZoneV2
        
        mock_hass = Mock()
        
        invalid_zone = HabitusZoneV2(
            zone_id="zone_1",
            name="",  # Empty name
            floor="ground_floor",
            entity_ids=[],
            entities=None
        )
        
        with pytest.raises(ValueError, match="name"):
            _validate_zone_v2(mock_hass, invalid_zone)

    def test_zone_validation_v2_duplicate_ids(self):
        """Test validation fails with duplicate entity IDs."""
        from ai_home_copilot.habitus_zones_store_v2 import _validate_zone_v2, HabitusZoneV2
        
        mock_hass = Mock()
        
        invalid_zone = HabitusZoneV2(
            zone_id="zone_1",
            name="Test Zone",
            floor="ground_floor",
            entity_ids=["light.test", "light.test"],  # Duplicate
            entities={"lights": ["light.test"]}
        )
        
        with pytest.raises(ValueError, match="duplicate"):
            _validate_zone_v2(mock_hass, invalid_zone)


class TestZoneNormalization:
    """Tests for zone data normalization."""

    def test_normalize_zone_v2_basic(self):
        """Test basic zone normalization."""
        from ai_home_copilot.habitus_zones_store_v2 import _normalize_zone_v2
        
        raw_zone = {
            "id": "zone_1",
            "name": "Living Room",
            "entity_ids": ["light.lr", "sensor.temp"],
            "floor": "ground_floor"
        }
        
        result = _normalize_zone_v2(raw_zone)
        
        assert result is not None
        assert result.zone_id == "zone_1"
        assert result.name == "Living Room"
        assert result.floor == "ground_floor"

    def test_normalize_zone_v2_with_default_floor(self):
        """Test zone normalization with default floor."""
        from ai_home_copilot.habitus_zones_store_v2 import _normalize_zone_v2
        
        raw_zone = {
            "id": "zone_1",
            "name": "Kitchen"
            # No floor specified
        }
        
        result = _normalize_zone_v2(raw_zone, default_floor="first_floor")
        
        assert result is not None
        assert result.floor == "first_floor"

    def test_normalize_zone_v2_invalid_data(self):
        """Test normalization with invalid data returns None."""
        from ai_home_copilot.habitus_zones_store_v2 import _normalize_zone_v2
        
        # Invalid - no ID
        result = _normalize_zone_v2({"name": "Test"})
        assert result is None
        
        # Invalid - wrong type
        result = _normalize_zone_v2("not_a_dict")
        assert result is None


class TestEntityStateValidation:
    """Tests for entity state validation."""

    def test_valid_entity_id_format(self):
        """Test valid entity ID format detection."""
        valid_ids = [
            "light.living_room",
            "sensor.temperature",
            "climate.kitchen",
            "binary_sensor.motion_hallway"
        ]
        
        for entity_id in valid_ids:
            parts = entity_id.split(".")
            assert len(parts) == 2
            assert all(part for part in parts)

    def test_invalid_entity_id_format(self):
        """Test invalid entity ID format detection."""
        invalid_ids = [
            "light",  # Missing domain
            ".living_room",  # Missing domain prefix
            "light.",  # Missing entity name
            "",  # Empty
            "light.living.room.extra"  # Too many parts
        ]
        
        for entity_id in invalid_ids:
            parts = entity_id.split(".")
            is_valid = len(parts) == 2 and all(part for part in parts)
            assert is_valid is False


class TestEntityRegistryOperations:
    """Tests for entity registry operations."""

    def test_entity_registry_mock(self):
        """Test entity registry mock structure."""
        mock_registry = {
            "light.living_room": {
                "entity_id": "light.living_room",
                "domain": "light",
                "unique_id": "light_living_room",
                "platform": "hue"
            },
            "sensor.temperature": {
                "entity_id": "sensor.temperature",
                "domain": "sensor",
                "unique_id": "sensor_temperature",
                "platform": "mqtt"
            }
        }
        
        # Test lookup
        entity = mock_registry.get("light.living_room")
        assert entity is not None
        assert entity["domain"] == "light"
        
        # Test not found
        entity = mock_registry.get("light.nonexistent")
        assert entity is None

    def test_entity_filtering_by_domain(self):
        """Test filtering entities by domain."""
        mock_registry = {
            "light.living_room": {"domain": "light"},
            "light.kitchen": {"domain": "light"},
            "sensor.temp": {"domain": "sensor"},
            "climate.hallway": {"domain": "climate"},
        }
        
        light_entities = [
            e for e in mock_registry.values()
            if e["domain"] == "light"
        ]
        
        assert len(light_entities) == 2
        assert all(e["domain"] == "light" for e in light_entities)


class TestDeviceRegistryOperations:
    """Tests for device registry operations."""

    def test_device_registry_mock(self):
        """Test device registry mock structure."""
        mock_registry = {
            "device_1": {
                "id": "device_1",
                "name": "Living Room Light",
                "identifiers": {("hue", "1")},
                "manufacturer": "Philips",
                "model": "Hue Bulb"
            }
        }
        
        device = mock_registry.get("device_1")
        assert device is not None
        assert device["manufacturer"] == "Philips"


class TestAreaRegistryOperations:
    """Tests for area registry operations."""

    def test_area_registry_mock(self):
        """Test area registry mock structure."""
        mock_registry = {
            "area_living_room": {
                "area_id": "area_living_room",
                "name": "Living Room",
                "icon": "mdi:sofa"
            }
        }
        
        area = mock_registry.get("area_living_room")
        assert area is not None
        assert area["name"] == "Living Room"

    def test_area_assignment(self):
        """Test entity-to-area assignment."""
        entity_with_area = {
            "entity_id": "light.living_room",
            "area_id": "area_living_room"
        }
        
        assert entity_with_area.get("area_id") == "area_living_room"
