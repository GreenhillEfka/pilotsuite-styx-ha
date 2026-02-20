"""Tests for Home Alerts Module - PilotSuite

Tests alert generation for:
- Battery warnings
- Climate deviations
- System issues
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from custom_components.ai_home_copilot.core.modules.home_alerts_module import (
    HomeAlertsModule,
    Alert,
    HomeAlertsState,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
    BATTERY_WARNING_THRESHOLD,
    BATTERY_CRITICAL_THRESHOLD,
)


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.states.async_all.return_value = []
    hass.data = {"ai_home_copilot": {}}
    return hass


@pytest.fixture
def mock_context(mock_hass):
    """Create a mock ModuleContext."""
    ctx = MagicMock()
    ctx.hass = mock_hass
    ctx.entry_id = "test_entry_123"
    return ctx


@pytest.fixture
def home_alerts_module():
    """Create a HomeAlertsModule instance."""
    return HomeAlertsModule()


class TestAlertDataclass:
    """Test Alert dataclass functionality."""

    def test_alert_creation(self):
        """Test alert creation with all fields."""
        alert = Alert(
            alert_id="battery_test_1",
            category="battery",
            severity=SEVERITY_MEDIUM,
            title="Niedriger Batteriestand",
            message="Device has 15% battery",
            entity_id="sensor.test_battery",
            value=15.0,
        )
        
        assert alert.alert_id == "battery_test_1"
        assert alert.category == "battery"
        assert alert.severity == SEVERITY_MEDIUM
        assert alert.acknowledged is False
        assert len(alert.actions) == 0

    def test_alert_with_actions(self):
        """Test alert creation with actions."""
        alert = Alert(
            alert_id="test_1",
            category="system",
            severity=SEVERITY_LOW,
            title="Test Alert",
            message="Test message",
            actions=[{"action": "acknowledge", "title": "Bestätigen"}],
        )
        
        assert len(alert.actions) == 1
        assert alert.actions[0]["action"] == "acknowledge"


class TestHomeAlertsModule:
    """Test HomeAlertsModule functionality."""

    def test_initial_state(self, home_alerts_module):
        """Test initial module state."""
        state = home_alerts_module.get_state()
        
        assert isinstance(state, HomeAlertsState)
        assert len(state.alerts) == 0
        assert state.health_score == 100
        assert state.alerts_by_category == {"battery": 0, "climate": 0, "presence": 0, "system": 0}

    def test_get_alerts_empty(self, home_alerts_module):
        """Test get_alerts with no alerts."""
        alerts = home_alerts_module.get_alerts()
        assert alerts == []

    def test_get_alerts_filtered_by_category(self, home_alerts_module):
        """Test filtering alerts by category."""
        # Add test alerts
        home_alerts_module._state.alerts = [
            Alert(alert_id="b1", category="battery", severity=SEVERITY_MEDIUM, title="Battery", message="Low"),
            Alert(alert_id="c1", category="climate", severity=SEVERITY_HIGH, title="Climate", message="Warm"),
            Alert(alert_id="b2", category="battery", severity=SEVERITY_CRITICAL, title="Battery2", message="Critical"),
        ]
        
        battery_alerts = home_alerts_module.get_alerts(category="battery")
        assert len(battery_alerts) == 2
        
        climate_alerts = home_alerts_module.get_alerts(category="climate")
        assert len(climate_alerts) == 1

    def test_get_alerts_filtered_by_severity(self, home_alerts_module):
        """Test filtering alerts by severity."""
        home_alerts_module._state.alerts = [
            Alert(alert_id="b1", category="battery", severity=SEVERITY_MEDIUM, title="Battery", message="Low"),
            Alert(alert_id="b2", category="battery", severity=SEVERITY_CRITICAL, title="Battery2", message="Critical"),
        ]
        
        critical_alerts = home_alerts_module.get_alerts(severity=SEVERITY_CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0].alert_id == "b2"

    def test_acknowledge_alert(self, home_alerts_module):
        """Test acknowledging an alert."""
        alert = Alert(alert_id="test_1", category="battery", severity=SEVERITY_LOW, title="Test", message="Test")
        home_alerts_module._state.alerts.append(alert)
        
        result = home_alerts_module.acknowledge_alert("test_1")
        
        assert result is True
        assert alert.acknowledged is True
        
        # Acknowledge non-existent alert
        result = home_alerts_module.acknowledge_alert("nonexistent")
        assert result is False


class TestAlertCounting:
    """Test alert counting and health score calculation."""

    def test_update_alert_counts(self, home_alerts_module):
        """Test alert counting by category."""
        home_alerts_module._state.alerts = [
            Alert(alert_id="b1", category="battery", severity=SEVERITY_LOW, title="Test", message="Test"),
            Alert(alert_id="b2", category="battery", severity=SEVERITY_MEDIUM, title="Test", message="Test"),
            Alert(alert_id="c1", category="climate", severity=SEVERITY_HIGH, title="Test", message="Test"),
            Alert(alert_id="s1", category="system", severity=SEVERITY_LOW, title="Test", message="Test"),
        ]
        
        home_alerts_module._update_alert_counts()
        
        assert home_alerts_module._state.alerts_by_category["battery"] == 2
        assert home_alerts_module._state.alerts_by_category["climate"] == 1
        assert home_alerts_module._state.alerts_by_category["system"] == 1
        assert home_alerts_module._state.alerts_by_category["presence"] == 0

    def test_health_score_deduction(self, home_alerts_module):
        """Test health score deduction based on alert severity."""
        # Add alerts of different severities
        home_alerts_module._state.alerts = [
            Alert(alert_id="c1", category="battery", severity=SEVERITY_CRITICAL, title="Test", message="Test"),
            Alert(alert_id="h1", category="climate", severity=SEVERITY_HIGH, title="Test", message="Test"),
            Alert(alert_id="m1", category="presence", severity=SEVERITY_MEDIUM, title="Test", message="Test"),
            Alert(alert_id="l1", category="system", severity=SEVERITY_LOW, title="Test", message="Test"),
        ]
        
        home_alerts_module._update_health_score()
        
        # Expected: 100 - 15 (critical) - 10 (high) - 5 (medium) - 2 (low) = 68
        assert home_alerts_module._state.health_score == 68

    def test_health_score_with_acknowledged(self, home_alerts_module):
        """Test that acknowledged alerts don't affect health score."""
        home_alerts_module._state.alerts = [
            Alert(alert_id="c1", category="battery", severity=SEVERITY_CRITICAL, title="Test", message="Test"),
            Alert(alert_id="a1", category="climate", severity=SEVERITY_HIGH, title="Test", message="Test"),
        ]
        
        home_alerts_module._update_health_score()
        initial_score = home_alerts_module._state.health_score
        
        # Acknowledge the critical alert
        home_alerts_module.acknowledge_alert("c1")
        home_alerts_module._update_health_score()
        
        # Score should improve (100 - 10 = 90 instead of 100 - 15 - 10 = 75)
        assert home_alerts_module._state.health_score == 90
        assert home_alerts_module._state.health_score > initial_score

    def test_health_score_bounds(self, home_alerts_module):
        """Test health score stays within 0-100 bounds."""
        # Add many critical alerts
        for i in range(20):
            home_alerts_module._state.alerts.append(
                Alert(alert_id=f"c{i}", category="battery", severity=SEVERITY_CRITICAL, title="Test", message="Test")
            )
        
        home_alerts_module._update_health_score()
        
        # Should be capped at 0
        assert home_alerts_module._state.health_score == 0
        
        # Clear all alerts
        home_alerts_module._state.alerts = []
        home_alerts_module._update_health_score()
        
        # Should be capped at 100
        assert home_alerts_module._state.health_score == 100


class TestAlertSorting:
    """Test alert sorting functionality."""

    def test_get_alerts_sorted_by_severity_then_time(self, home_alerts_module):
        """Test alerts are sorted by severity (desc) then creation time (desc)."""
        now = datetime.now()
        
        home_alerts_module._state.alerts = [
            Alert(alert_id="m1", category="presence", severity=SEVERITY_MEDIUM, title="Test", message="Test", created_at=now - timedelta(seconds=10)),
            Alert(alert_id="c1", category="battery", severity=SEVERITY_CRITICAL, title="Test", message="Test", created_at=now - timedelta(seconds=20)),
            Alert(alert_id="h1", category="climate", severity=SEVERITY_HIGH, title="Test", message="Test", created_at=now - timedelta(seconds=15)),
        ]
        
        sorted_alerts = home_alerts_module.get_alerts()
        
        # Should be: c1 (critical), h1 (high), m1 (medium)
        assert sorted_alerts[0].alert_id == "c1"
        assert sorted_alerts[1].alert_id == "h1"
        assert sorted_alerts[2].alert_id == "m1"
