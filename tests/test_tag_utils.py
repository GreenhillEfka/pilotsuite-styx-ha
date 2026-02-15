"""Unit tests for tag utilities (no Home Assistant dependency)."""

from custom_components.ai_home_copilot.tag_registry import (
    _is_user_tag,
    _is_pending_materialization,
    _tag_status,
    _label_id_from_obj,
    _label_name_from_obj,
    _should_materialize,
    SUPPORTED_SUBJECT_KINDS,
)


def test_is_user_tag():
    """Test user tag identification."""
    assert _is_user_tag("user.my_label") is True
    assert _is_user_tag("user.kitchen") is True
    assert _is_user_tag("aicp.kind.light") is False
    assert _is_user_tag("candidate.test") is False
    assert _is_user_tag("learned.motion") is False


def test_tag_status():
    """Test tag status extraction."""
    assert _tag_status({"status": "confirmed"}) == "confirmed"
    assert _tag_status({"status": "pending"}) == "pending"
    assert _tag_status({}) == "pending"  # default
    assert _tag_status(None) == "pending"


def test_is_pending_materialization():
    """Test pending tag detection."""
    # learned.* tags with pending status are not materialized
    assert _is_pending_materialization("learned.motion_detected", {"status": "pending"}) is True
    assert _is_pending_materialization("learned.motion_detected", {"status": "confirmed"}) is False

    # candidate.* tags with pending status are not materialized
    assert _is_pending_materialization("candidate.motion", {"status": "pending"}) is True
    assert _is_pending_materialization("candidate.motion", {"status": "confirmed"}) is False

    # confirmed non-learned/candidate tags don't block
    assert _is_pending_materialization("aicp.kind.light", {"status": "confirmed"}) is False

    # regular pending non-learned/candidate tags are not blocked by this check
    assert _is_pending_materialization("aicp.kind.light", {"status": "pending"}) is False


def test_label_id_from_obj():
    """Test label_id extraction from various formats."""
    # Dict with label_id
    assert _label_id_from_obj({"label_id": "abc123"}) == "abc123"
    # Dict with id
    assert _label_id_from_obj({"id": "xyz789"}) == "xyz789"
    # Object with label_id attribute
    class MockLabel:
        def __init__(self):
            self.label_id = "obj_id"
    assert _label_id_from_obj(MockLabel()) == "obj_id"
    # Invalid inputs
    assert _label_id_from_obj(None) is None
    assert _label_id_from_obj({}) is None


def test_label_name_from_obj():
    """Test label name extraction."""
    # Dict with name
    assert _label_name_from_obj({"name": "kitchen"}) == "kitchen"
    # Object with name attribute
    class MockLabel:
        def __init__(self):
            self.name = "bedroom"
    assert _label_name_from_obj(MockLabel()) == "bedroom"
    # Invalid
    assert _label_name_from_obj(None) is None
    assert _label_name_from_obj({}) is None


def test_should_materialize():
    """Test materialization policy."""
    # Default: materialize
    assert _should_materialize({}) is True

    # Explicit materialize_as_label=False
    assert _should_materialize({"ha": {"materialize_as_label": False}}) is False

    # Explicit materializes_in_ha=False
    assert _should_materialize({"ha": {"materializes_in_ha": False}}) is False

    # Both true: materialize
    assert _should_materialize({"ha": {"materialize_as_label": True, "materializes_in_ha": True}}) is True


def test_supported_subject_kinds():
    """Verify supported subject types for v0.1."""
    expected = {"entity", "device", "area", "automation", "scene", "script", "helper"}
    assert SUPPORTED_SUBJECT_KINDS == expected


if __name__ == "__main__":
    # Simple CLI runner for manual testing
    import sys

    tests = [
        test_is_user_tag,
        test_tag_status,
        test_is_pending_materialization,
        test_label_id_from_obj,
        test_label_name_from_obj,
        test_should_materialize,
        test_supported_subject_kinds,
    ]

    failed = 0
    for test in tests:
        try:
            test()
            print(f"✓ {test.__name__}")
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1

    if failed:
        print(f"\n{failed} test(s) failed")
        sys.exit(1)
    else:
        print(f"\nAll {len(tests)} tests passed!")
        sys.exit(0)
