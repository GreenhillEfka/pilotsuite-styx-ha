from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .storage import (
    CandidateState,
    async_get_candidate_state,
    async_set_candidate_state,
)


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    title: str
    blueprint_url: str | None = None


def _issue_id(entry_id: str, candidate_id: str) -> str:
    return f"cand_{entry_id}_{candidate_id}".replace("-", "_")


async def async_offer_candidate(hass: HomeAssistant, entry_id: str, candidate: Candidate) -> None:
    state = await async_get_candidate_state(hass, entry_id, candidate.candidate_id)
    if state in (CandidateState.ACCEPTED, CandidateState.DISMISSED):
        return

    await async_set_candidate_state(hass, entry_id, candidate.candidate_id, CandidateState.OFFERED)

    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(entry_id, candidate.candidate_id),
        is_fixable=True,
        is_persistent=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="candidate_suggestion",
        translation_placeholders={
            "title": candidate.title,
        },
        data={
            "entry_id": entry_id,
            "candidate_id": candidate.candidate_id,
            "blueprint_url": candidate.blueprint_url,
        },
        learn_more_url=candidate.blueprint_url,
    )


async def async_offer_demo_candidate(hass: HomeAssistant, entry_id: str) -> None:
    # Demo suggestion to validate the governance UX end-to-end.
    cand = Candidate(
        candidate_id="demo_a_to_b",
        title="A→B: Wenn A passiert, führe B aus (sicherer Blueprint)",
        blueprint_url=None,
    )
    await async_offer_candidate(hass, entry_id, cand)
