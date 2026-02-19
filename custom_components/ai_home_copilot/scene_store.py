"""Scene Store — persistent scene storage for Habitus Zones.

Allows saving snapshots of current zone conditions as HA-compatible scenes.
The habitus system learns patterns and offers presets.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCENE_STORE_KEY = f"{DOMAIN}.zone_scenes"
SCENE_STORE_VERSION = 1


@dataclass
class ZoneScene:
    """A saved scene snapshot for a habitus zone."""

    scene_id: str
    zone_id: str
    zone_name: str
    name: str
    entity_states: dict[str, dict[str, Any]]  # entity_id -> {state, attributes...}
    created_at: float = field(default_factory=time.time)
    applied_count: int = 0
    last_applied: float | None = None
    source: str = "manual"  # "manual", "learned", "preset"
    is_favorite: bool = False
    ha_scene_entity_id: str | None = None  # scene.xxx after HA registration

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "name": self.name,
            "entity_states": self.entity_states,
            "created_at": self.created_at,
            "applied_count": self.applied_count,
            "last_applied": self.last_applied,
            "source": self.source,
            "is_favorite": self.is_favorite,
            "ha_scene_entity_id": self.ha_scene_entity_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ZoneScene:
        return cls(
            scene_id=data.get("scene_id", ""),
            zone_id=data.get("zone_id", ""),
            zone_name=data.get("zone_name", ""),
            name=data.get("name", ""),
            entity_states=data.get("entity_states", {}),
            created_at=data.get("created_at", time.time()),
            applied_count=data.get("applied_count", 0),
            last_applied=data.get("last_applied"),
            source=data.get("source", "manual"),
            is_favorite=data.get("is_favorite", False),
            ha_scene_entity_id=data.get("ha_scene_entity_id"),
        )


# Built-in presets for common zone scenarios
SCENE_PRESETS: list[dict[str, Any]] = [
    {
        "preset_id": "morgen",
        "name": "Morgen",
        "icon": "mdi:weather-sunset-up",
        "description": "Sanfte Beleuchtung, angenehme Temperatur zum Aufwachen",
        "roles": {
            "lights": {"brightness_pct": 60, "color_temp_kelvin": 4000},
            "cover": {"position": 80},
            "heating": {"temperature": 21},
        },
    },
    {
        "preset_id": "tag",
        "name": "Tag",
        "icon": "mdi:white-balance-sunny",
        "description": "Volle Helligkeit, Rollos offen, normale Temperatur",
        "roles": {
            "lights": {"brightness_pct": 100, "color_temp_kelvin": 5500},
            "cover": {"position": 100},
            "heating": {"temperature": 21},
        },
    },
    {
        "preset_id": "abend",
        "name": "Abend",
        "icon": "mdi:weather-sunset-down",
        "description": "Warmes Licht, gedimmt, Rollos geschlossen",
        "roles": {
            "lights": {"brightness_pct": 40, "color_temp_kelvin": 2700},
            "cover": {"position": 0},
            "heating": {"temperature": 20},
        },
    },
    {
        "preset_id": "nacht",
        "name": "Nacht",
        "icon": "mdi:weather-night",
        "description": "Alles aus, Rollos zu, Heizung heruntergefahren",
        "roles": {
            "lights": {"state": "off"},
            "cover": {"position": 0},
            "heating": {"temperature": 17},
        },
    },
    {
        "preset_id": "film",
        "name": "Film",
        "icon": "mdi:movie-open",
        "description": "Gedimmtes Licht, Rollos zu, Medien bereit",
        "roles": {
            "lights": {"brightness_pct": 10, "color_temp_kelvin": 2200},
            "cover": {"position": 0},
        },
    },
    {
        "preset_id": "party",
        "name": "Party",
        "icon": "mdi:party-popper",
        "description": "Bunte Beleuchtung, volle Helligkeit",
        "roles": {
            "lights": {"brightness_pct": 100, "color_temp_kelvin": 3500},
            "cover": {"position": 50},
        },
    },
    {
        "preset_id": "konzentration",
        "name": "Konzentration",
        "icon": "mdi:head-lightbulb",
        "description": "Helles, kühles Licht für konzentriertes Arbeiten",
        "roles": {
            "lights": {"brightness_pct": 90, "color_temp_kelvin": 6000},
            "cover": {"position": 70},
            "heating": {"temperature": 20},
        },
    },
    {
        "preset_id": "abwesend",
        "name": "Abwesend",
        "icon": "mdi:home-export-outline",
        "description": "Energiesparmodus: alles aus, Heizung abgesenkt",
        "roles": {
            "lights": {"state": "off"},
            "cover": {"position": 0},
            "heating": {"temperature": 16},
            "media": {"state": "off"},
        },
    },
]


def _get_store(hass: HomeAssistant) -> Store:
    global_data = hass.data.setdefault(DOMAIN, {}).setdefault("_global", {})
    st = global_data.get("scene_store")
    if st is None:
        st = Store(hass, SCENE_STORE_VERSION, SCENE_STORE_KEY)
        global_data["scene_store"] = st
    return st


async def async_get_scenes(hass: HomeAssistant) -> dict[str, ZoneScene]:
    """Load all zone scenes from persistent storage."""
    store = _get_store(hass)
    raw = await store.async_load()
    if not raw:
        return {}
    return {
        sid: ZoneScene.from_dict(sdata)
        for sid, sdata in (raw.get("scenes") or {}).items()
    }


async def async_save_scenes(
    hass: HomeAssistant, scenes: dict[str, ZoneScene]
) -> None:
    """Persist zone scenes to storage."""
    store = _get_store(hass)
    await store.async_save(
        {"scenes": {sid: s.to_dict() for sid, s in scenes.items()}}
    )


async def async_upsert_scene(
    hass: HomeAssistant,
    scene: ZoneScene,
) -> ZoneScene:
    """Create or update a scene."""
    scenes = await async_get_scenes(hass)
    scenes[scene.scene_id] = scene
    await async_save_scenes(hass, scenes)
    _LOGGER.debug("Upserted scene: %s for zone %s", scene.scene_id, scene.zone_id)
    return scene


async def async_delete_scene(hass: HomeAssistant, scene_id: str) -> bool:
    """Delete a scene. Returns True if it existed."""
    scenes = await async_get_scenes(hass)
    if scene_id not in scenes:
        return False
    del scenes[scene_id]
    await async_save_scenes(hass, scenes)
    _LOGGER.debug("Deleted scene: %s", scene_id)
    return True


async def async_increment_apply_count(
    hass: HomeAssistant, scene_id: str
) -> None:
    """Increment the applied_count for a scene."""
    scenes = await async_get_scenes(hass)
    scene = scenes.get(scene_id)
    if scene:
        scene.applied_count += 1
        scene.last_applied = time.time()
        await async_save_scenes(hass, scenes)
