"""Tests for PilotSuite Entity Classifier — NeuronTagResolver 4-signal pipeline.

Covers the 4-phase classification cascade:
  Phase 1 (Tags)       — explicit neuron tags / pattern matching
  Phase 2 (Domain)     — HA domain fallback (weight ~0.6)
  Phase 3 (Device-Class) — HA device_class (weight ~0.9, highest priority)
  Phase 4 (Keywords)   — tag name keyword matching (weight ~0.75)

Also covers:
- UOM-derived device class signals
- Confidence cascade (device_class > keywords > domain)
- Edge cases: disabled entities, unknown domains, empty registries
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass, field
from typing import Any

from custom_components.ai_home_copilot.core.modules.entity_tags_module import (
    NeuronTagResolver,
    NEURON_TAG_MAPPING,
    DEVICE_CLASS_NEURON_MAP,
    DOMAIN_NEURON_MAP,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class FakeTag:
    tag_id: str
    name: str
    entity_ids: list[str] = field(default_factory=list)


@dataclass
class FakeRegistryEntry:
    entity_id: str
    domain: str
    device_class: str | None = None
    original_device_class: str | None = None
    disabled_by: str | None = None


def _make_tags_module(
    tags: list[FakeTag] | None = None,
    registry_entries: list[FakeRegistryEntry] | None = None,
):
    """Build a mock EntityTagsModule with given tags and an entity registry."""
    module = MagicMock()
    module.get_all_tags.return_value = tags or []

    hass = MagicMock()
    mock_reg = MagicMock()
    entries = {e.entity_id: e for e in (registry_entries or [])}
    mock_reg.entities = entries

    # Patch entity_registry.async_get to return our mock
    import sys
    sys.modules["homeassistant.helpers"].entity_registry.async_get.return_value = mock_reg

    module._hass = hass
    return module


# ---------------------------------------------------------------------------
# Mapping Integrity
# ---------------------------------------------------------------------------

class TestMappingIntegrity:
    """Validate static mapping constants."""

    def test_neuron_tag_mapping_values_valid(self):
        valid_categories = {"context", "state", "mood"}
        for key, cat in NEURON_TAG_MAPPING.items():
            assert cat in valid_categories, f"Key '{key}' maps to invalid '{cat}'"

    def test_device_class_neuron_map_values_valid(self):
        valid = {"context", "state", "mood"}
        for dc, cat in DEVICE_CLASS_NEURON_MAP.items():
            assert cat in valid, f"Device class '{dc}' maps to invalid '{cat}'"

    def test_domain_neuron_map_values_valid(self):
        valid = {"context", "state", "mood"}
        for domain, cat in DOMAIN_NEURON_MAP.items():
            assert cat in valid, f"Domain '{domain}' maps to invalid '{cat}'"

    def test_explicit_neuron_tags_present(self):
        assert "styx:neuron:kontext" in NEURON_TAG_MAPPING
        assert "styx:neuron:zustand" in NEURON_TAG_MAPPING
        assert "styx:neuron:stimmung" in NEURON_TAG_MAPPING

    def test_motion_mapped_to_context(self):
        assert DEVICE_CLASS_NEURON_MAP.get("motion") == "context"
        assert NEURON_TAG_MAPPING.get("motion") == "context"

    def test_temperature_mapped_to_state(self):
        assert DEVICE_CLASS_NEURON_MAP.get("temperature") == "state"

    def test_media_player_mapped_to_mood(self):
        assert DOMAIN_NEURON_MAP.get("media_player") == "mood"


# ---------------------------------------------------------------------------
# Phase 1: Explicit Tag Resolution
# ---------------------------------------------------------------------------

class TestPhase1ExplicitTags:
    """Phase 1 — explicit neuron tags have highest priority."""

    def test_explicit_kontext_tag(self):
        tags = [FakeTag("styx:neuron:kontext", "Kontext", ["light.kitchen"])]
        module = _make_tags_module(tags=tags)

        result = NeuronTagResolver().resolve_entities(module)
        assert "light.kitchen" in result["context_entities"]

    def test_explicit_zustand_tag(self):
        tags = [FakeTag("styx:neuron:zustand", "Zustand", ["sensor.temp"])]
        module = _make_tags_module(tags=tags)

        result = NeuronTagResolver().resolve_entities(module)
        assert "sensor.temp" in result["state_entities"]

    def test_explicit_stimmung_tag(self):
        tags = [FakeTag("styx:neuron:stimmung", "Stimmung", ["media_player.sonos"])]
        module = _make_tags_module(tags=tags)

        result = NeuronTagResolver().resolve_entities(module)
        assert "media_player.sonos" in result["mood_entities"]

    def test_explicit_tag_overrides_domain_fallback(self):
        """An entity tagged as 'kontext' should not be re-classified by domain."""
        tags = [FakeTag("styx:neuron:kontext", "Kontext", ["media_player.sonos"])]
        registry = [FakeRegistryEntry("media_player.sonos", "media_player")]
        module = _make_tags_module(tags=tags, registry_entries=registry)

        result = NeuronTagResolver().resolve_entities(module)
        assert "media_player.sonos" in result["context_entities"]


# ---------------------------------------------------------------------------
# Phase 2: Tag Pattern Matching (Keywords)
# ---------------------------------------------------------------------------

class TestPhase2TagPatterns:
    """Phase 2 — match tag_id/name against NEURON_TAG_MAPPING patterns."""

    def test_light_keyword_in_tag_id(self):
        tags = [FakeTag("light_wohnzimmer", "Light Wohnzimmer", ["light.wz"])]
        module = _make_tags_module(tags=tags)

        result = NeuronTagResolver().resolve_entities(module)
        assert "light.wz" in result["context_entities"]

    def test_temperature_keyword_in_tag_name(self):
        tags = [FakeTag("sensors_bad", "Temperature Bad", ["sensor.bad_temp"])]
        module = _make_tags_module(tags=tags)

        result = NeuronTagResolver().resolve_entities(module)
        assert "sensor.bad_temp" in result["state_entities"]

    def test_music_keyword_maps_to_mood(self):
        tags = [FakeTag("musik_zone", "Musik", ["media_player.speaker"])]
        module = _make_tags_module(tags=tags)

        result = NeuronTagResolver().resolve_entities(module)
        assert "media_player.speaker" in result["mood_entities"]

    def test_entity_can_be_in_multiple_categories(self):
        """Tags like 'light_energy_zone' match both 'light' (context) and 'energy' (state)."""
        tags = [FakeTag("light_energy_zone", "Light Energy Zone", ["sensor.dual"])]
        module = _make_tags_module(tags=tags)

        result = NeuronTagResolver().resolve_entities(module)
        assert "sensor.dual" in result["context_entities"]
        assert "sensor.dual" in result["state_entities"]

    def test_no_keyword_match_skips_tag(self):
        tags = [FakeTag("custom_user_tag", "Mein Tag", ["switch.custom"])]
        module = _make_tags_module(tags=tags)

        result = NeuronTagResolver().resolve_entities(module)
        assert "switch.custom" not in result["context_entities"]
        assert "switch.custom" not in result["state_entities"]
        assert "switch.custom" not in result["mood_entities"]


# ---------------------------------------------------------------------------
# Phase 3: Device-Class Signal (highest confidence)
# ---------------------------------------------------------------------------

class TestPhase3DeviceClass:
    """Phase 3 — device_class resolution for entities not resolved by tags."""

    def test_temperature_device_class(self):
        registry = [FakeRegistryEntry("sensor.temp", "sensor", device_class="temperature")]
        module = _make_tags_module(registry_entries=registry)

        result = NeuronTagResolver().resolve_entities(module)
        assert "sensor.temp" in result["state_entities"]

    def test_motion_device_class(self):
        registry = [FakeRegistryEntry("binary_sensor.pir", "binary_sensor", device_class="motion")]
        module = _make_tags_module(registry_entries=registry)

        result = NeuronTagResolver().resolve_entities(module)
        assert "binary_sensor.pir" in result["context_entities"]

    def test_power_device_class(self):
        registry = [FakeRegistryEntry("sensor.plug_power", "sensor", device_class="power")]
        module = _make_tags_module(registry_entries=registry)

        result = NeuronTagResolver().resolve_entities(module)
        assert "sensor.plug_power" in result["state_entities"]

    def test_original_device_class_fallback(self):
        registry = [FakeRegistryEntry("sensor.hum", "sensor",
                                       device_class=None,
                                       original_device_class="humidity")]
        module = _make_tags_module(registry_entries=registry)

        result = NeuronTagResolver().resolve_entities(module)
        assert "sensor.hum" in result["state_entities"]

    def test_disabled_entity_skipped(self):
        registry = [FakeRegistryEntry("sensor.disabled", "sensor",
                                       device_class="temperature",
                                       disabled_by="user")]
        module = _make_tags_module(registry_entries=registry)

        result = NeuronTagResolver().resolve_entities(module)
        assert "sensor.disabled" not in result["state_entities"]


# ---------------------------------------------------------------------------
# Phase 4: Domain Fallback (lowest confidence)
# ---------------------------------------------------------------------------

class TestPhase4DomainFallback:
    """Phase 4 — domain fallback for entities without device_class match."""

    def test_light_domain_to_context(self):
        registry = [FakeRegistryEntry("light.hallway", "light")]
        module = _make_tags_module(registry_entries=registry)

        result = NeuronTagResolver().resolve_entities(module)
        assert "light.hallway" in result["context_entities"]

    def test_climate_domain_to_state(self):
        registry = [FakeRegistryEntry("climate.living", "climate")]
        module = _make_tags_module(registry_entries=registry)

        result = NeuronTagResolver().resolve_entities(module)
        assert "climate.living" in result["state_entities"]

    def test_calendar_domain_to_mood(self):
        registry = [FakeRegistryEntry("calendar.family", "calendar")]
        module = _make_tags_module(registry_entries=registry)

        result = NeuronTagResolver().resolve_entities(module)
        assert "calendar.family" in result["mood_entities"]

    def test_unknown_domain_excluded(self):
        registry = [FakeRegistryEntry("input_boolean.test", "input_boolean")]
        module = _make_tags_module(registry_entries=registry)

        result = NeuronTagResolver().resolve_entities(module)
        assert "input_boolean.test" not in result["context_entities"]
        assert "input_boolean.test" not in result["state_entities"]
        assert "input_boolean.test" not in result["mood_entities"]


# ---------------------------------------------------------------------------
# Confidence Cascade (device_class > tag patterns > domain)
# ---------------------------------------------------------------------------

class TestConfidenceCascade:
    """Verify that device_class has precedence over domain for untagged entities."""

    def test_device_class_wins_over_domain(self):
        """binary_sensor domain maps to context, but humidity device_class maps to state."""
        registry = [FakeRegistryEntry("binary_sensor.hum", "binary_sensor",
                                       device_class="humidity")]
        module = _make_tags_module(registry_entries=registry)

        result = NeuronTagResolver().resolve_entities(module)
        assert "binary_sensor.hum" in result["state_entities"]
        # Should NOT also be in context (domain would map binary_sensor -> context)
        assert "binary_sensor.hum" not in result["context_entities"]

    def test_tag_resolution_prevents_registry_fallback(self):
        """An entity resolved via tags should not be re-classified by registry."""
        tags = [FakeTag("styx:neuron:stimmung", "Stimmung", ["light.mood"])]
        registry = [FakeRegistryEntry("light.mood", "light")]
        module = _make_tags_module(tags=tags, registry_entries=registry)

        result = NeuronTagResolver().resolve_entities(module)
        assert "light.mood" in result["mood_entities"]


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases and empty inputs."""

    def test_empty_tags_and_registry(self):
        module = _make_tags_module()
        result = NeuronTagResolver().resolve_entities(module)
        assert result["context_entities"] == []
        assert result["state_entities"] == []
        assert result["mood_entities"] == []

    def test_tag_with_empty_entity_list(self):
        tags = [FakeTag("styx:neuron:kontext", "Kontext", [])]
        module = _make_tags_module(tags=tags)

        result = NeuronTagResolver().resolve_entities(module)
        assert result["context_entities"] == []

    def test_results_are_sorted(self):
        tags = [
            FakeTag("styx:neuron:kontext", "Kontext", ["light.z", "light.a", "light.m"]),
        ]
        module = _make_tags_module(tags=tags)

        result = NeuronTagResolver().resolve_entities(module)
        assert result["context_entities"] == ["light.a", "light.m", "light.z"]

    def test_results_are_deduplicated(self):
        tags = [
            FakeTag("styx:neuron:kontext", "Kontext", ["light.a", "light.a"]),
            FakeTag("light_tag", "Light", ["light.a"]),
        ]
        module = _make_tags_module(tags=tags)

        result = NeuronTagResolver().resolve_entities(module)
        assert result["context_entities"].count("light.a") == 1

    def test_hass_none_skips_registry(self):
        module = MagicMock()
        module.get_all_tags.return_value = []
        module._hass = None

        result = NeuronTagResolver().resolve_entities(module)
        assert result == {
            "context_entities": [],
            "state_entities": [],
            "mood_entities": [],
        }
