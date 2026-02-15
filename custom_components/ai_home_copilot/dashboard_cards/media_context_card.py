"""
Media Context Card
==================

Generates a Lovelace UI card for media context visualization.
Shows:
- Active media players (music/TV)
- Current playback information
- Volume levels
- Play mode (shuffle, repeat)
- Media context (mood, zone)

Design: Clean card with media cover art placeholder
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class MediaContextData:
    """Media context data."""
    music_active: bool
    tv_active: bool
    music_primary_entity_id: str | None = None
    tv_primary_entity_id: str | None = None
    music_primary_area: str | None = None
    tv_primary_area: str | None = None
    music_now_playing: str | None = None
    tv_source: str | None = None
    music_active_count: int = 0
    tv_active_count: int = 0
    volume_music: float | None = None
    volume_tv: float | None = None
    media_cover: str | None = None
    play_mode: dict[str, bool] | None = None


def create_media_context_card(
    hass: HomeAssistant,
    media_data: MediaContextData,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a Media Context Card YAML configuration.
    
    Args:
        hass: Home Assistant instance
        media_data: Media context data
        config: Optional configuration overrides
        
    Returns:
        Lovelace card configuration dict
    """
    card_config = {
        "type": "vertical-stack",
        "cards": [
            _create_media_header_card(media_data),
            _create_media_status_card(media_data),
            _create_media_now_playing_card(media_data),
            _create_media_controls_card(media_data),
        ],
    }
    
    # Apply custom configuration if provided
    if config:
        card_config.update(config)
        
    return card_config


def _create_media_header_card(media_data: MediaContextData) -> dict[str, str]:
    """Create media header card."""
    return {
        "type": "horizontal-stack",
        "cards": [
            {
                "type": "custom:hui-card",
                "title": "📺 Medien",
                "icon": "mdi:play-box",
            },
        ],
    }


def _create_media_status_card(media_data: MediaContextData) -> dict[str, Any]:
    """Create media status card."""
    music_icon = "mdi:music" if media_data.music_active else "mdi:music-off"
    tv_icon = "mdi:television" if media_data.tv_active else "mdi:television-off"
    
    status_items = []
    
    if media_data.music_active:
        status_items.append({
            "type": "custom:hui-icon-card",
            "icon": music_icon,
            "name": "Musik",
            "entity": media_data.music_primary_entity_id,
        })
        
    if media_data.tv_active:
        status_items.append({
            "type": "custom:hui-icon-card",
            "icon": tv_icon,
            "name": "TV",
            "entity": media_data.tv_primary_entity_id,
        })
        
    if not media_data.music_active and not media_data.tv_active:
        status_items.append({
            "type": "markdown",
            "content": "Keine aktive Medienwiedergabe",
        })
        
    return {
        "type": "custom:hui-card",
        "title": "Status",
        "icon": "mdi:information",
        "cards": status_items,
    }


def _create_media_now_playing_card(media_data: MediaContextData) -> dict[str, Any]:
    """Create 'now playing' card."""
    content_lines = []
    
    if media_data.music_active and media_data.music_now_playing:
        content_lines.append(f"🎵 {media_data.music_now_playing}")
        if media_data.music_primary_area:
            content_lines.append(f"🏠 {media_data.music_primary_area}")
            
    if media_data.tv_active and media_data.tv_source:
        content_lines.append(f"📺 {media_data.tv_source}")
        if media_data.tv_primary_area:
            content_lines.append(f"🏠 {media_data.tv_primary_area}")
            
    if not content_lines:
        content_lines.append("Keine aktuellen Medieninformationen")
        
    content = "\n".join(content_lines)
    
    return {
        "type": "custom:hui-card",
        "title": "Jetzt spielend",
        "icon": "mdi:record-rec",
        "cards": [
            {
                "type": "markdown",
                "content": content,
            },
        ],
    }


def _create_media_controls_card(media_data: MediaContextData) -> dict[str, Any]:
    """Create media controls card."""
    controls = []
    
    if media_data.music_active:
        controls.append({
            "type": "custom:hui-button-card",
            "name": "Musik",
            "icon": "mdi:music-note",
            "entity": media_data.music_primary_entity_id,
            "tap_action": {
                "action": "more-info",
            },
        })
        
    if media_data.tv_active:
        controls.append({
            "type": "custom:hui-button-card",
            "name": "TV",
            "icon": "mdi:television",
            "entity": media_data.tv_primary_entity_id,
            "tap_action": {
                "action": "more-info",
            },
        })
        
    return {
        "type": "custom:hui-card",
        "title": "Steuerung",
        "icon": "mdi:remote",
        "cards": controls if controls else [
            {
                "type": "markdown",
                "content": "Keine Medien zum Steuern aktiv",
            },
        ],
    }


def get_media_context_card_yaml(media_data: MediaContextData) -> str:
    """
    Get media context card as YAML string.
    
    Args:
        media_data: Media context data
        
    Returns:
        YAML string for Lovelace configuration
    """
    card_dict = create_media_context_card(None, media_data)
    return _dict_to_yaml(card_dict)


def _dict_to_yaml(data: dict[str, Any], indent: int = 0) -> str:
    """Convert dict to YAML string (simple implementation)."""
    indent_str = "  " * indent
    lines = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{indent_str}- {key}:")
                lines.append(_dict_to_yaml(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{indent_str}- {key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(_dict_to_yaml(item, indent + 1))
                    else:
                        lines.append(f"{indent_str}  - {item}")
            else:
                lines.append(f"{indent_str}- {key}: {value}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                lines.append(_dict_to_yaml(item, indent))
            else:
                lines.append(f"{indent_str}- {item}")
    else:
        lines.append(f"{indent_str}{data}")
        
    return "\n".join(lines)
