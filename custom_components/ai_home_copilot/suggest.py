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

    # Optional issue customizations
    translation_key: str = "candidate_suggestion"
    translation_placeholders: dict[str, str] | None = None
    data: dict[str, Any] | None = None
    learn_more_url: str | None = None


def _issue_id(entry_id: str, candidate_id: str) -> str:
    return f"cand_{entry_id}_{candidate_id}".replace("-", "_")


async def async_offer_candidate(hass: HomeAssistant, entry_id: str, candidate: Candidate) -> None:
    state = await async_get_candidate_state(hass, entry_id, candidate.candidate_id)
    if state in (CandidateState.ACCEPTED, CandidateState.DISMISSED):
        return

    if state == CandidateState.DEFERRED:
        from homeassistant.util import dt as dt_util
        from .storage import async_get_candidate_record

        rec = await async_get_candidate_record(hass, entry_id, candidate.candidate_id)
        until_ts = rec.get("defer_until_ts")
        try:
            until_ts = float(until_ts)
        except Exception:  # noqa: BLE001
            until_ts = None

        if until_ts and dt_util.utcnow().timestamp() < until_ts:
            return

    await async_set_candidate_state(hass, entry_id, candidate.candidate_id, CandidateState.OFFERED)

    placeholders = candidate.translation_placeholders or {"title": candidate.title}
    data = {
        "entry_id": entry_id,
        "candidate_id": candidate.candidate_id,
        "blueprint_url": candidate.blueprint_url,
    }
    if candidate.data:
        data.update(candidate.data)

    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(entry_id, candidate.candidate_id),
        is_fixable=True,
        is_persistent=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=candidate.translation_key,
        translation_placeholders=placeholders,
        data=data,
        learn_more_url=candidate.learn_more_url or candidate.blueprint_url,
    )


async def async_offer_demo_candidate(hass: HomeAssistant, entry_id: str) -> None:
    # Demo suggestion to validate the governance UX end-to-end.
    cand = Candidate(
        candidate_id="demo_a_to_b",
        title="A→B: Wenn A passiert, führe B aus (sicherer Blueprint)",
        blueprint_url=None,
    )
    await async_offer_candidate(hass, entry_id, cand)
