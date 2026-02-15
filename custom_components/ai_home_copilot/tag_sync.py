from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .api import CopilotApiError
from .const import DOMAIN
from .tag_registry import (
    SyncReport,
    async_import_canonical_tags,
    async_replace_assignments_snapshot,
    async_sync_labels_now,
    get_label_registry_sync,
)

_LOGGER = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry:
    entries = hass.config_entries.async_entries(DOMAIN)
    if entry_id:
        for entry in entries:
            if entry.entry_id == entry_id:
                return entry
        raise HomeAssistantError(f"ai_home_copilot entry '{entry_id}' not found")

    if not entries:
        raise HomeAssistantError("No ai_home_copilot config entry is set up yet")
    if len(entries) > 1:
        _LOGGER.debug("Multiple ai_home_copilot entries found; defaulting to the first one")
    return entries[0]


def _get_api(hass: HomeAssistant, entry: ConfigEntry):
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    coordinator = entry_data.get("coordinator") if isinstance(entry_data, dict) else None
    api = getattr(coordinator, "api", None)
    if api is None:
        raise HomeAssistantError(
            "Copilot coordinator is not ready yet (restart Home Assistant or reload the integration)"
        )
    return api


def _report_to_dict(report: SyncReport | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "imported_user_aliases": report.imported_user_aliases,
        "created_labels": report.created_labels,
        "updated_subjects": report.updated_subjects,
        "skipped_pending": report.skipped_pending,
        "errors": report.errors,
    }


async def async_pull_tag_system_snapshot(
    hass: HomeAssistant,
    *,
    entry_id: str | None = None,
    limit: int = 500,
    lang: str = "de",
) -> dict[str, Any]:
    entry = _resolve_entry(hass, entry_id)
    api = _get_api(hass, entry)

    try:
        tags_payload = await api.async_get(f"/api/v1/tag-system/tags?lang={lang}&translations=0")
    except CopilotApiError as err:
        raise HomeAssistantError(f"Failed to fetch tag registry: {err}") from err

    tag_list = tags_payload.get("tags")
    if not isinstance(tag_list, list):
        tag_list = []
    tag_summary = await async_import_canonical_tags(
        hass,
        tags=tag_list,
        schema_version=str(tags_payload.get("schema_version")) if tags_payload.get("schema_version") else None,
        fetched_at=_now_iso(),
    )

    qs = f"limit={max(1, min(limit, 1000))}"
    try:
        assignments_payload = await api.async_get(f"/api/v1/tag-system/assignments?{qs}")
    except CopilotApiError as err:
        raise HomeAssistantError(f"Failed to fetch tag assignments: {err}") from err

    assignments_list = assignments_payload.get("assignments")
    if not isinstance(assignments_list, list):
        assignments_list = []

    assignment_summary = await async_replace_assignments_snapshot(
        hass,
        assignments=assignments_list,
        revision=assignments_payload.get("revision"),
        fetched_at=_now_iso(),
    )

    label_report = await async_sync_labels_now(hass)

    summary = {
        "entry_id": entry.entry_id,
        "tags": tag_summary,
        "assignments": assignment_summary,
        "assignment_revision": assignments_payload.get("revision"),
        "assignment_total": assignments_payload.get("total"),
        "label_sync": _report_to_dict(label_report),
    }

    _LOGGER.info(
        "Tag system pull completed: entry=%s tags=%s assignments=%s label_sync=%s",
        entry.entry_id,
        tag_summary,
        assignment_summary,
        summary["label_sync"],
    )
    return summary
