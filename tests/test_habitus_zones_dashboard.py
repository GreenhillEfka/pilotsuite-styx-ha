"""Tests for Habitus Zones Dashboard Config Flow Integration."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


class TestHabitusZonesDashboardConfigFlow:
    """Test suite for Habitus Zones Dashboard UI features."""

    def test_strings_json_valid(self):
        """Verify strings.json is valid JSON."""
        with open("custom_components/ai_home_copilot/strings.json", "r") as f:
            data = json.load(f)
        assert "config" in data
        assert "step" in data["config"]
        # Verify new dashboard steps exist
        assert "generate_dashboard" in data["config"]["step"]
        assert "publish_dashboard" in data["config"]["step"]
        # Verify menu_options include dashboard actions
        habitus_zones = data["config"]["step"]["habitus_zones"]
        menu_opts = habitus_zones.get("menu_options", {})
        assert "generate_dashboard" in menu_opts
        assert "publish_dashboard" in menu_opts

    def test_config_flow_imports(self):
        """Verify config_flow.py imports habitus_dashboard correctly."""
        # The config_flow should import from habitus_dashboard
        with open("custom_components/ai_home_copilot/config_flow.py", "r") as f:
            content = f.read()
        assert "async_generate_habitus_zones_dashboard" in content
        assert "async_publish_last_habitus_dashboard" in content

    def test_generate_dashboard_step_exists(self):
        """Verify async_step_generate_dashboard is defined."""
        with open("custom_components/ai_home_copilot/config_flow.py", "r") as f:
            content = f.read()
        assert "async_step_generate_dashboard" in content

    def test_publish_dashboard_step_exists(self):
        """Verify async_step_publish_dashboard is defined."""
        with open("custom_components/ai_home_copilot/config_flow.py", "r") as f:
            content = f.read()
        assert "async_step_publish_dashboard" in content

    def test_habitus_zones_menu_updated(self):
        """Verify habitus_zones menu includes dashboard options."""
        with open("custom_components/ai_home_copilot/config_flow.py", "r") as f:
            content = f.read()
        # Menu should include both dashboard options
        assert '"generate_dashboard"' in content
        assert '"publish_dashboard"' in content


class TestHabitusZonesDashboardErrors:
    """Test error handling for dashboard config flow."""

    def test_error_keys_exist(self):
        """Verify error keys are defined in strings.json."""
        with open("custom_components/ai_home_copilot/strings.json", "r") as f:
            data = json.load(f)
        # Error keys are under config.error, not top-level error
        errors = data.get("config", {}).get("error", {})
        assert "generation_failed" in errors
        assert "publish_failed" in errors
        assert "no_dashboard_generated" in errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
