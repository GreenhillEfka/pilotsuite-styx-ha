"""Regression tests for selector-backed entity settings."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from ai_home_copilot.config_schema_builders import _as_entity_list


def test_as_entity_list_handles_csv_string() -> None:
    assert _as_entity_list("light.a, light.b") == ["light.a", "light.b"]


def test_as_entity_list_handles_list() -> None:
    assert _as_entity_list(["sensor.a", "sensor.b"]) == ["sensor.a", "sensor.b"]


def test_as_entity_list_handles_none() -> None:
    assert _as_entity_list(None) == []
