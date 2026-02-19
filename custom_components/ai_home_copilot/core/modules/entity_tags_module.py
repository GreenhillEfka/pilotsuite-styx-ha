"""Entity Tags Module — manual entity tagging for targeted monitoring.

Provides a way for users to assign custom tags to HA entities, enabling
modules to query "give me all entities tagged as Licht" instead of blindly
scanning all entities.

Tags visible in Styx LLM context, in HA sensor entities, and queryable by
other modules via get_entities_by_tag().
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant

from .module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)


class EntityTagsModule(CopilotModule):
    """Module managing user-defined entity tags."""

    @property
    def name(self) -> str:
        return "entity_tags"

    @property
    def version(self) -> str:
        return "0.1.0"

    def __init__(self):
        self._tags: dict = {}   # tag_id -> EntityTag
        self._hass: Optional[HomeAssistant] = None
        self._entry_id: Optional[str] = None

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Load tags from storage and register in hass.data."""
        self._hass = ctx.hass
        self._entry_id = ctx.entry_id

        from ...entity_tags_store import async_get_entity_tags
        self._tags = await async_get_entity_tags(ctx.hass)

        ctx.hass.data.setdefault("ai_home_copilot", {})
        ctx.hass.data["ai_home_copilot"].setdefault(ctx.entry_id, {})
        ctx.hass.data["ai_home_copilot"][ctx.entry_id]["entity_tags_module"] = self

        _LOGGER.info(
            "EntityTagsModule setup: %d tags loaded",
            len(self._tags),
        )

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        entry_store = ctx.hass.data.get("ai_home_copilot", {}).get(ctx.entry_id, {})
        if isinstance(entry_store, dict):
            entry_store.pop("entity_tags_module", None)
        return True

    # ------------------------------------------------------------------
    # Public read API (sync — safe to call from sensors/modules)
    # ------------------------------------------------------------------

    def get_all_tags(self) -> list:
        """Return all EntityTag objects."""
        return list(self._tags.values())

    def get_entities_by_tag(self, tag_id: str) -> list[str]:
        """Return entity_ids that have the given tag."""
        tag = self._tags.get(tag_id)
        return list(tag.entity_ids) if tag else []

    def get_tags_for_entity(self, entity_id: str) -> list:
        """Return all tags that include this entity_id."""
        return [t for t in self._tags.values() if entity_id in t.entity_ids]

    def get_tag_count(self) -> int:
        return len(self._tags)

    def get_total_tagged_entities(self) -> int:
        """Total unique entities across all tags."""
        all_ids: set[str] = set()
        for tag in self._tags.values():
            all_ids.update(tag.entity_ids)
        return len(all_ids)

    def get_summary(self) -> dict[str, Any]:
        """Structured summary for sensor attributes."""
        return {
            "tag_count": len(self._tags),
            "tags": [
                {
                    "tag_id": t.tag_id,
                    "name": t.name,
                    "entity_count": len(t.entity_ids),
                    "color": t.color,
                    "icon": t.icon,
                }
                for t in self._tags.values()
            ],
        }

    # ------------------------------------------------------------------
    # Mutation API (async — persists to storage)
    # ------------------------------------------------------------------

    async def reload_from_storage(self) -> None:
        """Re-read tags from HA Storage (call after config flow saves)."""
        if self._hass:
            from ...entity_tags_store import async_get_entity_tags
            self._tags = await async_get_entity_tags(self._hass)
            _LOGGER.debug("EntityTagsModule reloaded: %d tags", len(self._tags))

    # ------------------------------------------------------------------
    # LLM Context
    # ------------------------------------------------------------------

    def get_context_for_llm(self) -> str:
        """Inject tag info into LLM system prompt."""
        if not self._tags:
            return ""
        lines = ["Manuelle Entitäts-Tags:"]
        for tag in self._tags.values():
            if not tag.entity_ids:
                continue
            sample = tag.entity_ids[:5]
            suffix = " …" if len(tag.entity_ids) > 5 else ""
            lines.append(f"  [{tag.name}]: {', '.join(sample)}{suffix}")
        return "\n".join(lines) if len(lines) > 1 else ""


def get_entity_tags_module(hass: HomeAssistant, entry_id: str) -> Optional[EntityTagsModule]:
    """Return the EntityTagsModule instance for a config entry, or None."""
    data = hass.data.get("ai_home_copilot", {}).get(entry_id, {})
    return data.get("entity_tags_module")
