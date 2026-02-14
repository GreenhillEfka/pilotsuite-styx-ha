"""Built-in modules for AI Home CoPilot.

This package provides a modular runtime architecture:
- legacy: Wraps the current integration behavior without changes
- unifi: UniFi network monitoring and candidate generation
- mood: Mood vector v0.1 for comfort/frugality/joy ranking

Each module inherits from CopilotModule and implements the lifecycle methods.
"""

from __future__ import annotations

from .legacy import LegacyModule
from .module import CopilotModule, ModuleContext
from .mood_module import MoodModule
from .mood_context_module import MoodContextModule

__all__ = ["LegacyModule", "CopilotModule", "ModuleContext", "MoodModule", "MoodContextModule"]
