"""Unit tests for tag utilities logic - No imports from custom_components.

Tests the pure logic functions for tag handling.

Run with: pytest tests/unit/test_tag_utils_logic.py -v
"""
import pytest


# ============================================================================
# PURE LOGIC FUNCTIONS (copied for unit testing without HA dependency)
# ============================================================================

def _is_user_tag(tag_name: str) -> bool:
    """Check if a tag is a user-defined tag."""
    return tag_name.startswith("user.")


def _tag_status(tag_data: dict) -> str:
    """Extract tag status with default."""
    if tag_data is None:
        return "pending"
    return tag_data.get("status", "pending")


def _is_pending_materialization(tag_name: str, tag_data: dict) -> bool:
    """Check if a tag is pending materialization."""
    status = _tag_status(tag_data)
    if status != "pending":
        return False
    return tag_name.startswith("learned.") or tag_name.startswith("candidate.")


def _label_id_from_obj(obj) -> str | None:
    """Extract label_id from various object formats."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get("label_id") or obj.get("id")
    return getattr(obj, "label_id", None)


def _label_name_from_obj(obj) -> str | None:
    """Extract label name from various object formats."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get("name")
    return getattr(obj, "name", None)


def _should_materialize(tag_data: dict) -> bool:
    """Check if a tag should be materialized as a label."""
    if not tag_data:
        return True
    ha_config = tag_data.get("ha", {})
    if ha_config.get("materialize_as_label") is False:
        return False
    if ha_config.get("materializes_in_ha") is False:
        return False
    return True


SUPPORTED_SUBJECT_KINDS = {"entity", "device", "area", "automation", "scene", "script", "helper"}


# ============================================================================
# TESTS
# ============================================================================

class TestUserTagIdentification:
    """Tests for user tag identification."""
    
    def test_user_tags(self):
        """Test user tag identification."""
        assert _is_user_tag("user.my_label") is True
        assert _is_user_tag("user.kitchen") is True
        assert _is_user_tag("user.bedroom_lights") is True
    
    def test_non_user_tags(self):
        """Test non-user tag identification."""
        assert _is_user_tag("aicp.kind.light") is False
        assert _is_user_tag("candidate.test") is False
        assert _is_user_tag("learned.motion") is False
        assert _is_user_tag("system.internal") is False


class TestTagStatus:
    """Tests for tag status extraction."""
    
    def test_explicit_status(self):
        """Test explicit status values."""
        assert _tag_status({"status": "confirmed"}) == "confirmed"
        assert _tag_status({"status": "pending"}) == "pending"
        assert _tag_status({"status": "rejected"}) == "rejected"
    
    def test_default_status(self):
        """Test default status when missing."""
        assert _tag_status({}) == "pending"
        assert _tag_status(None) == "pending"


class TestPendingMaterialization:
    """Tests for pending materialization detection."""
    
    def test_learned_pending(self):
        """Test learned.* tags with pending status."""
        assert _is_pending_materialization("learned.motion_detected", {"status": "pending"}) is True
        assert _is_pending_materialization("learned.motion_detected", {"status": "confirmed"}) is False
    
    def test_candidate_pending(self):
        """Test candidate.* tags with pending status."""
        assert _is_pending_materialization("candidate.motion", {"status": "pending"}) is True
        assert _is_pending_materialization("candidate.motion", {"status": "confirmed"}) is False
    
    def test_non_learned_candidate(self):
        """Test that non-learned/candidate tags don't block."""
        assert _is_pending_materialization("aicp.kind.light", {"status": "confirmed"}) is False
        assert _is_pending_materialization("aicp.kind.light", {"status": "pending"}) is False


class TestLabelIdExtraction:
    """Tests for label_id extraction from various formats."""
    
    def test_dict_with_label_id(self):
        """Test extraction from dict with label_id."""
        assert _label_id_from_obj({"label_id": "abc123"}) == "abc123"
    
    def test_dict_with_id(self):
        """Test extraction from dict with id."""
        assert _label_id_from_obj({"id": "xyz789"}) == "xyz789"
    
    def test_object_with_label_id(self):
        """Test extraction from object with label_id attribute."""
        class MockLabel:
            label_id = "obj_id"
        
        assert _label_id_from_obj(MockLabel()) == "obj_id"
    
    def test_invalid_inputs(self):
        """Test invalid inputs return None."""
        assert _label_id_from_obj(None) is None
        assert _label_id_from_obj({}) is None


class TestLabelNameExtraction:
    """Tests for label name extraction."""
    
    def test_dict_with_name(self):
        """Test extraction from dict with name."""
        assert _label_name_from_obj({"name": "kitchen"}) == "kitchen"
    
    def test_object_with_name(self):
        """Test extraction from object with name attribute."""
        class MockLabel:
            name = "bedroom"
        
        assert _label_name_from_obj(MockLabel()) == "bedroom"
    
    def test_invalid_inputs(self):
        """Test invalid inputs return None."""
        assert _label_name_from_obj(None) is None
        assert _label_name_from_obj({}) is None


class TestMaterializationPolicy:
    """Tests for materialization policy."""
    
    def test_default_materialize(self):
        """Test default is to materialize."""
        assert _should_materialize({}) is True
    
    def test_explicit_false(self):
        """Test explicit materialize_as_label=False."""
        assert _should_materialize({"ha": {"materialize_as_label": False}}) is False
    
    def test_materializes_in_ha_false(self):
        """Test materializes_in_ha=False."""
        assert _should_materialize({"ha": {"materializes_in_ha": False}}) is False
    
    def test_both_true(self):
        """Test both flags true."""
        assert _should_materialize({"ha": {"materialize_as_label": True, "materializes_in_ha": True}}) is True


class TestSupportedSubjectKinds:
    """Tests for supported subject kinds."""
    
    def test_expected_kinds(self):
        """Verify supported subject types for v0.1."""
        expected = {"entity", "device", "area", "automation", "scene", "script", "helper"}
        assert SUPPORTED_SUBJECT_KINDS == expected
    
    def test_kind_membership(self):
        """Test kind membership checking."""
        assert "entity" in SUPPORTED_SUBJECT_KINDS
        assert "device" in SUPPORTED_SUBJECT_KINDS
        assert "unknown" not in SUPPORTED_SUBJECT_KINDS


# Mark all tests as unit tests
pytestmark = pytest.mark.unit