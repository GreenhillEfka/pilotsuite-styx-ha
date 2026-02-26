"""Entity Tags config flow steps for PilotSuite options flow.

Menu:
  entity_tags → add_tag | edit_tag | delete_tag | back
"""
from __future__ import annotations

import logging
import re

import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

_LOGGER = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"^[a-z0-9_äöüß]+$")


def _build_add_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("tag_id", description={"suggested_value": "licht"}): str,
            vol.Required("tag_name"): str,
            vol.Optional("tag_entities", default=[]): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=True)
            ),
            vol.Optional("tag_color", default="#6366f1"): str,
        }
    )


def _build_select_tag_schema(tag_options: list[dict]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("tag_id"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=tag_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def _build_edit_entities_schema(
    tag_options: list[dict],
    *,
    selected_tag_id: str,
    default_entities: list[str],
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("tag_id", default=selected_tag_id): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=tag_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional("tag_entities", default=default_entities): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=True)
            ),
        }
    )


async def async_step_add_tag(flow, user_input=None) -> FlowResult:
    """Step: add a new entity tag."""
    errors: dict[str, str] = {}

    if user_input is not None:
        tag_id = user_input.get("tag_id", "").strip().lower().replace(" ", "_")
        tag_name = user_input.get("tag_name", "").strip()
        entity_ids = user_input.get("tag_entities", [])
        color = user_input.get("tag_color", "#6366f1").strip()

        if not tag_id or not _SLUG_RE.match(tag_id):
            errors["tag_id"] = "invalid_slug"
        elif not tag_name:
            errors["tag_name"] = "required"
        else:
            from .entity_tags_store import async_upsert_tag
            await async_upsert_tag(
                flow.hass,
                tag_id=tag_id,
                name=tag_name,
                entity_ids=list(entity_ids) if isinstance(entity_ids, (list, tuple)) else [entity_ids],
                color=color,
            )
            # Reload module so it picks up the new tag
            _reload_module(flow)
            return await flow.async_step_entity_tags()

    return flow.async_show_form(
        step_id="add_tag",
        data_schema=_build_add_schema(),
        errors=errors,
        description_placeholders={
            "hint": "tag_id muss lowercase sein, z.B. 'licht', 'alarm', 'energie'"
        },
    )


async def async_step_edit_tag(flow, user_input=None) -> FlowResult:
    """Step: edit entities of an existing tag."""
    tags = await _load_tags(flow)
    if not tags:
        return await flow.async_step_entity_tags()

    tag_options = [{"value": tid, "label": f"{t.name} ({len(t.entity_ids)} Entitäten)"} for tid, t in tags.items()]

    if user_input is not None:
        tag_id = str(user_input.get("tag_id", "")).strip()

        # First submit only selects a tag; show second form with preloaded entities.
        if "tag_entities" not in user_input:
            if tag_id in tags:
                schema = _build_edit_entities_schema(
                    tag_options,
                    selected_tag_id=tag_id,
                    default_entities=list(tags[tag_id].entity_ids),
                )
                return flow.async_show_form(
                    step_id="edit_tag",
                    data_schema=schema,
                    description_placeholders={"hint": "Entitäten bearbeiten und speichern"},
                )
            return await flow.async_step_entity_tags()

        entity_ids = user_input.get("tag_entities", [])
        if tag_id and tag_id in tags:
            from .entity_tags_store import async_upsert_tag

            await async_upsert_tag(
                flow.hass,
                tag_id=tag_id,
                name=tags[tag_id].name,
                entity_ids=list(entity_ids) if isinstance(entity_ids, (list, tuple)) else [entity_ids],
            )
            _reload_module(flow)
        return await flow.async_step_entity_tags()

    schema = _build_select_tag_schema(tag_options)
    return flow.async_show_form(
        step_id="edit_tag",
        data_schema=schema,
        description_placeholders={"hint": "Tag auswählen, dann Entitäten bearbeiten"},
    )


async def async_step_delete_tag(flow, user_input=None) -> FlowResult:
    """Step: delete an existing tag."""
    tags = await _load_tags(flow)
    if not tags:
        return await flow.async_step_entity_tags()

    tag_options = [{"value": tid, "label": f"{t.name}"} for tid, t in tags.items()]

    if user_input is not None:
        tag_id = user_input.get("tag_id", "")
        if tag_id:
            from .entity_tags_store import async_delete_tag
            await async_delete_tag(flow.hass, tag_id)
            _reload_module(flow)
        return await flow.async_step_entity_tags()

    return flow.async_show_form(
        step_id="delete_tag",
        data_schema=_build_select_tag_schema(tag_options),
        description_placeholders={"hint": "Wähle den zu löschenden Tag"},
    )


async def _load_tags(flow) -> dict:
    from .entity_tags_store import async_get_entity_tags
    return await async_get_entity_tags(flow.hass)


def _reload_module(flow) -> None:
    """Ask the entity_tags_module to reload from storage (if loaded)."""
    try:
        entry_id = flow._entry.entry_id if hasattr(flow, "_entry") else None
        if not entry_id:
            return
        data = flow.hass.data.get("ai_home_copilot", {}).get(entry_id, {})
        mod = data.get("entity_tags_module")
        if mod and hasattr(mod, "reload_from_storage"):
            flow.hass.async_create_task(mod.reload_from_storage())
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Failed to reload entity tags after save")
