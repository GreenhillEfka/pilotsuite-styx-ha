"""Tests for stale seed Repairs cleanup helpers."""

from __future__ import annotations

from custom_components.ai_home_copilot.repairs_cleanup import _is_stale_seed_issue


def test_stale_seed_issue_detects_low_signal_numeric_noise() -> None:
    issue = {
        "translation_key": "seed_suggestion",
        "translation_placeholders": {"title": "17"},
        "data": {
            "entry_id": "entry_1",
            "kind": "seed",
            "candidate_id": "seed_sensor_ai_home_copilot_seed_17",
            "seed_source": "sensor.some_seed_source",
            "seed_entities": [],
            "seed_text": "17",
        },
    }
    assert _is_stale_seed_issue(issue, "entry_1")


def test_stale_seed_issue_detects_internal_seed_source() -> None:
    issue = {
        "translation_key": "seed_suggestion",
        "translation_placeholders": {"title": "Vorschlag"},
        "data": {
            "entry_id": "entry_1",
            "kind": "seed",
            "candidate_id": "seed_x",
            "seed_source": "sensor.ai_home_copilot_seed_signal",
            "seed_entities": ["light.wohnzimmer"],
            "seed_text": "Wenn Bewegung erkannt wird, Licht einschalten",
        },
    }
    assert _is_stale_seed_issue(issue, "entry_1")


def test_stale_seed_issue_keeps_actionable_seed_with_entities() -> None:
    issue = {
        "translation_key": "seed_suggestion",
        "translation_placeholders": {"title": "Wenn Bewegung im Wohnzimmer"},
        "data": {
            "entry_id": "entry_1",
            "kind": "seed",
            "candidate_id": "seed_actionable_1",
            "seed_source": "sensor.external_recommendations",
            "seed_entities": ["binary_sensor.bewegung_wohnzimmer", "light.retrolampe"],
            "seed_text": "Wenn binary_sensor.bewegung_wohnzimmer auf on geht, dann light.retrolampe einschalten.",
        },
    }
    assert not _is_stale_seed_issue(issue, "entry_1")


def test_stale_seed_issue_ignores_other_config_entries() -> None:
    issue = {
        "translation_key": "seed_suggestion",
        "translation_placeholders": {"title": "on"},
        "data": {
            "entry_id": "other_entry",
            "kind": "seed",
            "candidate_id": "seed_other",
            "seed_source": "sensor.ai_home_copilot_seed_signal",
            "seed_entities": [],
            "seed_text": "on",
        },
    }
    assert not _is_stale_seed_issue(issue, "entry_1")

