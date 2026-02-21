"""Tests for EnergyContextModule frugality scoring (v5.0.0)."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from custom_components.ai_home_copilot.core.modules.energy_context_module import (
    EnergyContextModule,
    FrugalityMoodFactor,
)


@pytest.fixture
def energy_module():
    return EnergyContextModule()


def _make_coordinator(
    consumption=5.0,
    production=0.0,
    baseline=10.0,
    power=500,
    peak=1000,
    anomalies=0,
    shifting=None,
):
    """Create a mock coordinator with energy data."""
    coord = MagicMock()
    data = MagicMock()
    data.timestamp = datetime.now()
    data.total_consumption_today_kwh = consumption
    data.total_production_today_kwh = production
    data.current_power_watts = power
    data.peak_power_today_watts = peak
    data.anomalies_detected = anomalies
    data.shifting_opportunities = shifting or []
    data.baseline_kwh = baseline
    coord.data = data
    return coord


# ---------- Module Basics ----------


class TestModuleBasics:

    def test_module_name(self, energy_module):
        assert energy_module.name == "energy_context"

    def test_coordinator_default_none(self, energy_module):
        assert energy_module.coordinator is None

    def test_no_data_returns_none(self, energy_module):
        result = energy_module.get_frugality_mood_factor()
        assert result is None


# ---------- Frugality Scoring ----------


class TestFrugalityScoring:

    def test_frugal_below_baseline(self, energy_module):
        """Consumption well below baseline -> frugal, score > 0.7."""
        energy_module._coordinator = _make_coordinator(
            consumption=3.0, baseline=10.0
        )
        factor = energy_module.get_frugality_mood_factor()
        assert factor is not None
        assert isinstance(factor, FrugalityMoodFactor)
        assert factor.score >= 0.7
        assert factor.mood_type == "frugal"

    def test_wasteful_above_baseline(self, energy_module):
        """Consumption far above baseline -> wasteful, low score."""
        energy_module._coordinator = _make_coordinator(
            consumption=20.0, baseline=10.0
        )
        factor = energy_module.get_frugality_mood_factor()
        assert factor is not None
        assert factor.score < 0.3
        assert factor.mood_type == "wasteful"

    def test_neutral_at_baseline(self, energy_module):
        """Consumption slightly above baseline -> neutral."""
        energy_module._coordinator = _make_coordinator(
            consumption=12.0, baseline=10.0
        )
        factor = energy_module.get_frugality_mood_factor()
        assert factor is not None
        assert factor.mood_type == "neutral"

    def test_zero_baseline(self, energy_module):
        """Zero baseline should return neutral."""
        energy_module._coordinator = _make_coordinator(
            consumption=5.0, baseline=0.0
        )
        factor = energy_module.get_frugality_mood_factor()
        assert factor is not None
        assert factor.score == 0.5
        assert factor.mood_type == "neutral"

    def test_anomalies_in_reasons(self, energy_module):
        """Anomalies should appear in reasons."""
        energy_module._coordinator = _make_coordinator(
            consumption=5.0, baseline=10.0, anomalies=3
        )
        factor = energy_module.get_frugality_mood_factor()
        assert factor is not None
        reason_types = [r["reason"] for r in factor.reasons]
        assert "energy_anomalies" in reason_types

    def test_shifting_in_reasons(self, energy_module):
        """Shifting opportunities should appear in reasons."""
        energy_module._coordinator = _make_coordinator(
            consumption=5.0,
            baseline=10.0,
            shifting=["switch.dishwasher", "switch.dryer"],
        )
        factor = energy_module.get_frugality_mood_factor()
        assert factor is not None
        reason_types = [r["reason"] for r in factor.reasons]
        assert "load_shifting_possible" in reason_types

    def test_score_clamped_0_1(self, energy_module):
        """Score should always be 0.0-1.0."""
        energy_module._coordinator = _make_coordinator(
            consumption=500.0, baseline=10.0
        )
        factor = energy_module.get_frugality_mood_factor()
        assert factor is not None
        assert 0.0 <= factor.score <= 1.0


# ---------- Mood Dict ----------


class TestMoodDict:

    def test_to_mood_dict_structure(self, energy_module):
        """Mood dict should have the standard format."""
        energy_module._coordinator = _make_coordinator(
            consumption=5.0, baseline=10.0
        )
        mood = energy_module.to_mood_dict()
        assert mood is not None
        assert "mood_type" in mood
        assert "value" in mood
        assert "confidence" in mood
        assert "source" in mood
        assert mood["source"] == "energy_context"

    def test_to_mood_dict_none_when_unavailable(self, energy_module):
        mood = energy_module.to_mood_dict()
        assert mood is None


# ---------- Snapshot ----------


class TestSnapshot:

    def test_get_snapshot_when_unavailable(self, energy_module):
        result = energy_module.get_snapshot()
        assert result is None

    def test_get_snapshot_with_coordinator(self, energy_module):
        energy_module._coordinator = _make_coordinator(
            consumption=8.0, baseline=10.0
        )
        result = energy_module.get_snapshot()
        assert result is not None
        assert result["consumption_today_kwh"] == 8.0
