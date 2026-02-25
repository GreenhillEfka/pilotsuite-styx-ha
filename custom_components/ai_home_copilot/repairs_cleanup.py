from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_LOW_SIGNAL_TOKENS = {
    "",
    "on",
    "off",
    "true",
    "false",
    "unknown",
    "unavailable",
    "none",
    "null",
}
_INTERNAL_SEED_SOURCE_RE = re.compile(
    r"^(sensor|number|text)\.ai_home_copilot_.*seed",
    re.IGNORECASE,
)


def _issue_field(issue: Any, field: str, default: Any = None) -> Any:
    if isinstance(issue, dict):
        return issue.get(field, default)
    return getattr(issue, field, default)


def _as_issue_dict(issue: Any, field: str) -> dict[str, Any]:
    value = _issue_field(issue, field, {})
    return value if isinstance(value, dict) else {}


def _is_low_signal_seed_value(value: str) -> bool:
    text = str(value or "").strip().lower()
    if text in _LOW_SIGNAL_TOKENS:
        return True
    if re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?%?", text):
        return True
    return len(text) < 3


def _is_stale_seed_issue(issue: Any, entry_id: str) -> bool:
    data = _as_issue_dict(issue, "data")
    issue_entry_id = str(data.get("entry_id") or "").strip()
    if issue_entry_id and issue_entry_id != entry_id:
        return False

    translation_key = str(_issue_field(issue, "translation_key", "") or "")
    kind = str(data.get("kind") or "")
    candidate_id = str(data.get("candidate_id") or "")

    is_seed = (
        translation_key == "seed_suggestion"
        or kind == "seed"
        or candidate_id.lower().startswith("seed_")
    )
    if not is_seed:
        return False

    source = str(data.get("seed_source") or "").strip()
    if _INTERNAL_SEED_SOURCE_RE.match(source):
        return True

    entities = data.get("seed_entities")
    entity_ids = [eid for eid in entities if isinstance(eid, str) and eid.strip()] if isinstance(entities, list) else []
    text = str(data.get("seed_text") or "").strip()
    placeholders = _as_issue_dict(issue, "translation_placeholders")
    title = str(placeholders.get("title") or "").strip()

    if entity_ids:
        return False

    # Legacy noise signatures: "CoPilot Seed: on", "PilotSuite Seed: 17", etc.
    if _is_low_signal_seed_value(title):
        return True
    if _is_low_signal_seed_value(text):
        return True

    return False


def _iter_domain_issues(hass: HomeAssistant) -> list[tuple[str, Any]]:
    registry = ir.async_get(hass)
    issues = getattr(registry, "issues", None)
    if not isinstance(issues, dict):
        return []

    out: list[tuple[str, Any]] = []
    for key, issue in issues.items():
        domain = None
        issue_id = None
        if isinstance(key, tuple) and len(key) == 2:
            domain, issue_id = key
        if domain is None:
            domain = _issue_field(issue, "domain")
        if issue_id is None:
            issue_id = _issue_field(issue, "issue_id")
        if domain != DOMAIN or not isinstance(issue_id, str) or not issue_id:
            continue
        out.append((issue_id, issue))
    return out


async def async_cleanup_stale_seed_repairs(hass: HomeAssistant, entry_id: str) -> int:
    removed = 0
    for issue_id, issue in _iter_domain_issues(hass):
        if not _is_stale_seed_issue(issue, entry_id):
            continue
        try:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
            removed += 1
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Failed to delete stale seed issue %s", issue_id, exc_info=True)

    if removed:
        _LOGGER.info("Cleaned up %d stale seed Repairs issue(s)", removed)
    return removed

