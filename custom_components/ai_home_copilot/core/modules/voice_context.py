"""Voice Context Module - Speech Control and TTS for PilotSuite.

Features:
- Voice Command Parser: Parse voice commands into actions
- TTS Output: Text-to-speech via HA TTS services
- Voice State Tracking: Track voice assistant states
- Command Templates: Predefined command patterns
- Character System Integration: voice_tone aware responses
- Suggestions Integration: Context-aware voice suggestions
"""
from __future__ import annotations

import logging
import re
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from homeassistant.core import HomeAssistant, State

from ..core.module import CopilotModule, ModuleContext
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# Voice tone configurations mapped to character presets
VOICE_TONE_CONFIGS = {
    "formal": {
        "greeting": "Guten Tag. Wie kann ich behilflich sein?",
        "confirmations": ["Verstanden.", "Erledigt.", "Befehl ausgeführt."],
        "errors": ["Befehl konnte nicht ausgeführt werden.", "Ein Fehler ist aufgetreten."],
        "prefix": "",
    },
    "friendly": {
        "greeting": "Hey! Was kann ich für dich tun?",
        "confirmations": ["Klar!",
         "Mach ich gerne!", "Alles klar!", "Ist erledigt!"],
        "errors": ["Hm, das hat nicht geklappt.", "Da ist etwas schief gelaufen."],
        "prefix": "Super Idee! ",
    },
    "casual": {
        "greeting": "Ja, was gibt's?",
        "confirmations": ["Done.", "Geht klar.", "Fertig.", "Ja."],
        "errors": ["Hat nicht funktioniert.", "Fehler."],
        "prefix": "",
    },
    "cautious": {
        "greeting": "Ich bin bereit. Wie kann ich helfen?",
        "confirmations": ["Befehl ausgeführt. Soll ich bestätigen?", "Erledigt. Alles sicher."],
        "errors": ["Befehl konnte nicht ausgeführt werden. Sicherheitshalber abgebrochen."],
        "prefix": "Ich empfehle: ",
    },
}


# Voice command patterns (compiled for performance)
class CommandPattern:
    """Compiled command pattern with metadata."""
    
    def __init__(self, intent: str, patterns: list[str], entities_extractor: Optional[Callable] = None):
        self.intent = intent
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.entities_extractor = entities_extractor
    
    def match(self, text: str) -> tuple[bool, dict]:
        """Match text against patterns and extract entities."""
        for pattern in self.patterns:
            match = pattern.search(text)
            if match:
                entities = {}
                if self.entities_extractor and match.groups():
                    entities = self.entities_extractor(match)
                return True, entities
        return False, {}


# Entity extractors
def extract_temperature(match: re.Match) -> dict:
    return {"temperature": match.group(1)}

def extract_scene(match: re.Match) -> dict:
    return {"scene": match.group(1)}

def extract_automation(match: re.Match) -> dict:
    return {"automation": match.group(1)}

def extract_entity(match: re.Match) -> dict:
    return {"entity": match.group(1)}


# Command patterns
COMMAND_PATTERNS = [
    # Light controls
    CommandPattern("light_on", [
        r"schalte[s]?\s+(?:das\s+)?licht\s+an",
        r"licht\s+an",
        r"mach[e]?\s+(?:das\s+)?licht\s+an",
        r"turn\s+on\s+(?:the\s+)?light",
        r"lights?\s+on",
        r"licht\s+einschalten",
    ]),
    CommandPattern("light_off", [
        r"schalte[s]?\s+(?:das\s+)?licht\s+aus",
        r"licht\s+aus",
        r"mach[e]?\s+(?:das\s+)?licht\s+aus",
        r"turn\s+off\s+(?:the\s+)?light",
        r"lights?\s+off",
        r"licht\s+ausschalten",
    ]),
    CommandPattern("light_toggle", [
        r"schalte[s]?\s+(?:das\s+)?licht",
        r"toggle\s+licht",
        r"toggle\s+the\s+light",
        r"licht\s+umschalten",
    ]),
    
    # Climate controls
    CommandPattern("climate_warmer", [
        r"wärmer",
        r"heizer",
        r"wärmer\s+machen",
        r"turn\s+up\s+(?:the\s+)?heat",
        r"wärmer\s+stellen",
        r"temperatur\s+erhöhen",
    ]),
    CommandPattern("climate_cooler", [
        r"kühler",
        r"kälter",
        r"kühler\s+machen",
        r"turn\s+down\s+(?:the\s+)?heat",
        r"kühler\s+stellen",
        r"temperatur\s+verringern",
    ]),
    CommandPattern("climate_set", [
        r"setze\s+temperatur\s+auf\s+(\d+)",
        r"temperatur\s+(\d+)\s+grad",
        r"set\s+temperature\s+to\s+(\d+)",
        r"temperatur\s+auf\s+(\d+)\s+grad",
    ], extract_temperature),
    
    # Media controls
    CommandPattern("media_play", [
        r"\bplay\b",
        r"wiedergabe\s+start",
        r"abspielen",
        r"starten",
    ]),
    CommandPattern("media_pause", [
        r"\bpause\b",
        r"pausieren",
    ]),
    CommandPattern("media_stop", [
        r"\bstop\b",
        r"stopp",
        r"stoppen",
    ]),
    CommandPattern("media_volume_up", [
        r"lauter",
        r"volume\s+up",
        r"Lauter\s+stellen",
    ]),
    CommandPattern("media_volume_down", [
        r"leiser",
        r"volume\s+down",
        r"Leiser\s+stellen",
    ]),
    
    # Scene activations
    CommandPattern("scene_activate", [
        r"aktiviere\s+szene\s+(.+)",
        r"szene\s+(.+)",
        r"activate\s+scene\s+(.+)",
        r"scene\s+(.+)",
    ], extract_scene),
    
    # Automation triggers
    CommandPattern("automation_trigger", [
        r"starte\s+automation\s+(.+)",
        r"trigger\s+automation\s+(.+)",
        r"führe\s+automation\s+aus\s+(.+)",
        r"automation\s+(.+)\s+starten",
    ], extract_automation),
    
    # Status queries
    CommandPattern("status_query", [
        r"wie\s+ist\s+der\s+status\s+von\s+(.+)",
        r"status\s+von\s+(.+)",
        r"what\s+is\s+the\s+status\s+of\s+(.+)",
        r"ist\s+(.+)\s+an",
        r"is\s+(.+)\s+on",
        r"wie\s+steht\s+(.+)",
    ], extract_entity),
    
    # Help
    CommandPattern("help", [
        r"\bhilfe\b",
        r"\bhelp\b",
        r"was\s+kannst\s+du",
        r"was\s+geht",
    ]),
    
    # Quick search integration
    CommandPattern("search", [
        r"suche\s+nach\s+(.+)",
        r"finde\s+(.+)",
        r"search\s+for\s+(.+)",
    ], extract_entity),
]


@dataclass
class VoiceCommand:
    """Parsed voice command."""
    intent: str
    entities: dict[str, str] = field(default_factory=dict)
    raw_text: str = ""
    confidence: float = 0.0


@dataclass
class TTSRequest:
    """TTS output request."""
    text: str
    entity_id: Optional[str] = None
    language: str = "de"
    cache: bool = True


class VoiceContextModule(CopilotModule):
    """Voice Context Module for speech control and TTS."""
    
    def __init__(self):
        self._command_handlers: dict[str, Callable] = {}
        self._tts_default_entity: Optional[str] = None
        self._character_service = None
        self._voice_tone = "neutral"
    
    @property
    def name(self) -> str:
        return "voice_context"
    
    @property
    def version(self) -> str:
        return "1.1.0"
    
    @property
    def voice_tone(self) -> str:
        """Get current voice tone."""
        return self._voice_tone
    
    def set_character_service(self, service) -> None:
        """Set character service for voice_tone integration."""
        self._character_service = service
        self._update_voice_tone()
    
    def _update_voice_tone(self) -> None:
        """Update voice tone from character service."""
        if self._character_service:
            try:
                preset = self._character_service.get_current_preset()
                self._voice_tone = preset.voice.tone
                _LOGGER.info("Voice tone set to: %s", self._voice_tone)
            except Exception as e:
                _LOGGER.debug("Could not get voice tone: %s", e)
    
    def _get_tone_config(self) -> dict:
        """Get voice tone configuration."""
        return VOICE_TONE_CONFIGS.get(self._voice_tone, VOICE_TONE_CONFIGS["formal"])
    
    def _format_response(self, key: str, default: str = "") -> str:
        """Format response text based on voice tone."""
        tone_config = self._get_tone_config()
        
        if key == "greeting":
            # Use character service greeting if available
            if self._character_service:
                try:
                    return self._character_service.get_greeting()
                except Exception:  # noqa: BLE001
                    pass
            return tone_config.get("greeting", default)
        
        elif key == "confirmations":
            if self._character_service:
                try:
                    return self._character_service.get_confirmation()
                except Exception:  # noqa: BLE001
                    pass
            return random.choice(tone_config.get("confirmations", [default]))
        
        elif key == "errors":
            if self._character_service:
                try:
                    preset = self._character_service.get_current_preset()
                    return random.choice(preset.voice.errors)
                except Exception:  # noqa: BLE001
                    pass
            return tone_config.get("errors", [default])[0]
        
        return default
    
    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the voice context module."""
        _LOGGER.info("Setting up Voice Context Module v%s", self.version)
        
        # Get character service if available
        try:
            if hasattr(ctx, 'coordinator') and ctx.coordinator:
                self._character_service = getattr(ctx.coordinator, 'character_service', None)
                if self._character_service:
                    self._update_voice_tone()
        except Exception as e:
            _LOGGER.debug("Character service not available: %s", e)
        
        # Initialize voice state
        hass_data = ctx.hass.data.setdefault(DOMAIN, {}).setdefault("voice_context", {})
        hass_data["initialized"] = True
        hass_data["last_command"] = None
        hass_data["tts_history"] = []
        hass_data["voice_tone"] = self._voice_tone
        
        # Find default TTS entity
        self._discover_tts_entities(ctx.hass)
        
        # Register services
        self._register_services(ctx.hass)
        
        _LOGGER.info("Voice Context Module initialized, tone: %s, TTS: %s", 
                    self._voice_tone, self._tts_default_entity)
    
    def _discover_tts_entities(self, hass: HomeAssistant) -> None:
        """Discover available TTS entities."""
        # Look for TTS entities (media_player with TTS capability)
        media_states = hass.states.async_all("media_player")
        
        # Priority: Sonos, then smart speakers, then any media player
        priorities = ["sonos", "google_home", "echo", "homepod"]
        
        for priority in priorities:
            for entity in media_states:
                entity_id = entity.entity_id.lower()
                if priority in entity_id:
                    self._tts_default_entity = entity.entity_id
                    _LOGGER.info("Found priority TTS entity: %s", entity.entity_id)
                    return
        
        # Check for TTS capability
        for entity in media_states:
            if entity.attributes.get("supported_features", 0) & 0x1000:  # MEDIA_FEATURE_TTS
                self._tts_default_entity = entity.entity_id
                _LOGGER.info("Found TTS capable entity: %s", entity.entity_id)
                return
        
        # Fallback: use first available
        if media_states:
            self._tts_default_entity = media_states[0].entity_id
            _LOGGER.info("Using fallback media player as TTS: %s", self._tts_default_entity)
    
    def _register_services(self, hass: HomeAssistant) -> None:
        """Register voice services."""
        
        async def parse_command_service(call) -> dict:
            """Parse a voice command."""
            text = call.data.get("text", "")
            result = self.parse_command(text)
            return {
                "intent": result.intent,
                "entities": result.entities,
                "raw_text": result.raw_text,
                "confidence": result.confidence,
            }
        
        async def speak_service(call) -> dict:
            """Speak text via TTS."""
            text = call.data.get("text", "")
            entity_id = call.data.get("entity_id", self._tts_default_entity)
            language = call.data.get("language", "de")
            
            success = await self.speak(hass, text, entity_id, language)
            
            # Store in history
            history = hass.data.get(DOMAIN, {}).get("voice_context", {}).get("tts_history", [])
            history.append({
                "text": text,
                "entity_id": entity_id,
                "success": success,
            })
            # Keep only last 50
            if len(history) > 50:
                history = history[-50:]
            
            return {"success": success, "text": text}
        
        async def execute_voice_command_service(call) -> dict:
            """Parse and execute a voice command."""
            text = call.data.get("text", "")
            
            # Parse command
            command = self.parse_command(text)
            
            # Execute based on intent
            result = await self._execute_intent(hass, command)
            
            # Store last command
            voice_data = hass.data.setdefault(DOMAIN, {}).setdefault("voice_context", {})
            voice_data["last_command"] = {
                "text": text,
                "intent": command.intent,
                "entities": command.entities,
            }
            
            return result
        
        async def get_voice_state_service(call) -> dict:
            """Get current voice state."""
            voice_data = hass.data.get(DOMAIN, {}).get("voice_context", {})
            return {
                "last_command": voice_data.get("last_command"),
                "tts_available": self._tts_default_entity is not None,
                "default_tts_entity": self._tts_default_entity,
                "voice_tone": self._voice_tone,
            }
        
        async def set_voice_tone_service(call) -> dict:
            """Set voice tone."""
            tone = call.data.get("tone", "formal")
            if tone in VOICE_TONE_CONFIGS:
                self._voice_tone = tone
                hass.data.setdefault(DOMAIN, {}).setdefault("voice_context", {})["voice_tone"] = tone
                return {"success": True, "voice_tone": tone}
            return {"success": False, "error": "Invalid tone"}
        
        # Register services
        hass.services.async_register(DOMAIN, "parse_command", parse_command_service)
        hass.services.async_register(DOMAIN, "speak", speak_service)
        hass.services.async_register(DOMAIN, "execute_command", execute_voice_command_service)
        hass.services.async_register(DOMAIN, "get_voice_state", get_voice_state_service)
        hass.services.async_register(DOMAIN, "set_voice_tone", set_voice_tone_service)
    
    def parse_command(self, text: str) -> VoiceCommand:
        """Parse voice command text into structured command."""
        text_lower = text.lower().strip()
        
        best_match = None
        best_score = 0.0
        
        # Try each intent pattern
        for cmd_pattern in COMMAND_PATTERNS:
            matched, entities = cmd_pattern.match(text_lower)
            if matched:
                # Calculate confidence based on pattern specificity
                # Longer patterns = more specific = higher confidence
                pattern_length = max(len(p.pattern) for p in cmd_pattern.patterns)
                score = min(pattern_length / (len(text_lower) + 1) * 2, 1.0)
                
                if score > best_score:
                    best_score = score
                    best_match = VoiceCommand(
                        intent=cmd_pattern.intent,
                        raw_text=text,
                        confidence=score,
                        entities=entities,
                    )
        
        # Default to unknown if no match
        if not best_match:
            best_match = VoiceCommand(
                intent="unknown",
                raw_text=text,
                confidence=0.0,
            )
        
        return best_match
    
    async def _execute_intent(self, hass: HomeAssistant, command: VoiceCommand) -> dict:
        """Execute a parsed voice command."""
        intent = command.intent
        entities = command.entities
        
        try:
            # Execute based on intent
            if intent == "light_on":
                await self._handle_light(hass, "on", entities)
                return {"success": True, "message": self._format_response("confirmations", "Licht eingeschaltet")}
            
            elif intent == "light_off":
                await self._handle_light(hass, "off", entities)
                return {"success": True, "message": self._format_response("confirmations", "Licht ausgeschaltet")}
            
            elif intent == "light_toggle":
                await self._handle_light(hass, "toggle", entities)
                return {"success": True, "message": self._format_response("confirmations", "Licht umgeschaltet")}
            
            elif intent == "climate_warmer":
                await self._handle_climate(hass, "warmer")
                return {"success": True, "message": self._format_response("confirmations", "Wärmer eingestellt")}
            
            elif intent == "climate_cooler":
                await self._handle_climate(hass, "cooler")
                return {"success": True, "message": self._format_response("confirmations", "Kühler eingestellt")}
            
            elif intent == "climate_set":
                temp = entities.get("temperature", "21")
                await self._handle_climate(hass, "set", temp)
                return {"success": True, "message": f"Temperatur auf {temp} Grad eingestellt"}
            
            elif intent == "media_play":
                await self._handle_media(hass, "play")
                return {"success": True, "message": self._format_response("confirmations", "Wiedergabe gestartet")}
            
            elif intent == "media_pause":
                await self._handle_media(hass, "pause")
                return {"success": True, "message": self._format_response("confirmations", "Wiedergabe pausiert")}
            
            elif intent == "media_stop":
                await self._handle_media(hass, "stop")
                return {"success": True, "message": self._format_response("confirmations", "Wiedergabe gestoppt")}
            
            elif intent == "media_volume_up":
                await self._handle_volume(hass, "up")
                return {"success": True, "message": self._format_response("confirmations", "Lauter gestellt")}
            
            elif intent == "media_volume_down":
                await self._handle_volume(hass, "down")
                return {"success": True, "message": self._format_response("confirmations", "Leiser gestellt")}
            
            elif intent == "scene_activate":
                scene = entities.get("scene", "")
                await self._handle_scene(hass, scene)
                return {"success": True, "message": f"Szene '{scene}' aktiviert"}
            
            elif intent == "automation_trigger":
                automation = entities.get("automation", "")
                await self._handle_automation(hass, automation)
                return {"success": True, "message": f"Automation '{automation}' gestartet"}
            
            elif intent == "status_query":
                entity = entities.get("entity", "")
                status = await self._handle_status(hass, entity)
                return {"success": True, "message": status}
            
            elif intent == "search":
                entity = entities.get("entity", "")
                results = await self._handle_search(hass, entity)
                return {"success": True, "message": results}
            
            elif intent == "help":
                return {
                    "success": True,
                    "message": self._get_help_text(),
                }
            
            else:
                return {
                    "success": False,
                    "message": self._format_response("errors", "Befehl nicht erkannt"),
                }
                
        except Exception as e:
            _LOGGER.error("Error executing voice command: %s", e)
            return {
                "success": False,
                "message": self._format_response("errors", f"Fehler: {str(e)}"),
            }
    
    async def _handle_light(self, hass: HomeAssistant, action: str, entities: dict) -> None:
        """Handle light commands."""
        light_entity = entities.get("light")
        
        if light_entity:
            # Find matching light
            lights = hass.states.async_all("light")
            target = None
            for light in lights:
                if light_entity in light.entity_id or light_entity in light.name.lower():
                    target = light.entity_id
                    break
            
            if target:
                service = "turn_on" if action == "on" else ("turn_off" if action == "off" else "toggle")
                await hass.services.async_call("light", service, {"entity_id": target})
        else:
            # Toggle all lights
            if action == "on":
                await hass.services.async_call("light", "turn_on", {"entity_id": "all"})
            elif action == "off":
                await hass.services.async_call("light", "turn_off", {"entity_id": "all"})
            else:
                await hass.services.async_call("light", "toggle", {"entity_id": "all"})
    
    async def _handle_climate(self, hass: HomeAssistant, action: str, value: Optional[str] = None) -> None:
        """Handle climate commands."""
        climates = hass.states.async_all("climate")
        
        if not climates:
            return
        
        target = climates[0].entity_id
        
        if action == "warmer":
            current = climates[0].attributes.get("temperature", 21)
            await hass.services.async_call("climate", "set_temperature", {
                "entity_id": target,
                "temperature": min(current + 1, 30),
            })
        elif action == "cooler":
            current = climates[0].attributes.get("temperature", 21)
            await hass.services.async_call("climate", "set_temperature", {
                "entity_id": target,
                "temperature": max(current - 1, 16),
            })
        elif action == "set" and value:
            await hass.services.async_call("climate", "set_temperature", {
                "entity_id": target,
                "temperature": int(value),
            })
    
    async def _handle_media(self, hass: HomeAssistant, action: str) -> None:
        """Handle media commands."""
        media_players = hass.states.async_all("media_player")
        
        if not media_players:
            return
        
        # Use active player or first available
        target = None
        for player in media_players:
            if player.state == "playing":
                target = player.entity_id
                break
        
        if not target:
            target = media_players[0].entity_id
        
        service_map = {
            "play": "media_play",
            "pause": "media_pause",
            "stop": "media_stop",
        }
        
        if action in service_map:
            await hass.services.async_call("media_player", service_map[action], {"entity_id": target})
    
    async def _handle_volume(self, hass: HomeAssistant, direction: str) -> None:
        """Handle volume commands."""
        media_players = hass.states.async_all("media_player")
        
        if not media_players:
            return
        
        # Find active player
        target = None
        current_volume = 0.5
        
        for player in media_players:
            if player.state == "playing":
                target = player.entity_id
                current_volume = player.attributes.get("volume_level", 0.5)
                break
        
        if not target:
            target = media_players[0].entity_id
        
        # Adjust volume
        if direction == "up":
            new_volume = min(current_volume + 0.1, 1.0)
        else:
            new_volume = max(current_volume - 0.1, 0.0)
        
        await hass.services.async_call("media_player", "volume_set", {
            "entity_id": target,
            "volume_level": new_volume,
        })
    
    async def _handle_scene(self, hass: HomeAssistant, scene_name: str) -> None:
        """Handle scene activation."""
        scenes = hass.states.async_all("scene")
        
        target = None
        for scene in scenes:
            if scene_name.lower() in scene.entity_id or scene_name.lower() in scene.name.lower():
                target = scene.entity_id
                break
        
        if target:
            await hass.services.async_call("scene", "turn_on", {"entity_id": target})
        else:
            # Try by entity ID pattern
            scene_entity_id = f"scene.{scene_name.lower().replace(' ', '_')}"
            await hass.services.async_call("scene", "turn_on", {"entity_id": scene_entity_id})
    
    async def _handle_automation(self, hass: HomeAssistant, automation_name: str) -> None:
        """Handle automation trigger."""
        automations = hass.states.async_all("automation")
        
        target = None
        for automation in automations:
            if automation_name.lower() in automation.entity_id or automation_name.lower() in automation.name.lower():
                target = automation.entity_id
                break
        
        if target:
            await hass.services.async_call("automation", "trigger", {"entity_id": target})
    
    async def _handle_status(self, hass: HomeAssistant, entity_name: str) -> str:
        """Handle status query."""
        entities = hass.states.async_all()
        
        target = None
        for entity in entities:
            if entity_name.lower() in entity.entity_id or entity_name.lower() in entity.name.lower():
                target = entity
                break
        
        if target:
            state_str = "an" if target.state == "on" else "aus"
            return f"{target.name} ist {state_str}"
        else:
            return f"Entität '{entity_name}' nicht gefunden"
    
    async def _handle_search(self, hass: HomeAssistant, query: str) -> str:
        """Handle search query - integrates with QuickSearchModule."""
        try:
            # Try to get quick search module
            quick_search = None
            if hasattr(self, '_quick_search_module'):
                quick_search = self._quick_search_module
            else:
                # Try to find via coordinator or direct call
                from .quick_search import QuickSearchModule
                quick_search = QuickSearchModule()
            
            if quick_search:
                results = await quick_search.async_combined_search(hass, query, limit=5)
                if results.results:
                    response = "Gefunden: "
                    response += ", ".join([r.title for r in results.results[:3]])
                    return response
                return f"Keine Ergebnisse für '{query}'"
        except Exception as e:
            _LOGGER.debug("Search error: %s", e)
        
        return f"Suche nach '{query}' nicht möglich"
    
    def _get_help_text(self) -> str:
        """Get help text for available commands."""
        return (
            "Verfügbare Befehle: "
            "Licht an/aus, Temperatur wärmer/kühler, "
            "Szene [name], Status von [gerät], "
            " Lauter/leiser, Suche nach [name], Hilfe"
        )
    
    async def speak(
        self,
        hass: HomeAssistant,
        text: str,
        entity_id: Optional[str] = None,
        language: str = "de",
    ) -> bool:
        """Speak text via TTS."""
        target_entity = entity_id or self._tts_default_entity
        
        if not target_entity:
            _LOGGER.warning("No TTS entity available")
            return False
        
        try:
            # Use TTS service
            await hass.services.async_call("tts", "speak", {
                "entity_id": target_entity,
                "message": text,
                "language": language,
            })
            return True
        except Exception as e:
            # Fallback to media player
            try:
                await hass.services.async_call("media_player", "play_media", {
                    "entity_id": target_entity,
                    "media_content_type": "music",
                    "media_content_id": f"https://translate.google.com/translate_tts?tl={language}&q={text}",
                })
                return True
            except Exception as e2:
                _LOGGER.error("TTS error: %s, fallback: %s", e, e2)
                return False
    
    async def async_generate_voice_suggestions(
        self,
        hass: HomeAssistant,
        context: str = "",
    ) -> list[dict[str, Any]]:
        """Generate voice suggestions based on context.
        
        Integrates with Character System for voice_tone aware formatting.
        """
        suggestions = []
        
        # Get active entities for context
        lights_on = [s for s in hass.states.async_all("light") if s.state == "on"]
        climate_on = hass.states.async_all("climate")
        
        # Time-based suggestions
        from datetime import datetime
        hour = datetime.now().hour
        
        if hour < 6 or hour > 22:
            suggestions.append({
                "type": "time_awareness",
                "text": "Es ist spät. Soll ich leiser sprechen?",
                "action": "set_voice_tone",
                "params": {"tone": "casual"},
                "confidence": 0.8,
            })
        
        # Energy saving suggestion
        if lights_on and hour > 23:
            suggestions.append({
                "type": "energy",
                "text": "Noch Lichter an. Soll ich sie ausschalten?",
                "action": "light_off",
                "confidence": 0.7,
            })
        
        # Format suggestions with character voice
        if self._character_service and suggestions:
            for suggestion in suggestions:
                suggestion["formatted_text"] = self._character_service.format_suggestion(suggestion["text"])
        
        return suggestions
    
    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the module."""
        # Remove services
        ctx.hass.services.async_remove(DOMAIN, "parse_command")
        ctx.hass.services.async_remove(DOMAIN, "speak")
        ctx.hass.services.async_remove(DOMAIN, "execute_command")
        ctx.hass.services.async_remove(DOMAIN, "get_voice_state")
        ctx.hass.services.async_remove(DOMAIN, "set_voice_tone")
        
        _LOGGER.info("Voice Context Module unloaded")
        return True
