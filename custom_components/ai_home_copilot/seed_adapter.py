from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    CONF_SEED_ALLOWED_DOMAINS,
    CONF_SEED_BLOCKED_DOMAINS,
    CONF_SEED_MAX_OFFERS_PER_HOUR,
    CONF_SEED_MAX_OFFERS_PER_UPDATE,
    CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS,
    CONF_SUGGESTION_SEED_ENTITIES,
    DEFAULT_SEED_ALLOWED_DOMAINS,
    DEFAULT_SEED_BLOCKED_DOMAINS,
    DEFAULT_SEED_MAX_OFFERS_PER_HOUR,
    DEFAULT_SEED_MAX_OFFERS_PER_UPDATE,
    DEFAULT_SEED_MIN_SECONDS_BETWEEN_OFFERS,
    DEFAULT_SUGGESTION_SEED_ENTITIES,
    DOMAIN,
)
from .seed_store import SeedLimiterState, async_get_seed_limiter_state, async_set_seed_limiter_state
from .suggest import Candidate, async_offer_candidate

_LOGGER = logging.getLogger(__name__)

_ENTITY_ID_RE = re.compile(r"\b([a-z_]+\.[a-z0-9_]+)\b")


def _parse_domains(value: Any) -> set[str]:
    """Parse domains from config.

    Accepts either list[str] (older config) or a comma/space separated string.
    """

    if value is None:
        return set()

    if isinstance(value, str):
        parts = [p.strip() for p in re.split(r"[,\s]+", value) if p.strip()]
        return set(parts)

    if isinstance(value, list):
        out: set[str] = set()
        for v in value:
            if isinstance(v, str) and v.strip():
                out.add(v.strip())
        return out

    return set()


@dataclass(frozen=True)
class Seed:
    seed_id: str
    title: str
    text: str
    source_entity_id: str
    entities_found: list[str]


def _stable_id(source_entity_id: str, payload: str) -> str:
    h = hashlib.sha1()  # noqa: S324 (non-crypto; stable id)
    h.update(source_entity_id.encode("utf-8"))
    h.update(b"\n")
    h.update(payload.encode("utf-8"))
    return h.hexdigest()[:12]


def _truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _extract_text_from_item(item: Any) -> str:
    if item is None:
        return ""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        # Common fields used by suggestion generators
        parts: list[str] = []
        for k in (
            "title",
            "alias",
            "summary",
            "description",
            "reason",
            "explanation",
            "yaml",
            "automation_yaml",
            "automation",
        ):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
        if parts:
            return "\n".join(parts)
        # fallback: stable json
        try:
            return json.dumps(item, ensure_ascii=False, sort_keys=True)
        except Exception:  # noqa: BLE001
            return str(item)
    return str(item)


def _extract_seeds_from_state(
    source_entity_id: str,
    state: State,
    *,
    allowed_domains: set[str],
    blocked_domains: set[str],
) -> list[Seed]:
    attrs = state.attributes or {}

    candidates: list[Any] = []
    for key in ("suggestions", "items", "recommendations", "results"):
        v = attrs.get(key)
        if isinstance(v, list) and v:
            candidates = v
            break

    if not candidates:
        # Some integrations put the whole payload into a single attribute
        for key in ("suggestion", "result", "data", "payload"):
            v = attrs.get(key)
            if isinstance(v, (dict, list, str)):
                candidates = [v]
                break

    if not candidates:
        # Last resort: use the state itself if it looks like content
        if isinstance(state.state, str) and state.state not in ("unknown", "unavailable", ""):
            candidates = [state.state]

    seeds: list[Seed] = []
    for item in candidates[:20]:
        text = _extract_text_from_item(item)
        if not text.strip():
            continue

        entities_found = sorted(set(_ENTITY_ID_RE.findall(text)))

        # Apply domain allow/block lists to the detected entity_ids.
        if allowed_domains:
            entities_found = [e for e in entities_found if e.split(".")[0] in allowed_domains]
        if blocked_domains:
            entities_found = [e for e in entities_found if e.split(".")[0] not in blocked_domains]

        entities_found = entities_found[:12]

        # If filtering removed everything, skip (avoids spam / low-actionability).
        if (allowed_domains or blocked_domains) and not entities_found:
            continue

        payload = _truncate(text, 800)
        seed_id = _stable_id(source_entity_id, payload)

        title = _truncate(text.splitlines()[0], 80)
        seeds.append(
            Seed(
                seed_id=seed_id,
                title=title,
                text=payload,
                source_entity_id=source_entity_id,
                entities_found=entities_found,
            )
        )

    return seeds


async def _limiter_allow_offer(
    hass: HomeAssistant,
    *,
    max_per_hour: int,
    min_seconds_between: int,
) -> bool:
    now = dt_util.utcnow().timestamp()
    st = await async_get_seed_limiter_state(hass)

    # Reset window if needed
    if st.window_start_ts is None or now - st.window_start_ts >= 3600:
        st = SeedLimiterState(window_start_ts=now, count_in_window=0, last_offer_ts=st.last_offer_ts)

    if max_per_hour > 0 and st.count_in_window >= max_per_hour:
        return False

    if st.last_offer_ts is not None and min_seconds_between > 0:
        if now - st.last_offer_ts < min_seconds_between:
            return False

    st.count_in_window += 1
    st.last_offer_ts = now
    await async_set_seed_limiter_state(hass, st)
    return True


async def async_process_seed_entity(hass: HomeAssistant, entry: ConfigEntry, entity_id: str) -> None:
    st = hass.states.get(entity_id)
    if st is None:
        return

    cfg = entry.data | entry.options

    allowed_domains = _parse_domains(
        cfg.get(CONF_SEED_ALLOWED_DOMAINS, DEFAULT_SEED_ALLOWED_DOMAINS)
    )
    blocked_domains = _parse_domains(
        cfg.get(CONF_SEED_BLOCKED_DOMAINS, DEFAULT_SEED_BLOCKED_DOMAINS)
    )

    max_per_hour = int(cfg.get(CONF_SEED_MAX_OFFERS_PER_HOUR, DEFAULT_SEED_MAX_OFFERS_PER_HOUR) or 0)
    min_seconds_between = int(
        cfg.get(
            CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS,
            DEFAULT_SEED_MIN_SECONDS_BETWEEN_OFFERS,
        )
        or 0
    )
    max_per_update = int(
        cfg.get(CONF_SEED_MAX_OFFERS_PER_UPDATE, DEFAULT_SEED_MAX_OFFERS_PER_UPDATE) or 0
    )
    if max_per_update <= 0:
        max_per_update = 3

    seeds = _extract_seeds_from_state(
        entity_id,
        st,
        allowed_domains=allowed_domains,
        blocked_domains=blocked_domains,
    )

    offered = 0
    for seed in seeds:
        if offered >= max_per_update:
            break

        if not await _limiter_allow_offer(
            hass,
            max_per_hour=max_per_hour,
            min_seconds_between=min_seconds_between,
        ):
            break

        entities_str = ", ".join(seed.entities_found) if seed.entities_found else "(none detected)"
        cand = Candidate(
            candidate_id=f"seed_{entity_id}_{seed.seed_id}".replace(".", "_").replace("-", "_"),
            title=seed.title,
            translation_key="seed_suggestion",
            translation_placeholders={
                "title": seed.title,
                "source": entity_id,
                "entities": _truncate(entities_str, 120),
                "excerpt": _truncate(seed.text.strip().replace("\n", " "), 160),
            },
            data={
                "kind": "seed",
                "seed_source": entity_id,
                "seed_text": seed.text,
                "seed_entities": seed.entities_found,
            },
        )
        await async_offer_candidate(hass, entry.entry_id, cand)
        offered += 1


async def async_setup_seed_adapter(hass: HomeAssistant, entry: ConfigEntry) -> None:
    cfg = entry.data | entry.options
    entity_ids = cfg.get(CONF_SUGGESTION_SEED_ENTITIES, DEFAULT_SUGGESTION_SEED_ENTITIES)
    if not entity_ids:
        return

    # Accept either list[str] or csv string (dashboard config entity writes string)
    if isinstance(entity_ids, str):
        entity_ids = [p.strip() for p in re.split(r"[,\s]+", entity_ids) if p.strip()]

    if not isinstance(entity_ids, list) or not all(isinstance(x, str) for x in entity_ids):
        _LOGGER.warning("Invalid %s option; expected list[str] or csv string", CONF_SUGGESTION_SEED_ENTITIES)
        return

    @callback
    def _handle(event) -> None:
        new_state: State | None = event.data.get("new_state")
        if new_state is None:
            return
        hass.async_create_task(
            async_process_seed_entity(hass, entry, new_state.entity_id)
        )

    unsub = async_track_state_change_event(hass, entity_ids, _handle)
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if isinstance(entry_data, dict):
        entry_data["unsub_seed_adapter"] = unsub

    # Import current state once at startup
    for eid in entity_ids:
        hass.async_create_task(async_process_seed_entity(hass, entry, eid))
