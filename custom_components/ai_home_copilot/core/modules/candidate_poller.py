"""Candidate Poller Module – bridges Core API candidates → HA Repairs UI.

Periodically polls the Core Add-on's ``/api/v1/candidates?state=pending``
endpoint and converts each pending candidate into an HA Repairs issue via
``suggest.async_offer_candidate``.  After offering, marks the candidate as
*offered* in the Core so it is not re-polled.

The module also syncs user decisions (accepted / dismissed) back to the Core
when candidates change state on the HA side.

Poll interval is conservative (5 min default) to avoid overloading the Core.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.config_entries import ConfigEntry

from ...api import CopilotApiClient, CopilotApiError
from ...const import DOMAIN
from ...suggest import Candidate as SuggestCandidate, async_offer_candidate
from ..module import CopilotModule, ModuleContext

from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

# Poll every 5 minutes — low overhead, fast enough for non-real-time suggestions.
DEFAULT_POLL_INTERVAL = timedelta(minutes=5)

# Storage key used inside hass.data[DOMAIN][entry_id] for bookkeeping.
_DATA_KEY = "candidate_poller"


def _build_suggest_candidate(raw: dict[str, Any]) -> SuggestCandidate | None:
    """Convert a Core API candidate dict into an HA SuggestCandidate."""
    cid = raw.get("candidate_id")
    if not cid:
        return None

    metadata = raw.get("metadata") or {}
    evidence = raw.get("evidence") or {}

    trigger = metadata.get("trigger_entity", "")
    target = metadata.get("target_entity", "")

    # Build human-readable title from pattern entities.
    if trigger and target:
        title = f"A→B: {trigger} → {target}"
    else:
        title = f"A→B Pattern ({cid[:8]})"

    # Evidence data for N1 transparency display.
    data: dict[str, Any] = {"evidence": evidence}
    data["core_candidate_id"] = cid
    data["pattern_id"] = raw.get("pattern_id")

    # If the miner provided blueprint info, use it.
    blueprint_url = metadata.get("blueprint_url")
    blueprint_id = metadata.get("blueprint_id", "ai_home_copilot/a_to_b_safe.yaml")
    if blueprint_id:
        data["blueprint_id"] = blueprint_id

    # Pre-populate blueprint inputs from pattern metadata.
    blueprint_inputs: dict[str, Any] = {}
    if trigger:
        blueprint_inputs["a_entity"] = trigger
    if target:
        blueprint_inputs["b_target"] = {"entity_id": target}
    if blueprint_inputs:
        data["blueprint_inputs"] = blueprint_inputs
    data["risk"] = "medium"

    return SuggestCandidate(
        candidate_id=f"core_{cid}",
        kind="blueprint",
        title=title,
        blueprint_url=blueprint_url,
        translation_key="candidate_suggestion",
        translation_placeholders={"title": title},
        data=data,
    )


class CandidatePollerModule:
    """Module that polls Core for pending candidates and offers them in HA."""

    name = "candidate_poller"

    def __init__(self) -> None:
        self._unsub: CALLBACK_TYPE | None = None
        self._entry_id: str | None = None

    def _get_api(self, hass: HomeAssistant, entry: ConfigEntry) -> CopilotApiClient | None:
        """Retrieve the shared CopilotApiClient for this entry."""
        ent_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if isinstance(ent_data, dict):
            coord = ent_data.get("coordinator")
            api = getattr(coord, "api", None)
            if isinstance(api, CopilotApiClient):
                return api
        return None

    async def _poll_once(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Single poll cycle: fetch pending candidates, offer to HA, mark as offered."""
        api = self._get_api(hass, entry)
        if api is None:
            _LOGGER.debug("CandidatePoller: no API client available, skipping poll")
            return

        try:
            resp = await api.async_get("/api/v1/candidates?state=pending&include_ready_deferred=true&limit=10")
        except CopilotApiError as err:
            _LOGGER.warning("CandidatePoller: failed to fetch candidates: %s", err)
            return

        candidates_raw = resp.get("candidates", [])
        if not candidates_raw:
            _LOGGER.debug("CandidatePoller: no pending candidates")
            return

        _LOGGER.info("CandidatePoller: %d pending candidate(s) from Core", len(candidates_raw))

        for raw in candidates_raw:
            cand = _build_suggest_candidate(raw)
            if cand is None:
                continue

            try:
                await async_offer_candidate(hass, entry.entry_id, cand)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("CandidatePoller: failed to offer candidate %s", cand.candidate_id)
                continue

            # Mark as offered in Core (best-effort).
            core_id = raw.get("candidate_id")
            if core_id:
                try:
                    await api.async_post(
                        f"/api/v1/candidates/{core_id}",
                        {"state": "offered"},
                    )
                except CopilotApiError:
                    _LOGGER.debug("CandidatePoller: could not mark %s as offered in Core", core_id)

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        self._entry_id = ctx.entry.entry_id

        # Defensive: store bookkeeping data.
        ent_data = ctx.hass.data.setdefault(DOMAIN, {}).setdefault(ctx.entry.entry_id, {})
        if isinstance(ent_data, dict):
            ent_data[_DATA_KEY] = {"active": True, "polls": 0}

        # Schedule periodic poll.
        async def _tick(_now: Any) -> None:
            # Track poll count.
            d = ctx.hass.data.get(DOMAIN, {}).get(ctx.entry.entry_id)
            if isinstance(d, dict) and isinstance(d.get(_DATA_KEY), dict):
                d[_DATA_KEY]["polls"] = d[_DATA_KEY].get("polls", 0) + 1
            await self._poll_once(ctx.hass, ctx.entry)

        self._unsub = async_track_time_interval(ctx.hass, _tick, DEFAULT_POLL_INTERVAL)

        # Run first poll after a short delay (give Core time to start).
        async def _initial_poll() -> None:
            await asyncio.sleep(30)
            await self._poll_once(ctx.hass, ctx.entry)

        ctx.hass.async_create_task(_initial_poll())
        _LOGGER.info("CandidatePoller: started (interval=%s)", DEFAULT_POLL_INTERVAL)

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        if self._unsub:
            self._unsub()
            self._unsub = None

        ent_data = ctx.hass.data.get(DOMAIN, {}).get(ctx.entry.entry_id)
        if isinstance(ent_data, dict):
            ent_data.pop(_DATA_KEY, None)

        _LOGGER.info("CandidatePoller: stopped")
        return True
