"""Contract tests for Core endpoint paths used by the HA integration."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from ai_home_copilot.services.habitus_dashboard_cards_service import DASHBOARD_CARDS_ENDPOINT


def test_dashboard_cards_endpoint_is_api_v1() -> None:
    assert DASHBOARD_CARDS_ENDPOINT == "/api/v1/habitus/dashboard_cards"

