"""Candidate Poller Module – bridges Core API candidates → HA Repairs UI.

Periodically polls the Core Add-on's ``/api/v1/candidates?state=pending``
endpoint and converts each pending candidate into an HA Repairs issue via
``suggest.async_offer_candidate``.  After offering, marks the candidate as
*offered* in the Core so it is not re-polled.

The module also syncs user decisions (accepted / dismissed) back to the Core
when candidates change state on the HA side.

Poll interval is conservative (5 min default) to avoid overloading the Core.
Includes rate limiting and exponential backoff for API errors.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.config_entries import ConfigEntry

import voluptuous as vol

from homeassistant.core import ServiceCall

from ...api import CopilotApiClient, CopilotApiError
from ...const import DOMAIN
from ...suggest import Candidate as SuggestCandidate, async_offer_candidate
from ..module import CopilotModule, ModuleContext

from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

# Poll every 5 minutes — low overhead, fast enough for non-real-time suggestions.
DEFAULT_POLL_INTERVAL = timedelta(minutes=5)

# Rate limiting for API calls
MAX_REQUESTS_PER_MINUTE = 30
REQUEST_COST = 1.0  # Token cost per poll request

# Storage key used inside hass.data[DOMAIN][entry_id] for bookkeeping.
_DATA_KEY = "candidate_poller"


@dataclass(slots=True)
class _PollerState:
    """Internal state for candidate poller."""
    polling: bool = False
    last_poll_ts: float | None = None
    poll_count: int = 0
    error_count: int = 0
    error_streak: int = 0
    backoff_level: int = 0
    backoff_max_level: int = 5
    backoff_base_delay: float = 1.0
    rate_limit_tokens: float = MAX_REQUESTS_PER_MINUTE
    rate_limit_max_tokens: float = MAX_REQUESTS_PER_MINUTE
    rate_limit_refill_rate: float = MAX_REQUESTS_PER_MINUTE / 60.0
    rate_limit_last_refill: float = 0.0


def _rate_limit_refill(st: _PollerState) -> None:
    """Refill rate limit tokens based on elapsed time."""
    now = time.time()
    if st.rate_limit_last_refill == 0:
        st.rate_limit_last_refill = now
        return
    
    elapsed = now - st.rate_limit_last_refill
    st.rate_limit_tokens = min(
        st.rate_limit_max_tokens,
        st.rate_limit_tokens + (elapsed * st.rate_limit_refill_rate)
    )
    st.rate_limit_last_refill = now


def _rate_limit_consume(st: _PollerState, cost: float = 1.0) -> bool:
    """Try to consume tokens from the rate limiter. Returns True if allowed."""
    _rate_limit_refill(st)
    
    if st.rate_limit_tokens >= cost:
        st.rate_limit_tokens -= cost
        return True
    return False


def _get_backoff_delay(st: _PollerState) -> float:
    """Calculate exponential backoff delay based on error streak."""
    if st.backoff_level <= 0:
        return 0.0
    return min(st.backoff_base_delay * (2 ** st.backoff_level), 60.0)


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
        self._state = _PollerState()

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
        """Single poll cycle: fetch pending candidates, offer to HA, mark as offered.
        
        Includes rate limiting and exponential backoff for error resilience.
        """
        st = self._state
        
        # Prevent concurrent polls
        if st.polling:
            _LOGGER.debug("CandidatePoller: poll already in progress, skipping")
            return
        
        # Check rate limit
        if not _rate_limit_consume(st, cost=REQUEST_COST):
            _LOGGER.debug("CandidatePoller: rate limited, skipping poll")
            return
        
        # Apply exponential backoff if needed
        backoff_delay = _get_backoff_delay(st)
        if backoff_delay > 0:
            _LOGGER.debug("CandidatePoller: backing off %.1fs (level %d)", backoff_delay, st.backoff_level)
            await asyncio.sleep(backoff_delay)
        
        st.polling = True
        
        api = self._get_api(hass, entry)
        if api is None:
            _LOGGER.debug("CandidatePoller: no API client available, skipping poll")
            st.polling = False
            return

        try:
            resp = await api.async_get("/api/v1/candidates?state=pending&include_ready_deferred=true&limit=10")
            
            # Success - reset backoff
            st.backoff_level = 0
            st.error_streak = 0
            st.last_poll_ts = time.time()
            st.poll_count += 1
            
        except CopilotApiError as err:
            st.error_count += 1
            st.error_streak += 1
            st.backoff_level = min(st.backoff_level + 1, st.backoff_max_level)
            _LOGGER.warning("CandidatePoller: failed to fetch candidates: %s (backoff level %d)", err, st.backoff_level)
            st.polling = False
            return
        except Exception as err:
            st.error_count += 1
            st.error_streak += 1
            st.backoff_level = min(st.backoff_level + 1, st.backoff_max_level)
            _LOGGER.warning("CandidatePoller: unexpected error fetching candidates: %s", err)
            st.polling = False
            return

        candidates_raw = resp.get("candidates", [])
        if not candidates_raw:
            _LOGGER.debug("CandidatePoller: no pending candidates")
            st.polling = False
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

        st.polling = False

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

        # Register on-demand mining trigger service.
        await self._register_mining_service(ctx.hass, ctx.entry)

        # Run first poll after a short delay (give Core time to start).
        async def _initial_poll() -> None:
            await asyncio.sleep(30)
            await self._poll_once(ctx.hass, ctx.entry)

        ctx.hass.async_create_task(_initial_poll())
        _LOGGER.info("CandidatePoller: started (interval=%s)", DEFAULT_POLL_INTERVAL)

    async def _register_mining_service(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Register ``ai_home_copilot.trigger_mining`` service (on-demand Core mining run)."""

        if hass.services.has_service(DOMAIN, "trigger_mining"):
            return

        async def _handle_trigger_mining(call: ServiceCall) -> None:
            """Request a mining run from Core and immediately poll for new candidates."""
            api = self._get_api(hass, entry)
            if api is None:
                _LOGGER.error("trigger_mining: no Core API client available")
                return

            payload: dict[str, Any] = {}
            if call.data.get("min_confidence"):
                payload["min_confidence"] = call.data["min_confidence"]
            if call.data.get("min_support"):
                payload["min_support"] = call.data["min_support"]
            if call.data.get("min_lift"):
                payload["min_lift"] = call.data["min_lift"]

            try:
                result = await api.async_post("/api/v1/habitus/mine", payload)
                _LOGGER.info(
                    "trigger_mining: Core returned %d pattern(s)",
                    result.get("discovered", result.get("patterns_found", 0)),
                )
            except CopilotApiError as err:
                _LOGGER.error("trigger_mining: Core API error: %s", err)
                hass.bus.async_fire(
                    f"{DOMAIN}_mining_result",
                    {"ok": False, "error": str(err)},
                )
                return

            # Fire event so automations / UI can react.
            hass.bus.async_fire(
                f"{DOMAIN}_mining_result",
                {"ok": True, "result": result},
            )

            # Immediately poll for newly created candidates.
            await self._poll_once(hass, entry)

        hass.services.async_register(
            DOMAIN,
            "trigger_mining",
            _handle_trigger_mining,
            schema=vol.Schema(
                {
                    vol.Optional("min_confidence"): vol.Coerce(float),
                    vol.Optional("min_support"): vol.Coerce(float),
                    vol.Optional("min_lift"): vol.Coerce(float),
                }
            ),
        )
        _LOGGER.info("Registered service %s.trigger_mining", DOMAIN)

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        if self._unsub:
            self._unsub()
            self._unsub = None

        # Remove mining service if this is the last entry.
        entry_count = len(list(ctx.hass.config_entries.async_entries(DOMAIN)))
        if entry_count <= 1 and ctx.hass.services.has_service(DOMAIN, "trigger_mining"):
            ctx.hass.services.async_remove(DOMAIN, "trigger_mining")

        ent_data = ctx.hass.data.get(DOMAIN, {}).get(ctx.entry.entry_id)
        if isinstance(ent_data, dict):
            ent_data.pop(_DATA_KEY, None)

        _LOGGER.info("CandidatePoller: stopped")
        return True
