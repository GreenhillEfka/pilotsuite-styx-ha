"""Tests for the Suggestion Loader Module.

Tests initial JSON loading, event-driven loading, and deduplication.

Run with: pytest tests/test_suggestion_loader.py -v
"""
import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path


class TestSuggestionLoaderHelpers:
    """Tests for SuggestionLoaderModule helper methods."""

    def test_convert_initial_to_suggestion(self):
        """Test converting initial_suggestions.json item to Suggestion format."""
        from custom_components.ai_home_copilot.core.modules.suggestion_loader import (
            SuggestionLoaderModule,
        )

        item = {
            "id": "repair_unavailable_automations",
            "title": "Repair unavailable automations",
            "description": "9 automations are unavailable.",
            "type": "repair",
            "severity": "high",
            "affected_entities": ["automation.test1"],
            "example_yaml": "# fix here",
        }

        result = SuggestionLoaderModule._convert_initial_to_suggestion(item)

        assert result is not None
        assert result["suggestion_id"] == "initial_repair_unavailable_automations"
        assert result["pattern"] == "Repair unavailable automations"
        assert result["confidence"] == 0.7  # high severity
        assert result["source"] == "repair"
        assert result["priority"] == "high"
        assert len(result["evidence"]) == 1

    def test_convert_initial_no_id(self):
        """Test conversion returns None without id."""
        from custom_components.ai_home_copilot.core.modules.suggestion_loader import (
            SuggestionLoaderModule,
        )

        result = SuggestionLoaderModule._convert_initial_to_suggestion({"title": "test"})
        assert result is None

    def test_convert_initial_medium_severity(self):
        """Test conversion with medium severity."""
        from custom_components.ai_home_copilot.core.modules.suggestion_loader import (
            SuggestionLoaderModule,
        )

        item = {"id": "test", "title": "Test", "severity": "medium"}
        result = SuggestionLoaderModule._convert_initial_to_suggestion(item)
        assert result["confidence"] == 0.5
        assert result["priority"] == "medium"

    def test_convert_analysis_to_suggestion(self):
        """Test converting ImprovementSuggestion to Suggestion format."""
        from custom_components.ai_home_copilot.core.modules.suggestion_loader import (
            SuggestionLoaderModule,
        )

        item = {
            "zone_id": "wohnbereich",
            "suggestion_type": "missing_motion_light",
            "title": "Automatisches Licht bei Bewegung (wohnbereich)",
            "description": "Zone hat Bewegungssensoren und Lichter.",
            "example_yaml": "trigger:\n  - platform: state\n    entity_id: sensor.motion",
        }

        result = SuggestionLoaderModule._convert_analysis_to_suggestion(item)

        assert result is not None
        assert result["suggestion_id"] == "analysis_wohnbereich_missing_motion_light"
        assert result["source"] == "automation_analysis"
        assert result["zone_id"] == "wohnbereich"
        assert len(result["evidence"]) == 1

    def test_convert_analysis_no_title(self):
        """Test conversion returns None without title."""
        from custom_components.ai_home_copilot.core.modules.suggestion_loader import (
            SuggestionLoaderModule,
        )

        result = SuggestionLoaderModule._convert_analysis_to_suggestion({"zone_id": "test"})
        assert result is None

    def test_deduplication(self):
        """Test that duplicate patterns are rejected."""
        from custom_components.ai_home_copilot.core.modules.suggestion_loader import (
            SuggestionLoaderModule,
        )

        loader = SuggestionLoaderModule()
        loader._loaded_patterns.add("Test Pattern")

        suggestion = {"pattern": "Test Pattern"}
        assert not loader._is_new(suggestion)

        suggestion2 = {"pattern": "New Pattern"}
        assert loader._is_new(suggestion2)

    def test_dedup_empty_pattern(self):
        """Test that empty patterns are rejected."""
        from custom_components.ai_home_copilot.core.modules.suggestion_loader import (
            SuggestionLoaderModule,
        )

        loader = SuggestionLoaderModule()
        assert not loader._is_new({"pattern": ""})

    def test_get_store_returns_none(self):
        """Test _get_store returns None when store not available."""
        from custom_components.ai_home_copilot.core.modules.suggestion_loader import (
            SuggestionLoaderModule,
        )

        hass = MagicMock()
        hass.data = {}
        result = SuggestionLoaderModule._get_store(hass, "test_entry")
        assert result is None

    def test_get_store_returns_store(self):
        """Test _get_store returns the suggestion store."""
        from custom_components.ai_home_copilot.core.modules.suggestion_loader import (
            SuggestionLoaderModule,
        )

        store = MagicMock()
        hass = MagicMock()
        hass.data = {
            "ai_home_copilot": {
                "test_entry": {"suggestion_store": store}
            }
        }
        result = SuggestionLoaderModule._get_store(hass, "test_entry")
        assert result is store

    def test_severity_to_priority_mapping(self):
        """Test severity to priority mapping."""
        from custom_components.ai_home_copilot.core.modules.suggestion_loader import (
            _SEVERITY_TO_PRIORITY,
        )

        assert _SEVERITY_TO_PRIORITY["critical"] == "high"
        assert _SEVERITY_TO_PRIORITY["high"] == "high"
        assert _SEVERITY_TO_PRIORITY["warning"] == "medium"
        assert _SEVERITY_TO_PRIORITY["medium"] == "medium"
        assert _SEVERITY_TO_PRIORITY["info"] == "low"
        assert _SEVERITY_TO_PRIORITY["low"] == "low"

    def test_read_initial_json_missing_file(self):
        """Test reading initial suggestions when file doesn't exist."""
        from custom_components.ai_home_copilot.core.modules.suggestion_loader import (
            SuggestionLoaderModule,
        )

        with patch.object(Path, "exists", return_value=False):
            result = SuggestionLoaderModule._read_initial_json()
            assert result == {}

    def test_module_name_and_version(self):
        """Test module name and version."""
        from custom_components.ai_home_copilot.core.modules.suggestion_loader import (
            SuggestionLoaderModule,
        )

        loader = SuggestionLoaderModule()
        assert loader.name == "suggestion_loader"
        assert loader.version == "1.0"
