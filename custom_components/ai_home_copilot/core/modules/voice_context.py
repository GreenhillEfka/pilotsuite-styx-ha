"""Voice Context Module - Speech Control and TTS for AI Home CoPilot.

Features:
- Voice Command Parser: Parse voice commands into actions
- TTS Output: Text-to-speech via HA TTS services
- Voice State Tracking: Track voice assistant states
- Command Templates: Predefined command patterns
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.entity import get_entity_id

from ..core.module import CopilotModule, ModuleContext
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# Voice command patterns
COMMAND_PATTERNS = {
    # Light controls
    "light_on": [
        r"schalte das licht an",
        r"licht an",
        r"mach das licht an",
        r"turn on the light",
        r"lights on",
    ],
    "light_off": [
        r"schalte das licht aus",
        r"licht aus",
        r"mach das licht aus",
        r"turn off the light",
        r"lights off",
    ],
    "light_toggle": [
        r"schalte das licht",
        r"toggle licht",
        r"toggle the light",
    ],
    
    # Climate controls
    "climate_warmer": [
        r"wärmer",
        r"heizer",
        r"warmer",
        r"warmer machen",
        r"turn up the heat",
        r"warmer",
    ],
    "climate_cooler": [
        r"kühler",
        r"kälter",
        r"kühler machen",
        r"turn down the heat",
        r"cooler",
    ],
    "climate_set": [
        r"setze temperatur auf (\d+)",
        r"temperatur (\d+) grad",
        r"set temperature to (\d+)",
    ],
    
    # Media controls
    "media_play": [
        r"play",
        r"wiedergabe",
        r"abspielen",
        r"start",
    ],
    "media_pause": [
        r"pause",
        r"pausieren",
    ],
    "media_stop": [
        r"stop",
        r"stopp",
        r"stoppen",
    ],
    "media_volume_up": [
        r"lauter",
        r"volume up",
        r" Lauter",
    ],
    "media_volume_down": [
        r"leiser",
        r"volume down",
    ],
    
    # Scene activations
    "scene_activate": [
        r"aktiviere szene (.+)",
        r"szene (.+)",
        r"activate scene (.+)",
        r"scene (.+)",
    ],
    
    # Automation triggers
    "automation_trigger": [
        r"starte automation (.+)",
        r"trigger automation (.+)",
        r"führe automation aus (.+)",
    ],
    
    # Status queries
    "status_query": [
        r"wie ist der status von (.+)",
        r"status von (.+)",
        r"what is the status of (.+)",
        r"ist (.+) an",
        r"is (.+) on",
    ],
    
    # Help
    "help": [
        r"hilfe",
        r"help",
        r"was kannst du",
        r"what can you do",
    ],
}


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
    entity_id: Optional[str] = None  # TTS entity to use
    language: str = "de"
    cache: bool = True


class VoiceContextModule(CopilotModule):
    """Voice Context Module for speech control and TTS."""
    
    @property
    def name(self) -> str:
        return "voice_context"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def __init__(self):
        self._command_handlers: dict[str, Callable] = {}
        self._tts_default_entity: Optional[str] = None
    
    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the voice context module."""
        _LOGGER.info("Setting up Voice Context Module")
        
        # Initialize voice state
        hass_data = ctx.hass.data.setdefault(DOMAIN, {}).setdefault("voice_context", {})
        hass_data["initialized"] = True
        hass_data["last_command"] = None
        hass_data["tts_history"] = []
        
        # Find default TTS entity
        self._discover_tts_entities(ctx.hass)
        
        # Register services
        self._register_services(ctx.hass)
        
        _LOGGER.info("Voice Context Module initialized, default TTS: %s", self._tts_default_entity)
    
    def _discover_tts_entities(self, hass: HomeAssistant) -> None:
        """Discover available TTS entities."""
        # Look for TTS entities (media_player with TTS capability)
        media_states = hass.states.async_all("media_player")
        
        for entity in media_states:
            # Check if it supports TTS
            if entity.attributes.get("supported_features", 0) & 0x1000:  # MEDIA_FEATURE_TTS
                self._tts_default_entity = entity.entity_id
                _LOGGER.info("Found TTS entity: %s", entity.entity_id)
                return
        
        # Fallback: try to find any Sonos or smart speaker
        for entity in media_states:
            device_class = entity.attributes.get("device_class")
            if device_class in ["speaker", "tv"]:
                self._tts_default_entity = entity.entity_id
                _LOGGER.info("Using media player as TTS: %s", entity.entity_id)
                return
    
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
            hass.data[DOMAIN]["voice_context"]["tts_history"].append({
                "text": text,
                "entity_id": entity_id,
                "success": success,
            })
            
            return {"success": success, "text": text}
        
        async def execute_voice_command_service(call) -> dict:
            """Parse and execute a voice command."""
            text = call.data.get("text", "")
            
            # Parse command
            command = self.parse_command(text)
            
            # Execute based on intent
            result = await self._execute_intent(hass, command)
            
            # Store last command
            hass.data[DOMAIN]["voice_context"]["last_command"] = {
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
            }
        
        # Register services
        hass.services.async_register(DOMAIN, "parse_command", parse_command_service)
        hass.services.async_register(DOMAIN, "speak", speak_service)
        hass.services.async_register(DOMAIN, "execute_command", execute_voice_command_service)
        hass.services.async_register(DOMAIN, "get_voice_state", get_voice_state_service)
    
    def parse_command(self, text: str) -> VoiceCommand:
        """Parse voice command text into structured command."""
        text_lower = text.lower().strip()
        
        best_match = None
        best_score = 0.0
        
        # Try each intent pattern
        for intent, patterns in COMMAND_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    # Calculate confidence based on pattern specificity
                    score = len(pattern) / (len(text_lower) + 1)
                    
                    if score > best_score:
                        best_score = score
                        best_match = VoiceCommand(
                            intent=intent,
                            raw_text=text,
                            confidence=min(score * 10, 1.0),
                        )
                        
                        # Extract captured groups as entities
                        if match.groups():
                            if intent == "climate_set":
                                best_match.entities["temperature"] = match.group(1)
                            elif intent == "scene_activate":
                                best_match.entities["scene"] = match.group(1)
                            elif intent == "automation_trigger":
                                best_match.entities["automation"] = match.group(1)
                            elif intent == "status_query":
                                best_match.entities["entity"] = match.group(1)
        
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
            if intent == "light_on":
                # Find and turn on lights
                await self._handle_light(hass, "on", entities)
                return {"success": True, "message": "Licht eingeschaltet"}
            
            elif intent == "light_off":
                await self._handle_light(hass, "off", entities)
                return {"success": True, "message": "Licht ausgeschaltet"}
            
            elif intent == "light_toggle":
                await self._handle_light(hass, "toggle", entities)
                return {"success": True, "message": "Licht umgeschaltet"}
            
            elif intent == "climate_warmer":
                await self._handle_climate(hass, "warmer")
                return {"success": True, "message": "Wärmer eingestellt"}
            
            elif intent == "climate_cooler":
                await self._handle_climate(hass, "cooler")
                return {"success": True, "message": "Kühler eingestellt"}
            
            elif intent == "climate_set":
                temp = entities.get("temperature", "21")
                await self._handle_climate(hass, "set", temp)
                return {"success": True, "message": f"Temperatur auf {temp} Grad eingestellt"}
            
            elif intent == "media_play":
                await self._handle_media(hass, "play")
                return {"success": True, "message": "Wiedergabe gestartet"}
            
            elif intent == "media_pause":
                await self._handle_media(hass, "pause")
                return {"success": True, "message": "Wiedergabe pausiert"}
            
            elif intent == "media_stop":
                await self._handle_media(hass, "stop")
                return {"success": True, "message": "Wiedergabe gestoppt"}
            
            elif intent == "media_volume_up":
                await self._handle_volume(hass, "up")
                return {"success": True, "message": "Lauter gestellt"}
            
            elif intent == "media_volume_down":
                await self._handle_volume(hass, "down")
                return {"success": True, "message": "Leiser gestellt"}
            
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
            
            elif intent == "help":
                return {
                    "success": True,
                    "message": self._get_help_text(),
                }
            
            else:
                return {
                    "success": False,
                    "message": "Befehl nicht erkannt",
                }
                
        except Exception as e:
            _LOGGER.error("Error executing voice command: %s", e)
            return {
                "success": False,
                "message": f"Fehler: {str(e)}",
            }
    
    async def _handle_light(self, hass: HomeAssistant, action: str, entities: dict) -> None:
        """Handle light commands."""
        # Find lights - could be specific or all
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
                if action == "on":
                    await hass.services.async_call("light", "turn_on", {"entity_id": target})
                elif action == "off":
                    await hass.services.async_call("light", "turn_off", {"entity_id": target})
                else:
                    await hass.services.async_call("light", "toggle", {"entity_id": target})
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
        
        if action == "play":
            await hass.services.async_call("media_player", "media_play", {"entity_id": target})
        elif action == "pause":
            await hass.services.async_call("media_player", "media_pause", {"entity_id": target})
        elif action == "stop":
            await hass.services.async_call("media_player", "media_stop", {"entity_id": target})
    
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
        # Find matching scene
        scenes = hass.states.async_all("scene")
        
        target = None
        for scene in scenes:
            if scene_name in scene.entity_id or scene_name in scene.name.lower():
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
            if automation_name in automation.entity_id or automation_name in automation.name.lower():
                target = automation.entity_id
                break
        
        if target:
            await hass.services.async_call("automation", "trigger", {"entity_id": target})
    
    async def _handle_status(self, hass: HomeAssistant, entity_name: str) -> str:
        """Handle status query."""
        # Find entity
        entities = hass.states.async_all()
        
        target = None
        for entity in entities:
            if entity_name in entity.entity_id or entity_name in entity.name.lower():
                target = entity
                break
        
        if target:
            state_str = "an" if target.state == "on" else "aus"
            return f"{target.name} ist {state_str}"
        else:
            return f"Entität '{entity_name}' nicht gefunden"
    
    def _get_help_text(self) -> str:
        """Get help text for available commands."""
        return (
            "Verfügbare Befehle: "
            "Licht an/aus, Temperatur wärmer/kühler, "
            "Szene [name], Status von [gerät], "
            " Lauter/leiser, Hilfe"
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
            _LOGGER.error("TTS error: %s", e)
            return False
    
    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the module."""
        # Remove services
        ctx.hass.services.async_remove(DOMAIN, "parse_command")
        ctx.hass.services.async_remove(DOMAIN, "speak")
        ctx.hass.services.async_remove(DOMAIN, "execute_command")
        ctx.hass.services.async_remove(DOMAIN, "get_voice_state")
        
        _LOGGER.info("Voice Context Module unloaded")
        return True
