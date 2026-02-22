"""Tests for Lovelace dashboard wiring helpers."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from ai_home_copilot.dashboard_wiring import (  # noqa: E402
    SNIPPET_REL_PATH,
    _has_lovelace_root,
    _is_dashboard_wired,
    _snippet_content,
)


def test_has_lovelace_root_detects_key() -> None:
    assert _has_lovelace_root("default_config:\nlovelace:\n  mode: yaml\n")
    assert _has_lovelace_root("  lovelace :\n    mode: storage\n")
    assert not _has_lovelace_root("default_config:\nfrontend:\n")


def test_is_dashboard_wired_with_include_path() -> None:
    config = f"lovelace:\n  dashboards: !include {SNIPPET_REL_PATH}\n"
    assert _is_dashboard_wired(config)


def test_is_dashboard_wired_with_direct_dashboard_files() -> None:
    config = (
        "lovelace:\n"
        "  dashboards:\n"
        "    copilot-pilotsuite:\n"
        "      filename: ai_home_copilot/pilotsuite_dashboard_latest.yaml\n"
        "    copilot-habitus-zones:\n"
        "      filename: ai_home_copilot/habitus_zones_dashboard_latest.yaml\n"
    )
    assert _is_dashboard_wired(config)


def test_is_dashboard_wired_requires_both_dashboards() -> None:
    partial = "filename: ai_home_copilot/pilotsuite_dashboard_latest.yaml\n"
    assert not _is_dashboard_wired(partial)


def test_snippet_contains_both_dashboard_entries() -> None:
    snippet = _snippet_content()
    assert "copilot-pilotsuite:" in snippet
    assert "copilot-habitus-zones:" in snippet

