"""Tests for ConflictResolver engine."""

import pytest

from custom_components.ai_home_copilot.conflict_resolution import (
    ConflictResolver,
    ConflictState,
)


@pytest.fixture
def resolver():
    return ConflictResolver(threshold=0.3)


# ---------- Detection ----------


def test_no_conflict_single_user(resolver):
    moods = {"person.a": {"comfort": 0.7, "frugality": 0.3, "joy": 0.5}}
    state = resolver.evaluate(moods, {"person.a": 0.5})
    assert state.active is False
    assert len(state.conflicts) == 0


def test_no_conflict_similar_prefs(resolver):
    moods = {
        "person.a": {"comfort": 0.6, "frugality": 0.5, "joy": 0.4},
        "person.b": {"comfort": 0.7, "frugality": 0.5, "joy": 0.5},
    }
    state = resolver.evaluate(moods, {"person.a": 0.5, "person.b": 0.5})
    assert state.active is False


def test_conflict_detected(resolver):
    moods = {
        "person.a": {"comfort": 0.9, "frugality": 0.2, "joy": 0.5},
        "person.b": {"comfort": 0.3, "frugality": 0.8, "joy": 0.5},
    }
    state = resolver.evaluate(moods, {"person.a": 0.7, "person.b": 0.5})
    assert state.active is True
    assert len(state.conflicts) >= 1
    axes = {c.axis for c in state.conflicts}
    assert "comfort" in axes
    assert "frugality" in axes


def test_three_users_multi_conflict(resolver):
    moods = {
        "person.a": {"comfort": 0.9, "frugality": 0.1, "joy": 0.5},
        "person.b": {"comfort": 0.1, "frugality": 0.9, "joy": 0.5},
        "person.c": {"comfort": 0.5, "frugality": 0.5, "joy": 0.5},
    }
    state = resolver.evaluate(
        moods, {"person.a": 0.5, "person.b": 0.5, "person.c": 0.5}
    )
    assert state.active is True
    assert len(state.users_involved) == 3


# ---------- Resolution strategies ----------


def test_weighted_resolution(resolver):
    moods = {
        "person.admin": {"comfort": 0.9, "frugality": 0.2, "joy": 0.5},
        "person.user": {"comfort": 0.3, "frugality": 0.8, "joy": 0.5},
    }
    state = resolver.evaluate(moods, {"person.admin": 0.8, "person.user": 0.2})
    # Admin has 80% weight → comfort should be closer to 0.9
    assert state.resolved_mood["comfort"] > 0.7


def test_compromise_resolution(resolver):
    resolver.set_strategy("compromise")
    moods = {
        "person.a": {"comfort": 0.9, "frugality": 0.2, "joy": 0.5},
        "person.b": {"comfort": 0.3, "frugality": 0.8, "joy": 0.5},
    }
    state = resolver.evaluate(moods, {"person.a": 0.9, "person.b": 0.1})
    # Compromise ignores priority — equal average
    assert abs(state.resolved_mood["comfort"] - 0.6) < 0.01
    assert abs(state.resolved_mood["frugality"] - 0.5) < 0.01


def test_override_resolution(resolver):
    resolver.set_strategy("override", override_user="person.boss")
    moods = {
        "person.boss": {"comfort": 0.9, "frugality": 0.1, "joy": 0.8},
        "person.guest": {"comfort": 0.2, "frugality": 0.9, "joy": 0.3},
    }
    state = resolver.evaluate(moods, {"person.boss": 0.5, "person.guest": 0.5})
    assert state.resolved_mood["comfort"] == 0.9
    assert state.resolved_mood["joy"] == 0.8


def test_invalid_strategy_raises():
    r = ConflictResolver()
    with pytest.raises(ValueError):
        r.set_strategy("unknown")


# ---------- Serialization ----------


def test_to_dict(resolver):
    moods = {
        "person.a": {"comfort": 0.9, "frugality": 0.2, "joy": 0.5},
        "person.b": {"comfort": 0.3, "frugality": 0.8, "joy": 0.5},
    }
    state = resolver.evaluate(moods, {"person.a": 0.5, "person.b": 0.5})
    d = state.to_dict()
    assert "active" in d
    assert "conflict_count" in d
    assert "details" in d
    assert isinstance(d["details"], list)


# ---------- Edge cases ----------


def test_empty_users(resolver):
    state = resolver.evaluate({}, {})
    assert state.active is False
    assert state.resolved_mood == {"comfort": 0.5, "frugality": 0.5, "joy": 0.5}


def test_missing_axis_defaults(resolver):
    moods = {
        "person.a": {"comfort": 0.9},  # missing frugality, joy
        "person.b": {"frugality": 0.8},  # missing comfort, joy
    }
    state = resolver.evaluate(moods, {"person.a": 0.5, "person.b": 0.5})
    # Should not crash — missing values default to 0.5
    assert "comfort" in state.resolved_mood
