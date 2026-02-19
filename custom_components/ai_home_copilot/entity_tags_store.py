"""Entity Tags Store — persistent manual entity tags for PilotSuite.

Allows users to assign custom tags (e.g. "Licht", "Überwachen", "Energie")
to arbitrary HA entities. Modules can query tags to filter entities.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

ENTITY_TAGS_STORE_KEY = "ai_home_copilot.entity_tags"
ENTITY_TAGS_STORE_VERSION = 1

# Predefined tag colors
TAG_COLORS = {
    "licht": "#fbbf24",
    "klima": "#34d399",
    "sicherheit": "#f87171",
    "energie": "#60a5fa",
    "wasser": "#22d3ee",
    "heizung": "#fb923c",
    "überwachen": "#f472b6",
    "default": "#6366f1",
}


@dataclass
class EntityTag:
    """A user-defined entity tag with associated entities."""

    tag_id: str
    name: str
    entity_ids: list[str] = field(default_factory=list)
    color: str = "#6366f1"
    icon: str = "mdi:tag"
    module_hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag_id": self.tag_id,
            "name": self.name,
            "entity_ids": list(self.entity_ids),
            "color": self.color,
            "icon": self.icon,
            "module_hints": list(self.module_hints),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EntityTag":
        tag_id = data.get("tag_id", "")
        color = data.get("color") or TAG_COLORS.get(tag_id.lower(), TAG_COLORS["default"])
        return cls(
            tag_id=tag_id,
            name=data.get("name", tag_id),
            entity_ids=list(data.get("entity_ids", [])),
            color=color,
            icon=data.get("icon", "mdi:tag"),
            module_hints=list(data.get("module_hints", [])),
        )


def _get_store(hass: HomeAssistant) -> Store:
    return Store(hass, ENTITY_TAGS_STORE_VERSION, ENTITY_TAGS_STORE_KEY)


async def async_get_entity_tags(hass: HomeAssistant) -> dict[str, EntityTag]:
    """Load all entity tags from persistent storage."""
    store = _get_store(hass)
    raw = await store.async_load()
    if not raw:
        return {}
    return {
        tag_id: EntityTag.from_dict(tag_data)
        for tag_id, tag_data in (raw.get("tags") or {}).items()
    }


async def async_save_entity_tags(
    hass: HomeAssistant, tags: dict[str, EntityTag]
) -> None:
    """Persist entity tags to storage."""
    store = _get_store(hass)
    await store.async_save(
        {"tags": {tid: t.to_dict() for tid, t in tags.items()}}
    )


async def async_upsert_tag(
    hass: HomeAssistant,
    tag_id: str,
    name: str,
    entity_ids: list[str] | None = None,
    color: str | None = None,
    icon: str = "mdi:tag",
    module_hints: list[str] | None = None,
) -> EntityTag:
    """Create or update a tag."""
    tags = await async_get_entity_tags(hass)
    existing = tags.get(tag_id)
    tag = EntityTag(
        tag_id=tag_id,
        name=name,
        entity_ids=list(entity_ids or (existing.entity_ids if existing else [])),
        color=color or (existing.color if existing else TAG_COLORS.get(tag_id.lower(), TAG_COLORS["default"])),
        icon=icon,
        module_hints=list(module_hints or (existing.module_hints if existing else [])),
    )
    tags[tag_id] = tag
    await async_save_entity_tags(hass, tags)
    _LOGGER.debug("Upserted entity tag: %s (%d entities)", tag_id, len(tag.entity_ids))
    return tag


async def async_delete_tag(hass: HomeAssistant, tag_id: str) -> bool:
    """Delete a tag. Returns True if it existed."""
    tags = await async_get_entity_tags(hass)
    if tag_id not in tags:
        return False
    del tags[tag_id]
    await async_save_entity_tags(hass, tags)
    _LOGGER.debug("Deleted entity tag: %s", tag_id)
    return True
