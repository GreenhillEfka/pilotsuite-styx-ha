from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .storage import (
    async_mark_seen,
    async_record_offer,
    async_should_offer,
    async_upsert_candidate_snapshot,
)


@dataclass(frozen=True)
class Candidate:
    """Minimal v0.1 Candidate model used for offering Repairs issues.

    NOTE: This is intentionally small; the persisted snapshot in storage.py is also small.
    """

    candidate_id: str
    kind: Literal["blueprint", "seed"] = "blueprint"
    title: str = ""

    # kind=blueprint
    blueprint_url: str | None = None

    # kind=seed
    seed_source: str | None = None
    seed_entities: list[str] | None = None
    seed_text: str | None = None

    # Optional issue customizations
    translation_key: str = "candidate_suggestion"
    translation_placeholders: dict[str, str] | None = None
    data: dict[str, Any] | None = None
    learn_more_url: str | None = None


def issue_id_for_candidate(entry_id: str, candidate_id: str) -> str:
    """Stable HA-compatible issue_id (no '-')."""
    return f"cand_{entry_id}_{candidate_id}".replace("-", "_")


async def async_offer_candidate(hass: HomeAssistant, entry_id: str, candidate: Candidate) -> None:
    now_ts = dt_util.utcnow().timestamp()

    # Persist small, privacy-safe bookkeeping before offering.
    await async_mark_seen(hass, entry_id, candidate.candidate_id, ts=now_ts)
    await async_upsert_candidate_snapshot(hass, entry_id, candidate)

    if not await async_should_offer(
        hass, entry_id, candidate.candidate_id, now_ts=now_ts
    ):
        return

    # IMPORTANT: placeholders must cover all keys used in strings.json for the translation_key.
    # Otherwise HA may fail rendering the Repairs issue UI.
    placeholders = dict(candidate.translation_placeholders or {"title": candidate.title})

    if candidate.translation_key == "seed_suggestion":
        src = str(candidate.seed_source or "")
        ents = candidate.seed_entities or []
        ents_str = ", ".join([e for e in ents if isinstance(e, str)])
        excerpt = str(candidate.seed_text or "").strip().replace("\n", " ")
        if len(excerpt) > 160:
            excerpt = excerpt[:159] + "…"
        if len(ents_str) > 120:
            ents_str = ents_str[:119] + "…"
        placeholders.setdefault("source", src)
        placeholders.setdefault("entities", ents_str)
        placeholders.setdefault("excerpt", excerpt)
    issue_data: dict[str, Any] = {
        "entry_id": entry_id,
        "candidate_id": candidate.candidate_id,
        "kind": candidate.kind,
        "blueprint_url": candidate.blueprint_url,
        "seed_source": candidate.seed_source,
        "seed_entities": candidate.seed_entities,
        "seed_text": candidate.seed_text,
    }

    if candidate.data:
        issue_data.update(candidate.data)

    issue_id = issue_id_for_candidate(entry_id, candidate.candidate_id)

    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        is_persistent=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=candidate.translation_key,
        translation_placeholders=placeholders,
        data=issue_data,
        learn_more_url=candidate.learn_more_url or candidate.blueprint_url,
    )

    await async_record_offer(
        hass,
        entry_id,
        candidate.candidate_id,
        now_ts=now_ts,
        issue_id=issue_id,
    )


async def async_offer_demo_candidate(hass: HomeAssistant, entry_id: str) -> None:
    # Demo suggestion to validate the governance UX end-to-end.
    # Inputs are intentionally minimal; the Repairs flow can prompt for missing ones.
    cand = Candidate(
        candidate_id="demo_a_to_b",
        kind="blueprint",
        title="A→B: Wenn A passiert, führe B aus (sicherer Blueprint)",
        blueprint_url=None,
        data={
            "blueprint_id": "ai_home_copilot/a_to_b_safe.yaml",
            "blueprint_inputs": {},
            "risk": "medium",
        },
    )
    await async_offer_candidate(hass, entry_id, cand)
