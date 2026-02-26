from __future__ import annotations

import logging
from pathlib import Path
import re
import shutil

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import LEGACY_DASHBOARD_DIR, PRIMARY_DASHBOARD_DIR
from .habitus_dashboard_store import HabitusDashboardState, async_get_state, async_set_state
# DEPRECATED: v1 - prefer v2
# from .habitus_zones_store import async_get_zones, HabitusZone
from .habitus_zones_store_v2 import async_get_zones_v2, HabitusZoneV2

_LOGGER = logging.getLogger(__name__)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _safe_zone_path(zone_id: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", str(zone_id).lower()).strip("-")
    return slug or "zone"


def _yaml_q(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\").replace("\"", "\\\"")
    return f"\"{escaped}\""


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


def _camera_card_yaml(title: str, entity_id: str) -> str:
    return (
        "      - type: picture-entity\n"
        f"        entity: {entity_id}\n"
        f"        name: {title}\n"
        "        camera_view: live\n"
    )


def _gauge_card_yaml(title: str, entity_id: str, *, min_val: int = 0, max_val: int = 100,
                     severity_green: int = 70, severity_yellow: int = 40, severity_red: int = 20) -> str:
    return (
        "      - type: gauge\n"
        f"        entity: {entity_id}\n"
        f"        name: {title}\n"
        f"        min: {min_val}\n"
        f"        max: {max_val}\n"
        "        severity:\n"
        f"          green: {severity_green}\n"
        f"          yellow: {severity_yellow}\n"
        f"          red: {severity_red}\n"
    )


def _thermostat_card_yaml(entity_id: str) -> str:
    return (
        "      - type: thermostat\n"
        f"        entity: {entity_id}\n"
    )


def _picture_glance_yaml(title: str, camera_entity: str, overlay_entities: list[str]) -> str:
    lines = [
        "      - type: picture-glance",
        f"        title: {title}",
        f"        camera_image: {camera_entity}",
        "        entities:",
    ]
    for eid in overlay_entities[:6]:
        lines.append(f"          - {eid}")
    return "\n".join(lines)


def _mini_graph_yaml(title: str, entities: list[str], *, hours: int = 24) -> str:
    """Sensor card with graph line (built-in sensor card)."""
    if not entities:
        return ""
    lines = [
        "      - type: sensor",
        f"        entity: {entities[0]}",
        f"        name: {title}",
        "        graph: line",
        f"        hours_to_show: {hours}",
        "        detail: 2",
    ]
    return "\n".join(lines)


def _horizontal_stack_yaml(cards: list[str]) -> str:
    if not cards:
        return ""
    return "      - type: horizontal-stack\n        cards:\n" + "\n".join(
        c.replace("      - ", "          - ", 1) for c in cards if c
    )


def _zone_header_yaml(zone_name: str, entity_count: int, role_count: int) -> str:
    return (
        "      - type: markdown\n"
        f"        title: {zone_name}\n"
        "        content: |\n"
        f"          **Habitus Zone** | {entity_count} Entities | {role_count} Rollen\n"
    )


def _lovelace_yaml_for_zone(hass: HomeAssistant, z: HabitusZoneV2) -> str:
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
            if isinstance(v, (list, tuple, set)) and v:
                roles[str(k)] = [str(x) for x in v if str(x)]

    assigned: set[str] = set()
    for items in roles.values():
        assigned.update(items)

    # Fallback groups by domain for any unassigned entities
    domain_groups: dict[str, list[str]] = {
        "binary_sensor": [],
        "light": [],
        "camera": [],
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
    roles.setdefault("camera", domain_groups["camera"])
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
            _LOGGER.debug(
                "Average sensor %s not yet available for zone %s (%d sources)",
                eid, zone_id, len(sources),
            )
            return []
        return [_entity_card_yaml(title, eid)]

    cards: list[str] = []

    # Zone header with summary
    role_count = sum(1 for r in roles.values() if r)
    total_entities = len(z.entity_ids)
    cards.append(_zone_header_yaml(zone_name, total_entities, role_count))

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

    # Cover / Schloss
    if roles.get("cover"):
        cards.append(_entities_card_yaml("Rollo / Cover", roles.get("cover") or []))
    if roles.get("lock"):
        cards.append(_entities_card_yaml("Schloss", roles.get("lock") or [], secondary_info="last-changed"))

    # Heizung — enhanced with thermostat cards
    heating = roles.get("heating") or []
    if heating:
        climate_entities = [e for e in heating if e.startswith("climate.")]
        other_heating = [e for e in heating if not e.startswith("climate.")]
        for clim in climate_entities[:2]:
            cards.append(_thermostat_card_yaml(clim))
        if other_heating:
            cards.append(_entities_card_yaml("Heizung", other_heating))

    # Media
    if roles.get("media"):
        cards.append(_entities_card_yaml("Media / Lautstärke", roles.get("media") or [], secondary_info="last-changed"))

    # Camera — enhanced with picture-glance overlay
    if roles.get("camera"):
        cams = roles.get("camera") or []
        overlay_eids = (motion or [])[:2] + (lights or [])[:2]
        for cam in cams[:4]:
            if overlay_eids:
                cards.append(_picture_glance_yaml("Kamera Live", cam, overlay_eids))
            else:
                cards.append(_camera_card_yaml("Kamera Live", cam))
        if len(cams) > 1:
            cards.append(_entities_card_yaml("Kameras", cams))

    # Motion/Präsenz (mit letzter Änderung)
    motion = roles.get("motion") or []
    if motion:
        cards.append(_entities_card_yaml("Motion / Präsenz", motion, secondary_info="last-changed"))

    # Tür/Fenster
    if roles.get("door"):
        cards.append(_entities_card_yaml("Türsensor", roles.get("door") or [], secondary_info="last-changed"))
    if roles.get("window"):
        cards.append(_entities_card_yaml("Fenstersensor", roles.get("window") or [], secondary_info="last-changed"))

    # Messwerte — enhanced with gauge cards and mini graphs
    brightness = roles.get("brightness") or []
    if brightness:
        gauge_graphs: list[str] = []
        for b_eid in brightness[:2]:
            gauge_graphs.append(_mini_graph_yaml("Helligkeit", [b_eid], hours=12))
        if gauge_graphs:
            cards.append(_horizontal_stack_yaml(gauge_graphs))
        cards.append(_entities_card_yaml("Helligkeit", brightness))
        cards.append(_history_graph_yaml("Helligkeit — Verlauf (24h)", brightness))

    temperature = roles.get("temperature") or []
    if temperature:
        cards.extend(_maybe_avg_card("temperature", "Temperatur Ø", temperature))
        # Gauge card for first temperature sensor
        if temperature:
            cards.append(_gauge_card_yaml(
                "Temperatur", temperature[0],
                min_val=10, max_val=35,
                severity_green=22, severity_yellow=18, severity_red=15,
            ))
        cards.append(_entities_card_yaml("Temperatur", temperature))
        cards.append(_history_graph_yaml("Temperatur — Verlauf (24h)", temperature))

    humidity = roles.get("humidity") or []
    if humidity:
        cards.extend(_maybe_avg_card("humidity", "Luftfeuchte Ø", humidity))
        if humidity:
            cards.append(_gauge_card_yaml(
                "Luftfeuchte", humidity[0],
                min_val=0, max_val=100,
                severity_green=55, severity_yellow=40, severity_red=25,
            ))
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
        if illuminance:
            cards.append(_gauge_card_yaml(
                "Beleuchtungsstärke", illuminance[0],
                min_val=0, max_val=1000,
                severity_green=300, severity_yellow=100, severity_red=50,
            ))
        cards.append(_entities_card_yaml("Beleuchtungsstärke", illuminance))
        cards.append(_history_graph_yaml("Beleuchtungsstärke — Verlauf (24h)", illuminance))

    co2 = roles.get("co2") or []
    if co2:
        cards.append(_gauge_card_yaml(
            "CO₂", co2[0],
            min_val=300, max_val=2000,
            severity_green=800, severity_yellow=1000, severity_red=1500,
        ))
        cards.append(_entities_card_yaml("CO₂", co2))
        cards.append(_history_graph_yaml("CO₂ — Verlauf (24h)", co2))

    noise = roles.get("noise") or []
    if noise:
        cards.append(_gauge_card_yaml(
            "Lärm", noise[0],
            min_val=20, max_val=100,
            severity_green=45, severity_yellow=60, severity_red=75,
        ))
        cards.append(_entities_card_yaml("Lärm", noise))
        cards.append(_history_graph_yaml("Lärm — Verlauf (24h)", noise))

    pressure = roles.get("pressure") or []
    if pressure:
        cards.append(_entities_card_yaml("Luftdruck", pressure))
        cards.append(_history_graph_yaml("Luftdruck — Verlauf (24h)", pressure))

    power = roles.get("power") or []
    if power:
        cards.extend(_maybe_avg_card("power", "Leistung Ø", power))
        if power:
            cards.append(_gauge_card_yaml(
                "Leistung (W)", power[0],
                min_val=0, max_val=3000,
                severity_green=500, severity_yellow=1500, severity_red=2500,
            ))
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
    key_signals.extend((roles.get("camera") or [])[:2])
    key_signals.extend((lights or [])[:6])
    key_signals.extend((roles.get("media") or [])[:4])
    key_signals.extend((roles.get("heating") or [])[:2])
    key_signals.extend((temperature or [])[:2])
    key_signals.extend((humidity or [])[:2])

    cards.append(_history_graph_yaml("Übersicht — Verlauf (24h)", key_signals))
    cards.append(_logbook_yaml("Übersicht — Logbuch (24h)", key_signals))

    return (
        f"  - title: {_yaml_q(zone_name)}\n"
        f"    path: {_yaml_q('hz-' + _safe_zone_path(zone_id))}\n"
        f"    icon: mdi:home-circle\n"
        f"    cards:\n"
        + "\n\n".join(cards)
        + "\n"
    )


async def async_generate_habitus_zones_dashboard(
    hass: HomeAssistant,
    entry_id: str,
    *,
    notify: bool = True,
) -> Path:
    zones = await async_get_zones_v2(hass, entry_id)

    now = dt_util.now()
    ts = now.strftime("%Y%m%d_%H%M%S")

    views = []
    for z in zones:
        views.append(_lovelace_yaml_for_zone(hass, z))

    content = (
        "# Generiert von PilotSuite (Habitus-Zonen)\n"
        "# Governance-first: Diese Datei wird NICHT automatisch in Lovelace importiert.\n"
        "# Sie wird von den Buttons aktualisiert (Generate).\n\n"
        "title: Habitus-Zonen\n"
        "views:\n"
        + ("\n".join(views) if views else "  - title: Habitus Zones\n    path: habitus-zones\n    icon: mdi:layers-outline\n    cards: []\n")
    )

    primary_out_dir = Path(hass.config.path(PRIMARY_DASHBOARD_DIR))
    legacy_out_dir = Path(hass.config.path(LEGACY_DASHBOARD_DIR))
    out_path = primary_out_dir / f"habitus_zones_dashboard_{ts}.yaml"
    latest_path = primary_out_dir / "habitus_zones_dashboard_latest.yaml"
    legacy_latest_path = legacy_out_dir / "habitus_zones_dashboard_latest.yaml"

    await hass.async_add_executor_job(_write_text, out_path, content)
    await hass.async_add_executor_job(_write_text, latest_path, content)
    await hass.async_add_executor_job(_write_text, legacy_latest_path, content)

    st = await async_get_state(hass)
    st.last_path = str(out_path)
    await async_set_state(hass, st)

    if notify:
        persistent_notification.async_create(
            hass,
            (
                f"Generated Habitus zones dashboard YAML at:\n{out_path}\n\n"
                f"Latest (stable):\n{latest_path}\n\n"
                f"Legacy mirror:\n{legacy_latest_path}"
            ),
            title="PilotSuite Habitus dashboard",
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
    primary_dir = Path(hass.config.path(PRIMARY_DASHBOARD_DIR))
    legacy_dir = Path(hass.config.path(LEGACY_DASHBOARD_DIR))
    primary_latest = primary_dir / "habitus_zones_dashboard_latest.yaml"
    legacy_latest = legacy_dir / "habitus_zones_dashboard_latest.yaml"
    if primary_latest.exists():
        src = primary_latest
    elif legacy_latest.exists():
        src = legacy_latest
    else:
        src = Path(st.last_path)

    if not src.exists():
        raise FileNotFoundError(str(src))

    www_primary_dir = Path(hass.config.path("www")) / PRIMARY_DASHBOARD_DIR
    www_legacy_dir = Path(hass.config.path("www")) / LEGACY_DASHBOARD_DIR
    dst = www_primary_dir / "habitus_zones_dashboard_latest.yaml"
    legacy_dst = www_legacy_dir / "habitus_zones_dashboard_latest.yaml"

    await hass.async_add_executor_job(_copy, src, dst)
    await hass.async_add_executor_job(_copy, src, legacy_dst)

    st.last_published_path = str(dst)
    await async_set_state(hass, st)

    url = f"/local/{PRIMARY_DASHBOARD_DIR}/{dst.name}"
    persistent_notification.async_create(
        hass,
        (
            f"Habitus dashboard published (stable). Open: {url}\n\n"
            f"Legacy URL: /local/{LEGACY_DASHBOARD_DIR}/{dst.name}"
        ),
        title="PilotSuite Habitus dashboard download",
        notification_id="ai_home_copilot_habitus_dashboard_download",
    )

    _LOGGER.info("Published Habitus dashboard to %s (url=%s)", dst, url)
    return url
