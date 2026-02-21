"""Tests for VoiceContextModule — command parsing, voice tone, TTS discovery.

Covers:
- CommandPattern regex matching and entity extraction
- VoiceCommand confidence scoring
- Voice tone config switching
- Response formatting with character service fallback
- TTS entity discovery (priority-based)
- parse_command for all 15+ intents
"""
import re
from unittest.mock import MagicMock, AsyncMock, patch
import pytest


# ──────────────────────────────────────────────────────────────────────────
# Import the voice context module (needs HA mocks from conftest)
# ──────────────────────────────────────────────────────────────────────────

from custom_components.ai_home_copilot.core.modules.voice_context import (
    CommandPattern,
    VoiceCommand,
    TTSRequest,
    VoiceContextModule,
    VOICE_TONE_CONFIGS,
    COMMAND_PATTERNS,
    extract_temperature,
    extract_scene,
    extract_automation,
    extract_entity,
)


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────

@pytest.fixture
def module():
    """Create a fresh VoiceContextModule."""
    return VoiceContextModule()


@pytest.fixture
def mock_state():
    """Create a mock HA state."""
    def _make(entity_id, state="on", name=None, attributes=None):
        s = MagicMock()
        s.entity_id = entity_id
        s.state = state
        s.name = name or entity_id.split(".")[-1].replace("_", " ").title()
        s.attributes = attributes or {}
        return s
    return _make


# ──────────────────────────────────────────────────────────────────────────
# Tests: CommandPattern
# ──────────────────────────────────────────────────────────────────────────

class TestCommandPattern:
    def test_simple_match(self):
        cp = CommandPattern("test", [r"hello\s+world"])
        matched, entities = cp.match("hello world")
        assert matched is True
        assert entities == {}

    def test_no_match(self):
        cp = CommandPattern("test", [r"hello\s+world"])
        matched, entities = cp.match("goodbye world")
        assert matched is False

    def test_case_insensitive(self):
        cp = CommandPattern("test", [r"hello"])
        matched, _ = cp.match("HELLO")
        assert matched is True

    def test_entity_extraction(self):
        def extractor(m):
            return {"value": m.group(1)}
        cp = CommandPattern("test", [r"set\s+(\d+)"], extractor)
        matched, entities = cp.match("set 42")
        assert matched is True
        assert entities["value"] == "42"

    def test_multiple_patterns(self):
        cp = CommandPattern("test", [r"foo", r"bar", r"baz"])
        assert cp.match("contains foo")[0] is True
        assert cp.match("contains bar")[0] is True
        assert cp.match("contains baz")[0] is True
        assert cp.match("contains qux")[0] is False

    def test_no_extractor_with_groups(self):
        cp = CommandPattern("test", [r"value\s+(\d+)"])
        matched, entities = cp.match("value 42")
        assert matched is True
        assert entities == {}


# ──────────────────────────────────────────────────────────────────────────
# Tests: Entity Extractors
# ──────────────────────────────────────────────────────────────────────────

class TestExtractors:
    def test_extract_temperature(self):
        m = re.search(r"(\d+)", "set 22 grad")
        result = extract_temperature(m)
        assert result == {"temperature": "22"}

    def test_extract_scene(self):
        m = re.search(r"szene\s+(.+)", "szene abend")
        result = extract_scene(m)
        assert result == {"scene": "abend"}

    def test_extract_automation(self):
        m = re.search(r"automation\s+(.+)", "automation morgens")
        result = extract_automation(m)
        assert result == {"automation": "morgens"}

    def test_extract_entity(self):
        m = re.search(r"status\s+von\s+(.+)", "status von lampe")
        result = extract_entity(m)
        assert result == {"entity": "lampe"}


# ──────────────────────────────────────────────────────────────────────────
# Tests: VoiceContextModule — parse_command
# ──────────────────────────────────────────────────────────────────────────

class TestParseCommand:
    def test_light_on_german(self, module):
        cmd = module.parse_command("Licht an")
        assert cmd.intent == "light_on"
        assert cmd.confidence > 0

    def test_light_off_german(self, module):
        cmd = module.parse_command("Licht aus")
        assert cmd.intent == "light_off"

    def test_light_on_english(self, module):
        cmd = module.parse_command("turn on the light")
        assert cmd.intent == "light_on"

    def test_light_off_english(self, module):
        cmd = module.parse_command("lights off")
        assert cmd.intent == "light_off"

    def test_light_toggle(self, module):
        cmd = module.parse_command("Licht umschalten")
        assert cmd.intent == "light_toggle"

    def test_climate_warmer(self, module):
        cmd = module.parse_command("wärmer")
        assert cmd.intent == "climate_warmer"

    def test_climate_cooler(self, module):
        cmd = module.parse_command("kühler")
        assert cmd.intent == "climate_cooler"

    def test_climate_set_temperature(self, module):
        cmd = module.parse_command("setze temperatur auf 22")
        assert cmd.intent == "climate_set"
        assert cmd.entities.get("temperature") == "22"

    def test_climate_set_english(self, module):
        cmd = module.parse_command("set temperature to 25")
        assert cmd.intent == "climate_set"
        assert cmd.entities.get("temperature") == "25"

    def test_media_play(self, module):
        cmd = module.parse_command("play")
        assert cmd.intent == "media_play"

    def test_media_pause(self, module):
        cmd = module.parse_command("pause")
        assert cmd.intent == "media_pause"

    def test_media_stop(self, module):
        cmd = module.parse_command("stopp")
        assert cmd.intent == "media_stop"

    def test_volume_up(self, module):
        cmd = module.parse_command("lauter")
        assert cmd.intent == "media_volume_up"

    def test_volume_down(self, module):
        cmd = module.parse_command("leiser")
        assert cmd.intent == "media_volume_down"

    def test_scene_activate(self, module):
        cmd = module.parse_command("aktiviere szene abend")
        assert cmd.intent == "scene_activate"
        assert cmd.entities.get("scene") == "abend"

    def test_automation_trigger(self, module):
        cmd = module.parse_command("starte automation morgenroutine")
        assert cmd.intent == "automation_trigger"
        assert cmd.entities.get("automation") == "morgenroutine"

    def test_status_query(self, module):
        cmd = module.parse_command("wie ist der status von Lampe")
        assert cmd.intent == "status_query"
        assert cmd.entities.get("entity") is not None

    def test_search(self, module):
        cmd = module.parse_command("suche nach zigbee sensor")
        assert cmd.intent == "search"
        assert "zigbee sensor" in cmd.entities.get("entity", "")

    def test_help(self, module):
        cmd = module.parse_command("hilfe")
        assert cmd.intent == "help"

    def test_help_english(self, module):
        cmd = module.parse_command("help")
        assert cmd.intent == "help"

    def test_unknown_command(self, module):
        cmd = module.parse_command("random nonsense text xyz")
        assert cmd.intent == "unknown"
        assert cmd.confidence == 0.0

    def test_raw_text_preserved(self, module):
        cmd = module.parse_command("Licht an")
        assert cmd.raw_text == "Licht an"

    def test_empty_input(self, module):
        cmd = module.parse_command("")
        assert cmd.intent == "unknown"

    def test_confidence_range(self, module):
        cmd = module.parse_command("Licht an")
        assert 0.0 <= cmd.confidence <= 1.0

    def test_case_insensitive_matching(self, module):
        cmd = module.parse_command("LICHT AN")
        assert cmd.intent == "light_on"


# ──────────────────────────────────────────────────────────────────────────
# Tests: Voice Tone
# ──────────────────────────────────────────────────────────────────────────

class TestVoiceTone:
    def test_default_tone(self, module):
        assert module.voice_tone == "neutral"

    def test_tone_config_formal(self, module):
        module._voice_tone = "formal"
        config = module._get_tone_config()
        assert "Guten Tag" in config["greeting"]
        assert len(config["confirmations"]) > 0

    def test_tone_config_friendly(self, module):
        module._voice_tone = "friendly"
        config = module._get_tone_config()
        assert "Hey" in config["greeting"]

    def test_tone_config_casual(self, module):
        module._voice_tone = "casual"
        config = module._get_tone_config()
        assert "Done." in config["confirmations"]

    def test_tone_config_cautious(self, module):
        module._voice_tone = "cautious"
        config = module._get_tone_config()
        assert "Sicherheitshalber" in config["errors"][0]

    def test_unknown_tone_falls_back_to_formal(self, module):
        module._voice_tone = "nonexistent"
        config = module._get_tone_config()
        assert config == VOICE_TONE_CONFIGS["formal"]

    def test_format_response_greeting(self, module):
        module._voice_tone = "friendly"
        greeting = module._format_response("greeting")
        assert "Hey" in greeting

    def test_format_response_errors(self, module):
        module._voice_tone = "casual"
        error = module._format_response("errors", "default err")
        assert "funktioniert" in error or "Fehler" in error

    def test_format_response_unknown_key(self, module):
        result = module._format_response("nonexistent", "fallback")
        assert result == "fallback"

    def test_set_character_service(self, module):
        mock_service = MagicMock()
        mock_preset = MagicMock()
        mock_preset.voice.tone = "friendly"
        mock_service.get_current_preset.return_value = mock_preset

        module.set_character_service(mock_service)
        assert module.voice_tone == "friendly"

    def test_character_service_error_fallback(self, module):
        mock_service = MagicMock()
        mock_service.get_current_preset.side_effect = Exception("unavailable")

        module.set_character_service(mock_service)
        # Should keep default tone
        assert module.voice_tone == "neutral"

    def test_format_greeting_with_character_service(self, module):
        mock_service = MagicMock()
        mock_service.get_greeting.return_value = "Custom greeting"
        module._character_service = mock_service

        result = module._format_response("greeting")
        assert result == "Custom greeting"

    def test_format_confirmation_with_character_service(self, module):
        mock_service = MagicMock()
        mock_service.get_confirmation.return_value = "Custom ok"
        module._character_service = mock_service

        result = module._format_response("confirmations")
        assert result == "Custom ok"


# ──────────────────────────────────────────────────────────────────────────
# Tests: TTS Discovery
# ──────────────────────────────────────────────────────────────────────────

class TestTTSDiscovery:
    def test_discover_sonos_priority(self, module, mock_state):
        hass = MagicMock()
        hass.states.async_all.return_value = [
            mock_state("media_player.generic_speaker"),
            mock_state("media_player.sonos_living_room"),
        ]

        module._discover_tts_entities(hass)
        assert module._tts_default_entity == "media_player.sonos_living_room"

    def test_discover_google_home(self, module, mock_state):
        hass = MagicMock()
        hass.states.async_all.return_value = [
            mock_state("media_player.generic_speaker"),
            mock_state("media_player.google_home_kitchen"),
        ]

        module._discover_tts_entities(hass)
        assert module._tts_default_entity == "media_player.google_home_kitchen"

    def test_discover_tts_capability(self, module, mock_state):
        hass = MagicMock()
        hass.states.async_all.return_value = [
            mock_state("media_player.generic", attributes={"supported_features": 0x1000}),
        ]

        module._discover_tts_entities(hass)
        assert module._tts_default_entity == "media_player.generic"

    def test_fallback_to_first(self, module, mock_state):
        hass = MagicMock()
        hass.states.async_all.return_value = [
            mock_state("media_player.random_player"),
        ]

        module._discover_tts_entities(hass)
        assert module._tts_default_entity == "media_player.random_player"

    def test_no_media_players(self, module):
        hass = MagicMock()
        hass.states.async_all.return_value = []

        module._discover_tts_entities(hass)
        assert module._tts_default_entity is None


# ──────────────────────────────────────────────────────────────────────────
# Tests: Speak (TTS)
# ──────────────────────────────────────────────────────────────────────────

class TestSpeak:
    @pytest.mark.asyncio
    async def test_speak_no_entity(self, module):
        hass = MagicMock()
        result = await module.speak(hass, "hello")
        assert result is False

    @pytest.mark.asyncio
    async def test_speak_with_default_entity(self, module):
        module._tts_default_entity = "media_player.sonos"
        hass = MagicMock()
        hass.services.async_call = AsyncMock()

        result = await module.speak(hass, "Hallo Welt")
        assert result is True
        hass.services.async_call.assert_called_once_with("tts", "speak", {
            "entity_id": "media_player.sonos",
            "message": "Hallo Welt",
            "language": "de",
        })

    @pytest.mark.asyncio
    async def test_speak_custom_entity(self, module):
        module._tts_default_entity = "media_player.sonos"
        hass = MagicMock()
        hass.services.async_call = AsyncMock()

        result = await module.speak(hass, "test", entity_id="media_player.kitchen")
        assert result is True
        call_args = hass.services.async_call.call_args
        assert call_args[0][2]["entity_id"] == "media_player.kitchen"

    @pytest.mark.asyncio
    async def test_speak_tts_failure_fallback(self, module):
        module._tts_default_entity = "media_player.sonos"
        hass = MagicMock()
        # First call (TTS) fails, second (media_player) succeeds
        hass.services.async_call = AsyncMock(
            side_effect=[Exception("TTS failed"), None]
        )

        result = await module.speak(hass, "test")
        assert result is True
        assert hass.services.async_call.call_count == 2


# ──────────────────────────────────────────────────────────────────────────
# Tests: Module Properties
# ──────────────────────────────────────────────────────────────────────────

class TestModuleProperties:
    def test_name(self, module):
        assert module.name == "voice_context"

    def test_version(self, module):
        assert module.version == "1.1.0"

    def test_help_text(self, module):
        help_text = module._get_help_text()
        assert "Licht" in help_text
        assert "Temperatur" in help_text
        assert "Szene" in help_text


# ──────────────────────────────────────────────────────────────────────────
# Tests: VoiceCommand and TTSRequest dataclasses
# ──────────────────────────────────────────────────────────────────────────

class TestDataclasses:
    def test_voice_command_defaults(self):
        cmd = VoiceCommand(intent="test")
        assert cmd.intent == "test"
        assert cmd.entities == {}
        assert cmd.raw_text == ""
        assert cmd.confidence == 0.0

    def test_voice_command_full(self):
        cmd = VoiceCommand(
            intent="light_on",
            entities={"light": "kitchen"},
            raw_text="Licht an",
            confidence=0.9,
        )
        assert cmd.intent == "light_on"
        assert cmd.entities["light"] == "kitchen"

    def test_tts_request_defaults(self):
        req = TTSRequest(text="hello")
        assert req.text == "hello"
        assert req.entity_id is None
        assert req.language == "de"
        assert req.cache is True

    def test_tts_request_custom(self):
        req = TTSRequest(
            text="test",
            entity_id="media_player.sonos",
            language="en",
            cache=False,
        )
        assert req.language == "en"
        assert req.cache is False


# ──────────────────────────────────────────────────────────────────────────
# Tests: Command Patterns Coverage
# ──────────────────────────────────────────────────────────────────────────

class TestCommandPatternsCoverage:
    """Ensure all defined COMMAND_PATTERNS have at least one matching test."""

    def test_all_intents_reachable(self, module):
        """Verify each defined intent can be matched by at least one text."""
        test_inputs = {
            "light_on": "schalte das licht an",
            "light_off": "schalte das licht aus",
            "light_toggle": "toggle licht",
            "climate_warmer": "wärmer machen",
            "climate_cooler": "kühler machen",
            "climate_set": "setze temperatur auf 21",
            "media_play": "play",
            "media_pause": "pause",
            "media_stop": "stopp",
            "media_volume_up": "lauter",
            "media_volume_down": "leiser",
            "scene_activate": "aktiviere szene film",
            "automation_trigger": "starte automation morgenroutine",
            "status_query": "status von lampe",
            "help": "hilfe",
            "search": "suche nach sensor",
        }

        for expected_intent, text in test_inputs.items():
            cmd = module.parse_command(text)
            assert cmd.intent == expected_intent, (
                f"Expected intent '{expected_intent}' for text '{text}', "
                f"got '{cmd.intent}'"
            )
