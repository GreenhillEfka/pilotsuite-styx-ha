"""Tests for Habitus Zones Dashboard Config Flow Integration."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


class TestHabitusZonesDashboardConfigFlow:
    """Test suite for Habitus Zones Dashboard UI features."""

    def test_strings_json_valid(self):
        """Verify strings.json is valid JSON with React-first habitus menu."""
        with open("custom_components/ai_home_copilot/strings.json", "r") as f:
            data = json.load(f)
        assert "options" in data
        assert "step" in data["options"]
        # Legacy dashboard steps still exist as optional/manual actions.
        assert "generate_dashboard" in data["options"]["step"]
        assert "publish_dashboard" in data["options"]["step"]
        # Habitus menu now points to dashboard info (React/Core-first mode).
        habitus_zones = data["options"]["step"]["habitus_zones"]
        menu_opts = habitus_zones.get("menu_options", {})
        assert "dashboard_info" in menu_opts

    def test_config_flow_imports(self):
        """Verify legacy dashboard helper imports still exist for optional flow."""
        with open("custom_components/ai_home_copilot/config_options_flow.py", "r") as f:
            content = f.read()
        assert "async_generate_habitus_zones_dashboard" in content
        assert "async_publish_last_habitus_dashboard" in content

    def test_generate_dashboard_step_exists(self):
        """Verify async_step_generate_dashboard is defined."""
        with open("custom_components/ai_home_copilot/config_options_flow.py", "r") as f:
            content = f.read()
        assert "async_step_generate_dashboard" in content

    def test_publish_dashboard_step_exists(self):
        """Verify async_step_publish_dashboard is defined."""
        with open("custom_components/ai_home_copilot/config_options_flow.py", "r") as f:
            content = f.read()
        assert "async_step_publish_dashboard" in content

    def test_habitus_zones_menu_updated(self):
        """Verify habitus_zones menu uses dashboard_info entry."""
        with open("custom_components/ai_home_copilot/config_options_flow.py", "r") as f:
            content = f.read()
        assert '"dashboard_info"' in content


class TestHabitusZonesDashboardErrors:
    """Test error handling for dashboard config flow."""

    def test_error_keys_exist(self):
        """Verify error keys are defined in strings.json."""
        with open("custom_components/ai_home_copilot/strings.json", "r") as f:
            data = json.load(f)
        # Dashboard error keys are under options.error (options flow)
        errors = data.get("options", {}).get("error", {})
        assert "generation_failed" in errors
        assert "publish_failed" in errors
        assert "no_dashboard_generated" in errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
