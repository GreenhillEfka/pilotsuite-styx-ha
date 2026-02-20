from __future__ import annotations

import json
import logging
import os
import shutil
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry
from homeassistant.util import dt as dt_util

from .inventory_store import InventoryState, async_get_inventory_state, async_set_inventory_state
from .privacy import sanitize_text

_LOGGER = logging.getLogger(__name__)

EXPORT_DIR = "/config/ai_home_copilot/exports"
PUBLISH_DIR = "/config/www/ai_home_copilot"


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")



def _redact_text(s: str, *, max_len: int = 64) -> str:
    # Centralized sanitization kernel (security_privacy v0.1).
    return sanitize_text(s, max_chars=max_len)


def _default_publish(domain: str) -> tuple[str, str]:
    """Return (mode, label_mode)."""

    # Conservative defaults; operator can still see IDs in the exported inventory.
    if domain in {"camera"}:
        return ("blocked", "generic")

    if domain in {"device_tracker", "person"}:
        return ("blocked", "generic")

    if domain in {"lock", "alarm_control_panel"}:
        return ("anonymized", "generic")

    # Everything else visible by default (bounded; no attributes blobs).
    return ("visible", "full")


def _supports_from_state(domain: str, st: Any) -> list[str]:
    """Small allowlist for capabilities, derived from state attributes existence."""

    if st is None:
        return []

    attrs = getattr(st, "attributes", None)
    if not isinstance(attrs, dict):
        return []

    sup: list[str] = []

    if domain in {"light", "switch", "fan"}:
        sup.append("on_off")

    if domain == "light":
        if "brightness" in attrs:
            sup.append("brightness")
        if "color_temp" in attrs or "color_temp_kelvin" in attrs:
            sup.append("color_temp")
        if "rgb_color" in attrs or "hs_color" in attrs:
            sup.append("color")

    if domain == "climate":
        if "hvac_modes" in attrs or "hvac_mode" in attrs:
            sup.append("hvac_mode")
        if "temperature" in attrs:
            sup.append("temperature")

    if domain == "cover":
        if "current_position" in attrs:
            sup.append("position")

    if domain == "media_player":
        sup.append("media")
        if "volume_level" in attrs:
            sup.append("volume")

    # Deduplicate while preserving order.
    out: list[str] = []
    seen: set[str] = set()
    for x in sup:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


@dataclass
class _InvArea:
    id: str
    area_id: str
    label: str


@dataclass
class _InvDevice:
    id: str
    device_id: str
    label: str
    area_id: str | None


@dataclass
class _InvEntity:
    id: str
    entity_id: str
    domain: str
    label: str
    area_id: str | None
    device_id: str | None
    supports: list[str]
    publish_mode: str
    publish_label_mode: str


async def async_generate_and_publish_inventory(hass: HomeAssistant) -> dict[str, str]:
    """Generate a bounded HA inventory (JSON + Markdown) and publish under /local.

    Privacy-first:
    - no attributes blobs are exported
    - labels are redacted + truncated
    - conservative defaults for sensitive domains

    Returns URLs: {"json": "/local/...", "md": "/local/..."}
    """

    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(PUBLISH_DIR, exist_ok=True)

    ar = area_registry.async_get(hass)
    dr = device_registry.async_get(hass)
    er = entity_registry.async_get(hass)

    areas = list(ar.async_list_areas())
    devices = list(dr.devices.values())
    entities = list(er.entities.values())

    # Build simple maps
    area_by_id = {a.id: a for a in areas}
    dev_by_id = {d.id: d for d in devices}

    domain_counts = Counter(e.domain for e in entities)

    inv_areas: list[_InvArea] = []
    for a in areas:
        inv_areas.append(
            _InvArea(
                id=f"ha.area:{a.id}",
                area_id=a.id,
                label=_redact_text(a.name or a.id),
            )
        )

    inv_devices: list[_InvDevice] = []
    for d in devices:
        inv_devices.append(
            _InvDevice(
                id=f"ha.device:{d.id}",
                device_id=d.id,
                label=_redact_text(d.name or d.name_by_user or d.id),
                area_id=d.area_id,
            )
        )

    # Domain index for generic labeling.
    domain_idx: Counter[str] = Counter()

    inv_entities: list[_InvEntity] = []
    for e in entities:
        domain = e.domain
        mode, label_mode = _default_publish(domain)

        # Label priority: entity registry name -> original_name -> entity_id
        raw_label = e.name or e.original_name or e.entity_id
        safe_label = _redact_text(raw_label)

        if label_mode != "full":
            domain_idx[domain] += 1
            safe_label = f"{domain.replace('_', ' ').title()} {domain_idx[domain]}"

        st = hass.states.get(e.entity_id)
        supports = _supports_from_state(domain, st)

        # Area: entity-registry area overrides device area; else device area.
        area_id = e.area_id
        if not area_id and e.device_id:
            dev = dev_by_id.get(e.device_id)
            if dev is not None:
                area_id = dev.area_id

        inv_entities.append(
            _InvEntity(
                id=f"ha.entity:{e.entity_id}",
                entity_id=e.entity_id,
                domain=domain,
                label=safe_label,
                area_id=area_id,
                device_id=e.device_id,
                supports=supports,
                publish_mode=mode,
                publish_label_mode=label_mode,
            )
        )

    # Deterministic sort
    inv_areas.sort(key=lambda x: x.id)
    inv_devices.sort(key=lambda x: x.id)
    inv_entities.sort(key=lambda x: x.id)

    generated = datetime.now(timezone.utc).isoformat()

    payload: dict[str, Any] = {
        "schema": "ai_home_copilot_inventory",
        "version": 1,
        "generated": generated,
        "counts": {
            "areas": len(inv_areas),
            "devices": len(inv_devices),
            "entities": len(inv_entities),
        },
        "domains": dict(domain_counts),
        "areas": [asdict(x) for x in inv_areas],
        "devices": [asdict(x) for x in inv_devices],
        "entities": [asdict(x) for x in inv_entities],
        "notes": {
            "privacy": "Bounded export (no attributes). Labels redacted+truncated. Sensitive domains default anonymized/blocked.",
        },
    }

    stamp = _now_stamp()
    base = f"ai_home_copilot_inventory_{stamp}"
    json_path = os.path.join(EXPORT_DIR, base + ".json")
    md_path = os.path.join(EXPORT_DIR, base + ".md")

    def _write_json(path: str, obj: dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2)

    def _write_text(path: str, text: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    # Markdown summary (operator-readable)
    now_local = dt_util.now()
    ts_local = now_local.strftime("%Y-%m-%d %H:%M:%S")

    def _area_label(area_id: str | None) -> str:
        if not area_id:
            return "(unassigned)"
        a = area_by_id.get(area_id)
        return _redact_text(a.name) if a else _redact_text(area_id)

    md_lines: list[str] = []
    md_lines.append(f"# PilotSuite Inventory (generated {ts_local})")
    md_lines.append("")
    md_lines.append("## Totals")
    md_lines.append(f"- Areas: **{len(inv_areas)}**")
    md_lines.append(f"- Devices: **{len(inv_devices)}**")
    md_lines.append(f"- Entities: **{len(inv_entities)}**")
    md_lines.append("")
    md_lines.append("## Top domains")
    for dom, cnt in domain_counts.most_common(20):
        md_lines.append(f"- {dom}: {cnt}")

    md_lines.append("")
    md_lines.append("## Sample entities (first 50, bounded)")
    for it in inv_entities[:50]:
        md_lines.append(
            f"- `{it.entity_id}` ({it.domain}) — {it.label} — area={_area_label(it.area_id)} — publish={it.publish_mode}/{it.publish_label_mode}"
        )

    md_lines.append("")
    md_lines.append("## Notes")
    md_lines.append("- This is a bounded export (no raw HA attributes/state history).")
    md_lines.append("- Some domains are anonymized/blocked by default (privacy-first).")

    md_text = "\n".join(md_lines) + "\n"

    await hass.async_add_executor_job(_write_json, json_path, payload)
    await hass.async_add_executor_job(_write_text, md_path, md_text)

    # Publish to www so it is downloadable via /local
    dst_json = os.path.join(PUBLISH_DIR, os.path.basename(json_path))
    dst_md = os.path.join(PUBLISH_DIR, os.path.basename(md_path))

    def _copy(src: str, dst: str) -> None:
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    await hass.async_add_executor_job(_copy, json_path, dst_json)
    await hass.async_add_executor_job(_copy, md_path, dst_md)

    url_json = f"/local/ai_home_copilot/{os.path.basename(dst_json)}"
    url_md = f"/local/ai_home_copilot/{os.path.basename(dst_md)}"

    # Persist state
    st: InventoryState = await async_get_inventory_state(hass)
    st.last_generated_at = generated
    st.last_generated_json = json_path
    st.last_generated_md = md_path
    st.last_published_json = dst_json
    st.last_published_md = dst_md
    await async_set_inventory_state(hass, st)

    persistent_notification.async_create(
        hass,
        (
            "Inventory generated and published for download:\n"
            f"- Markdown: {url_md}\n"
            f"- JSON: {url_json}\n"
            "\nPrivacy: bounded export (no attributes blobs)."
        ),
        title="PilotSuite inventory",
        notification_id="ai_home_copilot_inventory",
    )

    _LOGGER.info("Inventory published (md=%s json=%s)", url_md, url_json)
    return {"md": url_md, "json": url_json}
