"""Tests for seed adapter noise filtering."""

from types import SimpleNamespace

from custom_components.ai_home_copilot.seed_adapter import _extract_seeds_from_state


def _state(state: str, attrs: dict | None = None):
    return SimpleNamespace(state=state, attributes=attrs or {})


def test_extract_seeds_ignores_trivial_state_values():
    seeds = _extract_seeds_from_state(
        "sensor.example",
        _state("on"),
        allowed_domains=set(),
        blocked_domains=set(),
    )
    assert seeds == []


def test_extract_seeds_ignores_numeric_noise_items():
    seeds = _extract_seeds_from_state(
        "sensor.example",
        _state(
            "ok",
            {"suggestions": ["17", "off", "42%"]},
        ),
        allowed_domains=set(),
        blocked_domains=set(),
    )
    assert seeds == []


def test_extract_seeds_keeps_actionable_text():
    seeds = _extract_seeds_from_state(
        "sensor.example",
        _state(
            "ok",
            {
                "suggestions": [
                    "Wenn binary_sensor.bewegung_wohnzimmer auf on geht, schalte light.shapes ein",
                ]
            },
        ),
        allowed_domains=set(),
        blocked_domains=set(),
    )
    assert len(seeds) == 1
    assert "binary_sensor.bewegung_wohnzimmer" in seeds[0].entities_found
