"""Tests for zone config flow helpers."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from ai_home_copilot.config_zones_flow import (
    _build_zone_form_schema,
    _ensure_unique_zone_id,
    _zone_id_from_name,
)


def _schema_keys(schema) -> set[str]:
    return {getattr(key, "schema", str(key)) for key in schema.schema.keys()}


def test_zone_id_from_name_normalizes_unicode() -> None:
    assert _zone_id_from_name("Wohnzimmer Süd") == "zone:wohnzimmer_sud"


def test_ensure_unique_zone_id_adds_suffix() -> None:
    existing = {"zone:wohnzimmer", "zone:wohnzimmer_2"}
    assert _ensure_unique_zone_id("zone:wohnzimmer", existing) == "zone:wohnzimmer_3"


def test_create_zone_schema_uses_area_selector_and_no_zone_id_field() -> None:
    schema = _build_zone_form_schema(
        mode="create",
        area_ids=[],
        area_options=[{"value": "area.living", "label": "Living Room"}],
        name="",
        motion_entity_id=None,
        light_entity_ids=[],
        role_entity_ids={},
        optional_entity_ids=[],
    )
    keys = _schema_keys(schema)
    assert "area_ids" in keys
    assert "zone_id" not in keys


def test_edit_zone_schema_has_no_zone_id_field() -> None:
    schema = _build_zone_form_schema(
        mode="edit",
        area_ids=["area.living", "area.kitchen"],
        area_options=[
            {"value": "area.living", "label": "Living Room"},
            {"value": "area.kitchen", "label": "Kitchen"},
        ],
        name="Wohnzimmer",
        motion_entity_id="binary_sensor.motion_wohnzimmer",
        light_entity_ids=["light.retrolampe"],
        role_entity_ids={
            "brightness": ["sensor.wohnzimmer_lux"],
            "co2": ["sensor.wohnzimmer_co2"],
        },
        optional_entity_ids=[],
    )
    keys = _schema_keys(schema)
    assert "area_ids" in keys
    assert "zone_id" not in keys
    assert "brightness_entity_ids" in keys
    assert "co2_entity_ids" in keys
