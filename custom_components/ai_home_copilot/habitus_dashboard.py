from __future__ import annotations

import logging
from pathlib import Path
import shutil

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .habitus_dashboard_store import HabitusDashboardState, async_get_state, async_set_state
from .habitus_zones_store import async_get_zones, HabitusZone

_LOGGER = logging.getLogger(__name__)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def _entities_card_yaml(title: str, entities: list[str]) -> str:
    lines = [
        "      - type: entities",
        f"        title: {title}",
        "        show_header_toggle: false",
        "        entities:",
    ]
    if not entities:
        lines.append("          - type: section")
        lines.append("            label: (none)")
    else:
        for eid in entities:
            lines.append(f"          - entity: {eid}")
    return "\n".join(lines)


def _history_graph_yaml(title: str, entities: list[str]) -> str:
    lines = [
        "      - type: history-graph",
        f"        title: {title}",
        "        hours_to_show: 24",
        "        entities:",
    ]
    if not entities:
        lines.append("          - sensor.time")
    else:
        for eid in entities[:12]:
            lines.append(f"          - {eid}")
    return "\n".join(lines)


def _logbook_yaml(title: str, entities: list[str]) -> str:
    lines = [
        "      - type: logbook",
        f"        title: {title}",
        "        hours_to_show: 24",
        "        entities:",
    ]
    if not entities:
        lines.append("          - sensor.time")
    else:
        for eid in entities[:12]:
            lines.append(f"          - {eid}")
    return "\n".join(lines)


def _lovelace_yaml_for_zone(z: HabitusZone) -> str:
    """Return a YAML snippet for one Lovelace view.

    UX goal: sensible, named sections for common "extra" entities:
    Helligkeit, Heizung, Luftfeuchte, Schloss, Tür/Fenster, Rollo, Lautstärke/Media, CO₂, etc.

    Zones may optionally provide a categorized mapping via `zone.entities`.
    """

    zone_id = z.zone_id
    zone_name = z.name

    # Categorized entities (role -> list)
    roles: dict[str, list[str]] = {}
    if isinstance(getattr(z, "entities", None), dict):
        for k, v in z.entities.items():
            if isinstance(v, list) and v:
                roles[str(k)] = [str(x) for x in v if str(x)]

    assigned: set[str] = set()
    for items in roles.values():
        assigned.update(items)

    # Fallback groups by domain for any unassigned entities
    domain_groups: dict[str, list[str]] = {
        "binary_sensor": [],
        "light": [],
        "cover": [],
        "climate": [],
        "lock": [],
        "media_player": [],
        "sensor": [],
        "other": [],
    }

    for eid in z.entity_ids:
        if eid in assigned:
            continue
        d = _domain(eid)
        if d in domain_groups:
            domain_groups[d].append(eid)
        else:
            domain_groups["other"].append(eid)

    # Fill common roles if missing
    roles.setdefault("motion", domain_groups["binary_sensor"])
    roles.setdefault("lights", domain_groups["light"])
    roles.setdefault("cover", domain_groups["cover"])
    roles.setdefault("heating", domain_groups["climate"])
    roles.setdefault("lock", domain_groups["lock"])
    roles.setdefault("media", domain_groups["media_player"])

    # Remaining sensors/other
    roles.setdefault("sensor", domain_groups["sensor"])
    roles.setdefault("other", domain_groups["other"])

    # Display order + naming
    ordered: list[tuple[str, str]] = [
        ("lights", "Licht"),
        ("cover", "Rollo / Cover"),
        ("lock", "Schloss"),
        ("heating", "Heizung"),
        ("media", "Media / Lautstärke"),
        ("motion", "Motion / Präsenz"),
        ("door", "Türsensor"),
        ("window", "Fenstersensor"),
        ("brightness", "Helligkeit"),
        ("temperature", "Temperatur"),
        ("humidity", "Luftfeuchte"),
        ("co2", "CO₂"),
        ("noise", "Lärm"),
        ("pressure", "Luftdruck"),
        ("sensor", "Weitere Sensoren"),
        ("other", "Weitere Entitäten"),
    ]

    cards: list[str] = []

    for key, title in ordered:
        ents = roles.get(key) or []
        if not ents:
            continue
        cards.append(_entities_card_yaml(f"{zone_name} — {title}", ents))

    # Key signals for history/logbook
    key_signals = []
    key_signals.extend((roles.get("motion") or [])[:2])
    key_signals.extend((roles.get("lights") or [])[:6])
    key_signals.extend((roles.get("media") or [])[:4])
    key_signals.extend((roles.get("heating") or [])[:2])

    cards.append(_history_graph_yaml(f"{zone_name} — History (24h)", key_signals))
    cards.append(_logbook_yaml(f"{zone_name} — Logbook (24h)", key_signals))

    return (
        f"  - title: {zone_name}\n"
        f"    path: hz-{zone_id}\n"
        f"    icon: mdi:home-circle\n"
        f"    cards:\n"
        + "\n\n".join(cards)
        + "\n"
    )


async def async_generate_habitus_zones_dashboard(hass: HomeAssistant, entry_id: str) -> Path:
    zones = await async_get_zones(hass, entry_id)

    now = dt_util.now()
    ts = now.strftime("%Y%m%d_%H%M%S")

    views = []
    for z in zones:
        views.append(_lovelace_yaml_for_zone(z))

    content = (
        "# Generated by AI Home CoPilot (Habitus zones)\n"
        "# Import this as a YAML dashboard or copy views into an existing dashboard.\n\n"
        "title: Habitus Zones\n"
        "views:\n"
        + ("\n".join(views) if views else "  - title: Habitus Zones\n    path: habitus-zones\n    icon: mdi:layers-outline\n    cards: []\n")
    )

    out_dir = Path(hass.config.path("ai_home_copilot"))
    out_path = out_dir / f"habitus_zones_dashboard_{ts}.yaml"
    latest_path = out_dir / "habitus_zones_dashboard_latest.yaml"

    await hass.async_add_executor_job(_write_text, out_path, content)
    await hass.async_add_executor_job(_write_text, latest_path, content)

    st = await async_get_state(hass)
    st.last_path = str(out_path)
    await async_set_state(hass, st)

    persistent_notification.async_create(
        hass,
        (
            f"Generated Habitus zones dashboard YAML at:\n{out_path}\n\n"
            f"Latest (stable):\n{latest_path}"
        ),
        title="AI Home CoPilot Habitus dashboard",
        notification_id="ai_home_copilot_habitus_dashboard",
    )

    _LOGGER.info("Generated Habitus zones dashboard at %s", out_path)
    return out_path


async def async_publish_last_habitus_dashboard(hass: HomeAssistant) -> str:
    st = await async_get_state(hass)

    if not st.last_path:
        # Nothing generated yet.
        raise FileNotFoundError("No Habitus dashboard generated yet")

    # Publish stable latest file, and keep timestamped archive locally.
    out_dir = Path(hass.config.path("ai_home_copilot"))
    latest_src = out_dir / "habitus_zones_dashboard_latest.yaml"
    if latest_src.exists():
        src = latest_src
    else:
        src = Path(st.last_path)

    if not src.exists():
        raise FileNotFoundError(str(src))

    www_dir = Path(hass.config.path("www")) / "ai_home_copilot"
    dst = www_dir / "habitus_zones_dashboard_latest.yaml"

    await hass.async_add_executor_job(_copy, src, dst)

    st.last_published_path = str(dst)
    await async_set_state(hass, st)

    url = f"/local/ai_home_copilot/{dst.name}"
    persistent_notification.async_create(
        hass,
        f"Habitus dashboard published (stable). Open: {url}",
        title="AI Home CoPilot Habitus dashboard download",
        notification_id="ai_home_copilot_habitus_dashboard_download",
    )

    _LOGGER.info("Published Habitus dashboard to %s (url=%s)", dst, url)
    return url
