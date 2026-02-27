"""Tests for the Unified Dashboard Pipeline.

Tests dashboard generation, zone loading, person discovery,
infrastructure discovery, and YAML writing.

Run with: pytest tests/test_dashboard_pipeline.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from pathlib import Path


class TestDashboardPipelineHelpers:
    """Tests for dashboard_pipeline helper functions."""

    def test_zone_v2_to_dict(self):
        """Test converting HabitusZoneV2 to dict."""
        from custom_components.ai_home_copilot.dashboard_pipeline import _zone_v2_to_dict

        zone = MagicMock()
        zone.zone_id = "wohnbereich"
        zone.name = "Wohnbereich"
        zone.entities = {"temperature": ["sensor.temp_1"], "lights": ["light.wohn"]}

        result = _zone_v2_to_dict(zone)
        assert result["zone_id"] == "wohnbereich"
        assert result["name"] == "Wohnbereich"
        assert "temperature" in result["entities"]

    def test_zone_v2_to_dict_plain_dict(self):
        """Test converting a plain dict (passthrough)."""
        from custom_components.ai_home_copilot.dashboard_pipeline import _zone_v2_to_dict

        zone = {"zone_id": "kueche", "name": "Kueche", "entities": {}}
        result = _zone_v2_to_dict(zone)
        assert result["zone_id"] == "kueche"

    def test_discover_persons(self):
        """Test dynamic person discovery."""
        from custom_components.ai_home_copilot.dashboard_pipeline import _discover_persons

        hass = MagicMock()
        state1 = MagicMock()
        state1.entity_id = "person.andreas"
        state1.attributes = {"friendly_name": "Andreas"}
        state2 = MagicMock()
        state2.entity_id = "person.efka"
        state2.attributes = {"friendly_name": "Efka"}

        hass.states.async_all.return_value = [state1, state2]

        persons = _discover_persons(hass)
        assert len(persons) == 2
        assert persons[0]["name"] == "Andreas"
        assert persons[1]["entity_id"] == "person.efka"

    def test_discover_persons_empty(self):
        """Test person discovery with no persons."""
        from custom_components.ai_home_copilot.dashboard_pipeline import _discover_persons

        hass = MagicMock()
        hass.states.async_all.return_value = []

        persons = _discover_persons(hass)
        assert persons == []

    def test_discover_infrastructure_energy(self):
        """Test infrastructure discovery categorizes energy entities."""
        from custom_components.ai_home_copilot.dashboard_pipeline import _discover_infrastructure

        hass = MagicMock()
        state = MagicMock()
        state.entity_id = "sensor.power_consumption"
        state.attributes = {"device_class": "power", "friendly_name": "Power"}
        hass.states.async_all.return_value = [state]

        infra = _discover_infrastructure(hass)
        assert len(infra["energy"]) == 1
        assert infra["energy"][0]["entity_id"] == "sensor.power_consumption"

    def test_discover_infrastructure_heating(self):
        """Test infrastructure discovery categorizes climate entities."""
        from custom_components.ai_home_copilot.dashboard_pipeline import _discover_infrastructure

        hass = MagicMock()
        state = MagicMock()
        state.entity_id = "climate.living_room"
        state.attributes = {"device_class": "", "friendly_name": "Living Room"}
        hass.states.async_all.return_value = [state]

        infra = _discover_infrastructure(hass)
        assert len(infra["heating"]) == 1

    def test_discover_infrastructure_security(self):
        """Test infrastructure discovery categorizes security entities."""
        from custom_components.ai_home_copilot.dashboard_pipeline import _discover_infrastructure

        hass = MagicMock()
        state = MagicMock()
        state.entity_id = "binary_sensor.smoke_detector"
        state.attributes = {"device_class": "smoke", "friendly_name": "Smoke"}
        hass.states.async_all.return_value = [state]

        infra = _discover_infrastructure(hass)
        assert len(infra["security"]) == 1

    def test_discover_infrastructure_weather(self):
        """Test infrastructure discovery categorizes weather entities."""
        from custom_components.ai_home_copilot.dashboard_pipeline import _discover_infrastructure

        hass = MagicMock()
        state = MagicMock()
        state.entity_id = "weather.home"
        state.attributes = {"device_class": "", "friendly_name": "Home Weather"}
        hass.states.async_all.return_value = [state]

        infra = _discover_infrastructure(hass)
        assert len(infra["weather"]) == 1

    def test_discover_infrastructure_camera(self):
        """Test cameras are categorized under security."""
        from custom_components.ai_home_copilot.dashboard_pipeline import _discover_infrastructure

        hass = MagicMock()
        state = MagicMock()
        state.entity_id = "camera.front_door"
        state.attributes = {"device_class": "", "friendly_name": "Front Door Cam"}
        hass.states.async_all.return_value = [state]

        infra = _discover_infrastructure(hass)
        assert len(infra["security"]) == 1
        assert infra["security"][0]["entity_id"] == "camera.front_door"


class TestDashboardGenerator3Tab:
    """Tests for the 3-tab generator with dynamic parameters."""

    def test_generate_full_dashboard_default(self):
        """Test generate_full_dashboard with default parameters."""
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_full_dashboard,
        )

        result = generate_full_dashboard(zones=[])
        assert result["title"] == "PilotSuite"
        assert len(result["views"]) == 3
        assert result["views"][0]["title"] == "Habitus"
        assert result["views"][1]["title"] == "Hausverwaltung"
        assert result["views"][2]["title"] == "Styx"

    def test_generate_with_dynamic_persons(self):
        """Test habitus tab with dynamic persons list."""
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_habitus_tab,
        )

        persons = [
            {"entity_id": "person.test_user", "name": "Test User"},
        ]
        result = generate_habitus_tab(zones=[], persons=persons)

        # Find persons card
        found = False
        for card in result["cards"]:
            if card.get("title") == "Personen":
                found = True
                assert len(card["entities"]) == 1
                assert card["entities"][0]["entity"] == "person.test_user"
        assert found

    def test_generate_without_persons_uses_fallback(self):
        """Test habitus tab uses hardcoded persons when none provided."""
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_habitus_tab,
        )

        result = generate_habitus_tab(zones=[], persons=None)
        for card in result["cards"]:
            if card.get("title") == "Personen":
                assert len(card["entities"]) == 5  # Hardcoded fallback
                break

    def test_generate_hausverwaltung_with_infrastructure(self):
        """Test dynamic Hausverwaltung tab."""
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_hausverwaltung_tab,
        )

        infra = {
            "energy": [{"entity_id": "sensor.power", "name": "Power"}],
            "heating": [{"entity_id": "climate.thermostat", "name": "Thermostat"}],
            "security": [],
            "devices": [],
            "network": [],
            "weather": [{"entity_id": "weather.home", "name": "Home"}],
        }

        result = generate_hausverwaltung_tab(infrastructure=infra)
        assert result["title"] == "Hausverwaltung"
        # Should have dynamic sections
        card_types = [c.get("type") for c in result["cards"]]
        assert "entities" in card_types

    def test_generate_hausverwaltung_fallback(self):
        """Test Hausverwaltung tab falls back to hardcoded without infrastructure."""
        from custom_components.ai_home_copilot.dashboard_cards.pilotsuite_3tab_generator import (
            generate_hausverwaltung_tab,
        )

        result = generate_hausverwaltung_tab(infrastructure=None)
        assert result["title"] == "Hausverwaltung"
        assert len(result["cards"]) >= 5  # All hardcoded sections


class TestDashboardPipelineLoadZones:
    """Tests for _load_zones function."""

    def test_load_zones_from_config_json(self):
        """Test loading zones from zones_config.json."""
        from custom_components.ai_home_copilot.dashboard_pipeline import _load_zones

        hass = MagicMock()
        entry = MagicMock()
        hass.data = {}  # No ZoneStore

        zones = _load_zones(hass, entry)
        # Should load from file (may be empty in test env)
        assert isinstance(zones, list)

    def test_load_zones_from_store_v2(self):
        """Test loading zones from ZoneStore V2."""
        from custom_components.ai_home_copilot.dashboard_pipeline import _load_zones

        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test_entry"

        mock_zone = MagicMock()
        mock_zone.zone_id = "wohnbereich"
        mock_zone.name = "Wohnbereich"
        mock_zone.entities = {"temperature": ["sensor.temp"]}

        store = MagicMock()
        store.async_get_zones_v2.return_value = [mock_zone]

        hass.data = {
            "ai_home_copilot": {
                "test_entry": {
                    "habitus_zones_store_v2": store,
                }
            }
        }

        zones = _load_zones(hass, entry)
        assert len(zones) == 1
        assert zones[0]["zone_id"] == "wohnbereich"
