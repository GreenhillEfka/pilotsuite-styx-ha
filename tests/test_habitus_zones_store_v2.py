"""Tests für Habitus Zones Store v2."""

import pytest
from unittest.mock import MagicMock, AsyncMock

# Import the module under test
import sys
sys.path.insert(0, '/config/.openclaw/workspace/ai_home_copilot_hacs_repo/custom_components/ai_home_copilot')

from habitus_zones_store_v2 import (
    HabitusZoneV2,
    ZONE_TYPE,
    ZONE_STATE,
    _normalize_zone_v2,
    _as_tuple,
    _parse_entities_mapping,
    KNOWN_ROLES,
)


class TestHabitusZoneV2:
    """Tests for HabitusZoneV2 dataclass."""

    def test_create_basic_zone(self):
        """Test creating a basic zone."""
        zone = HabitusZoneV2(
            zone_id="zone:wohnzimmer",
            name="Wohnzimmer",
            zone_type="room",
            entity_ids=("light.wohnzimmer", "binary_sensor.motion_wohnzimmer"),
        )
        
        assert zone.zone_id == "zone:wohnzimmer"
        assert zone.name == "Wohnzimmer"
        assert zone.zone_type == "room"
        assert zone.current_state == "idle"
        assert zone.graph_node_id == "zone:wohnzimmer"  # Auto-set

    def test_create_zone_with_hierarchy(self):
        """Test creating a zone with parent."""
        zone = HabitusZoneV2(
            zone_id="zone:wohnzimmer",
            name="Wohnzimmer",
            zone_type="room",
            parent_zone_id="zone:living_area",
            floor="EG",
        )
        
        assert zone.parent_zone_id == "zone:living_area"
        assert zone.floor == "EG"

    def test_create_zone_with_entities_roles(self):
        """Test zone with role-based entities."""
        zone = HabitusZoneV2(
            zone_id="zone:wohnzimmer",
            name="Wohnzimmer",
            zone_type="room",
            entities={
                "motion": ("binary_sensor.motion_wohnzimmer",),
                "lights": ("light.wohnzimmer", "light.sofa"),
                "temperature": ("sensor.temperatur_wohnzimmer",),
            },
        )
        
        assert zone.get_role_entities("motion") == ["binary_sensor.motion_wohnzimmer"]
        assert zone.get_role_entities("lights") == ["light.wohnzimmer", "light.sofa"]
        assert zone.get_all_entities() == {
            "binary_sensor.motion_wohnzimmer",
            "light.wohnzimmer",
            "light.sofa",
            "sensor.temperatur_wohnzimmer",
        }

    def test_invalid_zone_type_raises(self):
        """Test that invalid zone_type raises ValueError."""
        with pytest.raises(ValueError):
            HabitusZoneV2(
                zone_id="zone:test",
                name="Test",
                zone_type="invalid",  # type: ignore
            )

    def test_invalid_state_raises(self):
        """Test that invalid state raises ValueError."""
        with pytest.raises(ValueError):
            HabitusZoneV2(
                zone_id="zone:test",
                name="Test",
                current_state="invalid_state",  # type: ignore
            )

    def test_hierarchy_level(self):
        """Test hierarchy level calculation."""
        floor_zone = HabitusZoneV2(zone_id="zone:eg", name="EG", zone_type="floor")
        assert floor_zone.hierarchy_level == 0
        
        area_zone = HabitusZoneV2(zone_id="zone:living", name="Living Area", zone_type="area")
        assert area_zone.hierarchy_level == 1
        
        room_zone = HabitusZoneV2(zone_id="zone:wohnzimmer", name="Wohnzimmer", zone_type="room")
        assert room_zone.hierarchy_level == 2

    def test_empty_zone_id_raises(self):
        """Test that empty zone_id raises ValueError."""
        with pytest.raises(ValueError):
            HabitusZoneV2(zone_id="", name="Test")


class TestAsTuple:
    """Tests for _as_tuple helper."""

    def test_none_returns_empty_tuple(self):
        assert _as_tuple(None) == ()

    def test_list_returns_tuple(self):
        assert _as_tuple(["a", "b", "c"]) == ("a", "b", "c")

    def test_tuple_returns_tuple(self):
        assert _as_tuple(("a", "b")) == ("a", "b")

    def test_string_comma_separated(self):
        assert _as_tuple("a,b,c") == ("a", "b", "c")

    def test_string_newline_separated(self):
        assert _as_tuple("a\nb\nc") == ("a", "b", "c")

    def test_string_single_value(self):
        assert _as_tuple("single") == ("single",)


class TestParseEntitiesMapping:
    """Tests for _parse_entities_mapping helper."""

    def test_none_returns_none(self):
        assert _parse_entities_mapping(None) is None

    def test_dict_returns_dict(self):
        raw = {
            "motion": ["binary_sensor.motion_1", "binary_sensor.motion_2"],
            "lights": ["light.1", "light.2"],
        }
        result = _parse_entities_mapping(raw)
        
        assert result is not None
        assert "motion" in result
        assert "lights" in result

    def test_role_aliases(self):
        """Test that role aliases work."""
        raw = {
            "presence": ["binary_sensor.presence_1"],  # Alias for motion
            "luftfeuchte": ["sensor.humidity_1"],  # Alias for humidity
        }
        result = _parse_entities_mapping(raw)
        
        assert result is not None
        assert "motion" in result  # presence → motion
        assert "humidity" in result  # luftfeuchte → humidity

    def test_deduplication(self):
        """Test that duplicates are removed."""
        raw = {
            "lights": ["light.1", "light.2", "light.1"],  # Duplicate
        }
        result = _parse_entities_mapping(raw)
        
        assert result is not None
        assert len(result["lights"]) == 2
        assert "light.1" in result["lights"]
        assert "light.2" in result["lights"]


class TestNormalizeZoneV2:
    """Tests for _normalize_zone_v2 function."""

    def test_minimal_dict(self):
        """Test normalizing minimal dict."""
        raw = {
            "id": "zone:test",
            "name": "Test Zone",
        }
        zone = _normalize_zone_v2(raw)
        
        assert zone is not None
        assert zone.zone_id == "zone:test"
        assert zone.name == "Test Zone"
        assert zone.zone_type == "room"

    def test_full_dict(self):
        """Test normalizing full dict with all fields."""
        raw = {
            "id": "zone:wohnzimmer",
            "name": "Wohnzimmer",
            "zone_type": "room",
            "entities": {
                "motion": ["binary_sensor.motion_wohnzimmer"],
                "lights": ["light.wohnzimmer"],
            },
            "parent": "zone:living_area",
            "floor": "EG",
            "priority": 5,
            "tags": ["living", "entertainment"],
            "metadata": {"custom": "value"},
        }
        zone = _normalize_zone_v2(raw)
        
        assert zone is not None
        assert zone.zone_id == "zone:wohnzimmer"
        assert zone.parent_zone_id == "zone:living_area"
        assert zone.floor == "EG"
        assert zone.priority == 5
        assert zone.tags == ("living", "entertainment")
        assert zone.metadata == {"custom": "value"}

    def test_missing_id_returns_none(self):
        """Test that missing id returns None."""
        raw = {"name": "Test"}
        assert _normalize_zone_v2(raw) is None

    def test_zone_type_floor(self):
        """Test zone_type floor."""
        raw = {"id": "zone:eg", "zone_type": "floor"}
        zone = _normalize_zone_v2(raw)
        
        assert zone is not None
        assert zone.zone_type == "floor"

    def test_state_machine_state(self):
        """Test state field."""
        raw = {"id": "zone:test", "current_state": "active"}
        zone = _normalize_zone_v2(raw)
        
        assert zone is not None
        assert zone.current_state == "active"

    def test_invalid_zone_type_defaults_to_room(self):
        """Test that invalid zone_type defaults to room."""
        raw = {"id": "zone:test", "zone_type": "invalid"}
        zone = _normalize_zone_v2(raw)
        
        assert zone is not None
        assert zone.zone_type == "room"


class TestKnownRoles:
    """Tests for KNOWN_ROLES constant."""

    def test_contains_expected_roles(self):
        """Test that expected roles are defined."""
        assert "motion" in KNOWN_ROLES
        assert "lights" in KNOWN_ROLES
        assert "temperature" in KNOWN_ROLES
        assert "humidity" in KNOWN_ROLES
        assert "co2" in KNOWN_ROLES
        assert "media" in KNOWN_ROLES
        assert "power" in KNOWN_ROLES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
