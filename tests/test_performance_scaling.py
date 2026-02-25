"""Tests for PerformanceScalingModule (v5.0.0)."""

import pytest
import time
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.ai_home_copilot.core.modules.performance_scaling import (
    PerformanceScalingModule,
    PerformanceSnapshot,
    DEFAULT_THRESHOLDS,
)


@pytest.fixture
def perf_module():
    return PerformanceScalingModule()


# ---------- Recording ----------


class TestRecording:

    def test_record_api_response(self, perf_module):
        perf_module.record_api_response(150.0)
        perf_module.record_api_response(250.0)
        assert perf_module._request_count == 2
        assert len(perf_module._api_response_times) == 2

    def test_record_api_error(self, perf_module):
        perf_module.record_api_error()
        assert perf_module._error_count == 1
        assert perf_module._request_count == 1

    def test_record_coordinator_update(self, perf_module):
        perf_module.record_coordinator_update(3500.0)
        assert len(perf_module._coordinator_latencies) == 1

    def test_rolling_window_limit(self, perf_module):
        for i in range(600):
            perf_module.record_api_response(float(i))
        assert len(perf_module._api_response_times) == 500


# ---------- Snapshot ----------


class TestSnapshot:

    def test_get_snapshot_empty(self, perf_module):
        snap = perf_module.get_snapshot()
        assert isinstance(snap, PerformanceSnapshot)
        assert snap.request_count == 0
        assert snap.entity_count == 0

    def test_get_snapshot_with_data(self, perf_module):
        perf_module.record_api_response(100.0)
        perf_module.record_api_response(200.0)
        perf_module.record_api_error()
        snap = perf_module.get_snapshot()
        assert snap.request_count == 3
        assert snap.error_count == 1

    def test_snapshot_to_dict(self):
        snap = PerformanceSnapshot(timestamp=1000.0)
        d = snap.to_dict()
        assert "timestamp" in d
        assert "entity_count" in d
        assert d["timestamp"] == 1000.0


# ---------- Percentiles ----------


class TestPercentiles:

    def test_percentiles_empty(self, perf_module):
        p = perf_module.get_percentiles()
        assert p["p50"] == 0
        assert p["count"] == 0

    def test_percentiles_with_data(self, perf_module):
        for i in range(100):
            perf_module.record_api_response(float(i * 10))
        p = perf_module.get_percentiles()
        assert p["p50"] > 0
        assert p["p90"] > p["p50"]
        assert p["count"] == 100


# ---------- Thresholds ----------


class TestThresholds:

    def test_default_thresholds(self, perf_module):
        assert perf_module._thresholds == DEFAULT_THRESHOLDS

    def test_set_threshold(self, perf_module):
        perf_module.set_threshold("api_response_time_ms", 5000)
        assert perf_module._thresholds["api_response_time_ms"] == 5000

    def test_set_invalid_threshold(self, perf_module):
        perf_module.set_threshold("nonexistent", 999)
        assert "nonexistent" not in perf_module._thresholds


# ---------- Alerts ----------


class TestAlerts:

    def test_no_alerts_normal(self, perf_module):
        perf_module.record_api_response(100.0)
        alerts = perf_module._check_alerts()
        assert len(alerts) == 0

    def test_slow_api_alert(self, perf_module):
        for _ in range(10):
            perf_module.record_api_response(5000.0)
        alerts = perf_module._check_alerts()
        alert_types = [a["type"] for a in alerts]
        assert "api_slow" in alert_types

    def test_error_rate_alert(self, perf_module):
        for _ in range(90):
            perf_module.record_api_response(100.0)
        for _ in range(10):
            perf_module.record_api_error()
        alerts = perf_module._check_alerts()
        alert_types = [a["type"] for a in alerts]
        assert "error_rate_high" in alert_types

    def test_coordinator_slow_alert(self, perf_module):
        perf_module.record_coordinator_update(10000.0)
        alerts = perf_module._check_alerts()
        alert_types = [a["type"] for a in alerts]
        assert "coordinator_slow" in alert_types

    @patch(
        "custom_components.ai_home_copilot.core.modules.performance_scaling._LOGGER.warning"
    )
    def test_alert_logging_throttles_duplicates(self, mock_warn, perf_module):
        alert = {"type": "memory_high", "message": "Memory 2048MB exceeds 1536MB"}

        with patch(
            "custom_components.ai_home_copilot.core.modules.performance_scaling.time.time",
            side_effect=[1000.0, 1001.0, 2000.0],
        ):
            perf_module._log_alert(alert)
            perf_module._log_alert(alert)
            perf_module._log_alert(alert)

        assert mock_warn.call_count == 2
        # Final log should include duplicate suppression note.
        assert "suppressed" in str(mock_warn.call_args_list[-1][0][0]).lower()


# ---------- Edge Cases ----------


class TestEdgeCases:

    def test_module_name(self, perf_module):
        assert perf_module.name == "performance_scaling"

    def test_memory_fallback(self, perf_module):
        mem = perf_module._get_memory_mb()
        assert isinstance(mem, float)

    def test_count_entities_no_hass(self, perf_module):
        assert perf_module._count_entities() == 0

    def test_multiple_error_rate(self, perf_module):
        for _ in range(50):
            perf_module.record_api_error()
        assert perf_module._error_count == 50
        assert perf_module._request_count == 50
