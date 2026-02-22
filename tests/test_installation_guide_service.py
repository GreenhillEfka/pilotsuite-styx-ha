"""Tests for installation guide service helpers."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from ai_home_copilot.services_setup import _installation_guide_markdown  # noqa: E402


def test_installation_guide_mentions_primary_dashboard_paths() -> None:
    text = _installation_guide_markdown("192.168.30.18", 8909, token_set=True)
    assert "pilotsuite-styx/pilotsuite_dashboard_latest.yaml" in text
    assert "pilotsuite-styx/habitus_zones_dashboard_latest.yaml" in text
    assert "192.168.30.18:8909" in text
    assert "**gesetzt**" in text
