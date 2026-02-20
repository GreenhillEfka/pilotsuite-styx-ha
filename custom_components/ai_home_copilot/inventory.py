from __future__ import annotations

import logging
from collections import Counter, defaultdict
from pathlib import Path

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry
from homeassistant.util import dt as dt_util

from .overview_store import OverviewState, async_get_overview_state, async_set_overview_state

_LOGGER = logging.getLogger(__name__)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


async def async_generate_ha_overview(hass: HomeAssistant) -> Path:
    """Generate a structured overview of the HA instance.

    Privacy-first: stays local, writes to /config/ai_home_copilot/.
    """

    ar = area_registry.async_get(hass)
    dr = device_registry.async_get(hass)
    er = entity_registry.async_get(hass)

    areas = list(ar.async_list_areas())
    devices = list(dr.devices.values())
    entities = list(er.entities.values())

    domain_counts = Counter(e.domain for e in entities)

    # area_id → counts
    area_device_counts: Counter[str] = Counter()
    area_entity_counts: Counter[str] = Counter()

    # device_id → area_id
    device_area: dict[str, str | None] = {}
    for d in devices:
        device_area[d.id] = d.area_id
        if d.area_id:
            area_device_counts[d.area_id] += 1

    for e in entities:
        area_id = e.area_id
        if not area_id and e.device_id:
            area_id = device_area.get(e.device_id)
        if area_id:
            area_entity_counts[area_id] += 1

    # Unassigned
    unassigned_devices = sum(1 for d in devices if not d.area_id)
    unassigned_entities = 0
    for e in entities:
        area_id = e.area_id
        if not area_id and e.device_id:
            area_id = device_area.get(e.device_id)
        if not area_id:
            unassigned_entities += 1

    # Manufacturer breakdown (helps spot device families)
    mfg_counts = Counter((d.manufacturer or "(unknown)") for d in devices)

    # Group devices by (area, manufacturer) to spot clusters
    area_mfg: dict[str, Counter[str]] = defaultdict(Counter)
    for d in devices:
        if d.area_id:
            area_mfg[d.area_id][d.manufacturer or "(unknown)"] += 1

    now = dt_util.now()
    ts = now.strftime("%Y-%m-%d %H:%M:%S")

    def area_name(area_id: str) -> str:
        a = ar.async_get_area(area_id)
        return a.name if a else area_id

    md: list[str] = []
    md.append(f"# Home Assistant overview (generated {ts})")
    md.append("")
    md.append("## Totals")
    md.append(f"- Areas: **{len(areas)}**")
    md.append(f"- Devices: **{len(devices)}** (unassigned: {unassigned_devices})")
    md.append(f"- Entities: **{len(entities)}** (unassigned: {unassigned_entities})")
    md.append("")

    md.append("## Top domains (entities)")
    for domain, cnt in domain_counts.most_common(15):
        md.append(f"- {domain}: {cnt}")
    md.append("")

    md.append("## Areas (device/entity density)")
    # sort by entity density
    for area_id, cnt in area_entity_counts.most_common(30):
        md.append(
            f"- {area_name(area_id)}: devices={area_device_counts.get(area_id, 0)}, entities={cnt}"
        )
        # top manufacturers in area
        top_mfg = area_mfg.get(area_id)
        if top_mfg:
            top = ", ".join(f"{m}({c})" for m, c in top_mfg.most_common(5))
            md.append(f"  - manufacturers: {top}")
    md.append("")

    md.append("## Manufacturers (devices)")
    for mfg, cnt in mfg_counts.most_common(20):
        md.append(f"- {mfg}: {cnt}")
    md.append("")

    md.append("## Tag/Label system (recommendation)")
    md.append(
        "Home Assistant supports Areas (rooms) and, depending on your version, Labels. "
        "A pragmatic internal tagging convention that scales:"
    )
    md.append("- `room:<name>` for physical rooms/areas")
    md.append("- `system:<zigbee|zwave|network|energy|security>` for subsystems")
    md.append("- `role:<sensor|actuator|controller|media>` for device roles")
    md.append("- `critical` for devices/entities where failures should alert")
    md.append("")

    md.append("## Next clean-up suggestions (low risk)")
    md.append("- Assign areas to unassigned devices where possible (improves grouping).")
    md.append("- For noisy/large sensors, keep attributes small (avoid recorder 16KB warnings).")
    md.append("- Standardize naming: `<area> <device>` helps habit mining and suggestions.")

    content = "\n".join(md) + "\n"

    out_dir = Path(hass.config.path("ai_home_copilot"))
    out_path = out_dir / f"ha_overview_{now.strftime('%Y%m%d_%H%M%S')}.md"

    await hass.async_add_executor_job(_write_text, out_path, content)

    # Also copy to /share (if present) for easy access via Samba/Add-ons.
    shared_path = None
    try:
        share_dir = Path("/share") / "ai_home_copilot"
        if share_dir.exists() or share_dir.parent.exists():
            share_dir.mkdir(parents=True, exist_ok=True)
            shared_path = share_dir / out_path.name
            await hass.async_add_executor_job(_write_text, shared_path, content)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Unable to write overview to /share (not available)")

    # Persist last generated path (for later download/publish).
    st = await async_get_overview_state(hass)
    st.last_path = str(out_path)
    if shared_path is not None:
        st.last_shared_path = str(shared_path)
    await async_set_overview_state(hass, st)

    persistent_notification.async_create(
        hass,
        f"Generated Home Assistant overview report at: {out_path}",
        title="PilotSuite overview",
        notification_id="ai_home_copilot_overview",
    )

    _LOGGER.info("Generated HA overview report at %s", out_path)
    return out_path
