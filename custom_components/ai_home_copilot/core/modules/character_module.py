"""Character Module - Personality presets for PilotSuite.

This module provides character/personality management as a CopilotModule,
integrating with mood inference, suggestions, and voice interactions.

Architecture Note:
- This module was moved from core/character/service.py to follow
  the CopilotModule interface pattern.
- Provides a single source of truth for character configuration.
- Integrates with MoodModule for weighted mood calculations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.storage import Store

from ...const import DOMAIN
from ..module import CopilotModule, ModuleContext

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

# Storage
CHARACTER_STORAGE_VERSION = 1
CHARACTER_STORAGE_KEY = f"{DOMAIN}.character_config"


# Enums and Dataclasses
from enum import Enum
from dataclasses import dataclass, field


class CharacterMode(Enum):
    """Available character modes."""
    ASSISTANT = "assistant"      # Neutral, efficient, formal
    COMPANION = "companion"      # Warm, proactive, friendly
    GUARDIAN = "guardian"        # Security-focused, cautious
    EFFICIENCY = "efficiency"    # Optimization-focused, direct
    RELAXED = "relaxed"          # Calm, minimal suggestions


@dataclass
class MoodWeights:
    """Mood weight multipliers for character."""
    relax: float = 1.0
    focus: float = 1.0
    active: float = 1.0
    sleep: float = 1.0
    away: float = 1.0
    alert: float = 1.0
    social: float = 1.0
    recovery: float = 1.0


@dataclass
class SuggestionConfig:
    """Suggestion behavior for character."""
    frequency: str = "balanced"      # proactive, balanced, reactive, silent
    aggressiveness: float = 0.5      # 0.0 = wait for user, 1.0 = auto-execute
    auto_execute_threshold: float = 0.95  # Confidence needed for auto-execute
    max_per_hour: int = 5            # Max suggestions per hour
    quiet_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])


@dataclass
class VoiceConfig:
    """Voice behavior for character."""
    tone: str = "neutral"            # formal, friendly, casual, cautious
    greeting: str = "Bereit."
    goodbyes: List[str] = field(default_factory=lambda: ["Bis gleich."])
    confirmations: List[str] = field(default_factory=lambda: ["Erledigt.", "Verstanden."])
    errors: List[str] = field(default_factory=lambda: ["Das hat nicht geklappt."])
    suggestions_prefix: str = "Ich empfehle:"
    alerts_prefix: str = "Achtung:"


@dataclass
class AlertConfig:
    """Alert behavior for character."""
    security: bool = True
    energy: bool = True
    comfort: bool = True
    maintenance: bool = True
    safety_critical: bool = True  # Always on for guardian


@dataclass
class CharacterPreset:
    """A complete character preset."""
    name: CharacterMode
    display_name: str
    description: str
    mood_weights: MoodWeights
    suggestions: SuggestionConfig
    voice: VoiceConfig
    alerts: AlertConfig
    privacy_level: str = "balanced"  # strict, balanced, learning
    icon: str = "🤖"
    
    @classmethod
    def assistant(cls) -> "CharacterPreset":
        """Create assistant preset."""
        return cls(
            name=CharacterMode.ASSISTANT,
            display_name="Assistent",
            description="Neutral, effizient und sachlich. Hilft bei Bedarf.",
            mood_weights=MoodWeights(),
            suggestions=SuggestionConfig(
                frequency="reactive",
                aggressiveness=0.3,
                max_per_hour=3,
            ),
            voice=VoiceConfig(
                tone="formal",
                greeting="Guten Tag. Wie kann ich helfen?",
                suggestions_prefix="Vorschlag:",
            ),
            alerts=AlertConfig(),
            icon="🤖",
        )
    
    @classmethod
    def companion(cls) -> "CharacterPreset":
        """Create companion preset."""
        return cls(
            name=CharacterMode.COMPANION,
            display_name="Begleiter",
            description="Warm, proaktiv und freundlich. Kennt deine Vorlieben.",
            mood_weights=MoodWeights(
                relax=1.2,
                social=1.1,
                recovery=1.1,
            ),
            suggestions=SuggestionConfig(
                frequency="proactive",
                aggressiveness=0.6,
                max_per_hour=8,
                quiet_hours=[1, 2, 3, 4, 5],
            ),
            voice=VoiceConfig(
                tone="friendly",
                greeting="Hey! Wie kann ich helfen?",
                goodbyes=["Bis gleich!", "Gern geschehen!", "Schönen Tag!"],
                confirmations=["Alles klar!", "Mach ich!", "Erledigt! ✨"],
                suggestions_prefix="Ich habe da eine Idee:",
            ),
            alerts=AlertConfig(comfort=True, energy=True, security=True),
            icon="🦞",
        )
    
    @classmethod
    def guardian(cls) -> "CharacterPreset":
        """Create guardian preset."""
        return cls(
            name=CharacterMode.GUARDIAN,
            display_name="Wächter",
            description="Sicherheitsfokussiert und vorsichtig. Hält dein Zuhause sicher.",
            mood_weights=MoodWeights(
                alert=1.5,
                away=1.3,
            ),
            suggestions=SuggestionConfig(
                frequency="balanced",
                aggressiveness=0.4,
                auto_execute_threshold=0.99,
                max_per_hour=3,
            ),
            voice=VoiceConfig(
                tone="cautious",
                greeting="System aktiv. Alle Sensoren online.",
                suggestions_prefix="Sicherheitshinweis:",
                alerts_prefix="⚠️ Warnung:",
            ),
            alerts=AlertConfig(
                security=True,
                safety_critical=True,
                maintenance=True,
                energy=False,
                comfort=False,
            ),
            icon="🛡️",
        )
    
    @classmethod
    def efficiency(cls) -> "CharacterPreset":
        """Create efficiency preset."""
        return cls(
            name=CharacterMode.EFFICIENCY,
            display_name="Optimierer",
            description="Energiebewusst und direkt. Spart Ressourcen.",
            mood_weights=MoodWeights(
                away=1.3,
                sleep=1.2,
            ),
            suggestions=SuggestionConfig(
                frequency="proactive",
                aggressiveness=0.7,
                auto_execute_threshold=0.9,
                max_per_hour=10,
            ),
            voice=VoiceConfig(
                tone="direct",
                greeting="Bereit für Optimierung.",
                suggestions_prefix="Einsparpotenzial:",
            ),
            alerts=AlertConfig(energy=True, maintenance=True),
            icon="⚡",
        )
    
    @classmethod
    def relaxed(cls) -> "CharacterPreset":
        """Create relaxed preset."""
        return cls(
            name=CharacterMode.RELAXED,
            display_name="Entspannt",
            description="Ruhig und minimalistisch. Nur das Nötigste.",
            mood_weights=MoodWeights(
                relax=1.5,
                recovery=1.3,
            ),
            suggestions=SuggestionConfig(
                frequency="silent",
                aggressiveness=0.1,
                auto_execute_threshold=0.99,
                max_per_hour=2,
            ),
            voice=VoiceConfig(
                tone="casual",
                greeting="Alles gut.",
                goodbyes=["Bis dann."],
                confirmations=["Ok."],
                suggestions_prefix="Falls du magst:",
            ),
            alerts=AlertConfig(safety_critical=True),
            icon="😌",
        )


@dataclass
class CharacterConfig:
    """Runtime character configuration with persistence support."""
    current_mode: CharacterMode = CharacterMode.COMPANION
    custom_preset: Optional[CharacterPreset] = None
    
    def get_preset(self) -> CharacterPreset:
        """Get the active preset."""
        if self.custom_preset:
            return self.custom_preset
        
        presets = {
            CharacterMode.ASSISTANT: CharacterPreset.assistant,
            CharacterMode.COMPANION: CharacterPreset.companion,
            CharacterMode.GUARDIAN: CharacterPreset.guardian,
            CharacterMode.EFFICIENCY: CharacterPreset.efficiency,
            CharacterMode.RELAXED: CharacterPreset.relaxed,
        }
        return presets[self.current_mode]()


class CharacterModule(CopilotModule):
    """Character Module implementation as a CopilotModule.
    
    This module manages character presets and provides:
    - Character mode selection and persistence
    - Mood weight application
    - Suggestion filtering based on character settings
    - Voice formatting for responses
    - Alert configuration
    
    Integration points:
    - MoodModule: Uses character weights for mood calculations
    - VoiceContext: Uses voice config for TTS formatting
    - SuggestionPanel: Uses suggestion config for filtering
    """
    
    # Service schemas
    SET_MODE_SCHEMA = vol.Schema({
        vol.Required("mode"): vol.In([m.value for m in CharacterMode]),
    })
    
    SET_CUSTOM_SCHEMA = vol.Schema({
        vol.Required("name"): str,
        vol.Optional("display_name"): str,
        vol.Optional("mood_weights"): dict,
        vol.Optional("suggestions"): dict,
        vol.Optional("voice"): dict,
    })

    def __init__(self) -> None:
        """Initialize the character module."""
        self._hass: HomeAssistant | None = None
        self._entry_id: str | None = None
        self._config: CharacterConfig = CharacterConfig()
        self._presets: Dict[CharacterMode, CharacterPreset] = {}
        self._store: Store | None = None
        self._load_presets()

    @property
    def name(self) -> str:
        """Return module name."""
        return "character_module"
    
    @property
    def version(self) -> str:
        """Return module version."""
        return "0.1"
    
    def _load_presets(self) -> None:
        """Load all built-in presets."""
        self._presets = {
            CharacterMode.ASSISTANT: CharacterPreset.assistant(),
            CharacterMode.COMPANION: CharacterPreset.companion(),
            CharacterMode.GUARDIAN: CharacterPreset.guardian(),
            CharacterMode.EFFICIENCY: CharacterPreset.efficiency(),
            CharacterMode.RELAXED: CharacterPreset.relaxed(),
        }
    
    async def async_setup_entry(self, ctx: ModuleContext) -> bool:
        """Set up the character module for a config entry.
        
        Returns:
            True if setup was successful.
        """
        self._hass = ctx.hass
        self._entry_id = ctx.entry.entry_id
        
        # Initialize module data
        if DOMAIN not in ctx.hass.data:
            ctx.hass.data[DOMAIN] = {}
        
        if ctx.entry.entry_id not in ctx.hass.data[DOMAIN]:
            ctx.hass.data[DOMAIN][ctx.entry.entry_id] = {}
        
        entry_data = ctx.hass.data[DOMAIN][ctx.entry.entry_id]
        
        # Initialize storage
        self._store = Store(ctx.hass, CHARACTER_STORAGE_VERSION, CHARACTER_STORAGE_KEY)
        
        # Load persisted config
        await self._load_config()
        
        # Register module in hass.data for other modules to access
        entry_data["character_module"] = self
        entry_data["character_service"] = self  # Backward compat alias
        
        # Register services
        await self._register_services(ctx.hass, ctx.entry.entry_id)
        
        _LOGGER.info("Character module initialized for entry %s", ctx.entry.entry_id)
        return True

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the character module.
        
        Returns:
            True if unload was successful.
        """
        if ctx.hass is None or ctx.entry is None:
            _LOGGER.warning("Character module not properly initialized")
            return False
        
        try:
            entry_data = ctx.hass.data.get(DOMAIN, {}).get(ctx.entry.entry_id, {})
            
            # Persist current state before unload
            await self._save_config()
            
            # Clear data
            if "character_module" in entry_data:
                del entry_data["character_module"]
            if "character_service" in entry_data:
                del entry_data["character_service"]
            
            _LOGGER.info("Character module unloaded for entry %s", ctx.entry.entry_id)
            return True
            
        except Exception as e:
            _LOGGER.error("Error unloading character module: %s", e)
            return False

    async def _load_config(self) -> None:
        """Load configuration from HA storage."""
        if self._store is None:
            return
        
        data = await self._store.async_load() or {}
        
        # Get config for this entry
        entry_config = data.get(self._entry_id, {})
        
        if entry_config:
            mode_str = entry_config.get("current_mode", "companion")
            try:
                self._config.current_mode = CharacterMode(mode_str)
            except ValueError:
                _LOGGER.warning("Unknown character mode: %s, using companion", mode_str)
                self._config.current_mode = CharacterMode.COMPANION
            
            # Custom preset not persisted for simplicity
            self._config.custom_preset = None

    async def _save_config(self) -> None:
        """Save configuration to HA storage."""
        if self._store is None:
            return
        
        data = await self._store.async_load() or {}
        
        data[self._entry_id] = {
            "current_mode": self._config.current_mode.value,
        }
        
        await self._store.async_save(data)

    async def _register_services(self, hass: HomeAssistant, entry_id: str) -> None:
        """Register character module services."""
        
        # Service: set_character_mode
        service_name = f"set_character_mode_{entry_id}"
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN,
                service_name,
                self._handle_set_mode,
                schema=self.SET_MODE_SCHEMA
            )
        
        # Service: get_character_info
        service_name = f"get_character_info_{entry_id}"
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN,
                service_name,
                self._handle_get_info
            )

    async def _handle_set_mode(self, call: ServiceCall) -> None:
        """Handle set_character_mode service call."""
        mode_str = call.data.get("mode")
        
        try:
            mode = CharacterMode(mode_str)
            self._config.current_mode = mode
            self._config.custom_preset = None
            
            # Persist
            await self._save_config()
            
            _LOGGER.info("Character mode set to: %s", mode.value)
            
        except ValueError:
            _LOGGER.error("Invalid character mode: %s", mode_str)

    async def _handle_get_info(self, call: ServiceCall) -> Dict[str, Any]:
        """Handle get_character_info service call."""
        return self.to_dict()

    # Character Service API (for MoodModule and other consumers)
    
    def get_current_preset(self) -> CharacterPreset:
        """Get the current active preset."""
        if self._config.custom_preset:
            return self._config.custom_preset
        return self._presets.get(self._config.current_mode, CharacterPreset.companion())
    
    def set_mode(self, mode: CharacterMode) -> None:
        """Set the character mode."""
        self._config.current_mode = mode
        self._config.custom_preset = None
    
    def set_custom_preset(self, preset: CharacterPreset) -> None:
        """Set a custom preset."""
        self._config.custom_preset = preset
    
    def get_available_modes(self) -> List[Dict[str, Any]]:
        """Get list of available modes with info."""
        return [
            {
                "mode": mode.value,
                "display_name": preset.display_name,
                "description": preset.description,
                "icon": preset.icon,
            }
            for mode, preset in self._presets.items()
        ]
    
    def apply_mood_weights(self, base_mood: Dict[str, float]) -> Dict[str, float]:
        """Apply character mood weights to base mood scores."""
        preset = self.get_current_preset()
        weights = preset.mood_weights
        
        weighted_mood = {}
        for mood_type, score in base_mood.items():
            weight = getattr(weights, mood_type.lower(), 1.0)
            weighted_mood[mood_type] = score * weight
        
        return weighted_mood
    
    def should_suggest(self, hour: int, confidence: float, suggestion_count: int) -> bool:
        """Determine if a suggestion should be shown based on character settings."""
        preset = self.get_current_preset()
        suggestions = preset.suggestions
        
        # Check quiet hours
        if hour in suggestions.quiet_hours:
            return False
        
        # Check max suggestions
        if suggestion_count >= suggestions.max_per_hour:
            return False
        
        # Check frequency setting
        if suggestions.frequency == "silent":
            return False
        elif suggestions.frequency == "reactive":
            # Only show if explicitly requested or very high confidence
            return confidence >= 0.95
        elif suggestions.frequency == "proactive":
            # Show more suggestions
            return confidence >= 0.5
        else:  # balanced
            return confidence >= 0.7
    
    def should_auto_execute(self, confidence: float) -> bool:
        """Determine if a suggestion should be auto-executed."""
        preset = self.get_current_preset()
        threshold = preset.suggestions.auto_execute_threshold
        aggressiveness = preset.suggestions.aggressiveness
        
        # Higher aggressiveness = lower threshold
        effective_threshold = threshold - (aggressiveness * 0.1)
        return confidence >= effective_threshold
    
    def format_suggestion(self, suggestion_text: str) -> str:
        """Format a suggestion with character voice."""
        preset = self.get_current_preset()
        prefix = preset.voice.suggestions_prefix
        return f"{prefix} {suggestion_text}"
    
    def format_alert(self, alert_text: str, alert_type: str = "general") -> str:
        """Format an alert with character voice."""
        preset = self.get_current_preset()
        
        # Check if this alert type is enabled
        alerts = preset.alerts
        alert_type_map = {
            "security": alerts.security,
            "energy": alerts.energy,
            "comfort": alerts.comfort,
            "maintenance": alerts.maintenance,
            "safety_critical": alerts.safety_critical,
        }
        
        if not alert_type_map.get(alert_type, True):
            return ""  # Alert type not enabled
        
        prefix = preset.voice.alerts_prefix
        return f"{prefix} {alert_text}"
    
    def get_greeting(self) -> str:
        """Get character greeting."""
        preset = self.get_current_preset()
        return preset.voice.greeting
    
    def get_confirmation(self) -> str:
        """Get random confirmation message."""
        import random
        preset = self.get_current_preset()
        return random.choice(preset.voice.confirmations)
    
    def get_goodbye(self) -> str:
        """Get random goodbye message."""
        import random
        preset = self.get_current_preset()
        return random.choice(preset.voice.goodbyes)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export current configuration as dict."""
        preset = self.get_current_preset()
        return {
            "current_mode": self._config.current_mode.value,
            "preset": {
                "name": preset.name.value,
                "display_name": preset.display_name,
                "description": preset.description,
                "icon": preset.icon,
                "mood_weights": {
                    "relax": preset.mood_weights.relax,
                    "focus": preset.mood_weights.focus,
                    "active": preset.mood_weights.active,
                    "sleep": preset.mood_weights.sleep,
                    "away": preset.mood_weights.away,
                    "alert": preset.mood_weights.alert,
                    "social": preset.mood_weights.social,
                    "recovery": preset.mood_weights.recovery,
                },
                "suggestions": {
                    "frequency": preset.suggestions.frequency,
                    "aggressiveness": preset.suggestions.aggressiveness,
                    "max_per_hour": preset.suggestions.max_per_hour,
                },
                "voice": {
                    "tone": preset.voice.tone,
                    "greeting": preset.voice.greeting,
                },
            },
        }


# Module factory for dynamic loading
def create_module() -> CharacterModule:
    """Create a new CharacterModule instance."""
    return CharacterModule()


def get_character_module(hass, entry_id):
    """Return the CharacterModule instance for a config entry, or None."""
    data = hass.data.get("ai_home_copilot", {}).get(entry_id, {})
    return data.get("character_module")