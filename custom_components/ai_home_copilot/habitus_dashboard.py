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


def _entities_card_yaml(
    title: str,
    entities: list[str],
    *,
    secondary_info: str | None = None,
    show_header_toggle: bool = False,
) -> str:
    """Create an Entities card.

    If `secondary_info` is provided, it is applied to all rows.
    Example: secondary_info="last-changed".
    """

    # De-dupe while keeping order.
    seen: set[str] = set()
    uniq: list[str] = []
    for e in entities:
        if not e or e in seen:
            continue
        seen.add(e)
        uniq.append(e)

    lines = [
        "      - type: entities",
        f"        title: {title}",
        f"        show_header_toggle: {'true' if show_header_toggle else 'false'}",
        "        entities:",
    ]
    if not uniq:
        lines.append("          - type: section")
        lines.append("            label: (keine)")
    else:
        for eid in uniq:
            lines.append(f"          - entity: {eid}")
            if secondary_info:
                lines.append(f"            secondary_info: {secondary_info}")
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


def _service_button_yaml(title: str, icon: str, service: str, entity_ids: list[str]) -> str:
    # Simple built-in button card (no custom cards).
    # Note: this is a stateless control; it will always be tappable.
    ent_list = [e for e in entity_ids if e]
    target = "[]" if not ent_list else (
        "[" + ", ".join([f"'{e}'" for e in ent_list]) + "]"
    )
    return (
        "      - type: button\n"
        f"        name: {title}\n"
        f"        icon: {icon}\n"
        "        tap_action:\n"
        "          action: call-service\n"
        f"          service: {service}\n"
        "          target:\n"
        f"            entity_id: {target}\n"
    )


def _entity_card_yaml(title: str, entity_id: str) -> str:
    return (
        "      - type: entity\n"
        f"        entity: {entity_id}\n"
        f"        name: {title}\n"
    )


def _lovelace_yaml_for_zone(hass: HomeAssistant, z: HabitusZone) -> str:
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

    # Optional roles for energy/power
    roles.setdefault("power", [])
    roles.setdefault("energy", [])

    def _avg_entity_id(metric: str) -> str:
        # Stable entity_id created by the integration (if enabled/available).
        return f"sensor.ai_home_copilot_hz_{zone_id}_{metric}_avg"

    def _maybe_avg_card(metric: str, title: str, sources: list[str]) -> list[str]:
        # Policy: show average if there are >=2 source entities.
        if len(sources) < 2:
            return []
        eid = _avg_entity_id(metric)
        if hass.states.get(eid) is None:
            return []
        return [_entity_card_yaml(title, eid)]

    cards: list[str] = []

    # Licht
    lights = roles.get("lights") or []
    if lights:
        if len(lights) > 1:
            cards.append(
                _service_button_yaml(
                    "Licht (alle) umschalten",
                    "mdi:lightbulb-group",
                    "light.toggle",
                    lights,
                )
            )
        cards.append(_entities_card_yaml("Licht", lights, show_header_toggle=True))

    # Cover / Schloss / Heizung / Media
    if roles.get("cover"):
        cards.append(_entities_card_yaml("Rollo / Cover", roles.get("cover") or []))
    if roles.get("lock"):
        cards.append(_entities_card_yaml("Schloss", roles.get("lock") or []))
    if roles.get("heating"):
        cards.append(_entities_card_yaml("Heizung", roles.get("heating") or []))
    if roles.get("media"):
        cards.append(_entities_card_yaml("Media / Lautstärke", roles.get("media") or []))

    # Motion/Präsenz (mit letzter Änderung)
    motion = roles.get("motion") or []
    if motion:
        cards.append(_entities_card_yaml("Motion / Präsenz", motion, secondary_info="last-changed"))

    # Tür/Fenster
    if roles.get("door"):
        cards.append(_entities_card_yaml("Türsensor", roles.get("door") or []))
    if roles.get("window"):
        cards.append(_entities_card_yaml("Fenstersensor", roles.get("window") or []))

    # Messwerte (mit mehr Graphen)
    brightness = roles.get("brightness") or []
    if brightness:
        cards.append(_entities_card_yaml("Helligkeit", brightness))
        cards.append(_history_graph_yaml("Helligkeit — Verlauf (24h)", brightness))

    temperature = roles.get("temperature") or []
    if temperature:
        cards.extend(_maybe_avg_card("temperature", "Temperatur Ø", temperature))
        cards.append(_entities_card_yaml("Temperatur", temperature))
        cards.append(_history_graph_yaml("Temperatur — Verlauf (24h)", temperature))

    humidity = roles.get("humidity") or []
    if humidity:
        cards.extend(_maybe_avg_card("humidity", "Luftfeuchte Ø", humidity))
        cards.append(_entities_card_yaml("Luftfeuchte", humidity))
        cards.append(_history_graph_yaml("Luftfeuchte — Verlauf (24h)", humidity))

    # Thermostat (heating targets)
    thermostat = roles.get("thermostat") or []
    if thermostat:
        cards.extend(_maybe_avg_card("thermostat", "Thermostat Ø", thermostat))
        cards.append(_entities_card_yaml("Thermostat", thermostat))
        cards.append(_history_graph_yaml("Thermostat — Verlauf (24h)", thermostat))

    # Illuminance (light level sensors)
    illuminance = roles.get("illuminance") or []
    if illuminance:
        cards.extend(_maybe_avg_card("illuminance", "Beleuchtungsstärke Ø", illuminance))
        cards.append(_entities_card_yaml("Beleuchtungsstärke", illuminance))
        cards.append(_history_graph_yaml("Beleuchtungsstärke — Verlauf (24h)", illuminance))

    co2 = roles.get("co2") or []
    if co2:
        cards.append(_entities_card_yaml("CO₂", co2))
        cards.append(_history_graph_yaml("CO₂ — Verlauf (24h)", co2))

    noise = roles.get("noise") or []
    if noise:
        cards.append(_entities_card_yaml("Lärm", noise))
        cards.append(_history_graph_yaml("Lärm — Verlauf (24h)", noise))

    pressure = roles.get("pressure") or []
    if pressure:
        cards.append(_entities_card_yaml("Luftdruck", pressure))
        cards.append(_history_graph_yaml("Luftdruck — Verlauf (24h)", pressure))

    power = roles.get("power") or []
    if power:
        cards.extend(_maybe_avg_card("power", "Leistung Ø", power))
        cards.append(_entities_card_yaml("Strom (Leistung)", power))
        cards.append(_history_graph_yaml("Strom — Verlauf (24h)", power))

    energy = roles.get("energy") or []
    if energy:
        cards.append(_entities_card_yaml("Energie", energy))
        cards.append(_history_graph_yaml("Energie — Verlauf (24h)", energy))

    # Rest
    if roles.get("sensor"):
        cards.append(_entities_card_yaml("Weitere Sensoren", roles.get("sensor") or []))
    if roles.get("other"):
        cards.append(_entities_card_yaml("Weitere Entitäten", roles.get("other") or []))

    # Key signals for history/logbook (kuratiert)
    key_signals: list[str] = []
    key_signals.extend((motion or [])[:2])
    key_signals.extend((lights or [])[:6])
    key_signals.extend((roles.get("media") or [])[:4])
    key_signals.extend((roles.get("heating") or [])[:2])

    cards.append(_history_graph_yaml("Übersicht — Verlauf (24h)", key_signals))
    cards.append(_logbook_yaml("Übersicht — Logbuch (24h)", key_signals))

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
        views.append(_lovelace_yaml_for_zone(hass, z))

    content = (
        "# Generiert von AI Home CoPilot (Habitus-Zonen)\n"
        "# Governance-first: Diese Datei wird NICHT automatisch in Lovelace importiert.\n"
        "# Sie wird von den Buttons aktualisiert (Generate).\n\n"
        "title: Habitus-Zonen\n"
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
