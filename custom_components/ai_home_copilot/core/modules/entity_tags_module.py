"""Entity Tags Module v2 — Manual + automatic entity tagging for PilotSuite.

Provides a way for users to assign custom tags to HA entities, enabling
modules to query "give me all entities tagged as Licht" instead of blindly
scanning all entities.

Features:
- Manual tagging via config flow UI
- Auto "Styx" tagging: every entity Styx interacts with gets auto-tagged
- Auto zone tagging: entities added to Habitus zones get tagged
- Auto area tagging: entities get tagged based on their HA area
- Auto domain tagging: entities get tagged based on their HA domain
- HA Labels integration: reads native HA labels as PilotSuite tags
- Tags visible in LLM context, sensors, and queryable by modules

Tag types:
  - styx         → Auto: entities Styx interacted with
  - zone_*       → Auto: entities in Habitus zones
  - area_*       → Auto: entities in HA areas
  - domain_*     → Auto: entities by HA domain
  - ha_label_*   → Synced from HA native labels
  - (custom)     → Manual: user-defined tags
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant

from .module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)

STYX_TAG_ID = "styx"
STYX_TAG_NAME = "Styx"
STYX_TAG_COLOR = "#8b5cf6"  # Purple
STYX_TAG_ICON = "mdi:robot"


class EntityTagsModule(CopilotModule):
    """Module managing user-defined and auto-generated entity tags."""

    @property
    def name(self) -> str:
        return "entity_tags"

    @property
    def version(self) -> str:
        return "0.3.0"

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
            "EntityTagsModule v2 setup: %d tags loaded",
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

    def get_styx_entities(self) -> list[str]:
        """Return all entities tagged with 'Styx'."""
        return self.get_entities_by_tag(STYX_TAG_ID)

    def get_tags_for_entity(self, entity_id: str) -> list:
        """Return all tags that include this entity_id."""
        return [t for t in self._tags.values() if entity_id in t.entity_ids]

    def is_styx_entity(self, entity_id: str) -> bool:
        """Check if an entity is tagged with 'Styx'."""
        tag = self._tags.get(STYX_TAG_ID)
        return tag is not None and entity_id in tag.entity_ids

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
        styx_count = len(self.get_styx_entities())
        zone_tags = self.get_zone_tags()
        area_tags = self.get_area_tags()
        return {
            "tag_count": len(self._tags),
            "styx_tagged_count": styx_count,
            "zone_tag_count": len(zone_tags),
            "area_tag_count": len(area_tags),
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

    async def async_auto_tag_styx(self, entity_ids: list[str]) -> int:
        """Auto-tag entities with 'Styx' when Styx interacts with them.

        Called by tool execution, scene application, automation creation, etc.
        Returns the number of newly tagged entities.
        """
        if not self._hass or not entity_ids:
            return 0

        from ...entity_tags_store import async_upsert_tag

        current = self.get_styx_entities()
        new_ids = [eid for eid in entity_ids if eid not in current]
        if not new_ids:
            return 0

        merged = list(set(current + new_ids))
        await async_upsert_tag(
            self._hass,
            tag_id=STYX_TAG_ID,
            name=STYX_TAG_NAME,
            entity_ids=merged,
            color=STYX_TAG_COLOR,
            icon=STYX_TAG_ICON,
            module_hints=["pilotsuite", "monitoring"],
        )
        await self.reload_from_storage()
        _LOGGER.info("Auto-tagged %d entities with Styx (total: %d)", len(new_ids), len(merged))
        return len(new_ids)

    async def async_auto_tag_zone_entities(
        self, zone_id: str, zone_name: str, entity_ids: list[str]
    ) -> int:
        """Auto-tag entities with their Habitus zone when added to a zone.

        Creates a tag per zone (e.g. 'zone:wohnzimmer') and assigns all zone entities.
        This connects the entity tag system with the Habitus zone system.

        Returns the number of newly tagged entities.
        """
        if not self._hass or not entity_ids or not zone_id:
            return 0

        from ...entity_tags_store import async_upsert_tag

        # Zone tag ID: use zone_id directly (already prefixed with 'zone:')
        tag_id = zone_id.replace(":", "_")  # zone:wohnzimmer → zone_wohnzimmer
        tag_name = f"Zone: {zone_name}"

        # Zone tag color from role mapping
        zone_colors = {
            "bad": "#22d3ee",      # cyan
            "kueche": "#fb923c",   # orange
            "wohn": "#34d399",     # green
            "schlaf": "#6366f1",   # indigo
            "buero": "#60a5fa",    # blue
            "kinder": "#f472b6",   # pink
            "garten": "#34d399",   # green
            "flur": "#fbbf24",     # yellow
            "garage": "#6b7280",   # gray
            "keller": "#78716c",   # stone
            "ess": "#a78bfa",      # violet
            "wasch": "#38bdf8",    # sky
            "dach": "#d97706",     # amber
        }
        color = STYX_TAG_COLOR  # default purple
        zone_lower = zone_name.lower()
        for key, col in zone_colors.items():
            if key in zone_lower:
                color = col
                break

        current_tag = self._tags.get(tag_id)
        current_ids = set(current_tag.entity_ids) if current_tag else set()
        new_ids = [eid for eid in entity_ids if eid not in current_ids]

        merged = list(current_ids | set(entity_ids))
        await async_upsert_tag(
            self._hass,
            tag_id=tag_id,
            name=tag_name,
            entity_ids=merged,
            color=color,
            icon="mdi:map-marker-radius",
            module_hints=["habitus", "zone", zone_id],
        )
        await self.reload_from_storage()

        if new_ids:
            _LOGGER.info(
                "Auto-tagged %d entities with zone %s (total: %d)",
                len(new_ids), zone_id, len(merged),
            )

        # Also auto-tag with Styx (zone entities are Styx-relevant)
        await self.async_auto_tag_styx(entity_ids)

        return len(new_ids)

    async def async_auto_tag_by_area(
        self, area_id: str, area_name: str, entity_ids: list[str]
    ) -> int:
        """Auto-tag entities by their HA area.

        Creates a tag per area (e.g. 'area_wohnzimmer') and assigns all entities
        that belong to that area. This bridges HA areas with PilotSuite tags.

        Returns the number of newly tagged entities.
        """
        if not self._hass or not entity_ids or not area_id:
            return 0

        from ...entity_tags_store import async_upsert_tag

        tag_id = f"area_{area_id}"
        tag_name = f"Area: {area_name}"

        current_tag = self._tags.get(tag_id)
        current_ids = set(current_tag.entity_ids) if current_tag else set()
        new_ids = [eid for eid in entity_ids if eid not in current_ids]

        if not new_ids and current_tag:
            return 0

        merged = list(current_ids | set(entity_ids))
        await async_upsert_tag(
            self._hass,
            tag_id=tag_id,
            name=tag_name,
            entity_ids=merged,
            color="#94a3b8",  # slate
            icon="mdi:home-map-marker",
            module_hints=["ha_area", area_id],
        )
        await self.reload_from_storage()

        if new_ids:
            _LOGGER.info(
                "Auto-tagged %d entities with area %s (total: %d)",
                len(new_ids), area_id, len(merged),
            )
        return len(new_ids)

    def get_zone_tags(self) -> list:
        """Return all zone-related tags."""
        return [t for t in self._tags.values() if "habitus" in t.module_hints or t.tag_id.startswith("zone_")]

    def get_area_tags(self) -> list:
        """Return all area-related tags."""
        return [t for t in self._tags.values() if "ha_area" in t.module_hints or t.tag_id.startswith("area_")]

    def get_entities_for_zone(self, zone_id: str) -> list[str]:
        """Return entity_ids tagged for a specific zone."""
        tag_id = zone_id.replace(":", "_")
        return self.get_entities_by_tag(tag_id)

    def get_entities_for_area(self, area_id: str) -> list[str]:
        """Return entity_ids tagged for a specific HA area."""
        tag_id = f"area_{area_id}"
        return self.get_entities_by_tag(tag_id)

    async def async_auto_tag_from_zone_suggestions(
        self, suggestions: list[dict[str, Any]]
    ) -> int:
        """Bulk auto-tag entities from Core zone-suggestions response.

        Expects list of:
          {zone_id: "zone:wohnzimmer", zone_name: "Wohnzimmer", entity_ids: [...]}

        Returns total number of newly tagged entities.
        """
        total_new = 0
        for suggestion in suggestions:
            zone_id = suggestion.get("zone_id", "")
            zone_name = suggestion.get("zone_name", "")
            entity_ids = suggestion.get("entity_ids", [])
            if zone_id and entity_ids:
                count = await self.async_auto_tag_zone_entities(
                    zone_id, zone_name, entity_ids
                )
                total_new += count
        return total_new

    async def async_auto_tag_by_domain(
        self, domain: str, tag_id: str, tag_name: str,
        color: str = "#6366f1", icon: str = "mdi:tag"
    ) -> int:
        """Auto-tag all entities of a specific domain.

        Useful for domain-based grouping (e.g., all lights, all media_players).
        Returns the number of newly tagged entities.
        """
        if not self._hass:
            return 0

        from homeassistant.helpers import entity_registry
        ent_reg = entity_registry.async_get(self._hass)

        domain_entities = [
            eid for eid, entry in ent_reg.entities.items()
            if entry.domain == domain and entry.disabled_by is None
        ]

        if not domain_entities:
            return 0

        from ...entity_tags_store import async_upsert_tag

        current_tag = self._tags.get(tag_id)
        current_ids = set(current_tag.entity_ids) if current_tag else set()
        new_ids = [eid for eid in domain_entities if eid not in current_ids]

        if not new_ids:
            return 0

        merged = list(current_ids | set(domain_entities))
        await async_upsert_tag(
            self._hass,
            tag_id=tag_id,
            name=tag_name,
            entity_ids=merged,
            color=color,
            icon=icon,
            module_hints=["domain", domain],
        )
        await self.reload_from_storage()

        _LOGGER.info(
            "Auto-tagged %d entities of domain '%s' with tag '%s'",
            len(new_ids), domain, tag_id,
        )
        return len(new_ids)

    async def async_sync_ha_labels(self) -> int:
        """Sync HA native labels as PilotSuite tags.

        Reads entities' label assignments from the entity registry and creates
        corresponding PilotSuite tags prefixed with 'ha_label_'.

        Returns the number of label tags synced.
        """
        if not self._hass:
            return 0

        from homeassistant.helpers import entity_registry
        ent_reg = entity_registry.async_get(self._hass)
        from ...entity_tags_store import async_upsert_tag

        # Collect entity_ids by label
        label_entities: dict[str, list[str]] = {}
        for entity_id, entry in ent_reg.entities.items():
            if entry.disabled_by is not None:
                continue
            labels = getattr(entry, "labels", None)
            if not labels:
                continue
            for label in labels:
                label_entities.setdefault(label, []).append(entity_id)

        synced = 0
        for label_id, entity_ids in label_entities.items():
            tag_id = f"ha_label_{label_id}"
            tag_name = f"Label: {label_id}"
            await async_upsert_tag(
                self._hass,
                tag_id=tag_id,
                name=tag_name,
                entity_ids=entity_ids,
                color="#e2e8f0",  # light gray
                icon="mdi:label",
                module_hints=["ha_label", label_id],
            )
            synced += 1

        if synced > 0:
            await self.reload_from_storage()
            _LOGGER.info("Synced %d HA labels as PilotSuite tags", synced)

        return synced

    # ------------------------------------------------------------------
    # LLM Context
    # ------------------------------------------------------------------

    def get_context_for_llm(self) -> str:
        """Inject tag info into LLM system prompt."""
        if not self._tags:
            return ""
        lines = ["Entity-Tags:"]
        for tag in self._tags.values():
            if not tag.entity_ids:
                continue
            sample = tag.entity_ids[:5]
            suffix = " ..." if len(tag.entity_ids) > 5 else ""
            # Identify tag type
            if tag.tag_id == STYX_TAG_ID:
                marker = " [auto:styx]"
            elif tag.tag_id.startswith("zone_"):
                marker = " [auto:zone]"
            elif tag.tag_id.startswith("area_"):
                marker = " [auto:area]"
            elif tag.tag_id.startswith("ha_label_"):
                marker = " [ha:label]"
            elif tag.tag_id.startswith("domain_"):
                marker = " [auto:domain]"
            else:
                marker = ""
            lines.append(f"  [{tag.name}]{marker}: {', '.join(sample)}{suffix}")
        styx_count = len(self.get_styx_entities())
        if styx_count > 0:
            lines.append(f"  Styx hat insgesamt {styx_count} Entitaeten beruehrt.")
        zone_count = len(self.get_zone_tags())
        if zone_count > 0:
            lines.append(f"  {zone_count} Habitus-Zonen mit Tags verbunden.")
        return "\n".join(lines) if len(lines) > 1 else ""


def get_entity_tags_module(hass: HomeAssistant, entry_id: str) -> Optional[EntityTagsModule]:
    """Return the EntityTagsModule instance for a config entry, or None."""
    data = hass.data.get("ai_home_copilot", {}).get(entry_id, {})
    return data.get("entity_tags_module")
