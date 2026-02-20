"""Media control buttons for PilotSuite."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity

from .entity import CopilotBaseEntity

# Re-export from media_context_v2_entities
from .media_context_v2_entities import (
    VolumeUpButton,
    VolumeDownButton,
    VolumeMuteButton,
    ClearOverridesButton,
)
