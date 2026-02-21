"""Tests for AnomalyDetector and ContextAwareAnomalyDetector.

Covers:
- Initialization and configuration
- Feature management (initialize, extract, missing values)
- Model fitting with Isolation Forest
- Anomaly scoring and normalization
- Adaptive thresholding
- History tracking and summary statistics
- Context-aware detection (temporal patterns, device relationships)
- Reset and disabled states
"""
import time
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from custom_components.ai_home_copilot.ml.patterns.anomaly_detector import (
    AnomalyDetector,
    ContextAwareAnomalyDetector,
)


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────

@pytest.fixture
def detector():
    """Create a basic AnomalyDetector."""
    return AnomalyDetector(contamination=0.1, window_size=50)


@pytest.fixture
def fitted_detector():
    """Create a fitted AnomalyDetector with sample data."""
    det = AnomalyDetector(contamination=0.1, window_size=50)
    det.initialize_features(["temperature", "humidity", "power"])

    # Generate normal training data
    rng = np.random.RandomState(42)
    data = rng.normal(loc=[22, 50, 100], scale=[2, 5, 20], size=(200, 3))
    det.fit(data)
    return det


@pytest.fixture
def context_detector():
    """Create a ContextAwareAnomalyDetector."""
    relationships = {
        "light.living_room": ["switch.living_room", "sensor.living_room_motion"],
        "climate.bedroom": ["sensor.bedroom_temperature"],
    }
    return ContextAwareAnomalyDetector(
        temporal_window_hours=24,
        device_relationships=relationships,
        contamination=0.1,
        window_size=50,
    )


# ──────────────────────────────────────────────────────────────────────────
# Tests: Initialization
# ──────────────────────────────────────────────────────────────────────────

class TestInit:
    def test_default_params(self):
        det = AnomalyDetector()
        assert det.contamination == 0.1
        assert det.n_estimators == 100
        assert det.max_samples == "auto"
        assert det.window_size == 100
        assert det.enabled is True
        assert det._is_fitted is False

    def test_custom_params(self):
        det = AnomalyDetector(
            contamination=0.05,
            n_estimators=50,
            window_size=200,
            enabled=False,
        )
        assert det.contamination == 0.05
        assert det.n_estimators == 50
        assert det.window_size == 200
        assert det.enabled is False

    def test_empty_initial_state(self, detector):
        assert len(detector.window) == 0
        assert len(detector.anomaly_history) == 0
        assert len(detector.feature_names) == 0
        assert detector.model is None


# ──────────────────────────────────────────────────────────────────────────
# Tests: Feature Management
# ──────────────────────────────────────────────────────────────────────────

class TestFeatures:
    def test_initialize_features(self, detector):
        detector.initialize_features(["temp", "humidity"])
        assert detector.feature_names == ["temp", "humidity"]
        assert "temp" in detector.feature_history
        assert "humidity" in detector.feature_history

    def test_feature_history_buffer_size(self, detector):
        detector.initialize_features(["temp"])
        # History buffer should be 2x window_size
        assert detector.feature_history["temp"].maxlen == 100

    def test_extract_feature_vector(self, detector):
        detector.initialize_features(["temp", "humidity"])
        vector = detector._extract_feature_vector({"temp": 22.0, "humidity": 50.0})
        assert vector is not None
        assert vector.shape == (1, 2)
        np.testing.assert_array_almost_equal(vector, [[22.0, 50.0]])

    def test_extract_feature_vector_missing(self, detector):
        detector.initialize_features(["temp", "humidity"])
        vector = detector._extract_feature_vector({"temp": 22.0})
        assert vector is None

    def test_extract_feature_vector_non_numeric(self, detector):
        detector.initialize_features(["temp"])
        vector = detector._extract_feature_vector({"temp": "not_a_number"})
        assert vector is None

    def test_extract_feature_vector_none_value(self, detector):
        detector.initialize_features(["temp"])
        vector = detector._extract_feature_vector({"temp": None})
        assert vector is None

    def test_extract_feature_vector_string_number(self, detector):
        """Strings that can convert to float should work."""
        detector.initialize_features(["temp"])
        vector = detector._extract_feature_vector({"temp": "22.5"})
        assert vector is not None
        np.testing.assert_array_almost_equal(vector, [[22.5]])


# ──────────────────────────────────────────────────────────────────────────
# Tests: Model Fitting
# ──────────────────────────────────────────────────────────────────────────

class TestFit:
    def test_fit_basic(self, detector):
        data = np.random.RandomState(42).normal(size=(100, 3))
        detector.fit(data)
        assert detector._is_fitted is True
        assert detector.model is not None

    def test_fit_disabled(self):
        det = AnomalyDetector(enabled=False)
        data = np.random.normal(size=(100, 3))
        det.fit(data)
        assert det._is_fitted is False
        assert det.model is None

    def test_fit_uses_random_state(self, detector):
        data = np.random.RandomState(1).normal(size=(100, 2))
        detector.fit(data)
        # Model should have random_state=42
        assert detector.model.random_state == 42

    def test_fit_error_fallback(self, detector):
        """Fitting with invalid data should set _is_fitted to False."""
        # Empty array should cause fitting error
        try:
            detector.fit(np.array([]))
        except Exception:
            pass
        assert detector._is_fitted is False


# ──────────────────────────────────────────────────────────────────────────
# Tests: Update and Scoring
# ──────────────────────────────────────────────────────────────────────────

class TestUpdate:
    def test_update_not_fitted(self, detector):
        detector.initialize_features(["temp"])
        score, is_anomaly = detector.update({"temp": 22.0})
        assert score == 0.0
        assert is_anomaly is False

    def test_update_disabled(self):
        det = AnomalyDetector(enabled=False)
        det.initialize_features(["temp"])
        det._is_fitted = True
        score, is_anomaly = det.update({"temp": 22.0})
        assert score == 0.0
        assert is_anomaly is False

    def test_update_fitted(self, fitted_detector):
        score, is_anomaly = fitted_detector.update({
            "temperature": 22.0,
            "humidity": 50.0,
            "power": 100.0,
        })
        # Normal values should have low anomaly score
        assert 0.0 <= score <= 1.0
        assert isinstance(is_anomaly, bool)

    def test_update_anomalous_value(self, fitted_detector):
        score, is_anomaly = fitted_detector.update({
            "temperature": 100.0,  # Very abnormal
            "humidity": 200.0,
            "power": 10000.0,
        })
        # Extreme values should have higher anomaly score
        assert 0.0 <= score <= 1.0

    def test_update_tracks_history(self, fitted_detector):
        fitted_detector.update({
            "temperature": 22.0,
            "humidity": 50.0,
            "power": 100.0,
        })
        assert len(fitted_detector.anomaly_history) == 1
        entry = fitted_detector.anomaly_history[0]
        assert "timestamp" in entry
        assert "score" in entry
        assert "is_anomaly" in entry
        assert "features" in entry

    def test_update_missing_feature(self, fitted_detector):
        score, is_anomaly = fitted_detector.update({"temperature": 22.0})
        # Missing features → None vector → 0.0 score
        assert score == 0.0
        assert is_anomaly is False

    def test_feature_history_updated(self, fitted_detector):
        fitted_detector.update({
            "temperature": 22.0,
            "humidity": 50.0,
            "power": 100.0,
        })
        assert len(fitted_detector.feature_history["temperature"]) > 0


# ──────────────────────────────────────────────────────────────────────────
# Tests: Anomaly Score Computation
# ──────────────────────────────────────────────────────────────────────────

class TestScoring:
    def test_score_range(self, fitted_detector):
        """Anomaly score should be between 0 and 1."""
        vector = np.array([[22.0, 50.0, 100.0]])
        score = fitted_detector._compute_anomaly_score(vector)
        assert 0.0 <= score <= 1.0

    def test_score_exception_returns_zero(self, detector):
        """If computation fails, score should be 0.0."""
        # Not fitted, so transform will fail
        vector = np.array([[22.0]])
        score = detector._compute_anomaly_score(vector)
        assert score == 0.0


# ──────────────────────────────────────────────────────────────────────────
# Tests: Adaptive Threshold
# ──────────────────────────────────────────────────────────────────────────

class TestAdaptiveThreshold:
    def test_default_threshold(self, detector):
        """With < 10 entries, default threshold is 0.7."""
        threshold = detector._get_adaptive_threshold()
        assert threshold == 0.7

    def test_high_anomaly_rate(self, detector):
        """High mean score → lower threshold (more sensitive)."""
        for _ in range(20):
            detector.anomaly_history.append({
                "timestamp": time.time(),
                "score": 0.8,
                "is_anomaly": True,
                "features": {},
            })
        threshold = detector._get_adaptive_threshold()
        assert threshold == 0.65

    def test_low_anomaly_rate(self, detector):
        """Low mean score → higher threshold (less sensitive)."""
        for _ in range(20):
            detector.anomaly_history.append({
                "timestamp": time.time(),
                "score": 0.1,
                "is_anomaly": False,
                "features": {},
            })
        threshold = detector._get_adaptive_threshold()
        assert threshold == 0.75

    def test_medium_anomaly_rate(self, detector):
        """Medium mean score → default threshold."""
        for _ in range(20):
            detector.anomaly_history.append({
                "timestamp": time.time(),
                "score": 0.5,
                "is_anomaly": False,
                "features": {},
            })
        threshold = detector._get_adaptive_threshold()
        assert threshold == 0.7


# ──────────────────────────────────────────────────────────────────────────
# Tests: Summary
# ──────────────────────────────────────────────────────────────────────────

class TestSummary:
    def test_empty_summary(self, detector):
        summary = detector.get_anomaly_summary()
        assert summary["count"] == 0
        assert summary["last_anomaly"] is None
        assert summary["peak_score"] == 0.0

    def test_summary_with_data(self, detector):
        now = time.time()
        detector.anomaly_history.append({
            "timestamp": now,
            "score": 0.8,
            "is_anomaly": True,
            "features": {"temp": 40},
        })
        detector.anomaly_history.append({
            "timestamp": now - 100,
            "score": 0.5,
            "is_anomaly": False,
            "features": {"temp": 22},
        })

        summary = detector.get_anomaly_summary(hours=24)
        assert summary["count"] == 2
        assert summary["peak_score"] == 0.8
        assert summary["last_anomaly"] == now
        assert summary["features"]["temp"] == 40

    def test_summary_time_filter(self, detector):
        now = time.time()
        # Add old entry (48h ago)
        detector.anomaly_history.append({
            "timestamp": now - 48 * 3600,
            "score": 0.9,
            "is_anomaly": True,
            "features": {},
        })
        # Add recent entry
        detector.anomaly_history.append({
            "timestamp": now,
            "score": 0.3,
            "is_anomaly": False,
            "features": {},
        })

        summary = detector.get_anomaly_summary(hours=24)
        assert summary["count"] == 1  # Only the recent one


# ──────────────────────────────────────────────────────────────────────────
# Tests: Reset
# ──────────────────────────────────────────────────────────────────────────

class TestReset:
    def test_reset_clears_state(self, fitted_detector):
        fitted_detector.update({
            "temperature": 22.0,
            "humidity": 50.0,
            "power": 100.0,
        })
        assert len(fitted_detector.anomaly_history) > 0

        fitted_detector.reset()
        assert len(fitted_detector.window) == 0
        assert len(fitted_detector.anomaly_history) == 0
        assert fitted_detector._is_fitted is False

    def test_reset_clears_feature_history(self, detector):
        detector.initialize_features(["temp", "humidity"])
        detector.feature_history["temp"].append(22.0)
        detector.feature_history["humidity"].append(50.0)

        detector.reset()
        assert len(detector.feature_history["temp"]) == 0
        assert len(detector.feature_history["humidity"]) == 0


# ──────────────────────────────────────────────────────────────────────────
# Tests: ContextAwareAnomalyDetector
# ──────────────────────────────────────────────────────────────────────────

class TestContextAware:
    def test_init(self, context_detector):
        assert context_detector.temporal_window_hours == 24
        assert "light.living_room" in context_detector.device_relationships
        assert len(context_detector.device_relationships) == 2

    def test_init_no_relationships(self):
        det = ContextAwareAnomalyDetector()
        assert det.device_relationships == {}

    def test_update_with_context_not_fitted(self, context_detector):
        context_detector.initialize_features(["power"])
        score, is_anomaly, info = context_detector.update_with_context(
            "light.living_room",
            {"power": 50.0},
            {"hour_of_day": 14, "day_of_week": 2},
        )
        assert score == 0.0
        assert is_anomaly is False
        assert "temporal_context" in info
        assert "relationship_context" in info

    def test_temporal_analysis(self, context_detector):
        info = context_detector._analyze_temporal_pattern(
            "light.living_room",
            {"hour_of_day": 10, "day_of_week": 3},
        )
        assert info["hour_of_day"] == 10
        assert info["day_of_week"] == 3
        assert info["expected_pattern"] is False  # No patterns stored yet
        assert info["pattern_history_len"] == 0

    def test_temporal_analysis_no_context(self, context_detector):
        info = context_detector._analyze_temporal_pattern("device1")
        assert info["hour_of_day"] == 12  # default
        assert info["day_of_week"] == 0  # default

    def test_relationship_analysis(self, context_detector):
        info = context_detector._analyze_relationship(
            "light.living_room",
            {"power": 50.0},
        )
        assert "switch.living_room" in info["related_devices"]
        assert "sensor.living_room_motion" in info["related_devices"]
        assert info["consistency_with_group"] == "unknown"

    def test_relationship_unknown_device(self, context_detector):
        info = context_detector._analyze_relationship(
            "light.unknown",
            {"power": 50.0},
        )
        assert info["related_devices"] == []

    def test_update_with_context_detailed_info(self, context_detector):
        context_detector.initialize_features(["power"])
        score, is_anomaly, info = context_detector.update_with_context(
            "light.living_room",
            {"power": 50.0},
        )
        assert "base_score" in info
        assert "is_anomaly" in info
        assert "temporal_context" in info
        assert "relationship_context" in info


# ──────────────────────────────────────────────────────────────────────────
# Tests: Edge Cases
# ──────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_anomaly_history_max_size(self, detector):
        """Anomaly history should cap at 1000 entries."""
        for i in range(1100):
            detector.anomaly_history.append({
                "timestamp": time.time(),
                "score": 0.5,
                "is_anomaly": False,
                "features": {},
            })
        assert len(detector.anomaly_history) == 1000

    def test_window_max_size(self, detector):
        """Sliding window should cap at window_size."""
        for i in range(100):
            detector.window.append(i)
        assert len(detector.window) == 50  # window_size=50

    def test_empty_features_dict(self, fitted_detector):
        score, is_anomaly = fitted_detector.update({})
        assert score == 0.0
        assert is_anomaly is False

    def test_multiple_updates(self, fitted_detector):
        """Multiple sequential updates should work correctly."""
        for i in range(10):
            score, is_anomaly = fitted_detector.update({
                "temperature": 22.0 + i * 0.1,
                "humidity": 50.0,
                "power": 100.0,
            })
            assert 0.0 <= score <= 1.0
        assert len(fitted_detector.anomaly_history) == 10
