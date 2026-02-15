"""Standalone tests for brain_graph_viz core functions.

Tests HTML rendering, score normalization without HA dependencies.
"""
import math
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, '/config/.openclaw/workspace/ai_home_copilot_hacs_repo/custom_components/ai_home_copilot')

from brain_graph_viz import _safe_float, _normalize_scores, _render_html
from privacy import sanitize_text


# ========== Tests für _safe_float ==========

def test_safe_float_none_returns_default():
    assert _safe_float(None, 0.5) == 0.5
    assert _safe_float(None) == 0.0
    print("✓ _safe_float: None returns default")

def test_safe_float_valid():
    assert _safe_float(3.14) == 3.14
    assert _safe_float(-1.5) == -1.5
    assert _safe_float(0.0) == 0.0
    print("✓ _safe_float: valid floats")

def test_safe_float_int():
    assert _safe_float(42) == 42.0
    assert _safe_float(0) == 0.0
    print("✓ _safe_float: integers converted")

def test_safe_float_nan():
    assert _safe_float(float('nan')) == 0.0
    assert _safe_float(float('nan'), 99.0) == 99.0
    print("✓ _safe_float: NaN handled")

def test_safe_float_inf():
    assert _safe_float(float('inf')) == 0.0
    assert _safe_float(float('-inf'), -1.0) == -1.0
    print("✓ _safe_float: Infinity handled")

def test_safe_float_invalid():
    assert _safe_float("not a number") == 0.0
    assert _safe_float("") == 0.0
    print("✓ _safe_float: invalid strings handled")


# ========== Tests für _normalize_scores ==========

def test_normalize_empty():
    assert _normalize_scores([]) == []
    print("✓ _normalize_scores: empty list")

def test_normalize_single():
    result = _normalize_scores([{"score": 5.0}])
    assert result == [0.5]
    print("✓ _normalize_scores: single node = 0.5")

def test_normalize_identical():
    result = _normalize_scores([{"score": 3.0}, {"score": 3.0}, {"score": 3.0}])
    assert result == [0.5, 0.5, 0.5]
    print("✓ _normalize_scores: identical scores = 0.5")

def test_normalize_varying():
    result = _normalize_scores([
        {"score": 1.0},
        {"score": 5.0},
        {"score": 3.0},
    ])
    assert result[0] == 0.0
    assert result[1] == 1.0
    assert result[2] == 0.5
    print("✓ _normalize_scores: varying scores normalized correctly")

def test_normalize_missing_score():
    result = _normalize_scores([{"id": "a"}, {"score": 5.0}, {}])
    assert result[0] == 0.0
    assert result[1] == 1.0
    assert result[2] == 0.0
    print("✓ _normalize_scores: missing scores default to 0.0")

def test_normalize_non_dict():
    result = _normalize_scores([{"score": 1.0}, "not_dict", None, {"score": 5.0}])
    assert result[0] == 0.0
    assert result[1] == 0.0
    assert result[2] == 0.0
    assert result[3] == 1.0
    print("✓ _normalize_scores: non-dict items handled")


# ========== Tests für _render_html ==========

def test_render_empty():
    html = _render_html(nodes=[], edges=[], title="Empty Test")
    assert "<!doctype html>" in html
    assert "Empty Test" in html
    assert "Generated:" in html
    print("✓ _render_html: empty graph renders")

def test_render_nodes():
    html = _render_html(
        nodes=[
            {"id": "node1", "label": "Mood", "score": 0.8},
            {"id": "node2", "label": "Energy", "score": 0.3},
        ],
        edges=[{"from": "node1", "to": "node2"}],
        title="Node Test"
    )
    assert "Mood" in html
    assert "Energy" in html
    assert "<circle" in html
    print("✓ _render_html: nodes render with labels")

def test_render_edges():
    nodes = [{"id": f"n{i}", "label": f"N{i}", "score": 0.5} for i in range(3)]
    edges = [{"from": "n0", "to": "n1"}, {"from": "n1", "to": "n2"}]
    html = _render_html(nodes=nodes, edges=edges, title="Edge Test")
    assert html.count('<line') == 2
    print("✓ _render_html: edges render as lines")

def test_render_score_size():
    low = _render_html(nodes=[{"id": "l", "label": "Low", "score": 0.0}], edges=[], title="L")
    high = _render_html(nodes=[{"id": "h", "label": "High", "score": 1.0}], edges=[], title="H")
    assert 'r="4.0"' in low
    assert 'r="14.0"' in high
    print("✓ _render_html: score affects circle radius")

def test_render_title_sanitize():
    html = _render_html(
        nodes=[],
        edges=[],
        title="<script>alert('xss')</script>Test"
    )
    assert "<script>" not in html
    print("✓ _render_html: title sanitized")

def test_render_structure():
    html = _render_html(
        nodes=[{"id": "test", "label": "Test", "score": 0.5}],
        edges=[],
        title="Structure"
    )
    assert '<!doctype html>' in html
    assert '<head>' in html
    assert '<body>' in html
    assert '<title>' in html
    assert 'viewBox="0 0 1000 800"' in html
    print("✓ _render_html: complete HTML structure")


# ========== Tests für sanitize_text ==========

def test_sanitize_basic():
    assert sanitize_text("hello") == "hello"
    assert sanitize_text(None) == ""
    print("✓ sanitize_text: basic cases")

def test_sanitize_email():
    result = sanitize_text("contact: test@example.com")
    assert "[REDACTED_EMAIL]" in result
    print("✓ sanitize_text: email redaction")

def test_sanitize_phone():
    result = sanitize_text("call: +49 123 456789")
    assert "[REDACTED_PHONE]" in result
    print("✓ sanitize_text: phone redaction")

def test_sanitize_ip():
    result = sanitize_text("server: 192.168.1.1")
    assert "192.168.x.x" in result
    result2 = sanitize_text("ip: 8.8.8.8")
    assert "[REDACTED_IP]" in result2
    print("✓ sanitize_text: IP handling")

def test_sanitize_truncate():
    long = "x" * 1000
    result = sanitize_text(long, max_chars=100)
    assert len(result) <= 110  # 100 + truncation suffix
    print("✓ sanitize_text: truncation works")


# ========== Main Test Runner ==========

def run_all_tests():
    print("=" * 60)
    print("Brain Graph Viz - Standalone Tests")
    print("=" * 60)
    print()

    print("Testing _safe_float:")
    test_safe_float_none_returns_default()
    test_safe_float_valid()
    test_safe_float_int()
    test_safe_float_nan()
    test_safe_float_inf()
    test_safe_float_invalid()
    print()

    print("Testing _normalize_scores:")
    test_normalize_empty()
    test_normalize_single()
    test_normalize_identical()
    test_normalize_varying()
    test_normalize_missing_score()
    test_normalize_non_dict()
    print()

    print("Testing _render_html:")
    test_render_empty()
    test_render_nodes()
    test_render_edges()
    test_render_score_size()
    test_render_title_sanitize()
    test_render_structure()
    print()

    print("Testing sanitize_text:")
    test_sanitize_basic()
    test_sanitize_email()
    test_sanitize_phone()
    test_sanitize_ip()
    test_sanitize_truncate()
    print()

    print("=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
