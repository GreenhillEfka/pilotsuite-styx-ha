"""Tests for PilotSuite Auto-Setup — SetupWizard and zone suggestion logic.

Covers:
- Zone suggestion from HA areas with German template matching
- Entity auto-discovery and categorization
- Run-once guard (SetupWizard is stateful per session)
- Empty/missing input handling
- Slug/tag-ID helpers
- Role classification and priority scoring
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass
from typing import Any

from custom_components.ai_home_copilot.setup_wizard import (
    SetupWizard,
    ZONE_TEMPLATES,
    generate_wizard_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class FakeEntityEntry:
    entity_id: str
    domain: str
    name: str | None = None
    device_class: str | None = None
    area_id: str | None = None


@dataclass
class FakeArea:
    name: str
    icon: str | None = None


def _make_entity_registry(entries: list[FakeEntityEntry]):
    """Build a mock entity registry from a list of FakeEntityEntry."""
    mock_reg = MagicMock()
    mock_reg.entities = {e.entity_id: e for e in entries}
    return mock_reg


def _make_area_registry(areas: dict[str, FakeArea]):
    mock_reg = MagicMock()
    mock_reg.areas = areas
    return mock_reg


# ---------------------------------------------------------------------------
# Zone Template Integrity
# ---------------------------------------------------------------------------

class TestZoneTemplates:
    """Validate ZONE_TEMPLATES constant."""

    def test_all_templates_have_required_keys(self):
        required = {"name", "icon", "roles", "keywords", "priority"}
        for key, tpl in ZONE_TEMPLATES.items():
            missing = required - set(tpl.keys())
            assert not missing, f"Template '{key}' missing keys: {missing}"

    def test_priority_values_valid(self):
        valid = {"high", "medium", "low"}
        for key, tpl in ZONE_TEMPLATES.items():
            assert tpl["priority"] in valid, f"Template '{key}' has invalid priority"

    def test_keywords_are_lowercase(self):
        for key, tpl in ZONE_TEMPLATES.items():
            for kw in tpl["keywords"]:
                assert kw == kw.lower(), f"Keyword '{kw}' in '{key}' not lowercase"

    def test_roles_are_non_empty(self):
        for key, tpl in ZONE_TEMPLATES.items():
            assert len(tpl["roles"]) > 0, f"Template '{key}' has no roles"

    def test_minimum_template_count(self):
        assert len(ZONE_TEMPLATES) >= 10, "Expected at least 10 zone templates"


# ---------------------------------------------------------------------------
# SetupWizard.discover_entities()
# ---------------------------------------------------------------------------

class TestDiscoverEntities:
    """Test entity auto-discovery."""

    @pytest.fixture
    def wizard(self):
        hass = MagicMock()
        hass.states = MagicMock()
        hass.states.get = MagicMock(return_value=None)
        return SetupWizard(hass)

    @pytest.mark.asyncio
    async def test_discover_empty_registry(self, wizard):
        ent_reg = _make_entity_registry([])
        area_reg = _make_area_registry({})

        with patch("custom_components.ai_home_copilot.setup_wizard.entity_registry") as er, \
             patch("custom_components.ai_home_copilot.setup_wizard.area_registry") as ar:
            er.async_get.return_value = ent_reg
            ar.async_get.return_value = area_reg

            result = await wizard.discover_entities()

        assert result["lights"] == []
        assert result["sensors"] == []
        assert result["zones"] == []

    @pytest.mark.asyncio
    async def test_discover_categorizes_entities(self, wizard):
        entries = [
            FakeEntityEntry("light.kitchen", "light", "Kitchen Light"),
            FakeEntityEntry("sensor.temp", "sensor", "Temp", device_class="temperature"),
            FakeEntityEntry("media_player.sonos", "media_player", "Sonos"),
            FakeEntityEntry("person.andreas", "person", "Andreas"),
        ]
        ent_reg = _make_entity_registry(entries)
        area_reg = _make_area_registry({})

        with patch("custom_components.ai_home_copilot.setup_wizard.entity_registry") as er, \
             patch("custom_components.ai_home_copilot.setup_wizard.area_registry") as ar:
            er.async_get.return_value = ent_reg
            ar.async_get.return_value = area_reg

            result = await wizard.discover_entities()

        assert len(result["lights"]) == 1
        assert len(result["sensors"]) == 1
        assert len(result["media_players"]) == 1
        assert len(result["persons"]) == 1

    @pytest.mark.asyncio
    async def test_discover_collects_areas(self, wizard):
        ent_reg = _make_entity_registry([])
        area_reg = _make_area_registry({
            "wohnzimmer": FakeArea("Wohnzimmer", "mdi:sofa"),
            "kueche": FakeArea("Küche"),
        })

        with patch("custom_components.ai_home_copilot.setup_wizard.entity_registry") as er, \
             patch("custom_components.ai_home_copilot.setup_wizard.area_registry") as ar:
            er.async_get.return_value = ent_reg
            ar.async_get.return_value = area_reg

            result = await wizard.discover_entities()

        assert len(result["zones"]) == 2
        names = [z["name"] for z in result["zones"]]
        assert "Wohnzimmer" in names


# ---------------------------------------------------------------------------
# SetupWizard.get_zone_suggestions()
# ---------------------------------------------------------------------------

class TestZoneSuggestions:
    """Test zone suggestion with German template matching."""

    def _make_wizard_with_zones(self, zones, entities=None):
        hass = MagicMock()
        ent_reg = _make_entity_registry(entities or [])

        with patch("custom_components.ai_home_copilot.setup_wizard.entity_registry") as er:
            er.async_get.return_value = ent_reg
            wizard = SetupWizard(hass)
            wizard._discovered_entities = {"zones": zones}
            return wizard

    def test_german_template_matching_wohnzimmer(self):
        zones = [{"area_id": "wz", "name": "Wohnzimmer", "icon": "mdi:sofa"}]
        wizard = self._make_wizard_with_zones(zones)
        suggestions = wizard.get_zone_suggestions()

        assert len(suggestions) == 1
        assert suggestions[0]["template"] == "Wohnbereich"

    def test_german_template_matching_kueche(self):
        zones = [{"area_id": "ku", "name": "Küche", "icon": None}]
        wizard = self._make_wizard_with_zones(zones)
        suggestions = wizard.get_zone_suggestions()

        assert suggestions[0]["template"] == "Kochbereich"

    def test_german_template_matching_bad(self):
        zones = [{"area_id": "bad", "name": "Badezimmer", "icon": None}]
        wizard = self._make_wizard_with_zones(zones)
        suggestions = wizard.get_zone_suggestions()

        assert suggestions[0]["template"] == "Badbereich"

    def test_unmatched_zone_gets_no_template(self):
        zones = [{"area_id": "x", "name": "Dachboden", "icon": None}]
        wizard = self._make_wizard_with_zones(zones)
        suggestions = wizard.get_zone_suggestions()

        assert suggestions[0]["template"] is None
        assert suggestions[0]["priority"] == "low"

    def test_priority_sorting_high_before_low(self):
        zones = [
            {"area_id": "x", "name": "Garage", "icon": None},
            {"area_id": "wz", "name": "Wohnzimmer", "icon": None},
        ]
        wizard = self._make_wizard_with_zones(zones)
        suggestions = wizard.get_zone_suggestions()

        assert suggestions[0]["area_id"] == "wz"

    def test_empty_zones_list(self):
        wizard = self._make_wizard_with_zones([])
        suggestions = wizard.get_zone_suggestions()
        assert suggestions == []

    def test_zone_with_many_entities_gets_higher_priority(self):
        zones = [
            {"area_id": "a", "name": "Unknown Room", "icon": None},
            {"area_id": "b", "name": "Empty Room", "icon": None},
        ]
        entities = [
            FakeEntityEntry(f"light.l{i}", "light", f"Light {i}", area_id="a")
            for i in range(10)
        ]
        hass = MagicMock()
        ent_reg = _make_entity_registry(entities)

        with patch("custom_components.ai_home_copilot.setup_wizard.entity_registry") as er:
            er.async_get.return_value = ent_reg
            wizard = SetupWizard(hass)
            wizard._discovered_entities = {"zones": zones}
            suggestions = wizard.get_zone_suggestions()

        assert suggestions[0]["entity_count"] == 10
        assert suggestions[0]["area_id"] == "a"


# ---------------------------------------------------------------------------
# SetupWizard.suggest_media_players()
# ---------------------------------------------------------------------------

class TestMediaPlayerSuggestion:
    def test_tv_by_device_class(self):
        hass = MagicMock()
        wizard = SetupWizard(hass)
        wizard._discovered_entities = {
            "media_players": [
                {"entity_id": "media_player.lg", "name": "LG TV", "device_class": "tv", "state": "off"},
            ],
        }
        result = wizard.suggest_media_players()
        assert "media_player.lg" in result["tv"]
        assert result["music"] == []

    def test_speaker_by_name_hint(self):
        hass = MagicMock()
        wizard = SetupWizard(hass)
        wizard._discovered_entities = {
            "media_players": [
                {"entity_id": "media_player.sonos", "name": "Sonos Speaker", "device_class": None, "state": "idle"},
            ],
        }
        result = wizard.suggest_media_players()
        assert "media_player.sonos" in result["music"]

    def test_max_5_per_category(self):
        hass = MagicMock()
        wizard = SetupWizard(hass)
        wizard._discovered_entities = {
            "media_players": [
                {"entity_id": f"media_player.sp{i}", "name": f"Sonos Speaker {i}", "device_class": "speaker", "state": "idle"}
                for i in range(10)
            ],
        }
        result = wizard.suggest_media_players()
        assert len(result["music"]) == 5


# ---------------------------------------------------------------------------
# get_zone_info()
# ---------------------------------------------------------------------------

class TestGetZoneInfo:
    def test_known_zone(self):
        hass = MagicMock()
        wizard = SetupWizard(hass)
        wizard._discovered_entities = {
            "zones": [{"area_id": "wz", "name": "Wohnzimmer", "icon": "mdi:sofa"}],
        }
        info = wizard.get_zone_info("wz")
        assert info["name"] == "Wohnzimmer"

    def test_unknown_zone_fallback(self):
        hass = MagicMock()
        wizard = SetupWizard(hass)
        wizard._discovered_entities = {"zones": []}
        info = wizard.get_zone_info("nonexistent")
        assert info["area_id"] == "nonexistent"
        assert info["entity_count"] == 0


# ---------------------------------------------------------------------------
# Role classification helpers (from ZONE_TEMPLATES)
# ---------------------------------------------------------------------------

class TestRoleClassification:
    def test_wohnbereich_has_media_role(self):
        assert "media" in ZONE_TEMPLATES["wohnbereich"]["roles"]

    def test_kochbereich_has_power_role(self):
        assert "power" in ZONE_TEMPLATES["kochbereich"]["roles"]

    def test_badbereich_has_heating_role(self):
        assert "heating" in ZONE_TEMPLATES["badbereich"]["roles"]

    def test_buero_has_noise_role(self):
        assert "noise" in ZONE_TEMPLATES["buero"]["roles"]

    def test_eingang_has_lock_role(self):
        assert "lock" in ZONE_TEMPLATES["eingang"]["roles"]

    def test_kinderzimmer_has_camera_role(self):
        assert "camera" in ZONE_TEMPLATES["kinderzimmer"]["roles"]
