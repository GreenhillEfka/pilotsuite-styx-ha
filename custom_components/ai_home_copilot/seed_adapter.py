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

from .const import CONF_SUGGESTION_SEED_ENTITIES, DEFAULT_SUGGESTION_SEED_ENTITIES, DOMAIN
from .suggest import Candidate, async_offer_candidate

_LOGGER = logging.getLogger(__name__)

_ENTITY_ID_RE = re.compile(r"\b([a-z_]+\.[a-z0-9_]+)\b")


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


def _extract_seeds_from_state(source_entity_id: str, state: State) -> list[Seed]:
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

        entities_found = sorted(set(_ENTITY_ID_RE.findall(text)))[:12]
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


async def async_process_seed_entity(hass: HomeAssistant, entry: ConfigEntry, entity_id: str) -> None:
    st = hass.states.get(entity_id)
    if st is None:
        return

    for seed in _extract_seeds_from_state(entity_id, st):
        entities_str = ", ".join(seed.entities_found) if seed.entities_found else "(none detected)"
        cand = Candidate(
            candidate_id=f"seed_{entity_id}_{seed.seed_id}".replace(".", "_").replace("-", "_"),
            title=seed.title,
            translation_key="seed_suggestion",
            translation_placeholders={
                "title": seed.title,
                "source": entity_id,
                "entities": _truncate(entities_str, 120),
            },
            data={
                "kind": "seed",
                "seed_source": entity_id,
                "seed_text": seed.text,
                "seed_entities": seed.entities_found,
            },
        )
        await async_offer_candidate(hass, entry.entry_id, cand)


async def async_setup_seed_adapter(hass: HomeAssistant, entry: ConfigEntry) -> None:
    cfg = entry.data | entry.options
    entity_ids = cfg.get(CONF_SUGGESTION_SEED_ENTITIES, DEFAULT_SUGGESTION_SEED_ENTITIES)
    if not entity_ids:
        return

    if not isinstance(entity_ids, list) or not all(isinstance(x, str) for x in entity_ids):
        _LOGGER.warning("Invalid %s option; expected list[str]", CONF_SUGGESTION_SEED_ENTITIES)
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
    hass.data[DOMAIN][entry.entry_id]["unsub_seed_adapter"] = unsub

    # Import current state once at startup
    for eid in entity_ids:
        hass.async_create_task(async_process_seed_entity(hass, entry, eid))
