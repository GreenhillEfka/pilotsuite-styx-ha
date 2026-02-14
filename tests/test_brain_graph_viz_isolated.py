"""Isolated tests for brain_graph_viz core logic.

Copy of functions for standalone testing without HA dependencies.
"""
import math


# ===== Copied from brain_graph_viz.py =====

def _safe_float(x, default=0.0):
    """Safe float conversion with defaults."""
    try:
        if x is None:
            return default
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def _normalize_scores(nodes):
    """Normalize scores to 0-1 range."""
    raw = []
    for n in nodes:
        if not isinstance(n, dict):
            raw.append(0.0)
            continue
        raw.append(_safe_float(n.get("score"), 0.0))

    if not raw:
        return []

    lo = min(raw)
    hi = max(raw)
    if hi - lo < 1e-9:
        return [0.5 for _ in raw]

    out = []
    for v in raw:
        out.append((v - lo) / (hi - lo))
    return out


# ===== Copied from privacy.py =====

def sanitize_text(text, max_chars=500):
    """Simple sanitize without regex for test."""
    if text is None:
        return ""
    s = str(text)
    if not s:
        return ""
    # Simple truncation
    if len(s) > max_chars:
        suffix = "…(truncated)…"
        keep = max(0, max_chars - len(suffix))
        return s[:keep] + suffix
    return s


# ===== Tests =====

def test_safe_float():
    assert _safe_float(None, 0.5) == 0.5
    assert _safe_float(3.14) == 3.14
    assert _safe_float(float('nan')) == 0.0
    assert _safe_float(float('inf')) == 0.0
    assert _safe_float("not_number") == 0.0
    print("✓ _safe_float: all cases pass")

def test_normalize():
    assert _normalize_scores([]) == []
    assert _normalize_scores([{"score": 5.0}]) == [0.5]
    r = _normalize_scores([{"score": 1.0}, {"score": 5.0}, {"score": 3.0}])
    assert r[0] == 0.0 and r[1] == 1.0 and r[2] == 0.5
    r = _normalize_scores([{"score": 3.0}, {"score": 3.0}])
    assert r == [0.5, 0.5]
    print("✓ _normalize_scores: all cases pass")

def test_sanitize():
    assert sanitize_text("hello") == "hello"
    assert sanitize_text(None) == ""
    assert len(sanitize_text("x" * 1000, max_chars=100)) <= 110
    print("✓ sanitize_text: all cases pass")


if __name__ == "__main__":
    print("=" * 50)
    print("Brain Graph Viz - Isolated Tests")
    print("=" * 50)
    test_safe_float()
    test_normalize()
    test_sanitize()
    print("=" * 50)
    print("✓ ALL ISOLATED TESTS PASSED!")
    print("=" * 50)
