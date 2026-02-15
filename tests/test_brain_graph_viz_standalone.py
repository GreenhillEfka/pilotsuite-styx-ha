"""Standalone tests for brain_graph_viz core functions.

These tests require Home Assistant because the module imports HA components.
"""
import pytest

# Mark as integration test
pytestmark = pytest.mark.integration

import math
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, '/config/.openclaw/workspace/ai_home_copilot_hacs_repo/custom_components/ai_home_copilot')

# Skip if HA not installed
try:
    from brain_graph_viz import _safe_float, _normalize_scores, _render_html
    from privacy import sanitize_text
except ImportError:
    pytest.skip("Home Assistant not installed", allow_module_level=True)


# ========== Tests für _safe_float ==========

def test_safe_float_none_returns_default():
    assert _safe_float(None, 0.5) == 0.5
    assert _safe_float(None) == 0.0
    print("✓ _safe_float: None returns default")

def test_safe_float_valid():
    assert _safe_float(3.14) == 3.14
    assert _safe_float(-1.5) == -1.5
    print("✓ _safe_float: Valid floats work")

def test_safe_float_string():
    assert _safe_float("2.5") == 2.5
    print("✓ _safe_float: String conversion")

def test_safe_float_invalid_string():
    assert _safe_float("invalid", 1.0) == 1.0
    print("✓ _safe_float: Invalid string returns default")

def test_safe_float_inf():
    assert _safe_float(float('inf'), 0.0) == 0.0
    assert _safe_float(float('-inf'), 0.0) == 0.0
    print("✓ _safe_float: Inf clamped to default")


# ========== Tests für _normalize_scores ==========

def test_normalize_scores_basic():
    scores = {"a": 0.8, "b": 0.4, "c": 0.0}
    result = _normalize_scores(scores)
    assert "a" in result
    assert "b" in result
    print("✓ _normalize_scores: Basic normalization")

def test_normalize_scores_empty():
    result = _normalize_scores({})
    assert result == {}
    print("✓ _normalize_scores: Empty dict handled")

def test_normalize_scores_single():
    result = _normalize_scores({"only_one": 0.5})
    assert "only_one" in result
    print("✓ _normalize_scores: Single element")


# ========== Tests für sanitize_text ==========

def test_sanitize_text_basic():
    result = sanitize_text("test_entity")
    assert result is not None
    print("✓ sanitize_text: Basic sanitization")

def test_sanitize_text_empty():
    result = sanitize_text("")
    assert result is not None
    print("✓ sanitize_text: Empty string handled")

def test_sanitize_text_special_chars():
    result = sanitize_text("entity-with_special.chars:123")
    assert result is not None
    print("✓ sanitize_text: Special chars handled")


# ========== Tests für _render_html ==========

def test_render_html_basic():
    html = _render_html([], {})
    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html or "<html" in html
    print("✓ _render_html: Basic HTML generation")

def test_render_html_with_nodes():
    # Create mock node data
    nodes = [
        {"id": "node1", "label": "Test", "score": 0.5, "x": 100, "y": 100}
    ]
    html = _render_html(nodes, {})
    assert isinstance(html, str)
    print("✓ _render_html: HTML with nodes")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])