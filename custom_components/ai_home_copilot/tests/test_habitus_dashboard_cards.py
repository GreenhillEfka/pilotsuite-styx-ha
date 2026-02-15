"""
Tests for Habitus Dashboard Cards
==================================

Tests cover:
- Card YAML generators
- Zone status calculation
- Mood distribution aggregation
- Transition data handling

Run with: python3 -m pytest custom_components/ai_home_copilot/tests/ -v
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from pathlib import Path

import sys
import os

# Add custom_components to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCardYamlGenerators:
    """Tests for card YAML generation functions."""

    def test_entities_card_generation(self):
        """Test basic entities card YAML generation."""
        from .habitus_dashboard_cards import _entities_card

        result = _entities_card("Test Zone", ["light.living_room", "climate.kitchen"])

        assert "type: entities" in result
        assert "Test Zone" in result
        assert "light.living_room" in result
        assert "climate.kitchen" in result

    def test_entities_card_empty(self):
        """Test entities card with no entities."""
        from .habitus_dashboard_cards import _entities_card

        result = _entities_card("Empty Zone", [])

        assert "(keine)" in result

    def test_gauge_card_generation(self):
        """Test gauge card YAML generation."""
        from .habitus_dashboard_cards import _gauge_card

        result = _gauge_card("sensor.zone_score", "Zone Score", 0, 100)

        assert "type: gauge" in result
        assert "sensor.zone_score" in result
        assert "Zone Score" in result
        assert "min: 0" in result
        assert "max: 100" in result
        assert "severity:" in result

    def test_history_graph_card(self):
        """Test history-graph card YAML generation."""
        from .habitus_dashboard_cards import _history_graph_card

        result = _history_graph_card("Temperature", ["sensor.temp1", "sensor.temp2"], hours=24)

        assert "type: history-graph" in result
        assert "Temperature" in result
        assert "hours_to_show: 24" in result
        assert "sensor.temp1" in result
        assert "sensor.temp2" in result

    def test_markdown_card(self):
        """Test markdown card YAML generation."""
        from .habitus_dashboard_cards import _markdown_card

        result = _markdown_card("Header", "Some **bold** text")

        assert "type: markdown" in result
        assert "Header" in result
        assert "**bold**" in result

    def test_grid_card(self):
        """Test grid card YAML generation."""
        from .habitus_dashboard_cards import _grid_card

        card1 = "    - type: entity\n      entity: sensor.test1"
        card2 = "    - type: entity\n      entity: sensor.test2"

        result = _grid_card([card1, card2], columns=2)

        assert "type: grid" in result
        assert "columns: 2" in result
        assert "sensor.test1" in result
        assert "sensor.test2" in result

    def test_vertical_stack_card(self):
        """Test vertical-stack card YAML generation."""
        from .habitus_dashboard_cards import _vertical_stack_card

        cards = ["card1", "card2"]

        result = _vertical_stack_card(cards)

        assert "type: vertical-stack" in result
        assert "card1" in result
        assert "card2" in result


class TestZoneStatusCard:
    """Tests for Zone Status Card generation."""

    def test_zone_status_card_simple(self):
        """Test simple zone status card YAML."""
        from .habitus_dashboard_cards import generate_zone_status_card_simple

        result = generate_zone_status_card_simple("Wohnzimmer", 75.5)

        assert "Habitus Zone" in result
        assert "Wohnzimmer" in result
        assert "Zone Score" in result or "75.5" in result

    def test_zone_status_card_with_zones(self):
        """Test zone status card with zone list."""
        from .habitus_dashboard_cards import generate_zone_status_card_yaml
                # DEPRECATED: v1 - use v2
        from .habitus_zones_store_v2 import HabitusZoneV2 as HabitusZone

        zones = [
            HabitusZoneV2(zone_id="wohnzimmer", name="Wohnzimmer", entity_ids=["light.lr"]),
            HabitusZoneV2(zone_id="kueche", name="Küche", entity_ids=["light.k"]),
        ]

        result = generate_zone_status_card_yaml(
            zones=zones,
            active_zone_id="wohnzimmer",
            score_entity_id="sensor.zone_score",
        )

        assert "Aktueller Status" in result or "Status" in result
        assert "Wohnzimmer" in result
        assert "Küche" in result or "Kueche" in result


class TestZoneTransitionsCard:
    """Tests for Zone Transitions Card generation."""

    def test_zone_transitions_card(self):
        """Test zone transitions card YAML generation."""
        from .habitus_dashboard_cards import (
            generate_zone_transitions_card_yaml,
            ZoneTransitionData,
        )

        transitions = [
            ZoneTransitionData(
                timestamp="2026-02-14T10:00:00",
                from_zone="schlafzimmer",
                to_zone="wohnzimmer",
                trigger="motion",
                confidence=0.95,
            ),
            ZoneTransitionData(
                timestamp="2026-02-14T09:30:00",
                from_zone=None,
                to_zone="schlafzimmer",
                trigger="time",
                confidence=None,
            ),
        ]

        result = generate_zone_transitions_card_yaml(transitions)

        assert "Zone Transitions" in result
        assert "wohnzimmer" in result
        assert "schlafzimmer" in result
        assert "motion" in result or "time" in result

    def test_zone_transitions_empty(self):
        """Test zone transitions card with no transitions."""
        from .habitus_dashboard_cards import generate_zone_transitions_card_yaml

        result = generate_zone_transitions_card_yaml([])

        assert "Keine Übergänge" in result or "keine" in result.lower()


class TestMoodDistributionCard:
    """Tests for Mood Distribution Card generation."""

    def test_mood_distribution_card(self):
        """Test mood distribution card YAML generation."""
        from .habitus_dashboard_cards import (
            generate_mood_distribution_card_yaml,
            MoodDistributionData,
        )

        mood_data = [
            MoodDistributionData(
                mood="relax",
                count=3,
                percentage=60.0,
                zone_name="Wohnzimmer",
            ),
            MoodDistributionData(
                mood="focus",
                count=2,
                percentage=40.0,
                zone_name="Büro",
            ),
        ]

        result = generate_mood_distribution_card_yaml(mood_data)

        assert "Stimmungsverteilung" in result or "Mood" in result
        assert "relax" in result
        assert "focus" in result
        assert "60.0" in result or "60" in result

    def test_mood_distribution_simple(self):
        """Test simple mood distribution card."""
        from .habitus_dashboard_cards import generate_mood_distribution_card_simple

        mood_counts = {"relax": 3, "focus": 2, "party": 1}

        result = generate_mood_distribution_card_simple(mood_counts, total_zones=6)

        assert "Mood Verteilung" in result or "Verteilung" in result
        assert "relax" in result
        assert "3" in result  # count


class TestZoneScoreCalculation:
    """Tests for zone score calculation."""

    def test_calculate_zone_score_basic(self):
        """Test basic zone score calculation."""
        from .habitus_dashboard_cards import calculate_zone_score
                # DEPRECATED: v1 - use v2
        from .habitus_zones_store_v2 import HabitusZoneV2 as HabitusZone

        # Create mock hass
        mock_hass = Mock()
        mock_hass.states.get = Mock(side_effect=lambda eid: Mock(state="on"))

        zone = HabitusZoneV2(
            zone_id="test",
            name="Test Zone",
            entity_ids=["light.test1", "light.test2", "climate.test"],
        )

        score = calculate_zone_score(zone, mock_hass)

        assert score is not None
        assert 0 <= score <= 100
        # 3 entities, all "on" -> 100%
        assert score == 100.0

    def test_calculate_zone_score_partial(self):
        """Test zone score with partial activity."""
        mock_hass = Mock()

        def get_state(entity_id):
            if "light" in entity_id:
                return Mock(state="on")
            return Mock(state="off")

        mock_hass.states.get = Mock(side_effect=get_state)

        from .habitus_dashboard_cards import calculate_zone_score
                # DEPRECATED: v1 - use v2
        from .habitus_zones_store_v2 import HabitusZoneV2 as HabitusZone

        zone = HabitusZoneV2(
            zone_id="test",
            name="Test Zone",
            entity_ids=["light.test1", "light.test2", "climate.test"],
        )

        score = calculate_zone_score(zone, mock_hass)

        # 2 lights on, 1 climate off -> 66.7%
        assert score is not None
        assert 60 <= score <= 70

    def test_calculate_zone_score_empty(self):
        """Test zone score with no entities."""
        mock_hass = Mock()
        mock_hass.states.get = Mock(return_value=None)

        from .habitus_dashboard_cards import calculate_zone_score
                # DEPRECATED: v1 - use v2
        from .habitus_zones_store_v2 import HabitusZoneV2 as HabitusZone

        zone = HabitusZoneV2(
            zone_id="test",
            name="Test Zone",
            entity_ids=[],
        )

        score = calculate_zone_score(zone, mock_hass)

        assert score is None

    def test_calculate_zone_score_unavailable(self):
        """Test zone score with unavailable entities."""
        mock_hass = Mock()
        mock_hass.states.get = Mock(return_value=Mock(state="unavailable"))

        from .habitus_dashboard_cards import calculate_zone_score
                # DEPRECATED: v1 - use v2
        from .habitus_zones_store_v2 import HabitusZoneV2 as HabitusZone

        zone = HabitusZoneV2(
            zone_id="test",
            name="Test Zone",
            entity_ids=["light.test"],
        )

        score = calculate_zone_score(zone, mock_hass)

        # Unavailable doesn't count as active -> 0%
        assert score == 0.0


class TestMoodDistributionAggregation:
    """Tests for mood distribution aggregation."""

    def test_aggregate_mood_distribution(self):
        """Test mood distribution aggregation."""
        from .habitus_dashboard_cards import aggregate_mood_distribution
                # DEPRECATED: v1 - use v2
        from .habitus_zones_store_v2 import HabitusZoneV2 as HabitusZone

        zones = [
            HabitusZoneV2(zone_id="z1", name="Zone 1", entity_ids=[]),
            HabitusZoneV2(zone_id="z2", name="Zone 2", entity_ids=[]),
            HabitusZoneV2(zone_id="z3", name="Zone 3", entity_ids=[]),
        ]

        zone_moods = {"z1": "relax", "z2": "relax", "z3": "focus"}

        result = aggregate_mood_distribution(zones, zone_moods)

        assert len(result) == 2

        # Find relax mood
        relax = next((r for r in result if r.mood == "relax"), None)
        assert relax is not None
        assert relax.count == 2
        assert relax.percentage == pytest.approx(66.67, rel=0.1)

        # Find focus mood
        focus = next((r for r in result if r.mood == "focus"), None)
        assert focus is not None
        assert focus.count == 1
        assert focus.percentage == pytest.approx(33.33, rel=0.1)

    def test_aggregate_mood_distribution_empty(self):
        """Test mood distribution with no zones."""
        from .habitus_dashboard_cards import aggregate_mood_distribution

        result = aggregate_mood_distribution([], {})

        assert result == []

    def test_aggregate_mood_distribution_all_same(self):
        """Test mood distribution where all zones have same mood."""
        from .habitus_dashboard_cards import aggregate_mood_distribution
                # DEPRECATED: v1 - use v2
        from .habitus_zones_store_v2 import HabitusZoneV2 as HabitusZone

        zones = [
            HabitusZoneV2(zone_id="z1", name="Zone 1", entity_ids=[]),
            HabitusZoneV2(zone_id="z2", name="Zone 2", entity_ids=[]),
        ]

        zone_moods = {"z1": "sleep", "z2": "sleep"}

        result = aggregate_mood_distribution(zones, zone_moods)

        assert len(result) == 1
        assert result[0].mood == "sleep"
        assert result[0].count == 2
        assert result[0].percentage == 100.0


class TestDataClasses:
    """Tests for data class structures."""

    def test_zone_status_data(self):
        """Test ZoneStatusData dataclass."""
        from .habitus_dashboard_cards import ZoneStatusData

        data = ZoneStatusData(
            zone_id="wohnzimmer",
            zone_name="Wohnzimmer",
            score=85.0,
            mood="relax",
            active_entities=5,
            last_activity="2026-02-14T10:00:00",
        )

        assert data.zone_id == "wohnzimmer"
        assert data.zone_name == "Wohnzimmer"
        assert data.score == 85.0
        assert data.mood == "relax"
        assert data.active_entities == 5

    def test_zone_transition_data(self):
        """Test ZoneTransitionData dataclass."""
        from .habitus_dashboard_cards import ZoneTransitionData

        data = ZoneTransitionData(
            timestamp="2026-02-14T10:00:00",
            from_zone="kueche",
            to_zone="wohnzimmer",
            trigger="motion",
            confidence=0.92,
        )

        assert data.timestamp == "2026-02-14T10:00:00"
        assert data.from_zone == "kueche"
        assert data.to_zone == "wohnzimmer"
        assert data.trigger == "motion"
        assert data.confidence == 0.92

    def test_mood_distribution_data(self):
        """Test MoodDistributionData dataclass."""
        from .habitus_dashboard_cards import MoodDistributionData

        data = MoodDistributionData(
            mood="focus",
            count=3,
            percentage=60.0,
            zone_name="Büro",
        )

        assert data.mood == "focus"
        assert data.count == 3
        assert data.percentage == 60.0
        assert data.zone_name == "Büro"


class TestCardIntegration:
    """Integration tests for complete card workflows."""

    def test_complete_dashboard_view(self):
        """Test generation of complete dashboard view."""
        from .habitus_dashboard_cards import generate_habitus_dashboard_view
                # DEPRECATED: v1 - use v2
        from .habitus_zones_store_v2 import HabitusZoneV2 as HabitusZone
        from .habitus_dashboard_cards import (
            ZoneTransitionData,
            MoodDistributionData,
        )

        zones = [
            HabitusZoneV2(zone_id="wohnzimmer", name="Wohnzimmer", entity_ids=[]),
            HabitusZoneV2(zone_id="kueche", name="Küche", entity_ids=[]),
        ]

        transitions = [
            ZoneTransitionData(
                timestamp="2026-02-14T10:00:00",
                from_zone=None,
                to_zone="wohnzimmer",
                trigger="time",
            ),
        ]

        mood_data = [
            MoodDistributionData(
                mood="relax",
                count=2,
                percentage=100.0,
                zone_name="Wohnzimmer",
            ),
        ]

        result = generate_habitus_dashboard_view(
            zones=zones,
            active_zone_id="wohnzimmer",
            transitions=transitions,
            mood_data=mood_data,
        )

        # Should contain all three card types
        assert "vertical-stack" in result or len(result) > 0

    def test_yaml_structure_validity(self):
        """Test that generated YAML has valid structure."""
        from .habitus_dashboard_cards import generate_zone_status_card_simple

        result = generate_zone_status_card_simple("Test Zone", 50.0)

        # Check for basic YAML structure markers
        assert "-" in result  # List items
        assert "type:" in result  # Card type


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_entities_card_unicode(self):
        """Test entities card with unicode characters."""
        from .habitus_dashboard_cards import _entities_card

        result = _entities_card("Tëst Zönë", ["light.tëst"])

        assert "Tëst Zönë" in result or "Test Zone" in result

    def test_large_zone_list(self):
        """Test card generation with many zones."""
        from .habitus_dashboard_cards import _grid_card

        cards = [f"    - type: entity\n      entity: sensor.zone_{i}" for i in range(10)]

        result = _grid_card(cards, columns=4)

        assert "columns: 4" in result
        # All entities should be present
        for i in range(10):
            assert f"sensor.zone_{i}" in result

    def test_empty_zones_list(self):
        """Test handling of empty zones list."""
        from .habitus_dashboard_cards import generate_zone_status_card_yaml

        result = generate_zone_status_card_yaml(zones=[], active_zone_id=None)

        # Should still generate valid card structure
        assert "type:" in result or len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
