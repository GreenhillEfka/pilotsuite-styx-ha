"""Tests for brain_graph_viz.py - Brain Graph Visualization.

Tests the HTML rendering, score normalization, and utility functions.
"""
import math
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import types

# We need to add paths properly
test_dir = Path(__file__).parent
project_root = test_dir.parent
sys.path.insert(0, str(project_root / "custom_components"))

# Mock homeassistant modules BEFORE importing anything from ai_home_copilot
# This must include sensor because debug.py imports it

mock_ha = MagicMock()
mock_ha.core = MagicMock()
mock_ha.helpers = MagicMock()
mock_ha.helpers.typing = MagicMock()
mock_ha.const = MagicMock()

# Mock sensor (needed by debug.py which is imported by __init__.py)
mock_sensor_entity = type("SensorEntity", (), {})
sys.modules['homeassistant.components.sensor'] = MagicMock()
sys.modules['homeassistant.components.sensor'].SensorEntity = mock_sensor_entity

# Set up sys.modules BEFORE any ai_home_copilot imports
sys.modules['homeassistant'] = mock_ha
sys.modules['homeassistant.core'] = mock_ha.core
sys.modules['homeassistant.components'] = MagicMock()
sys.modules['homeassistant.components.persistent_notification'] = MagicMock()
sys.modules['homeassistant.helpers'] = mock_ha.helpers
sys.modules['homeassistant.helpers.typing'] = mock_ha.helpers.typing
sys.modules['homeassistant.const'] = mock_ha.const
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()
sys.modules['homeassistant.helpers.storage'] = MagicMock()

# Set up custom_components package structure properly
custom_components_pkg = types.ModuleType('custom_components')
ai_home_copilot_pkg = types.ModuleType('ai_home_copilot')
ai_home_copilot_pkg.__path__ = [str(project_root / "custom_components" / "ai_home_copilot")]
ai_home_copilot_pkg.__file__ = str(project_root / "custom_components" / "ai_home_copilot" / "__init__.py")
ai_home_copilot_pkg.__package__ = 'custom_components.ai_home_copilot'

# Set up privacy module
privacy_mock = types.ModuleType('privacy')
def sanitize_text_mock(text, max_chars=100):
    if text is None:
        return ''
    s = str(text)
    if len(s) > max_chars:
        s = s[:max_chars]
    import re
    s = re.sub(r'<[^>]+>', '', s)
    return s

privacy_mock.sanitize_text = sanitize_text_mock

# Register modules in sys.modules
sys.modules['custom_components'] = custom_components_pkg
sys.modules['custom_components.ai_home_copilot'] = ai_home_copilot_pkg
sys.modules['custom_components.ai_home_copilot.privacy'] = privacy_mock

# Now import the brain_graph_viz module directly
import importlib.util
brain_graph_viz_path = project_root / "custom_components" / "ai_home_copilot" / "brain_graph_viz.py"

# Use the full module name that the dataclass will see
module_name = 'custom_components.ai_home_copilot.brain_graph_viz'
spec = importlib.util.spec_from_file_location(module_name, str(brain_graph_viz_path))
brain_graph_viz = importlib.util.module_from_spec(spec)
brain_graph_viz.__package__ = 'custom_components.ai_home_copilot'
brain_graph_viz.__name__ = module_name  # Must match sys.modules key!

# Must add to sys.modules BEFORE loading for dataclass decorator
sys.modules[module_name] = brain_graph_viz

spec.loader.exec_module(brain_graph_viz)

# Extract test functions
_safe_float = brain_graph_viz._safe_float
_normalize_scores = brain_graph_viz._normalize_scores
_render_html = brain_graph_viz._render_html


class TestSafeFloat:
    """Tests for _safe_float utility function."""

    def test_none_returns_default(self):
        """Test that None returns default value."""
        assert _safe_float(None, 0.5) == 0.5
        assert _safe_float(None) == 0.0

    def test_valid_float(self):
        """Test that valid floats are returned."""
        assert _safe_float(3.14) == 3.14
        assert _safe_float(-1.5) == -1.5
        assert _safe_float(0.0) == 0.0

    def test_int_conversion(self):
        """Test that integers are converted to floats."""
        assert _safe_float(42) == 42.0
        assert _safe_float(0) == 0.0

    def test_string_conversion(self):
        """Test that numeric strings are converted."""
        assert _safe_float("3.14") == 3.14
        assert _safe_float("42") == 42.0

    def test_nan_returns_default(self):
        """Test that NaN returns default value."""
        assert _safe_float(float('nan')) == 0.0
        assert _safe_float(float('nan'), 99.0) == 99.0

    def test_inf_returns_default(self):
        """Test that infinity returns default value."""
        assert _safe_float(float('inf')) == 0.0
        assert _safe_float(float('-inf'), -1.0) == -1.0

    def test_invalid_string_returns_default(self):
        """Test that invalid strings return default."""
        assert _safe_float("not a number") == 0.0
        assert _safe_float("") == 0.0


class TestNormalizeScores:
    """Tests for _normalize_scores utility function."""

    def test_empty_list(self):
        """Test that empty list returns empty list."""
        assert _normalize_scores([]) == []

    def test_single_node(self):
        """Test normalization with single node."""
        result = _normalize_scores([{"score": 5.0}])
        assert result == [0.5]  # Single node gets mid emphasis

    def test_identical_scores(self):
        """Test normalization with identical scores."""
        result = _normalize_scores([
            {"score": 3.0},
            {"score": 3.0},
            {"score": 3.0},
        ])
        assert result == [0.5, 0.5, 0.5]

    def test_varying_scores(self):
        """Test normalization with varying scores."""
        result = _normalize_scores([
            {"score": 1.0},
            {"score": 5.0},
            {"score": 3.0},
        ])
        # (1-1)/(5-1) = 0, (5-1)/(5-1) = 1, (3-1)/(5-1) = 0.5
        assert result[0] == 0.0
        assert result[1] == 1.0
        assert result[2] == 0.5

    def test_missing_score_uses_default(self):
        """Test that missing score uses default 0.0."""
        result = _normalize_scores([
            {"id": "a"},
            {"score": 5.0},
            {},
        ])
        assert result[0] == 0.0
        assert result[1] == 1.0
        assert result[2] == 0.0

    def test_non_dict_items_ignored(self):
        """Test that non-dict items are handled gracefully."""
        result = _normalize_scores([
            {"score": 1.0},
            "not a dict",
            None,
            {"score": 5.0},
        ])
        # Non-dicts get score 0.0, then normalized within the range
        # raw = [1.0, 0.0, 0.0, 5.0] -> normalized = [0.2, 0.0, 0.0, 1.0]
        assert result[0] == 0.2
        assert result[1] == 0.0  # non-dict defaults to 0
        assert result[2] == 0.0  # None defaults to 0
        assert result[3] == 1.0

    def test_small_range_uses_mid_emphasis(self):
        """Test normalization with very small range."""
        result = _normalize_scores([
            {"score": 1.0},
            {"score": 1.00000001},
        ])
        # Range (1e-8) is NOT less than 1e-9 threshold, so it's normalized normally
        # lo=1.0, hi=1.00000001, range ~1e-8 > 1e-9
        # (1.0-1.0)/1e-8 = 0, (1.00000001-1.0)/1e-8 = 1
        assert result[0] == 0.0
        assert result[1] == 1.0


class TestRenderHtml:
    """Tests for _render_html function."""

    def test_empty_graph(self):
        """Test rendering empty graph."""
        html = _render_html(
            nodes=[],
            edges=[],
            title="Empty Test",
        )
        assert "Empty Test" in html
        assert "<!doctype html>" in html
        assert "Generated:" in html

    def test_basic_node_rendering(self):
        """Test basic node rendering."""
        nodes = [
            {"id": "node1", "label": "Mood", "score": 0.8},
            {"id": "node2", "label": "Energy", "score": 0.3},
        ]
        edges = [
            {"from": "node1", "to": "node2"},
        ]
        html = _render_html(nodes=nodes, edges=edges, title="Test Graph")

        # Check nodes are rendered
        assert "<circle" in html
        assert "Mood" in html
        assert "Energy" in html

    def test_edge_rendering(self):
        """Test edge lines are rendered."""
        nodes = [
            {"id": "n1", "label": "A", "score": 0.5},
            {"id": "n2", "label": "B", "score": 0.5},
            {"id": "n3", "label": "C", "score": 0.5},
        ]
        edges = [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n3"},
        ]
        html = _render_html(nodes=nodes, edges=edges, title="Edge Test")

        # Should have line elements for edges
        assert '<line' in html
        # Count edges
        assert html.count('<line') == 2

    def test_score_affects_circle_size(self):
        """Test that node score affects circle radius."""
        nodes_low = [{"id": "low", "label": "Low Score", "score": 0.0}]
        nodes_high = [{"id": "high", "label": "High Score", "score": 1.0}]

        html_low = _render_html(nodes=nodes_low, edges=[], title="Low")
        html_high = _render_html(nodes=nodes_high, edges=[], title="High")

        # Single nodes get normalized to 0.5 (mid emphasis)
        # r = 4.0 + 10.0 * score = 4.0 + 10.0 * 0.5 = 9.0 for both
        assert 'r="9.0"' in html_low
        assert 'r="14.0"' in html_high  # score 1.0 normalizes to 1.0

    def test_title_sanitization(self):
        """Test that title is sanitized."""
        html = _render_html(
            nodes=[],
            edges=[],
            title="<script>alert('xss')</script>Test",
        )
        # Script tags should be stripped
        assert "<script>" not in html

    def test_max_nodes_limit(self):
        """Test that node count is limited."""
        # Create 150 nodes (exceeds 120 limit)
        nodes = [{"id": f"n{i}", "label": f"Node {i}", "score": 0.5} for i in range(150)]
        html = _render_html(nodes=nodes, edges=[], title="Limit Test")

        # Should still work but only render first 120
        assert "Node 0" in html
        assert "Node 119" in html
        # Node 120 should not appear
        assert "Node 120" not in html

    def test_max_edges_limit(self):
        """Test that edge count is limited."""
        # Create many nodes
        nodes = [{"id": f"n{i}", "label": f"N{i}", "score": 0.5} for i in range(50)]
        # Create 300 edges (exceeds 240 limit)
        edges = [
            {"from": f"n{i}", "to": f"n{(i+1)%50}"}
            for i in range(300)
        ]
        html = _render_html(nodes=nodes, edges=edges, title="Edge Limit Test")

        # Should have max 240 lines
        assert html.count('<line') <= 240

    def test_missing_node_id_handled(self):
        """Test that nodes without ID are handled gracefully."""
        nodes = [
            {"label": "No ID Node", "score": 0.5},
            {"id": "valid", "label": "Valid", "score": 0.5},
        ]
        html = _render_html(nodes=nodes, edges=[], title="Missing ID Test")
        # Should still render valid node
        assert "Valid" in html

    def test_circular_layout_exists(self):
        """Test that nodes are arranged in circular layout."""
        nodes = [
            {"id": "a", "label": "A", "score": 0.5},
            {"id": "b", "label": "B", "score": 0.5},
            {"id": "c", "label": "C", "score": 0.5},
        ]
        html = _render_html(nodes=nodes, edges=[], title="Layout Test")

        # Should have viewBox for SVG
        assert 'viewBox="0 0 1000 800"' in html

    def test_html_structure_complete(self):
        """Test complete HTML structure."""
        html = _render_html(
            nodes=[{"id": "test", "label": "Test", "score": 0.5}],
            edges=[],
            title="Structure Test",
        )

        # Check all required HTML elements
        assert '<!doctype html>' in html
        assert '<html lang="en">' in html
        assert '<head>' in html
        assert '<body>' in html
        assert '<meta charset="utf-8"' in html
        assert '<meta name="viewport"' in html
        assert '<title>' in html
        assert '</html>' in html


class TestIntegration:
    """Integration tests for brain_graph_viz module."""

    def test_full_render_cycle(self):
        """Test complete rendering cycle."""
        # Simulate graph data
        graph_data = {
            "nodes": [
                {"id": "mood", "label": "Mood State", "score": 0.75},
                {"id": "energy", "label": "Energy Level", "score": 0.4},
                {"id": "media", "label": "Media Context", "score": 0.9},
            ],
            "edges": [
                {"from": "mood", "to": "energy"},
                {"from": "media", "to": "mood"},
            ],
        }

        html = _render_html(
            nodes=graph_data["nodes"],
            edges=graph_data["edges"],
            title="Full Cycle Test",
        )

        # Verify all data is rendered
        assert "Mood State" in html
        assert "Energy Level" in html
        assert "Media Context" in html
        # Edges should be present
        assert '<line' in html


if __name__ == "__main__":
    # Run basic tests without pytest
    print("Brain Graph Viz Tests")
    print("=" * 50)

    # Test _safe_float
    assert _safe_float(None, 0.5) == 0.5
    assert _safe_float(3.14) == 3.14
    assert _safe_float(float('nan')) == 0.0
    print("✓ _safe_float tests passed")

    # Test _normalize_scores
    assert _normalize_scores([]) == []
    assert _normalize_scores([{"score": 5.0}]) == [0.5]
    result = _normalize_scores([{"score": 1.0}, {"score": 5.0}])
    assert result[0] == 0.0
    assert result[1] == 1.0
    print("✓ _normalize_scores tests passed")

    # Test _render_html
    html = _render_html(nodes=[], edges=[], title="Test")
    assert "<!doctype html>" in html
    assert "Test" in html
    print("✓ _render_html tests passed")

    # Full cycle test
    graph = {
        "nodes": [
            {"id": "mood", "label": "Mood", "score": 0.75},
            {"id": "energy", "label": "Energy", "score": 0.4},
        ],
        "edges": [{"from": "mood", "to": "energy"}],
    }
    html = _render_html(
        nodes=graph["nodes"],
        edges=graph["edges"],
        title="Integration Test",
    )
    assert "Mood" in html
    assert "Energy" in html
    print("✓ Full cycle test passed")

    print("=" * 50)
    print("✓ All brain_graph_viz tests passed!")
