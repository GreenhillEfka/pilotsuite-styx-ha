"""Character Models - Personality presets."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, List


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
    """Runtime character configuration."""
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