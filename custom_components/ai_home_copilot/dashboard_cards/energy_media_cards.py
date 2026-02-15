"""Energy and Media cards for comprehensive dashboard.

Cards:
- Energy Card: Consumption, production, anomalies
- Media Card: Music, TV, room distribution
"""
from __future__ import annotations

from typing import Any, Optional

# Try to import context types
try:
    from .energy_context import EnergySnapshot
    from .media_context import MediaContextData
except ImportError:
    EnergySnapshot = Any
    MediaContextData = Any


def create_energy_card(
    energy_data: Optional[Any],  # EnergySnapshot | None
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create detailed Energy Card.
    
    Shows:
    - Current consumption/production
    - Peak power today
    - Anomalies detected
    - Shifting opportunities
    """
    config = config or {}
    
    if not energy_data:
        return {
            "type": "markdown",
            "content": "**Energiedaten nicht verfügbar**",
        }
    
    cards = [
        {
            "type": "grid",
            "columns": 2,
            "cards": [
                {
                    "type": "stat",
                    "name": "Verbrauch heute",
                    "value": f"{getattr(energy_data, 'total_consumption_today_kwh', 0):.1f}",
                    "unit": "kWh",
                    "icon": "mdi:flash",
                },
                {
                    "type": "stat",
                    "name": "Produktion heute",
                    "value": f"{getattr(energy_data, 'total_production_today_kwh', 0):.1f}",
                    "unit": "kWh",
                    "icon": "mdi:solar-panel",
                },
            ],
        },
        {
            "type": "grid",
            "columns": 2,
            "cards": [
                {
                    "type": "stat",
                    "name": "Aktuelle Leistung",
                    "value": f"{getattr(energy_data, 'current_power_watts', 0):.0f}",
                    "unit": "W",
                    "icon": "mdi:lightning-bolt",
                },
                {
                    "type": "stat",
                    "name": "Spitzenleistung",
                    "value": f"{getattr(energy_data, 'peak_power_today_watts', 0):.0f}",
                    "unit": "W",
                    "icon": "mdi:chart-line-variant",
                },
            ],
        },
    ]
    
    # Add anomalies if any
    anomalies = getattr(energy_data, 'anomalies_detected', 0)
    if anomalies and anomalies > 0:
        cards.append({
            "type": "entity",
            "entity": "sensor.energy_anomalies",
            "name": f"{anomalies} Anomalien erkannt",
            "icon": "mdi:alert",
        })
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "⚡ Energie"),
        "cards": cards,
    }


def create_media_card(
    media_data: Optional[Any],  # MediaContextData | None
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create detailed Media Card.
    
    Shows:
    - Currently playing music
    - Active TV/source
    - Room distribution
    """
    config = config or {}
    
    if not media_data:
        return {
            "type": "markdown",
            "content": "**Keine Media-Daten verfügbar**",
        }
    
    cards = []
    
    # Music status
    music_active = getattr(media_data, 'music_active', False)
    if music_active:
        cards.append({
            "type": "entity",
            "entity": getattr(media_data, 'music_primary_entity_id', "media_player.music") or "media_player.music",
            "name": f"🎵 {getattr(media_data, 'music_now_playing', 'Musik') or 'Musik'}",
            "icon": "mdi:music",
            "secondary_info": getattr(media_data, 'music_primary_area', ''),
        })
    else:
        cards.append({
            "type": "markdown",
            "content": "**🎵 Keine Musik aktiv**",
        })
    
    # TV status
    tv_active = getattr(media_data, 'tv_active', False)
    if tv_active:
        cards.append({
            "type": "entity",
            "entity": getattr(media_data, 'tv_primary_entity_id', "media_player.tv") or "media_player.tv",
            "name": f"📺 {getattr(media_data, 'tv_source', 'TV') or 'TV'}",
            "icon": "mdi:television",
            "secondary_info": getattr(media_data, 'tv_primary_area', ''),
        })
    
    # Summary stats
    music_count = getattr(media_data, 'music_active_count', 0)
    tv_count = getattr(media_data, 'tv_active_count', 0)
    
    cards.append({
        "type": "grid",
        "columns": 2,
        "cards": [
            {
                "type": "stat",
                "name": "Aktive Player",
                "value": str(music_count + tv_count),
                "icon": "mdi:play-circle",
            },
            {
                "type": "stat",
                "name": "Musik-Player",
                "value": str(music_count),
                "icon": "mdi:music-note",
            },
        ],
    })
    
    return {
        "type": "vertical-stack",
        "title": config.get("title", "📺 Media"),
        "cards": cards,
    }


__all__ = [
    "create_energy_card",
    "create_media_card",
]
