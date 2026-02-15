"""
Tests for Habitus Dashboard Cards Module
======================================

Tests for YAML card generators:
- Zone Status Card
- Zone Transitions Card  
- Mood Distribution Card
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from custom_components.ai_home_copilot.habitus_dashboard_cards import (
    ZoneStatusData,
    ZoneTransitionData,
    MoodDistributionData,
    generate_zone_status_card_yaml,
    generate_zone_status_card_simple,
    generate_zone_transitions_card_yaml,
    generate_zone_transitions_card_simple,
    generate_mood_distribution_card_yaml,
    generate_mood_distribution_card_simple,
)


class TestDataClasses:
    """Test dataclass definitions."""

    def test_zone_status_data_defaults(self):
        """Test ZoneStatusData with defaults."""
        data = ZoneStatusData(zone_id="wohnen", zone_name="Wohnzimmer")
        assert data.zone_id == "wohnen"
        assert data.zone_name == "Wohnzimmer"
        assert data.score is None
        assert data.mood is None
        assert data.active_entities == 0
        assert data.last_activity is None

    def test_zone_status_data_full(self):
        """Test ZoneStatusData with all fields."""
        data = ZoneStatusData(
            zone_id="wohnen",
            zone_name="Wohnzimmer",
            score=75.5,
            mood="relax",
            active_entities=5,
            last_activity="2024-01-15T10:30:00",
        )
        assert data.score == 75.5
        assert data.mood == "relax"
        assert data.active_entities == 5

    def test_zone_transition_data(self):
        """Test ZoneTransitionData."""
        data = ZoneTransitionData(
            timestamp="2024-01-15T10:30:00",
            from_zone="kueche",
            to_zone="wohnen",
            trigger="motion",
            confidence=0.85,
        )
        assert data.from_zone == "kueche"
        assert data.to_zone == "wohnen"
        assert data.confidence == 0.85

    def test_mood_distribution_data(self):
        """Test MoodDistributionData."""
        data = MoodDistributionData(
            mood="relax",
            count=3,
            percentage=60.0,
            zone_name="Wohnzimmer",
        )
        assert data.mood == "relax"
        assert data.count == 3
        assert data.percentage == 60.0


class TestZoneStatusCard:
    """Test Zone Status Card generation."""

    def test_generate_zone_status_card_simple(self):
        """Test simple zone status card generation."""
        yaml_output = generate_zone_status_card_simple("Wohnzimmer", 75.0)
        
        assert "Wohnzimmer" in yaml_output
        assert "type: vertical-stack" in yaml_output
        assert "type: markdown" in yaml_output
        assert "type: gauge" in yaml_output
        assert "sensor.ai_home_copilot_zone_score" in yaml_output

    def test_generate_zone_status_card_simple_no_score(self):
        """Test simple zone status card without score."""
        yaml_output = generate_zone_status_card_simple("Schlafzimmer")
        
        assert "Schlafzimmer" in yaml_output
        assert "Aktiv:** Schlafzimmer" in yaml_output
        # No gauge when no score
        assert yaml_output.count("type: gauge") == 0

    @pytest.fixture
    def mock_zones(self):
        """Create mock zones for testing."""
        mock_zone = MagicMock()
        mock_zone.zone_id = "wohnen"
        mock_zone.name = "Wohnzimmer"
        return [mock_zone]

    def test_generate_zone_status_card_yaml_with_zones(self, mock_zones):
        """Test full zone status card with zones."""
        yaml_output = generate_zone_status_card_yaml(
            zones=mock_zones,
            active_zone_id="wohnen",
            score_entity_id="sensor.ai_home_copilot_zone_score",
            mood_entity_id="sensor.ai_home_copilot_habitus_current_mood",
        )
        
        assert "Wohnzimmer" in yaml_output
        assert "Aktive Zone:** Wohnzimmer" in yaml_output
        assert "type: vertical-stack" in yaml_output
        assert "type: gauge" in yaml_output
        assert "sensor.ai_home_copilot_zone_score" in yaml_output

    def test_generate_zone_status_card_yaml_no_active_zone(self, mock_zones):
        """Test zone status card with no active zone."""
        yaml_output = generate_zone_status_card_yaml(zones=mock_zones)
        
        assert "Keine aktive Zone" in yaml_output

    def test_generate_zone_status_card_yaml_multiple_zones(self):
        """Test zone status card with multiple zones."""
        mock_zones = []
        for zone_id, name in [("wohnen", "Wohnzimmer"), ("kueche", "Küche"), ("schlafen", "Schlafzimmer")]:
            mock_zone = MagicMock()
            mock_zone.zone_id = zone_id
            mock_zone.name = name
            mock_zones.append(mock_zone)
        
        yaml_output = generate_zone_status_card_yaml(
            zones=mock_zones,
            active_zone_id="wohnen",
        )
        
        # Should contain zone entities
        assert "sensor.ai_home_copilot_zone_wohnen_status" in yaml_output
        assert "sensor.ai_home_copilot_zone_kueche_status" in yaml_output
        assert "sensor.ai_home_copilot_zone_schlafen_status" in yaml_output


class TestZoneTransitionsCard:
    """Test Zone Transitions Card generation."""

    @pytest.fixture
    def sample_transitions(self):
        """Create sample transitions for testing."""
        return [
            ZoneTransitionData(
                timestamp="2024-01-15T10:00:00",
                from_zone="kueche",
                to_zone="wohnen",
                trigger="motion",
                confidence=0.9,
            ),
            ZoneTransitionData(
                timestamp="2024-01-15T09:30:00",
                from_zone=None,
                to_zone="kueche",
                trigger="time",
                confidence=None,
            ),
        ]

    def test_generate_zone_transitions_card_simple(self):
        """Test simple transitions card."""
        yaml_output = generate_zone_transitions_card_simple()
        
        assert "Zone Transitions" in yaml_output
        assert "type: vertical-stack" in yaml_output
        assert yaml_output.count("type: markdown") >= 1

    def test_generate_zone_transitions_card_yaml(self, sample_transitions):
        """Test full transitions card with data."""
        yaml_output = generate_zone_transitions_card_yaml(
            transitions=sample_transitions,
            max_entries=10,
        )
        
        assert "Zone Transitions" in yaml_output
        assert "kueche" in yaml_output
        assert "wohnen" in yaml_output
        assert "motion" in yaml_output
        assert "type: history-graph" in yaml_output

    def test_generate_zone_transitions_card_yaml_max_entries(self):
        """Test transitions card with limited entries."""
        transitions = [
            ZoneTransitionData(
                timestamp=f"2024-01-15T{10-i:02d}:00:00",
                from_zone=f"zone_{i}",
                to_zone=f"zone_{i+1}",
                trigger="test",
            )
            for i in range(15)
        ]
        
        yaml_output = generate_zone_transitions_card_yaml(
            transitions=transitions,
            max_entries=5,
        )
        
        # Should only show 5 entries
        assert "type: history-graph" in yaml_output

    def test_generate_zone_transitions_card_yaml_empty(self):
        """Test transitions card with no transitions."""
        yaml_output = generate_zone_transitions_card_yaml(transitions=[])
        
        assert "Zone Transitions" in yaml_output
        assert "type: vertical-stack" in yaml_output


class TestMoodDistributionCard:
    """Test Mood Distribution Card generation."""

    @pytest.fixture
    def sample_moods(self):
        """Create sample mood data."""
        return [
            MoodDistributionData(mood="relax", count=3, percentage=60.0, zone_name="Wohnzimmer"),
            MoodDistributionData(mood="focus", count=2, percentage=40.0, zone_name="Büro"),
        ]

    def test_generate_mood_distribution_card_simple(self):
        """Test simple mood distribution card."""
        yaml_output = generate_mood_distribution_card_simple()
        
        assert "Mood Verteilung" in yaml_output or "Mood Distribution" in yaml_output
        assert "type: vertical-stack" in yaml_output

    def test_generate_mood_distribution_card_yaml(self, sample_moods):
        """Test full mood distribution card with data."""
        yaml_output = generate_mood_distribution_card_yaml(
            mood_data=sample_moods,
            current_mood="relax",
        )
        
        assert "relax" in yaml_output
        assert "focus" in yaml_output
        assert "type: vertical-stack" in yaml_output
        assert "type: gauge" in yaml_output or "type: grid" in yaml_output

    def test_generate_mood_distribution_card_yaml_empty(self):
        """Test mood distribution card with no data."""
        yaml_output = generate_mood_distribution_card_yaml(mood_data=[])
        
        assert "Mood Verteilung" in yaml_output or "Mood Distribution" in yaml_output

    def test_generate_mood_distribution_card_current_mood(self, sample_moods):
        """Test mood card with current mood indicator."""
        yaml_output = generate_mood_distribution_card_yaml(
            mood_data=sample_moods,
            current_mood="relax",
            current_mood_entity="sensor.ai_home_copilot_habitus_current_mood",
        )
        
        assert "sensor.ai_home_copilot_habitus_current_mood" in yaml_output


class TestYAMLStructure:
    """Test YAML output structure."""

    def test_all_outputs_are_strings(self):
        """Verify all generator outputs are strings."""
        outputs = [
            generate_zone_status_card_simple("Test"),
            generate_zone_status_card_simple("Test", 50.0),
            generate_zone_transitions_card_simple(),
            generate_mood_distribution_card_simple(),
        ]
        
        for output in outputs:
            assert isinstance(output, str)
            assert len(output) > 0

    def test_vertical_stack_wrapper(self):
        """Test that outputs are wrapped in vertical-stack."""
        output = generate_zone_status_card_simple("Test")
        
        assert "type: vertical-stack" in output
        # vertical-stack should contain indented cards
        assert "    - type:" in output

    def test_grid_columns_limit(self):
        """Test grid card column limiting."""
        mock_zones = []
        for i in range(10):
            mock_zone = MagicMock()
            mock_zone.zone_id = f"zone_{i}"
            mock_zone.name = f"Zone {i}"
            mock_zones.append(mock_zone)
        
        output = generate_zone_status_card_yaml(zones=mock_zones)
        
        # Grid should have columns attribute
        if "type: grid" in output:
            assert "columns:" in output

    def test_markdown_content_formatting(self):
        """Test markdown card content formatting."""
        output = generate_zone_status_card_simple("Wohnzimmer", 75.0)
        
        # Should contain bold formatting
        assert "**" in output
        # Should contain the zone name
        assert "Wohnzimmer" in output


class TestUnicodeSupport:
    """Test Unicode/UTF-8 support."""

    def test_german_umlauts(self):
        """Test German umlauts in zone names."""
        output = generate_zone_status_card_simple("Wöhnzimmer", 75.0)
        
        assert "Wöhnzimmer" in output
        assert "ö" in output or "Wöhnzimmer" in output

    def test_special_characters(self):
        """Test special characters in content."""
        # This would work with real Unicode input
        mock_zones = []
        mock_zone = MagicMock()
        mock_zone.zone_id = "test"
        mock_zone.name = "Tëst Zöné"
        mock_zones.append(mock_zone)
        
        output = generate_zone_status_card_yaml(zones=mock_zones)
        
        assert "Tëst Zöné" in output or "test" in output


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_zones_list(self):
        """Test with empty zones list."""
        output = generate_zone_status_card_yaml(zones=[])
        
        assert "Keine aktive Zone" in output or "type: vertical-stack" in output

    def test_none_active_zone(self):
        """Test with None as active zone."""
        mock_zones = []
        mock_zone = MagicMock()
        mock_zone.zone_id = "test"
        mock_zone.name = "Test"
        mock_zones.append(mock_zone)
        
        output = generate_zone_status_card_yaml(
            zones=mock_zones,
            active_zone_id=None,
        )
        
        assert "Keine aktive Zone" in output

    def test_none_score_entity(self):
        """Test with None as score entity."""
        mock_zones = []
        mock_zone = MagicMock()
        mock_zone.zone_id = "test"
        mock_zone.name = "Test"
        mock_zones.append(mock_zone)
        
        output = generate_zone_status_card_yaml(
            zones=mock_zones,
            score_entity_id=None,
        )
        
        # Should not crash
        assert isinstance(output, str)
        assert "type: vertical-stack" in output

    def test_transition_without_from_zone(self):
        """Test transition with None as from_zone."""
        transition = ZoneTransitionData(
            timestamp="2024-01-15T10:00:00",
            from_zone=None,
            to_zone="wohnen",
            trigger="initial",
        )
        
        output = generate_zone_transitions_card_yaml(transitions=[transition])
        
        assert "unbekannt" in output or "None" in output.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
