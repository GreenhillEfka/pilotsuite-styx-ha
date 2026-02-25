"""Regression tests for entity profile defaults."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from ai_home_copilot.entity_profile import get_entity_profile, is_full_entity_profile


def test_entity_profile_defaults_to_core() -> None:
    entry = SimpleNamespace(data={}, options={})
    assert get_entity_profile(entry) == "core"
    assert is_full_entity_profile(entry) is False


def test_entity_profile_uses_options_override() -> None:
    entry = SimpleNamespace(data={"entity_profile": "core"}, options={"entity_profile": "full"})
    assert get_entity_profile(entry) == "full"
    assert is_full_entity_profile(entry) is True


def test_entity_profile_invalid_value_falls_back_to_core() -> None:
    entry = SimpleNamespace(data={"entity_profile": "invalid"}, options={})
    assert get_entity_profile(entry) == "core"
