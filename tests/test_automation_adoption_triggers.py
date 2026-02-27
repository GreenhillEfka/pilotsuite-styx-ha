"""Tests for Automation Adoption trigger parsing.

Tests YAML parsing, trigger extraction, and full automation config building.

Run with: pytest tests/test_automation_adoption_triggers.py -v
"""
import pytest
from unittest.mock import MagicMock


class TestYamlTriggerParsing:
    """Tests for YAML trigger and automation parsing."""

    def test_parse_yaml_triggers_simple(self):
        """Test parsing simple trigger from YAML."""
        from custom_components.ai_home_copilot.core.modules.automation_adoption import (
            AutomationAdoptionModule,
        )

        yaml_str = """\
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
"""
        triggers = AutomationAdoptionModule._parse_yaml_triggers(yaml_str)
        assert len(triggers) == 1
        assert triggers[0]["platform"] == "state"
        assert triggers[0]["entity_id"] == "binary_sensor.motion"

    def test_parse_yaml_triggers_multiple(self):
        """Test parsing multiple triggers."""
        from custom_components.ai_home_copilot.core.modules.automation_adoption import (
            AutomationAdoptionModule,
        )

        yaml_str = """\
trigger:
  - platform: time
    at: "06:00:00"
    id: morning
  - platform: time
    at: "22:00:00"
    id: night
action:
  - service: climate.set_temperature
"""
        triggers = AutomationAdoptionModule._parse_yaml_triggers(yaml_str)
        assert len(triggers) == 2
        assert triggers[0]["platform"] == "time"
        assert triggers[1]["at"] == "22:00:00"

    def test_parse_yaml_triggers_sun(self):
        """Test parsing sun event triggers."""
        from custom_components.ai_home_copilot.core.modules.automation_adoption import (
            AutomationAdoptionModule,
        )

        yaml_str = """\
trigger:
  - platform: sun
    event: sunrise
    offset: "+00:15:00"
action:
  - service: cover.open_cover
"""
        triggers = AutomationAdoptionModule._parse_yaml_triggers(yaml_str)
        assert len(triggers) == 1
        assert triggers[0]["platform"] == "sun"
        assert triggers[0]["event"] == "sunrise"

    def test_parse_yaml_triggers_invalid(self):
        """Test parsing returns empty list for invalid YAML."""
        from custom_components.ai_home_copilot.core.modules.automation_adoption import (
            AutomationAdoptionModule,
        )

        triggers = AutomationAdoptionModule._parse_yaml_triggers("not: [valid: yaml: {{")
        assert triggers == []

    def test_parse_yaml_triggers_empty(self):
        """Test parsing returns empty list for empty string."""
        from custom_components.ai_home_copilot.core.modules.automation_adoption import (
            AutomationAdoptionModule,
        )

        triggers = AutomationAdoptionModule._parse_yaml_triggers("")
        assert triggers == []

    def test_parse_full_yaml_automation(self):
        """Test parsing a complete YAML automation."""
        from custom_components.ai_home_copilot.core.modules.automation_adoption import (
            AutomationAdoptionModule,
        )

        yaml_str = """\
alias: "Auto-Licht bei Bewegung"
description: "Schaltet Licht ein bei Bewegung."
trigger:
  - platform: state
    entity_id: binary_sensor.motion_wohn
    to: "on"
condition:
  - condition: state
    entity_id: light.wohn
    state: "off"
action:
  - service: light.turn_on
    target:
      entity_id: light.wohn
mode: restart
"""
        result = AutomationAdoptionModule._parse_full_yaml_automation(yaml_str)

        assert result is not None
        assert result["alias"] == "Auto-Licht bei Bewegung"
        assert len(result["trigger"]) == 1
        assert len(result["action"]) == 1
        assert len(result["condition"]) == 1
        assert result["mode"] == "restart"

    def test_parse_full_yaml_no_trigger(self):
        """Test parsing returns None if no triggers."""
        from custom_components.ai_home_copilot.core.modules.automation_adoption import (
            AutomationAdoptionModule,
        )

        yaml_str = """\
action:
  - service: light.turn_on
"""
        result = AutomationAdoptionModule._parse_full_yaml_automation(yaml_str)
        assert result is None

    def test_parse_full_yaml_no_action(self):
        """Test parsing returns None if no actions."""
        from custom_components.ai_home_copilot.core.modules.automation_adoption import (
            AutomationAdoptionModule,
        )

        yaml_str = """\
trigger:
  - platform: state
    entity_id: binary_sensor.motion
"""
        result = AutomationAdoptionModule._parse_full_yaml_automation(yaml_str)
        assert result is None

    def test_parse_full_yaml_invalid(self):
        """Test parsing returns None for invalid YAML."""
        from custom_components.ai_home_copilot.core.modules.automation_adoption import (
            AutomationAdoptionModule,
        )

        result = AutomationAdoptionModule._parse_full_yaml_automation("{{invalid")
        assert result is None


class TestBuildAutomationConfig:
    """Tests for _build_automation_config with YAML parsing."""

    def test_build_config_with_yaml(self):
        """Test building config from example_yaml."""
        from custom_components.ai_home_copilot.core.modules.automation_adoption import (
            AutomationAdoptionModule,
        )

        module = AutomationAdoptionModule()

        yaml_str = """\
alias: "Heizplan (kueche)"
trigger:
  - platform: time
    at: "06:00:00"
action:
  - service: climate.set_temperature
    target:
      entity_id: climate.kueche
    data:
      temperature: 21
mode: single
"""
        config = module._build_automation_config(
            "test_id", "Heizplan", [], {"example_yaml": yaml_str}
        )

        assert config["alias"] == "Heizplan (kueche)"
        assert len(config["trigger"]) == 1
        assert config["trigger"][0]["platform"] == "time"
        assert len(config["action"]) == 1

    def test_build_config_without_yaml(self):
        """Test building config from structured actions."""
        from custom_components.ai_home_copilot.core.modules.automation_adoption import (
            AutomationAdoptionModule,
        )

        module = AutomationAdoptionModule()

        actions = [
            {
                "domain": "light",
                "action": "turn_on",
                "entity_ids": ["light.wohn"],
                "brightness_pct": 80,
            }
        ]

        config = module._build_automation_config(
            "test_id", "Turn on light", actions, {}
        )

        assert config["alias"] == "Styx: Turn on light"
        assert len(config["action"]) == 1
        assert config["action"][0]["service"] == "light.turn_on"
        assert config["action"][0]["data"]["brightness_pct"] == 80
        assert config["trigger"] == []  # No YAML to parse

    def test_build_config_partial_yaml_triggers_only(self):
        """Test building config with YAML that has triggers but parse_full fails."""
        from custom_components.ai_home_copilot.core.modules.automation_adoption import (
            AutomationAdoptionModule,
        )

        module = AutomationAdoptionModule()

        # YAML with trigger but no action → parse_full returns None
        # But _parse_yaml_triggers still extracts the trigger
        yaml_str = """\
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: "on"
"""
        actions = [{"domain": "light", "action": "turn_on", "entity_ids": ["light.wohn"]}]
        config = module._build_automation_config(
            "test_id", "Motion Light", actions, {"example_yaml": yaml_str}
        )

        # Full parse fails (no action in YAML), falls back to structured
        assert len(config["action"]) == 1
        # But triggers are extracted from YAML
        assert len(config["trigger"]) == 1
        assert config["trigger"][0]["platform"] == "state"
