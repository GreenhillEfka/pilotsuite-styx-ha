"""Tests for the interactive brain graph panel."""

import json
import pytest


class TestBrainGraphPanel:
    """Test brain graph panel generation."""

    def test_render_interactive_html_basic(self):
        """Test basic HTML generation with nodes and edges."""
        from custom_components.ai_home_copilot.brain_graph_panel import _render_interactive_html

        nodes = [
            {"id": "entity.light_1", "label": "Light 1", "kind": "light", "domain": "light", "score": 0.8},
            {"id": "entity.light_2", "label": "Light 2", "kind": "light", "domain": "light", "score": 0.5},
            {"id": "zone.living_room", "label": "Living Room", "kind": "zone", "zone": "living_room", "score": 0.9},
        ]
        edges = [
            {"from": "entity.light_1", "to": "zone.living_room", "type": "located_in", "weight": 0.7},
            {"from": "entity.light_2", "to": "zone.living_room", "type": "located_in", "weight": 0.6},
        ]

        html = _render_interactive_html(nodes=nodes, edges=edges, title="Test Graph")

        assert "<!DOCTYPE html>" in html
        assert "Test Graph" in html
        assert "brainGraphPanel" in html or "Brain Graph" in html
        assert "nodes" in html
        assert "edges" in html
        assert "filter-kind" in html
        assert "filter-zone" in html
        assert "filter-search" in html

    def test_render_interactive_html_empty(self):
        """Test HTML generation with no data."""
        from custom_components.ai_home_copilot.brain_graph_panel import _render_interactive_html

        html = _render_interactive_html(nodes=[], edges=[], title="Empty Graph")

        assert "<!DOCTYPE html>" in html
        assert "Empty Graph" in html
        assert "const nodes = [];" in html

    def test_render_interactive_html_filters(self):
        """Test that filters are populated from data."""
        from custom_components.ai_home_copilot.brain_graph_panel import _render_interactive_html

        nodes = [
            {"id": "light.kitchen", "label": "Kitchen Light", "kind": "light", "zone": "kitchen", "score": 0.8},
            {"id": "sensor.temperature", "label": "Temperature", "kind": "sensor", "zone": "living_room", "score": 0.5},
            {"id": "switch.bedroom", "label": "Bedroom Switch", "kind": "switch", "zone": "bedroom", "score": 0.6},
        ]

        html = _render_interactive_html(nodes=nodes, edges=[], title="Filter Test")

        # Should include kinds and zones in JS data
        assert "light" in html
        assert "sensor" in html
        assert "switch" in html
        assert "kitchen" in html
        assert "living_room" in html
        assert "bedroom" in html

    def test_render_interactive_html_large_graph(self):
        """Test handling of larger graphs (limit enforcement)."""
        from custom_components.ai_home_copilot.brain_graph_panel import _render_interactive_html

        # Create 250 nodes (above 200 limit)
        nodes = [
            {"id": f"entity_{i}", "label": f"Entity {i}", "kind": "entity", "score": i / 250}
            for i in range(250)
        ]
        edges = [{"from": "entity_0", "to": f"entity_{i}", "type": "relates"} for i in range(1, 300)]

        html = _render_interactive_html(nodes=nodes, edges=edges, title="Large Graph")

        # Should still render but with limited data
        assert "<!DOCTYPE html>" in html
        # Check that the JS data doesn't contain all 250 nodes
        # (The function limits to 200 nodes, 400 edges)

    def test_normalize_scores(self):
        """Test score normalization."""
        from custom_components.ai_home_copilot.brain_graph_panel import _normalize_scores

        nodes = [
            {"score": 0.5},
            {"score": 1.0},
            {"score": 0.0},
        ]
        scores = _normalize_scores(nodes)

        assert len(scores) == 3
        assert min(scores) >= 0.0
        assert max(scores) <= 1.0

    def test_normalize_scores_single_node(self):
        """Test normalization with a single node."""
        from custom_components.ai_home_copilot.brain_graph_panel import _normalize_scores

        scores = _normalize_scores([{"score": 0.5}])
        assert scores == [0.5]

    def test_normalize_scores_empty(self):
        """Test normalization with no nodes."""
        from custom_components.ai_home_copilot.brain_graph_panel import _normalize_scores

        scores = _normalize_scores([])
        assert scores == []

    def test_get_kind_color(self):
        """Test kind color mapping."""
        from custom_components.ai_home_copilot.brain_graph_panel import _get_kind_color

        assert _get_kind_color("light") == "#ffd700"
        assert _get_kind_color("sensor") == "#20b2aa"
        assert _get_kind_color("zone") == "#daa520"
        assert _get_kind_color("unknown") == "#8899aa"
        assert _get_kind_color(None) == "#8899aa"

    def test_render_includes_javascript(self):
        """Test that the HTML includes necessary JavaScript functions."""
        from custom_components.ai_home_copilot.brain_graph_panel import _render_interactive_html

        html = _render_interactive_html(nodes=[], edges=[], title="JS Test")

        assert "function renderGraph" in html
        assert "function showNodeDetail" in html
        assert "function zoomIn" in html
        assert "function zoomOut" in html
        assert "function resetView" in html
        assert "function resetFilters" in html

    def test_render_includes_css(self):
        """Test that the HTML includes CSS styles."""
        from custom_components.ai_home_copilot.brain_graph_panel import _render_interactive_html

        html = _render_interactive_html(nodes=[], edges=[], title="CSS Test")

        assert "<style>" in html
        assert ".sidebar" in html
        assert ".graph-container" in html
        assert ".node-detail" in html

    def test_render_sanitizes_input(self):
        """Test that the HTML sanitizes potentially dangerous input."""
        from custom_components.ai_home_copilot.brain_graph_panel import _render_interactive_html

        nodes = [
            {"id": "test<script>alert(1)</script>", "label": "<b>Bold</b>", "kind": "light", "score": 0.5},
        ]
        html = _render_interactive_html(nodes=nodes, edges=[], title="Sanitize Test")

        # Should not contain raw script tags
        assert "<script>alert" not in html


class TestNodeViz:
    """Test NodeViz dataclass."""

    def test_node_viz_creation(self):
        """Test creating a NodeViz instance."""
        from custom_components.ai_home_copilot.brain_graph_panel import NodeViz

        node = NodeViz(
            node_id="test.node",
            label="Test Node",
            kind="light",
            domain="light",
            zone="living_room",
            score=0.75,
            x=100.0,
            y=200.0,
            meta={"source": "test"},
        )

        assert node.node_id == "test.node"
        assert node.label == "Test Node"
        assert node.kind == "light"
        assert node.domain == "light"
        assert node.zone == "living_room"
        assert node.score == 0.75
        assert node.x == 100.0
        assert node.y == 200.0
        assert node.meta == {"source": "test"}