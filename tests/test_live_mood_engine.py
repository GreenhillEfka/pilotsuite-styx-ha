"""Tests for LiveMoodEngine -- local mood calculation from real Entity states.

Covers:
- Comfort calculation (temperature scoring)
- Joy calculation (media playing state)
- Frugality calculation (power consumption)
- _safe_float helper
- Mood summary aggregation (get_summary)
- _linear_score helper
- _avg helper
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

DOMAIN = "ai_home_copilot"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hass_state(entity_id: str, state_value: str, attributes=None):
    """Create a mock State object."""
    s = MagicMock()
    s.entity_id = entity_id
    s.state = state_value
    s.attributes = attributes or {}
    return s


def _make_hass(states_map: dict[str, str] | None = None):
    """Build a mock hass with states.get() returning from a mapping."""
    hass = MagicMock()
    _states = {}
    if states_map:
        for eid, val in states_map.items():
            _states[eid] = _make_hass_state(eid, val)

    hass.states.get = MagicMock(side_effect=lambda eid: _states.get(eid))
    hass.states.async_all = MagicMock(return_value=[])
    return hass


def _make_zone(zone_id: str, entities: dict[str, list[str]] | None = None):
    """Create a mock HabitusZoneV2."""
    zone = MagicMock()
    zone.zone_id = zone_id
    ents = entities or {}

    zone.get_role_entities = MagicMock(side_effect=lambda role: ents.get(role, []))

    # get_all_entities returns all entity IDs across all roles
    all_ents = set()
    for role_ents in ents.values():
        all_ents.update(role_ents)
    zone.get_all_entities = MagicMock(return_value=all_ents)

    return zone


# ---------------------------------------------------------------------------
# Tests: _safe_float
# ---------------------------------------------------------------------------

class TestSafeFloat:
    """Test the _safe_float helper."""

    def test_valid_numeric_state(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _safe_float,
        )

        hass = _make_hass({"sensor.temp": "22.5"})
        assert _safe_float(hass, "sensor.temp") == 22.5

    def test_unknown_state_returns_none(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _safe_float,
        )

        hass = _make_hass({"sensor.temp": "unknown"})
        assert _safe_float(hass, "sensor.temp") is None

    def test_unavailable_state_returns_none(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _safe_float,
        )

        hass = _make_hass({"sensor.temp": "unavailable"})
        assert _safe_float(hass, "sensor.temp") is None

    def test_missing_entity_returns_none(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _safe_float,
        )

        hass = _make_hass({})
        assert _safe_float(hass, "sensor.nonexistent") is None

    def test_empty_string_returns_none(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _safe_float,
        )

        hass = _make_hass({"sensor.temp": ""})
        assert _safe_float(hass, "sensor.temp") is None

    def test_non_numeric_string_returns_none(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _safe_float,
        )

        hass = _make_hass({"sensor.temp": "abc"})
        assert _safe_float(hass, "sensor.temp") is None


# ---------------------------------------------------------------------------
# Tests: Comfort calculation
# ---------------------------------------------------------------------------

class TestComputeComfort:
    """Test _compute_comfort at different temperatures."""

    def test_22c_optimal_high_comfort(self):
        """22 degrees C is within optimal range -> comfort should be high (1.0)."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_comfort,
        )

        hass = _make_hass({"sensor.temp": "22.0"})
        zone = _make_zone("zone:test", {"temperature": ["sensor.temp"]})

        score = _compute_comfort(hass, zone)
        assert score >= 0.9, f"22C should give high comfort, got {score}"

    def test_15c_below_range_low_comfort(self):
        """15 degrees C is below TEMP_MIN (18) -> comfort should be low (0.0)."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_comfort,
        )

        hass = _make_hass({"sensor.temp": "15.0"})
        zone = _make_zone("zone:test", {"temperature": ["sensor.temp"]})

        score = _compute_comfort(hass, zone)
        assert score <= 0.1, f"15C should give low comfort, got {score}"

    def test_30c_above_range_low_comfort(self):
        """30 degrees C is above TEMP_MAX (28) -> comfort should be low (0.0)."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_comfort,
        )

        hass = _make_hass({"sensor.temp": "30.0"})
        zone = _make_zone("zone:test", {"temperature": ["sensor.temp"]})

        score = _compute_comfort(hass, zone)
        assert score <= 0.1, f"30C should give low comfort, got {score}"

    def test_no_sensors_returns_neutral(self):
        """Zone with no temperature sensors -> avg returns 0.5."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_comfort,
        )

        hass = _make_hass({})
        zone = _make_zone("zone:test", {})

        score = _compute_comfort(hass, zone)
        assert score == 0.5  # _avg([]) returns 0.5

    def test_humidity_contributes_to_comfort(self):
        """Optimal humidity (50%) combined with optimal temp -> high comfort."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_comfort,
        )

        hass = _make_hass({"sensor.temp": "23.0", "sensor.humid": "50.0"})
        zone = _make_zone(
            "zone:test",
            {"temperature": ["sensor.temp"], "humidity": ["sensor.humid"]},
        )

        score = _compute_comfort(hass, zone)
        assert score >= 0.9


# ---------------------------------------------------------------------------
# Tests: Joy calculation
# ---------------------------------------------------------------------------

class TestComputeJoy:
    """Test _compute_joy from media player states."""

    def test_media_playing_gives_high_joy(self):
        """A playing media player should add joy."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_joy,
        )

        hass = _make_hass({"media_player.sonos": "playing"})
        # Also make person states empty
        hass.states.async_all = MagicMock(return_value=[])
        zone = _make_zone("zone:test", {"media": ["media_player.sonos"]})

        score = _compute_joy(hass, zone)
        # 1 playing -> 0.25, no persons bonus -> total 0.25
        assert score >= 0.2, f"Playing media should give joy >= 0.2, got {score}"

    def test_media_idle_gives_baseline_joy(self):
        """Idle media player -> only baseline joy (0.1)."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_joy,
        )

        hass = _make_hass({"media_player.sonos": "idle"})
        hass.states.async_all = MagicMock(return_value=[])
        zone = _make_zone("zone:test", {"media": ["media_player.sonos"]})

        score = _compute_joy(hass, zone)
        assert score == 0.1  # baseline

    def test_two_playing_media_adds_more_joy(self):
        """Two playing media players -> 0.5 + persons."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_joy,
        )

        hass = _make_hass({
            "media_player.sonos": "playing",
            "media_player.tv": "playing",
        })
        hass.states.async_all = MagicMock(return_value=[])
        zone = _make_zone(
            "zone:test",
            {"media": ["media_player.sonos", "media_player.tv"]},
        )

        score = _compute_joy(hass, zone)
        # 2 * 0.25 = 0.5
        assert score >= 0.4

    def test_persons_home_add_joy(self):
        """Two persons home should add 0.15 to joy score."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_joy,
        )

        hass = _make_hass({})
        person1 = _make_hass_state("person.andreas", "home")
        person2 = _make_hass_state("person.efka", "home")
        hass.states.async_all = MagicMock(return_value=[person1, person2])
        zone = _make_zone("zone:test", {"media": ["media_player.sonos"]})

        score = _compute_joy(hass, zone)
        # 2 persons home -> +0.15 (no playing media, but score > 0 so no baseline)
        assert score == 0.15


# ---------------------------------------------------------------------------
# Tests: Frugality calculation
# ---------------------------------------------------------------------------

class TestComputeFrugality:
    """Test _compute_frugality from power consumption."""

    def test_low_power_high_frugality(self):
        """< 50W total -> frugality should be 1.0."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_frugality,
        )

        hass = _make_hass({"sensor.power": "30.0"})
        zone = _make_zone("zone:test", {"power": ["sensor.power"]})

        score = _compute_frugality(hass, zone)
        assert score == 1.0

    def test_high_power_low_frugality(self):
        """500W -> frugality should be 0.0."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_frugality,
        )

        hass = _make_hass({"sensor.power": "500.0"})
        zone = _make_zone("zone:test", {"power": ["sensor.power"]})

        score = _compute_frugality(hass, zone)
        assert score == 0.0

    def test_mid_power_mid_frugality(self):
        """275W (midpoint of 50..500) -> frugality should be around 0.5."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_frugality,
        )

        hass = _make_hass({"sensor.power": "275.0"})
        zone = _make_zone("zone:test", {"power": ["sensor.power"]})

        score = _compute_frugality(hass, zone)
        assert 0.4 <= score <= 0.6, f"275W should be ~0.5 frugality, got {score}"

    def test_no_power_entities_neutral(self):
        """No power sensors -> neutral (0.5)."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_frugality,
        )

        hass = _make_hass({})
        zone = _make_zone("zone:test", {})

        score = _compute_frugality(hass, zone)
        assert score == 0.5

    def test_unavailable_power_neutral(self):
        """Unavailable power reading -> neutral (0.5)."""
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _compute_frugality,
        )

        hass = _make_hass({"sensor.power": "unavailable"})
        zone = _make_zone("zone:test", {"power": ["sensor.power"]})

        score = _compute_frugality(hass, zone)
        assert score == 0.5


# ---------------------------------------------------------------------------
# Tests: _linear_score helper
# ---------------------------------------------------------------------------

class TestLinearScore:
    """Test the _linear_score helper directly."""

    def test_inside_optimal_range(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _linear_score,
        )

        assert _linear_score(23.0, 22.0, 24.0, 18.0, 28.0) == 1.0

    def test_at_bad_low(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _linear_score,
        )

        assert _linear_score(18.0, 22.0, 24.0, 18.0, 28.0) == 0.0

    def test_at_bad_high(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _linear_score,
        )

        assert _linear_score(28.0, 22.0, 24.0, 18.0, 28.0) == 0.0

    def test_midpoint_below_optimal(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            _linear_score,
        )

        # 20.0 is halfway between 18 and 22 -> should be 0.5
        assert _linear_score(20.0, 22.0, 24.0, 18.0, 28.0) == 0.5


# ---------------------------------------------------------------------------
# Tests: _avg helper
# ---------------------------------------------------------------------------

class TestAvg:
    """Test the _avg helper."""

    def test_empty_returns_neutral(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import _avg

        assert _avg([]) == 0.5

    def test_single_value(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import _avg

        assert _avg([0.8]) == 0.8

    def test_multiple_values(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import _avg

        assert _avg([0.4, 0.6]) == 0.5


# ---------------------------------------------------------------------------
# Tests: Mood summary aggregation
# ---------------------------------------------------------------------------

class TestMoodSummary:
    """Test LiveMoodEngine.get_summary()."""

    def test_summary_empty_zones(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            LiveMoodEngine,
        )

        engine = LiveMoodEngine()
        summary = engine.get_summary()
        assert summary["zones_tracked"] == 0
        assert summary["average_comfort"] == 0.5

    def test_summary_with_moods(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            LiveMoodEngine,
        )

        engine = LiveMoodEngine()
        # Inject mood data directly
        engine._live_mood = {
            "zone:a": {"comfort": 0.8, "joy": 0.6, "frugality": 0.9},
            "zone:b": {"comfort": 0.6, "joy": 0.4, "frugality": 0.7},
        }

        summary = engine.get_summary()
        assert summary["zones_tracked"] == 2
        assert summary["average_comfort"] == 0.7  # (0.8+0.6)/2
        assert summary["average_joy"] == 0.5       # (0.6+0.4)/2
        assert summary["average_frugality"] == 0.8  # (0.9+0.7)/2

    def test_get_zone_mood_returns_none_for_unknown(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            LiveMoodEngine,
        )

        engine = LiveMoodEngine()
        assert engine.get_zone_mood("zone:nonexistent") is None

    def test_get_all_moods_returns_copy(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            LiveMoodEngine,
        )

        engine = LiveMoodEngine()
        engine._live_mood = {"zone:a": {"comfort": 0.5, "joy": 0.5, "frugality": 0.5}}

        all_moods = engine.get_all_moods()
        assert len(all_moods) == 1
        assert "zone:a" in all_moods

    def test_mood_changed_detects_significant_change(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            LiveMoodEngine,
        )

        old = {"comfort": 0.5, "joy": 0.5, "frugality": 0.5}
        new = {"comfort": 0.7, "joy": 0.5, "frugality": 0.5}
        assert LiveMoodEngine._mood_changed(old, new) is True

    def test_mood_changed_ignores_tiny_change(self):
        from custom_components.ai_home_copilot.core.modules.live_mood_engine import (
            LiveMoodEngine,
        )

        old = {"comfort": 0.500, "joy": 0.500, "frugality": 0.500}
        new = {"comfort": 0.505, "joy": 0.500, "frugality": 0.500}
        assert LiveMoodEngine._mood_changed(old, new) is False
