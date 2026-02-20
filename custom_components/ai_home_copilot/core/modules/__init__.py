"""Built-in modules for PilotSuite.

This package provides a modular runtime architecture:
- legacy: Wraps the current integration behavior without changes
- unifi: UniFi network monitoring and candidate generation
- mood: Mood vector v0.1 for comfort/frugality/joy ranking
- character: Personality presets for mood weighting and voice formatting

Each module inherits from CopilotModule and implements the lifecycle methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .legacy import LegacyModule
    from .module import CopilotModule, ModuleContext
    from .mood_module import MoodModule
    from .mood_context_module import MoodContextModule
    from .user_preference_module import UserPreferenceModule
    from .unifi_module import UniFiModule
    from .character_module import CharacterModule

__all__ = [
    "LegacyModule",
    "CopilotModule",
    "ModuleContext",
    "MoodModule",
    "MoodContextModule",
    "UserPreferenceModule",
    "UniFiModule",
    "CharacterModule",
]
