"""Tests for PilotSuite 3-Tab Dashboard Generator.

Covers:
- generate_full_dashboard returns dict with 3 views
- Habitus tab has mood gauges
- Hausverwaltung tab has energy section
- Styx tab has brain graph iframe
- Zone entities come from zones_config.json
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

DOMAIN = "ai_home_copilot"

# Path to the real zones_config.json
_ZONES_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "ai_home_copilot"
    / "data"
    / "zones_config.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_zones() -> list[dict]:
    """Load zone data from the bundled zones_config.json."""
    with open(_ZONES_CONFIG_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("zones", [])


def _find_card_recursive(cards: list[dict], card_type: str) -> list[dict]:
    """Recursively find all cards of a given type."""
    found = []
    for card in cards:
        if card.get("type") == card_type:
            found.append(card)
        # Recurse into nested card containers
        for key in ("cards",):
            if key in card and isinstance(card[key], list):
                found.extend(_find_card_recursive(card[key], card_type))
    return found


# ---------------------------------------------------------------------------
# Tests: generate_full_dashboard
# ---------------------------------------------------------------------------

class TestFullDashboard:
    """Test top-level dashboard generation."""

    def test_returns_dict_with_three_views(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_full_dashboard,
        )

        zones = _load_zones()
        dashboard = generate_full_dashboard(zones=zones)

        assert isinstance(dashboard, dict)
        assert "views" in dashboard
        assert len(dashboard["views"]) == 3

    def test_dashboard_title_is_pilotsuite(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_full_dashboard,
        )

        dashboard = generate_full_dashboard(zones=_load_zones())
        assert dashboard["title"] == "PilotSuite"

    def test_view_paths(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_full_dashboard,
        )

        dashboard = generate_full_dashboard(zones=_load_zones())
        paths = [v["path"] for v in dashboard["views"]]
        assert paths == ["habitus", "hausverwaltung", "styx"]

    def test_auto_loads_zones_config_when_none(self):
        """When zones=None, generate_full_dashboard loads from file."""
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_full_dashboard,
        )

        dashboard = generate_full_dashboard(zones=None)
        assert len(dashboard["views"]) == 3
        # Habitus tab should have zone grid cards (proves zones were loaded)
        habitus = dashboard["views"][0]
        grid_cards = _find_card_recursive(habitus["cards"], "grid")
        assert len(grid_cards) >= 1


# ---------------------------------------------------------------------------
# Tests: Habitus tab (Tab 1)
# ---------------------------------------------------------------------------

class TestHabitusTab:
    """Test Tab 1: Habitus -- Mood gauges, zone grid, persons."""

    def test_has_mood_gauges(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_habitus_tab,
        )

        zones = _load_zones()
        tab = generate_habitus_tab(zones)

        # First card should be the mood gauge horizontal-stack
        gauge_stack = tab["cards"][0]
        assert gauge_stack["type"] == "horizontal-stack"

        gauges = _find_card_recursive(gauge_stack["cards"], "gauge")
        assert len(gauges) == 3

        gauge_entities = {g["entity"] for g in gauges}
        assert "sensor.ai_home_copilot_mood_comfort" in gauge_entities
        assert "sensor.ai_home_copilot_mood_joy" in gauge_entities
        assert "sensor.ai_home_copilot_mood_frugality" in gauge_entities

    def test_has_zone_grid_cards(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_habitus_tab,
        )

        zones = _load_zones()
        tab = generate_habitus_tab(zones)

        grid_cards = _find_card_recursive(tab["cards"], "grid")
        assert len(grid_cards) >= 1, "Habitus tab should contain zone grid cards"

    def test_has_persons_card(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_habitus_tab,
        )

        zones = _load_zones()
        tab = generate_habitus_tab(zones)

        entity_cards = _find_card_recursive(tab["cards"], "entities")
        person_entities = set()
        for card in entity_cards:
            for ent in card.get("entities", []):
                eid = ent if isinstance(ent, str) else ent.get("entity", "")
                if eid.startswith("person."):
                    person_entities.add(eid)

        assert "person.andreas" in person_entities

    def test_has_temperature_history(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_habitus_tab,
        )

        zones = _load_zones()
        tab = generate_habitus_tab(zones)

        history_cards = _find_card_recursive(tab["cards"], "history-graph")
        temp_histories = [
            c for c in history_cards if "Raumtemperaturen" in c.get("title", "")
        ]
        assert len(temp_histories) == 1
        assert len(temp_histories[0]["entities"]) >= 5  # Most zones have temp sensors


# ---------------------------------------------------------------------------
# Tests: Hausverwaltung tab (Tab 2)
# ---------------------------------------------------------------------------

class TestHausverwaltungTab:
    """Test Tab 2: Hausverwaltung -- Energy, heating, security."""

    def test_has_energy_section(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_hausverwaltung_tab,
        )

        tab = generate_hausverwaltung_tab()

        # Find energy-related entity cards
        all_entities = []
        for card in tab["cards"]:
            entity_cards = _find_card_recursive([card], "entity")
            for ec in entity_cards:
                all_entities.append(ec.get("entity", ""))

        energy_entities = [e for e in all_entities if "electric_consumption" in e or "electric_production" in e]
        assert len(energy_entities) >= 2, "Hausverwaltung should have energy consumption + production entities"

    def test_has_heating_section(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_hausverwaltung_tab,
        )

        tab = generate_hausverwaltung_tab()

        # Look for heating-related cards by title
        heating_sections = [
            c for c in tab["cards"]
            if "Heizung" in c.get("title", "")
        ]
        assert len(heating_sections) >= 1

    def test_has_security_section(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_hausverwaltung_tab,
        )

        tab = generate_hausverwaltung_tab()

        security_sections = [
            c for c in tab["cards"]
            if "Sicherheit" in c.get("title", "")
        ]
        assert len(security_sections) >= 1

    def test_has_weather_card(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_hausverwaltung_tab,
        )

        tab = generate_hausverwaltung_tab()

        weather_cards = [
            c for c in tab["cards"] if c.get("type") == "weather-forecast"
        ]
        assert len(weather_cards) == 1


# ---------------------------------------------------------------------------
# Tests: Styx tab (Tab 3)
# ---------------------------------------------------------------------------

class TestStyxTab:
    """Test Tab 3: Styx -- Neural pipeline, brain graph, suggestions."""

    def test_has_brain_graph_iframe(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_styx_tab,
        )

        tab = generate_styx_tab()

        iframe_cards = _find_card_recursive(tab["cards"], "iframe")
        assert len(iframe_cards) >= 1

        brain_iframe = iframe_cards[0]
        assert "/brain_graph/" in brain_iframe["url"]

    def test_has_neural_pipeline_section(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_styx_tab,
        )

        tab = generate_styx_tab()

        pipeline_sections = [
            c for c in tab["cards"]
            if "Neural Pipeline" in c.get("title", "")
        ]
        assert len(pipeline_sections) >= 1

    def test_has_mood_history_graphs(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_styx_tab,
        )

        tab = generate_styx_tab()

        history_cards = _find_card_recursive(tab["cards"], "history-graph")
        assert len(history_cards) >= 2  # Comfort + Joy

    def test_has_suggestion_section(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_styx_tab,
        )

        tab = generate_styx_tab()

        suggestion_sections = [
            c for c in tab["cards"]
            if "Vorschlaege" in c.get("title", "")
        ]
        assert len(suggestion_sections) >= 1

    def test_has_system_status_section(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_styx_tab,
        )

        tab = generate_styx_tab()

        status_sections = [
            c for c in tab["cards"]
            if "System Status" in c.get("title", "")
        ]
        assert len(status_sections) >= 1


# ---------------------------------------------------------------------------
# Tests: Zone entities from zones_config.json
# ---------------------------------------------------------------------------

class TestZoneEntitiesIntegration:
    """Verify zone entities in dashboard come from zones_config.json."""

    def test_zone_card_contains_real_entities(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_habitus_tab,
        )

        zones = _load_zones()
        tab = generate_habitus_tab(zones)

        # Collect all entity IDs referenced in the Habitus tab
        all_entity_ids = set()
        entity_cards = _find_card_recursive(tab["cards"], "entities")
        for card in entity_cards:
            for ent in card.get("entities", []):
                eid = ent if isinstance(ent, str) else ent.get("entity", "")
                if eid and not eid.startswith("person."):
                    all_entity_ids.add(eid)

        # Collect all entity IDs from zones_config.json
        zone_entity_ids = set()
        for zone in zones:
            for role_ents in zone.get("entities", {}).values():
                zone_entity_ids.update(role_ents)

        # Entities in the dashboard that come from zones should be a subset
        matched = all_entity_ids & zone_entity_ids
        assert len(matched) >= 5, (
            f"Expected at least 5 zone entities in Habitus tab, found {len(matched)}"
        )

    def test_nine_zone_cards_in_grid(self):
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_habitus_tab,
        )

        zones = _load_zones()
        assert len(zones) == 9
        tab = generate_habitus_tab(zones)

        # Count vertical-stack cards inside grids (each zone is a vertical-stack)
        grid_cards = _find_card_recursive(tab["cards"], "grid")
        zone_card_count = 0
        for grid in grid_cards:
            for inner in grid.get("cards", []):
                if inner.get("type") == "vertical-stack":
                    zone_card_count += 1

        assert zone_card_count == 9, (
            f"Expected 9 zone cards in grid, got {zone_card_count}"
        )
