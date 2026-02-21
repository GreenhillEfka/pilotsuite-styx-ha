"""Tests for Dashboard Card Generator (v5.6.0)."""

import pytest
import yaml

from custom_components.ai_home_copilot.dashboard.card_generator import (
    generate_energy_overview_card,
    generate_schedule_card,
    generate_sankey_card,
    generate_zone_cards,
    generate_anomaly_card,
    generate_full_dashboard,
    dashboard_to_yaml,
)


HOST = "192.168.1.100"
PORT = 8909


# ═══════════════════════════════════════════════════════════════════════════
# Energy Overview Card
# ═══════════════════════════════════════════════════════════════════════════


class TestEnergyOverviewCard:
    def test_returns_vertical_stack(self):
        card = generate_energy_overview_card(HOST, PORT)
        assert card["type"] == "vertical-stack"

    def test_has_title(self):
        card = generate_energy_overview_card(HOST, PORT)
        assert "Energie" in card["title"]

    def test_has_gauges(self):
        card = generate_energy_overview_card(HOST, PORT)
        # Should have horizontal stack with 2 gauges + 1 power gauge
        assert len(card["cards"]) == 2
        inner = card["cards"][0]
        assert inner["type"] == "horizontal-stack"
        assert len(inner["cards"]) == 2

    def test_power_gauge_max(self):
        card = generate_energy_overview_card(HOST, PORT)
        power_gauge = card["cards"][1]
        assert power_gauge["max"] == 11000

    def test_consumption_severity(self):
        card = generate_energy_overview_card(HOST, PORT)
        cons_gauge = card["cards"][0]["cards"][0]
        assert "severity" in cons_gauge
        assert cons_gauge["severity"]["green"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# Schedule Card
# ═══════════════════════════════════════════════════════════════════════════


class TestScheduleCard:
    def test_returns_vertical_stack(self):
        card = generate_schedule_card(HOST, PORT)
        assert card["type"] == "vertical-stack"

    def test_has_entity_card(self):
        card = generate_schedule_card(HOST, PORT)
        entity_card = card["cards"][0]
        assert entity_card["type"] == "entity"
        assert "schedule" in entity_card["entity"]

    def test_has_markdown_table(self):
        card = generate_schedule_card(HOST, PORT)
        md_card = card["cards"][1]
        assert md_card["type"] == "markdown"
        assert "Tagesplan" in md_card["content"]
        assert "Gesamtkosten" in md_card["content"]

    def test_markdown_uses_jinja(self):
        card = generate_schedule_card(HOST, PORT)
        md = card["cards"][1]["content"]
        assert "state_attr" in md
        assert "{% for" in md


# ═══════════════════════════════════════════════════════════════════════════
# Sankey Card
# ═══════════════════════════════════════════════════════════════════════════


class TestSankeyCard:
    def test_returns_iframe(self):
        card = generate_sankey_card(HOST, PORT)
        assert card["type"] == "iframe"

    def test_url_contains_host(self):
        card = generate_sankey_card(HOST, PORT)
        assert HOST in card["url"]
        assert str(PORT) in card["url"]

    def test_url_has_svg_endpoint(self):
        card = generate_sankey_card(HOST, PORT)
        assert "sankey.svg" in card["url"]
        assert "theme=dark" in card["url"]

    def test_has_aspect_ratio(self):
        card = generate_sankey_card(HOST, PORT)
        assert card["aspect_ratio"] == "16:9"


# ═══════════════════════════════════════════════════════════════════════════
# Zone Cards
# ═══════════════════════════════════════════════════════════════════════════


class TestZoneCards:
    def test_empty_zones_returns_markdown(self):
        card = generate_zone_cards(HOST, PORT, [])
        assert card["type"] == "markdown"
        assert "Keine" in card["content"]

    def test_zones_returns_vertical_stack(self):
        zones = [
            {"zone_id": "kitchen", "zone_name": "Kueche"},
            {"zone_id": "living", "zone_name": "Wohnzimmer"},
        ]
        card = generate_zone_cards(HOST, PORT, zones)
        assert card["type"] == "vertical-stack"
        assert len(card["cards"]) == 2

    def test_zone_card_has_title(self):
        zones = [{"zone_id": "kitchen", "zone_name": "Kueche"}]
        card = generate_zone_cards(HOST, PORT, zones)
        assert card["cards"][0]["title"] == "Kueche"

    def test_zone_card_has_footer_graph(self):
        zones = [{"zone_id": "kitchen", "zone_name": "Kueche"}]
        card = generate_zone_cards(HOST, PORT, zones)
        assert "footer" in card["cards"][0]
        assert card["cards"][0]["footer"]["type"] == "graph"


# ═══════════════════════════════════════════════════════════════════════════
# Anomaly Card
# ═══════════════════════════════════════════════════════════════════════════


class TestAnomalyCard:
    def test_returns_conditional(self):
        card = generate_anomaly_card()
        assert card["type"] == "conditional"

    def test_has_conditions(self):
        card = generate_anomaly_card()
        assert len(card["conditions"]) > 0

    def test_inner_card_is_markdown(self):
        card = generate_anomaly_card()
        assert card["card"]["type"] == "markdown"

    def test_content_mentions_anomalies(self):
        card = generate_anomaly_card()
        assert "Anomalie" in card["card"]["content"]


# ═══════════════════════════════════════════════════════════════════════════
# Full Dashboard
# ═══════════════════════════════════════════════════════════════════════════


class TestFullDashboard:
    def test_has_required_fields(self):
        dash = generate_full_dashboard(HOST, PORT)
        assert "title" in dash
        assert "path" in dash
        assert "icon" in dash
        assert "cards" in dash

    def test_path_is_slug(self):
        dash = generate_full_dashboard(HOST, PORT)
        assert dash["path"] == "pilotsuite-energy"

    def test_default_includes_all_sections(self):
        dash = generate_full_dashboard(HOST, PORT)
        # overview + schedule + sankey + anomalies = 4 cards
        assert len(dash["cards"]) == 4

    def test_exclude_schedule(self):
        dash = generate_full_dashboard(HOST, PORT, include_schedule=False)
        types = [c["type"] for c in dash["cards"]]
        # No entity card for schedule
        assert len(dash["cards"]) == 3

    def test_exclude_sankey(self):
        dash = generate_full_dashboard(HOST, PORT, include_sankey=False)
        types = [c["type"] for c in dash["cards"]]
        assert "iframe" not in types

    def test_exclude_anomalies(self):
        dash = generate_full_dashboard(HOST, PORT, include_anomalies=False)
        types = [c["type"] for c in dash["cards"]]
        assert "conditional" not in types

    def test_with_zones(self):
        zones = [{"zone_id": "kitchen", "zone_name": "Kueche"}]
        dash = generate_full_dashboard(HOST, PORT, zones=zones)
        # overview + schedule + sankey + zones + anomalies = 5
        assert len(dash["cards"]) == 5

    def test_without_zones(self):
        dash = generate_full_dashboard(HOST, PORT, zones=None)
        # No zone cards when no zones
        assert len(dash["cards"]) == 4


# ═══════════════════════════════════════════════════════════════════════════
# YAML Export
# ═══════════════════════════════════════════════════════════════════════════


class TestYAMLExport:
    def test_returns_string(self):
        result = dashboard_to_yaml(HOST, PORT)
        assert isinstance(result, str)

    def test_valid_yaml(self):
        result = dashboard_to_yaml(HOST, PORT)
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)

    def test_has_views(self):
        result = dashboard_to_yaml(HOST, PORT)
        parsed = yaml.safe_load(result)
        assert "views" in parsed
        assert len(parsed["views"]) == 1

    def test_view_has_cards(self):
        result = dashboard_to_yaml(HOST, PORT)
        parsed = yaml.safe_load(result)
        view = parsed["views"][0]
        assert "cards" in view
        assert len(view["cards"]) >= 3

    def test_with_zones(self):
        zones = [
            {"zone_id": "kitchen", "zone_name": "Kueche"},
            {"zone_id": "bath", "zone_name": "Bad"},
        ]
        result = dashboard_to_yaml(HOST, PORT, zones=zones)
        parsed = yaml.safe_load(result)
        assert len(parsed["views"][0]["cards"]) >= 4

    def test_yaml_contains_pilotsuite(self):
        result = dashboard_to_yaml(HOST, PORT)
        assert "pilotsuite" in result.lower() or "PilotSuite" in result
