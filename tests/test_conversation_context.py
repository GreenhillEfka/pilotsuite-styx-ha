"""Tests for the Conversation Context Builder.

Tests system prompt construction from live HA data.

Run with: pytest tests/test_conversation_context.py -v
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


def _make_hass_with_states(states=None):
    """Create a mock hass with states."""
    hass = MagicMock()
    hass.data = {}
    hass.config.location_name = "Paradiesgarten"

    all_states = states or []

    def async_all(domain=None):
        if domain:
            return [s for s in all_states if s.entity_id.startswith(f"{domain}.")]
        return all_states

    hass.states.async_all = async_all
    hass.states.get = MagicMock(return_value=None)
    return hass


class TestConversationContext:
    """Tests for conversation_context module."""

    def test_get_home_name(self):
        """Test extracting home name from HA config."""
        from custom_components.ai_home_copilot.conversation_context import _get_home_name

        hass = MagicMock()
        hass.config.location_name = "Paradiesgarten"
        assert _get_home_name(hass) == "Paradiesgarten"

    def test_get_home_name_fallback(self):
        """Test home name fallback."""
        from custom_components.ai_home_copilot.conversation_context import _get_home_name

        hass = MagicMock()
        hass.config.location_name = None
        assert _get_home_name(hass) == "Zuhause"

    def test_build_persons_section(self):
        """Test persons section from person.* entities."""
        from custom_components.ai_home_copilot.conversation_context import _build_persons_section

        state1 = MagicMock()
        state1.entity_id = "person.andreas"
        state1.state = "home"
        state1.attributes = {"friendly_name": "Andreas"}

        state2 = MagicMock()
        state2.entity_id = "person.efka"
        state2.state = "not_home"
        state2.attributes = {"friendly_name": "Efka"}

        hass = _make_hass_with_states([state1, state2])
        result = _build_persons_section(hass)

        assert "=== Personen ===" in result
        assert "Andreas: zuhause" in result
        assert "Efka: not_home" in result

    def test_build_persons_section_empty(self):
        """Test persons section with no person entities."""
        from custom_components.ai_home_copilot.conversation_context import _build_persons_section

        hass = _make_hass_with_states([])
        result = _build_persons_section(hass)
        assert result == ""

    def test_build_weather_section(self):
        """Test weather section."""
        from custom_components.ai_home_copilot.conversation_context import _build_weather_section

        state = MagicMock()
        state.entity_id = "weather.home"
        state.state = "cloudy"
        state.attributes = {"friendly_name": "Home", "temperature": 9.1}

        hass = _make_hass_with_states([state])
        result = _build_weather_section(hass)

        assert "=== Wetter ===" in result
        assert "cloudy" in result
        assert "9.1" in result

    def test_build_weather_section_empty(self):
        """Test weather section with no weather entity."""
        from custom_components.ai_home_copilot.conversation_context import _build_weather_section

        hass = _make_hass_with_states([])
        result = _build_weather_section(hass)
        assert result == ""

    def test_build_mood_section_from_coordinator(self):
        """Test mood section from coordinator data."""
        from custom_components.ai_home_copilot.conversation_context import _build_mood_section

        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test"

        coordinator = MagicMock()
        coordinator.data = {
            "mood": {
                "mood": "relax",
                "confidence": 0.85,
                "dimensions": {"comfort": 0.78, "joy": 0.45},
            }
        }

        hass.data = {"ai_home_copilot": {"test": {"coordinator": coordinator}}}

        result = _build_mood_section(hass, entry)
        assert "=== Stimmung ===" in result
        assert "relax" in result
        assert "85%" in result

    def test_build_mood_section_from_live_mood(self):
        """Test mood section from live_mood data."""
        from custom_components.ai_home_copilot.conversation_context import _build_mood_section

        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test"

        hass.data = {
            "ai_home_copilot": {
                "test": {
                    "live_mood": {
                        "wohnbereich": {"comfort": 0.8, "joy": 0.5, "frugality": 0.6},
                        "kueche": {"comfort": 0.7, "joy": 0.4, "frugality": 0.5},
                    }
                }
            }
        }

        result = _build_mood_section(hass, entry)
        assert "Komfort: 75%" in result
        assert "Freude: 45%" in result
        assert "Sparsamkeit: 55%" in result

    def test_build_mood_section_empty(self):
        """Test mood section with no data."""
        from custom_components.ai_home_copilot.conversation_context import _build_mood_section

        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test"
        hass.data = {"ai_home_copilot": {"test": {}}}

        result = _build_mood_section(hass, entry)
        assert result == ""

    def test_build_analysis_section(self):
        """Test automation analysis section."""
        from custom_components.ai_home_copilot.conversation_context import _build_analysis_section

        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test"

        hass.data = {
            "ai_home_copilot": {
                "test": {
                    "automation_analysis": {
                        "automation_count": 110,
                        "repair_hints": [1, 2, 3, 4, 5],
                    }
                }
            }
        }

        result = _build_analysis_section(hass, entry)
        assert "110 gesamt" in result
        assert "5 Reparatur-Hinweise" in result

    def test_build_analysis_section_empty(self):
        """Test analysis section with no data."""
        from custom_components.ai_home_copilot.conversation_context import _build_analysis_section

        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test"
        hass.data = {"ai_home_copilot": {"test": {}}}

        result = _build_analysis_section(hass, entry)
        assert result == ""

    def test_build_suggestions_section_from_analysis(self):
        """Test suggestions section from automation analysis."""
        from custom_components.ai_home_copilot.conversation_context import _build_suggestions_section

        hass = MagicMock()
        entry = MagicMock()
        entry.entry_id = "test"

        hass.data = {
            "ai_home_copilot": {
                "test": {
                    "automation_analysis": {
                        "suggestions": [
                            {"title": "CO2-Lueftung"},
                            {"title": "Fenster-Heizung"},
                            {"title": "Solar"},
                        ]
                    }
                }
            }
        }

        result = _build_suggestions_section(hass, entry)
        assert "=== Vorschlaege" in result
        assert "CO2-Lueftung" in result

    def test_state_val_helper(self):
        """Test _state_val helper."""
        from custom_components.ai_home_copilot.conversation_context import _state_val

        hass = MagicMock()
        state = MagicMock()
        state.state = "22.5"
        hass.states.get.return_value = state

        assert _state_val(hass, "sensor.temp") == "22.5"

    def test_state_val_unavailable(self):
        """Test _state_val with unavailable entity."""
        from custom_components.ai_home_copilot.conversation_context import _state_val

        hass = MagicMock()
        state = MagicMock()
        state.state = "unavailable"
        hass.states.get.return_value = state

        assert _state_val(hass, "sensor.temp") == ""

    def test_state_val_none(self):
        """Test _state_val with nonexistent entity."""
        from custom_components.ai_home_copilot.conversation_context import _state_val

        hass = MagicMock()
        hass.states.get.return_value = None

        assert _state_val(hass, "sensor.temp") == ""

    @pytest.mark.asyncio
    async def test_async_build_system_prompt(self):
        """Test full system prompt building."""
        from custom_components.ai_home_copilot.conversation_context import async_build_system_prompt

        person_state = MagicMock()
        person_state.entity_id = "person.andreas"
        person_state.state = "home"
        person_state.attributes = {"friendly_name": "Andreas"}

        weather_state = MagicMock()
        weather_state.entity_id = "weather.home"
        weather_state.state = "cloudy"
        weather_state.attributes = {"friendly_name": "Home", "temperature": 9.1}

        hass = _make_hass_with_states([person_state, weather_state])
        entry = MagicMock()
        entry.entry_id = "test"
        entry.options = {"assistant_name": "Styx"}
        entry.data = {}

        hass.data = {"ai_home_copilot": {"test": {}}}

        prompt = await async_build_system_prompt(hass, entry)

        assert "Styx" in prompt
        assert "Paradiesgarten" in prompt
        assert "Andreas" in prompt
        assert len(prompt) <= 2000

    @pytest.mark.asyncio
    async def test_prompt_truncation(self):
        """Test that prompt is truncated to max length."""
        from custom_components.ai_home_copilot.conversation_context import async_build_system_prompt

        hass = _make_hass_with_states([])
        entry = MagicMock()
        entry.entry_id = "test"
        entry.options = {}
        entry.data = {}
        hass.data = {"ai_home_copilot": {"test": {}}}

        prompt = await async_build_system_prompt(hass, entry)
        assert len(prompt) <= 2000
