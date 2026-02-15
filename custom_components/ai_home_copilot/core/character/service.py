"""Character Service - Manage character presets and apply to mood/suggestions."""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from .models import (
    CharacterMode, CharacterPreset, CharacterConfig,
    MoodWeights, SuggestionConfig, VoiceConfig, AlertConfig
)


class CharacterService:
    """Service to manage character presets and apply them to mood/suggestions."""
    
    def __init__(self, hass=None, coordinator=None):
        """Initialize the service."""
        self.hass = hass
        self.coordinator = coordinator
        self._config = CharacterConfig()
        self._presets: Dict[CharacterMode, CharacterPreset] = {}
        self._load_presets()
    
    def _load_presets(self) -> None:
        """Load all built-in presets."""
        self._presets = {
            CharacterMode.ASSISTANT: CharacterPreset.assistant(),
            CharacterMode.COMPANION: CharacterPreset.companion(),
            CharacterMode.GUARDIAN: CharacterPreset.guardian(),
            CharacterMode.EFFICIENCY: CharacterPreset.efficiency(),
            CharacterMode.RELAXED: CharacterPreset.relaxed(),
        }
    
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
EOF