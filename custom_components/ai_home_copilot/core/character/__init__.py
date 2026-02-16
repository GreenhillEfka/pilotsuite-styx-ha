"""Copilot Character System - Personality presets for AI Home CoPilot.

DEPRECATED: This module has been moved to core/modules/character_module.py
to follow the CopilotModule interface pattern.

This file provides backward compatibility for existing imports.
For new code, import from core.modules.character_module instead.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "core.character is deprecated. Use core.modules.character_module instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location for backward compatibility
from ..modules.character_module import (
    CharacterPreset,
    CharacterMode,
    CharacterConfig,
    CharacterModule,
    MoodWeights,
    SuggestionConfig,
    VoiceConfig,
    AlertConfig,
    create_module,
)

# Alias for backward compat - CharacterService is now CharacterModule
CharacterService = CharacterModule

__all__ = [
    "CharacterPreset",
    "CharacterMode",
    "CharacterConfig",
    "CharacterModule",
    "CharacterService",  # Backward compat alias
    "MoodWeights",
    "SuggestionConfig",
    "VoiceConfig",
    "AlertConfig",
    "create_module",
]