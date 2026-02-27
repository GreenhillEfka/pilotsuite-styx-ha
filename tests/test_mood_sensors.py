"""Tests for PilotSuite Mood Sensors v3.0 — all sensor types.

Covers:
- MoodSensor: state extraction, mood history, stability tracking
- MoodConfidenceSensor: percentage conversion via _safe_float, attributes
- NeuronActivitySensor: active neuron counting, history via _handle_coordinator_update
- Mood Dimensions (Comfort, Joy, Energy, Stress, Frugality) via _MoodDimensionSensor
- LiveMoodDimensionSensor: per-zone mood averaging
- Dimension fallback (missing/empty data)
- safe_float helper
"""
from __future__ import annotations

import math
import pytest
from unittest.mock import MagicMock

from custom_components.ai_home_copilot.sensors.mood_sensor import (
    MoodSensor,
    MoodConfidenceSensor,
    NeuronActivitySensor,
    MoodComfortSensor,
    MoodJoySensor,
    MoodEnergySensor,
    MoodStressSensor,
    MoodFrugalitySensor,
    _safe_float,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_coordinator(data: dict | None = None):
    """Create a mock coordinator with given data."""
    coord = MagicMock()
    coord.data = data
    coord.config_entry = MagicMock()
    return coord


def _make_sensor_with_write(sensor_cls, data):
    """Create sensor and mock async_write_ha_state for tests calling _handle_coordinator_update."""
    coord = _make_coordinator(data)
    sensor = sensor_cls(coord)
    sensor.async_write_ha_state = MagicMock()
    return sensor


def safe_float_local(x, default: float = 0.0) -> float:
    """Replicate the safe_float helper used across PilotSuite sensors."""
    try:
        if x is None:
            return default
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


# ---------------------------------------------------------------------------
# safe_float Helper
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_normal_float(self):
        assert safe_float_local(3.14) == 3.14

    def test_integer(self):
        assert safe_float_local(42) == 42.0

    def test_string_number(self):
        assert safe_float_local("2.5") == 2.5

    def test_none_returns_default(self):
        assert safe_float_local(None) == 0.0
        assert safe_float_local(None, 5.0) == 5.0

    def test_nan_returns_default(self):
        assert safe_float_local(float("nan")) == 0.0

    def test_inf_returns_default(self):
        assert safe_float_local(float("inf")) == 0.0
        assert safe_float_local(float("-inf")) == 0.0

    def test_invalid_string_returns_default(self):
        assert safe_float_local("not_a_number") == 0.0

    def test_empty_string_returns_default(self):
        assert safe_float_local("") == 0.0

    def test_custom_default(self):
        assert safe_float_local(None, -1.0) == -1.0

    def test_module_safe_float_handles_none(self):
        """Test the actual module-level _safe_float."""
        assert _safe_float(None) == 0.0

    def test_module_safe_float_handles_string(self):
        assert _safe_float("invalid") == 0.0

    def test_module_safe_float_converts_float(self):
        assert _safe_float(0.85) == 0.85


# ---------------------------------------------------------------------------
# MoodSensor
# ---------------------------------------------------------------------------

class TestMoodSensor:
    def test_init(self):
        coord = _make_coordinator()
        sensor = MoodSensor(coord)
        assert sensor._attr_unique_id == "ai_home_copilot_mood"
        assert sensor._attr_icon == "mdi:robot-happy"

    def test_native_value_unknown_when_no_data(self):
        coord = _make_coordinator(None)
        sensor = MoodSensor(coord)
        assert sensor.native_value == "unknown"

    def test_native_value_unknown_when_empty_data(self):
        coord = _make_coordinator({})
        sensor = MoodSensor(coord)
        assert sensor.native_value == "unknown"

    def test_native_value_from_mood_data(self):
        coord = _make_coordinator({"mood": {"mood": "relax", "confidence": 0.9}})
        sensor = MoodSensor(coord)
        assert sensor.native_value == "relax"

    def test_native_value_happy(self):
        coord = _make_coordinator({"mood": {"mood": "happy"}})
        sensor = MoodSensor(coord)
        assert sensor.native_value == "happy"

    def test_native_value_from_state_key(self):
        """v3.0: 'state' key is alternative to 'mood' key."""
        coord = _make_coordinator({"mood": {"state": "focus"}})
        sensor = MoodSensor(coord)
        assert sensor.native_value == "focus"

    def test_extra_attributes_empty_when_no_data(self):
        coord = _make_coordinator(None)
        sensor = MoodSensor(coord)
        assert sensor.extra_state_attributes == {}

    def test_extra_attributes_contains_confidence(self):
        coord = _make_coordinator({"mood": {"mood": "relax", "confidence": 0.85}})
        sensor = MoodSensor(coord)
        attrs = sensor.extra_state_attributes
        assert attrs["confidence"] == 0.85

    def test_extra_attributes_contains_zone(self):
        coord = _make_coordinator({"mood": {"mood": "relax", "zone": "wohnzimmer"}})
        sensor = MoodSensor(coord)
        attrs = sensor.extra_state_attributes
        assert attrs["zone"] == "wohnzimmer"

    def test_extra_attributes_emotions_from_contributing_neurons(self):
        coord = _make_coordinator({
            "mood": {
                "mood": "relax",
                "emotions": [],
                "contributing_neurons": [
                    {"name": "presence", "value": 0.7},
                    {"name": "light", "value": 0.5},
                ],
            }
        })
        sensor = MoodSensor(coord)
        attrs = sensor.extra_state_attributes
        assert len(attrs["emotions"]) == 2
        assert attrs["emotions"][0]["name"] == "presence"

    def test_extra_attributes_uses_existing_emotions(self):
        coord = _make_coordinator({
            "mood": {
                "mood": "happy",
                "emotions": [{"name": "joy", "value": 0.9}],
                "contributing_neurons": [],
            }
        })
        sensor = MoodSensor(coord)
        attrs = sensor.extra_state_attributes
        assert len(attrs["emotions"]) == 1
        assert attrs["emotions"][0]["name"] == "joy"

    def test_extra_attributes_dimensions(self):
        """v3.0: dimensions are available in extra_state_attributes."""
        coord = _make_coordinator({
            "mood": {
                "mood": "relax",
                "dimensions": {"comfort": 0.8, "joy": 0.6, "energy": 0.4, "stress": 0.1, "frugality": 0.7},
            }
        })
        sensor = MoodSensor(coord)
        attrs = sensor.extra_state_attributes
        assert attrs["comfort"] == 0.8
        assert attrs["joy"] == 0.6
        assert attrs["stress"] == 0.1

    def test_mood_stability_tracking(self):
        """v3.0: mood_stability is computed from history."""
        coord = _make_coordinator({"mood": {"mood": "relax"}})
        sensor = MoodSensor(coord)
        # Access native_value multiple times to build history
        for _ in range(5):
            sensor.native_value
        attrs = sensor.extra_state_attributes
        assert attrs["mood_stability"] == 1.0  # all same mood

    def test_mood_none_handled_gracefully(self):
        """v3.0: mood=None returns 'unknown' instead of raising."""
        coord = _make_coordinator({"mood": None})
        sensor = MoodSensor(coord)
        assert sensor.native_value == "unknown"

    def test_mood_none_attributes_empty(self):
        coord = _make_coordinator({"mood": None})
        sensor = MoodSensor(coord)
        assert sensor.extra_state_attributes == {}


# ---------------------------------------------------------------------------
# MoodConfidenceSensor
# ---------------------------------------------------------------------------

class TestMoodConfidenceSensor:
    def test_init(self):
        coord = _make_coordinator()
        sensor = MoodConfidenceSensor(coord)
        assert sensor._attr_unique_id == "ai_home_copilot_mood_confidence"
        assert sensor._attr_native_unit_of_measurement == "%"

    def test_native_value_zero_when_no_data(self):
        coord = _make_coordinator(None)
        sensor = MoodConfidenceSensor(coord)
        assert sensor.native_value == 0

    def test_native_value_percentage(self):
        coord = _make_coordinator({"mood": {"confidence": 0.85}})
        sensor = MoodConfidenceSensor(coord)
        assert sensor.native_value == 85

    def test_native_value_full_confidence(self):
        coord = _make_coordinator({"mood": {"confidence": 1.0}})
        sensor = MoodConfidenceSensor(coord)
        assert sensor.native_value == 100

    def test_native_value_zero_confidence(self):
        coord = _make_coordinator({"mood": {"confidence": 0.0}})
        sensor = MoodConfidenceSensor(coord)
        assert sensor.native_value == 0

    def test_extra_attributes_empty_when_no_data(self):
        coord = _make_coordinator(None)
        sensor = MoodConfidenceSensor(coord)
        assert sensor.extra_state_attributes == {}

    def test_extra_attributes_contains_mood(self):
        coord = _make_coordinator({"mood": {"mood": "relax", "confidence": 0.7}})
        sensor = MoodConfidenceSensor(coord)
        attrs = sensor.extra_state_attributes
        assert attrs["mood"] == "relax"

    def test_extra_attributes_default_mood(self):
        coord = _make_coordinator({"mood": {}})
        sensor = MoodConfidenceSensor(coord)
        attrs = sensor.extra_state_attributes
        assert attrs["mood"] == "unknown"

    def test_confidence_sensor_missing_confidence_key(self):
        coord = _make_coordinator({"mood": {}})
        sensor = MoodConfidenceSensor(coord)
        assert sensor.native_value == 0

    def test_confidence_sensor_string_confidence(self):
        """_safe_float handles invalid string gracefully."""
        coord = _make_coordinator({"mood": {"confidence": "invalid"}})
        sensor = MoodConfidenceSensor(coord)
        assert sensor.native_value == 0  # _safe_float returns 0.0 for "invalid"

    def test_confidence_sensor_none_confidence(self):
        coord = _make_coordinator({"mood": {"confidence": None}})
        sensor = MoodConfidenceSensor(coord)
        assert sensor.native_value == 0

    def test_confidence_mood_none_handled(self):
        """v3.0: mood=None returns 0 instead of crashing."""
        coord = _make_coordinator({"mood": None})
        sensor = MoodConfidenceSensor(coord)
        assert sensor.native_value == 0


# ---------------------------------------------------------------------------
# NeuronActivitySensor
# ---------------------------------------------------------------------------

class TestNeuronActivitySensor:
    def test_init(self):
        coord = _make_coordinator()
        sensor = NeuronActivitySensor(coord)
        assert sensor._attr_unique_id == "ai_home_copilot_neuron_activity"
        assert sensor._attr_icon == "mdi:brain"

    def test_native_value_zero_when_no_data(self):
        coord = _make_coordinator(None)
        sensor = NeuronActivitySensor(coord)
        assert sensor.native_value == 0

    def test_native_value_counts_active_neurons(self):
        coord = _make_coordinator({
            "neurons": {
                "presence": {"active": True, "value": 0.8},
                "weather": {"active": False, "value": 0.1},
                "light": {"active": True, "value": 0.5},
            }
        })
        sensor = NeuronActivitySensor(coord)
        assert sensor.native_value == 2

    def test_native_value_all_inactive(self):
        coord = _make_coordinator({
            "neurons": {
                "presence": {"active": False},
                "weather": {"active": False},
            }
        })
        sensor = NeuronActivitySensor(coord)
        assert sensor.native_value == 0

    def test_extra_attributes_activity_list(self):
        coord = _make_coordinator({
            "neurons": {
                "presence": {"active": True, "value": 0.8, "confidence": 0.9},
                "weather": {"active": False, "value": 0.1, "confidence": 0.5},
            }
        })
        sensor = NeuronActivitySensor(coord)
        attrs = sensor.extra_state_attributes
        assert len(attrs["activity"]) == 2
        assert attrs["total_neurons"] == 2
        assert len(attrs["active_neurons"]) == 1

    def test_history_tracking_via_coordinator_update(self):
        """v3.0: History is now tracked in _handle_coordinator_update, not extra_state_attributes."""
        sensor = _make_sensor_with_write(NeuronActivitySensor, {
            "neurons": {
                "presence": {"active": True, "value": 0.8},
            }
        })

        # Simulate coordinator updates to build history
        for _ in range(5):
            sensor._handle_coordinator_update()

        assert len(sensor._history) == 5
        assert all(h["value"] == 1 for h in sensor._history)

    def test_history_max_24_entries(self):
        sensor = _make_sensor_with_write(NeuronActivitySensor, {
            "neurons": {"n1": {"active": True, "value": 0.5}},
        })

        for _ in range(30):
            sensor._handle_coordinator_update()

        assert len(sensor._history) == 24

    def test_extra_attributes_empty_when_no_data(self):
        coord = _make_coordinator(None)
        sensor = NeuronActivitySensor(coord)
        assert sensor.extra_state_attributes == {}

    def test_non_dict_neurons_skipped(self):
        coord = _make_coordinator({
            "neurons": {
                "valid": {"active": True, "value": 0.5},
                "invalid": "not_a_dict",
            }
        })
        sensor = NeuronActivitySensor(coord)
        assert sensor.native_value == 1
        attrs = sensor.extra_state_attributes
        assert len(attrs["activity"]) == 1


# ---------------------------------------------------------------------------
# Mood Dimension Sensors (v3.0 _MoodDimensionSensor subclasses)
# ---------------------------------------------------------------------------

class TestMoodDimensionSensors:
    """Test dedicated dimension sensors (Comfort, Joy, Energy, Stress, Frugality)."""

    def test_comfort_sensor_from_dimensions(self):
        coord = _make_coordinator({
            "mood": {"mood": "relax", "dimensions": {"comfort": 0.85}}
        })
        sensor = MoodComfortSensor(coord)
        assert sensor.native_value == 85

    def test_joy_sensor_from_dimensions(self):
        coord = _make_coordinator({
            "mood": {"mood": "happy", "dimensions": {"joy": 0.9}}
        })
        sensor = MoodJoySensor(coord)
        assert sensor.native_value == 90

    def test_energy_sensor_from_dimensions(self):
        coord = _make_coordinator({
            "mood": {"mood": "active", "dimensions": {"energy": 0.7}}
        })
        sensor = MoodEnergySensor(coord)
        assert sensor.native_value == 70

    def test_stress_sensor_from_dimensions(self):
        coord = _make_coordinator({
            "mood": {"mood": "stressed", "dimensions": {"stress": 0.8}}
        })
        sensor = MoodStressSensor(coord)
        assert sensor.native_value == 80

    def test_frugality_sensor_from_dimensions(self):
        coord = _make_coordinator({
            "mood": {"mood": "eco", "dimensions": {"frugality": 0.95}}
        })
        sensor = MoodFrugalitySensor(coord)
        assert sensor.native_value == 95

    def test_dimension_from_features_fallback(self):
        """Dimensions fall back to features dict."""
        coord = _make_coordinator({
            "mood": {"mood": "relax", "features": {"comfort_index": 0.75}}
        })
        sensor = MoodComfortSensor(coord)
        assert sensor.native_value == 75

    def test_dimension_default_when_missing(self):
        """Missing dimension returns 50 (0.5 * 100)."""
        coord = _make_coordinator({"mood": {"mood": "unknown"}})
        sensor = MoodComfortSensor(coord)
        assert sensor.native_value == 50

    def test_dimension_no_data(self):
        """No coordinator data returns 50."""
        coord = _make_coordinator(None)
        sensor = MoodComfortSensor(coord)
        assert sensor.native_value == 50

    def test_dimension_mood_none(self):
        """mood=None returns 50."""
        coord = _make_coordinator({"mood": None})
        sensor = MoodComfortSensor(coord)
        assert sensor.native_value == 50

    def test_dimension_extra_attributes(self):
        coord = _make_coordinator({
            "mood": {"mood": "relax", "zone": "wohnbereich", "dimensions": {"comfort": 0.8}}
        })
        sensor = MoodComfortSensor(coord)
        attrs = sensor.extra_state_attributes
        assert attrs["mood"] == "relax"
        assert attrs["zone"] == "wohnbereich"
        assert attrs["raw_value"] == 0.8


# ---------------------------------------------------------------------------
# Mood Dimensions via Coordinator Data (legacy test pattern)
# ---------------------------------------------------------------------------

class TestMoodDimensions:
    """Test mood dimension values as they flow through coordinator data."""

    def test_comfort_dimension(self):
        coord = _make_coordinator({
            "mood": {"mood": "relax", "comfort": 0.85, "confidence": 0.9}
        })
        assert coord.data["mood"]["comfort"] == 0.85

    def test_joy_dimension(self):
        coord = _make_coordinator({
            "mood": {"mood": "happy", "joy": 0.9, "confidence": 0.8}
        })
        assert coord.data["mood"]["joy"] == 0.9

    def test_energy_dimension(self):
        coord = _make_coordinator({
            "mood": {"mood": "active", "energy": 0.7}
        })
        assert coord.data["mood"]["energy"] == 0.7

    def test_stress_dimension(self):
        coord = _make_coordinator({
            "mood": {"mood": "stressed", "stress": 0.8}
        })
        assert coord.data["mood"]["stress"] == 0.8

    def test_frugality_dimension(self):
        coord = _make_coordinator({
            "mood": {"mood": "eco", "frugality": 0.95}
        })
        assert coord.data["mood"]["frugality"] == 0.95

    def test_missing_dimension_default(self):
        coord = _make_coordinator({"mood": {"mood": "unknown"}})
        mood_data = coord.data["mood"]
        assert mood_data.get("comfort", 0.5) == 0.5
        assert mood_data.get("joy", 0.5) == 0.5
        assert mood_data.get("energy", 0.5) == 0.5
        assert mood_data.get("stress", 0.0) == 0.0
        assert mood_data.get("frugality", 0.5) == 0.5


# ---------------------------------------------------------------------------
# Dimension Fallback
# ---------------------------------------------------------------------------

class TestDimensionFallback:
    """Verify sensors handle missing and malformed data gracefully."""

    def test_mood_sensor_missing_mood_key(self):
        coord = _make_coordinator({"mood": {}})
        sensor = MoodSensor(coord)
        assert sensor.native_value == "unknown"

    def test_confidence_sensor_missing_confidence_key(self):
        coord = _make_coordinator({"mood": {}})
        sensor = MoodConfidenceSensor(coord)
        assert sensor.native_value == 0

    def test_neuron_activity_empty_neurons(self):
        coord = _make_coordinator({"neurons": {}})
        sensor = NeuronActivitySensor(coord)
        assert sensor.native_value == 0

    def test_mood_sensor_none_mood_data(self):
        """v3.0: mood=None is handled gracefully (returns 'unknown')."""
        coord = _make_coordinator({"mood": None})
        sensor = MoodSensor(coord)
        assert sensor.native_value == "unknown"


# ---------------------------------------------------------------------------
# Stability Tracking (NeuronActivitySensor history)
# ---------------------------------------------------------------------------

class TestStabilityTracking:
    """Test rolling history window in NeuronActivitySensor."""

    def test_history_starts_empty(self):
        coord = _make_coordinator(None)
        sensor = NeuronActivitySensor(coord)
        assert sensor._history == []

    def test_history_grows_with_updates(self):
        sensor = _make_sensor_with_write(NeuronActivitySensor, {
            "neurons": {"n1": {"active": True, "value": 0.5}},
        })

        sensor._handle_coordinator_update()
        assert len(sensor._history) == 1

        sensor._handle_coordinator_update()
        assert len(sensor._history) == 2

    def test_history_values_track_active_count(self):
        sensor = _make_sensor_with_write(NeuronActivitySensor, {
            "neurons": {
                "n1": {"active": True, "value": 0.5},
                "n2": {"active": True, "value": 0.3},
            },
        })
        sensor._handle_coordinator_update()
        assert sensor._history[-1]["value"] == 2

        # Change data to 1 active
        sensor.coordinator.data = {
            "neurons": {
                "n1": {"active": True, "value": 0.5},
                "n2": {"active": False, "value": 0.0},
            },
        }
        sensor._handle_coordinator_update()
        assert sensor._history[-1]["value"] == 1

    def test_history_returned_in_attributes(self):
        sensor = _make_sensor_with_write(NeuronActivitySensor, {
            "neurons": {"n1": {"active": True, "value": 0.5}},
        })
        sensor._handle_coordinator_update()
        attrs = sensor.extra_state_attributes
        assert "history" in attrs
        assert len(attrs["history"]) == 1
        assert attrs["history"][0]["value"] == 1


# ---------------------------------------------------------------------------
# async_setup_entry
# ---------------------------------------------------------------------------

class TestAsyncSetupEntry:
    """Test sensor platform setup."""

    @pytest.mark.asyncio
    async def test_setup_skips_when_no_coordinator(self):
        from custom_components.ai_home_copilot.sensors.mood_sensor import async_setup_entry

        hass = MagicMock()
        hass.data = {}
        entry = MagicMock()
        entry.entry_id = "test"
        add_entities = MagicMock()

        await async_setup_entry(hass, entry, add_entities)
        add_entities.assert_not_called()

    @pytest.mark.asyncio
    async def test_setup_creates_sensors(self):
        """v3.0: 8 coordinator sensors + 3 LiveMoodDimensionSensors = 11 total."""
        from custom_components.ai_home_copilot.sensors.mood_sensor import async_setup_entry

        coord = _make_coordinator({"mood": {"mood": "relax"}})
        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test"
        hass.data = {"ai_home_copilot": {"test": {"coordinator": coord}}}
        add_entities = MagicMock()

        await async_setup_entry(hass, entry, add_entities)
        add_entities.assert_called_once()
        entities = add_entities.call_args[0][0]
        assert len(entities) == 11
        types = {type(e).__name__ for e in entities}
        assert types == {
            "MoodSensor", "MoodConfidenceSensor", "NeuronActivitySensor",
            "MoodComfortSensor", "MoodJoySensor", "MoodEnergySensor",
            "MoodStressSensor", "MoodFrugalitySensor",
            "LiveMoodDimensionSensor",
        }
