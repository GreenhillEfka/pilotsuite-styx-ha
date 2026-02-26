from __future__ import annotations

import logging
from pathlib import Path
import shutil

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DEVLOG_PUSH_ENABLED,
    CONF_MEDIA_MUSIC_PLAYERS,
    CONF_MEDIA_TV_PLAYERS,
    CONF_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
    CONF_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
    CONF_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
    DEFAULT_DEVLOG_PUSH_ENABLED,
    DEFAULT_MEDIA_MUSIC_PLAYERS,
    DEFAULT_MEDIA_TV_PLAYERS,
    DEFAULT_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
    DEFAULT_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
    DEFAULT_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
    LEGACY_DASHBOARD_DIR,
    PRIMARY_DASHBOARD_DIR,
)
# DEPRECATED: v1 - prefer v2
# from .habitus_zones_store import async_get_zones
from .habitus_zones_store_v2 import async_get_zones_v2
from .pilotsuite_dashboard_store import PilotSuiteDashboardState, async_get_state, async_set_state

_LOGGER = logging.getLogger(__name__)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _resolve_entity(hass: HomeAssistant, candidates: list[str]) -> str | None:
    """Pick first existing entity_id from candidates."""
    for entity_id in candidates:
        if hass.states.get(entity_id) is not None:
            return entity_id
    return None


def _compact_entities(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _existing_entities(hass: HomeAssistant, entity_ids: list[str]) -> list[str]:
    return [entity_id for entity_id in entity_ids if hass.states.get(entity_id) is not None]


def _entities_card(title: str, entities: list[str]) -> str:
    clean_entities = [eid for eid in entities if isinstance(eid, str) and eid.strip()]
    lines = [
        "      - type: entities",
        f"        title: {_yaml_q(title)}",
        "        show_header_toggle: false",
        "        entities:",
    ]
    if not clean_entities:
        lines.append("          - type: section")
        lines.append("            label: (no entities)")
    else:
        for eid in clean_entities:
            lines.append(f"          - entity: {eid}")
    return "\n".join(lines)


def _markdown_card(title: str, content: str) -> str:
    return (
        "      - type: markdown\n"
        f"        title: {_yaml_q(title)}\n"
        "        content: |\n"
        + "\n".join(["          " + ln for ln in content.strip().splitlines()])
        + "\n"
    )


def _grid_card(cards: list[str], *, columns: int = 2) -> str:
    # cards entries are already full YAML card snippets starting with "      - type: ...".
    # Convert them into nested cards under a grid card.
    nested = []
    for c in cards:
        # strip leading list marker indentation (6 spaces + '- ')
        lines = c.splitlines()
        if not lines:
            continue
        if lines[0].startswith("      - "):
            lines[0] = "        - " + lines[0][8:]
        else:
            lines[0] = "        - " + lines[0].lstrip()
        for i in range(1, len(lines)):
            if lines[i].startswith("        "):
                # increase indentation by 2 to align under grid.cards
                lines[i] = "  " + lines[i]
            else:
                lines[i] = "          " + lines[i].lstrip()
        nested.append("\n".join(lines))

    return (
        "      - type: grid\n"
        f"        columns: {int(columns)}\n"
        "        square: false\n"
        "        cards:\n"
        + "\n\n".join(nested)
        + "\n"
    )


def _view(title: str, path: str, icon: str, cards_yaml: str) -> str:
    return (
        f"  - title: {_yaml_q(title)}\n"
        f"    path: {_yaml_q(path)}\n"
        f"    icon: {icon}\n"
        f"    cards:\n"
        f"{cards_yaml}\n"
    )


def _yaml_q(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\").replace("\"", "\\\"")
    return f"\"{escaped}\""


async def async_generate_pilotsuite_dashboard(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    notify: bool = True,
) -> Path:
    """Generate a governance-first Lovelace YAML dashboard.

    PilotSuite goal: give operators a ready-to-import dashboard *without* auto-modifying Lovelace.
    """

    cfg = entry.data | entry.options

    zones = await async_get_zones_v2(hass, entry.entry_id)
    has_zones = len(zones) > 0

    music_players = cfg.get(CONF_MEDIA_MUSIC_PLAYERS, DEFAULT_MEDIA_MUSIC_PLAYERS)
    tv_players = cfg.get(CONF_MEDIA_TV_PLAYERS, DEFAULT_MEDIA_TV_PLAYERS)
    has_media = bool(music_players) or bool(tv_players)

    devlogs_enabled = bool(cfg.get(CONF_DEVLOG_PUSH_ENABLED, DEFAULT_DEVLOG_PUSH_ENABLED))

    # Known entity_ids from this integration (stable unique_ids).
    overview_entities = _compact_entities([
        _resolve_entity(
            hass,
            ["binary_sensor.ai_home_copilot_online", "binary_sensor.pilotsuite_styx_online"],
        ),
        _resolve_entity(
            hass,
            ["sensor.ai_home_copilot_version", "sensor.pilotsuite_styx_version"],
        ),
        _resolve_entity(
            hass,
            ["sensor.ai_home_copilot_core_api_v1", "sensor.pilotsuite_core_api_v1"],
        ),
        _resolve_entity(
            hass,
            ["sensor.ai_home_copilot_habitus_zones_count", "sensor.pilotsuite_habitus_zones_count"],
        ),
    ])

    # Systemressourcen (optional; nur anzeigen, wenn vorhanden)
    resource_candidates = [
        # system_monitor (typisch)
        "sensor.processor_use",
        "sensor.memory_use_percent",
        "sensor.disk_use_percent",
        "sensor.load_1m",
        "sensor.load_5m",
        "sensor.load_15m",
        # alternative naming (je nach Setup)
        "sensor.cpu_use",
        "sensor.ram_use_percent",
        "sensor.system_monitor_processor_use",
        "sensor.system_monitor_memory_use_percent",
    ]
    resource_entities = [e for e in resource_candidates if hass.states.get(e) is not None]

    operations_entities = _compact_entities([
        _resolve_entity(
            hass,
            ["button.ai_home_copilot_reload_config_entry", "button.pilotsuite_reload_config_entry"],
        ),
        _resolve_entity(
            hass,
            ["button.ai_home_copilot_forwarder_status", "button.pilotsuite_forwarder_status"],
        ),
        _resolve_entity(
            hass,
            ["button.ai_home_copilot_fetch_ha_errors", "button.pilotsuite_fetch_ha_errors"],
        ),
    ])

    show_safety_backup = bool(
        cfg.get(
            CONF_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
            DEFAULT_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
        )
    )
    if show_safety_backup:
        operations_entities.extend(
            _existing_entities(
                hass,
                [
                "button.ai_home_copilot_safety_backup_create",
                "button.ai_home_copilot_safety_backup_status",
                ],
            )
        )

    show_dev_surface = bool(
        cfg.get(
            CONF_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
            DEFAULT_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
        )
    )
    if show_dev_surface:
        operations_entities.extend(
            _existing_entities(
                hass,
                [
                "button.ai_home_copilot_ping_core",
                "button.ai_home_copilot_enable_debug_30m",
                "button.ai_home_copilot_disable_debug",
                "button.ai_home_copilot_clear_error_digest",
                ],
            )
        )

    show_graph_bridge = bool(
        cfg.get(
            CONF_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
            DEFAULT_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
        )
    )
    if show_graph_bridge:
        operations_entities.extend(
            _existing_entities(
                hass,
                [
                "button.ai_home_copilot_preview_graph_candidates",
                "button.ai_home_copilot_offer_graph_candidates",
                ],
            )
        )

    operations_entities.extend(
        _existing_entities(
            hass,
            [
            "button.ai_home_copilot_generate_config_snapshot",
            "button.ai_home_copilot_download_config_snapshot",
            ],
        )
    )
    operations_entities = _compact_entities(operations_entities)

    # Generate reicht: die Dashboards referenzieren jeweils die stabile `*_latest.yaml` Datei.
    # Download/Publish ist nur für /local-Downloads nötig.
    dashboards_entities = _compact_entities([
        _resolve_entity(
            hass,
            ["button.ai_home_copilot_generate_pilotsuite_dashboard", "button.pilotsuite_generate_pilotsuite_dashboard"],
        ),
        _resolve_entity(
            hass,
            ["button.ai_home_copilot_generate_habitus_dashboard", "button.pilotsuite_generate_habitus_dashboard"],
        ),
    ])

    core_entities = _compact_entities([
        _resolve_entity(
            hass,
            ["button.ai_home_copilot_fetch_core_capabilities", "button.pilotsuite_fetch_core_capabilities"],
        ),
        _resolve_entity(
            hass,
            ["button.ai_home_copilot_fetch_core_events", "button.pilotsuite_fetch_core_events"],
        ),
        _resolve_entity(
            hass,
            ["button.ai_home_copilot_fetch_core_graph_state", "button.pilotsuite_fetch_core_graph_state"],
        ),
    ])

    habitus_entities = _existing_entities(
        hass,
        [
        "button.ai_home_copilot_validate_habitus_zones",
        ],
    )

    media_entities = _existing_entities(
        hass,
        [
        "sensor.ai_home_copilot_music_now_playing",
        "sensor.ai_home_copilot_music_primary_area",
        "sensor.ai_home_copilot_music_active_count",
        "sensor.ai_home_copilot_tv_primary_area",
        "sensor.ai_home_copilot_tv_source",
        "sensor.ai_home_copilot_tv_active_count",
        ],
    )

    # Dev push buttons are disabled-by-default; keep the read-only fetch visible.
    # Dev/Fehler-Surface: hier bündeln wir die "sichtbar machen" Buttons.
    dev_entities = _existing_entities(
        hass,
        [
        "button.ai_home_copilot_fetch_ha_errors",
        "button.ai_home_copilot_devlogs_fetch",
        "button.ai_home_copilot_forwarder_status",
        "button.ai_home_copilot_fetch_core_events",
        "button.ai_home_copilot_fetch_core_capabilities",
        ],
    )

    views: list[str] = []

    host = str(cfg.get("host") or "homeassistant.local")
    port = int(cfg.get("port") or 8909)
    if host.startswith("http://") or host.startswith("https://"):
        core_base = f"{host}:{port}" if ":" not in host.split("//", 1)[1] else host
    else:
        core_base = f"http://{host}:{port}"

    # ── VIEW 1: SYSTEM OVERVIEW ──────────────────────────────────────
    intro = _markdown_card(
        "PilotSuite Styx",
        f"""
**System-Dashboard** — generiert von PilotSuite (governance-first).

**Core:** [{core_base}/health]({core_base}/health)
| [{core_base}/version]({core_base}/version)
""",
    )

    system_entities = _compact_entities([
        *overview_entities,
        _resolve_entity(hass, [
            "sensor.ai_home_copilot_pipeline_health",
            "sensor.pilotsuite_styx_pipeline_health",
        ]),
        _resolve_entity(hass, [
            "sensor.ai_home_copilot_llm_health",
            "sensor.pilotsuite_styx_llm_health",
        ]),
    ])

    module_status_entity = _resolve_entity(hass, [
        "sensor.pilotsuite_styx_pilotsuite_module_status",
        f"sensor.{entry.entry_id}_module_status",
    ])
    module_entities: list[str] = []
    if module_status_entity:
        module_entities.append(module_status_entity)
    core_modules_entity = _resolve_entity(hass, [
        "sensor.ai_home_copilot_core_modules",
    ])
    if core_modules_entity:
        module_entities.append(core_modules_entity)
    rag_status_entity = _resolve_entity(hass, [
        "sensor.ai_home_copilot_rag_status",
    ])
    if rag_status_entity:
        module_entities.append(rag_status_entity)

    system_grid_cards = [
        _entities_card("Systemstatus", system_entities),
        _entities_card("Module & Core", module_entities),
        _entities_card("Betrieb", operations_entities),
    ]
    if resource_entities:
        system_grid_cards.append(_entities_card("Systemressourcen", resource_entities))
    system_grid_cards.append(_entities_card("Dashboards", dashboards_entities))

    system_grid = _grid_card(system_grid_cards, columns=2)
    views.append(_view("System", "copilot-system", "mdi:cog", "\n\n".join([intro, system_grid])))

    # ── VIEW 2: NEURONEN & STIMMUNG ──────────────────────────────────
    mood_entities_list = _existing_entities(hass, [
        "sensor.ai_home_copilot_mood",
        "sensor.ai_home_copilot_mood_confidence",
        "sensor.ai_home_copilot_neuron_activity",
        "sensor.ai_home_copilot_neuron_layers",
    ])
    neuron_14_entities = _existing_entities(hass, [
        "sensor.ai_home_copilot_presence_room",
        "sensor.ai_home_copilot_presence_person",
        "sensor.ai_home_copilot_activity_level",
        "sensor.ai_home_copilot_activity_stillness",
        "sensor.ai_home_copilot_time_of_day",
        "sensor.ai_home_copilot_day_type",
        "sensor.ai_home_copilot_routine_stability",
        "sensor.ai_home_copilot_light_level",
        "sensor.ai_home_copilot_noise_level",
        "sensor.ai_home_copilot_weather_context",
        "sensor.ai_home_copilot_calendar_load",
        "sensor.ai_home_copilot_attention_load",
        "sensor.ai_home_copilot_stress_proxy",
        "sensor.ai_home_copilot_energy_proxy",
    ])
    media_neuron_entities = _existing_entities(hass, [
        "sensor.ai_home_copilot_media_activity",
        "sensor.ai_home_copilot_media_intensity",
    ])

    neuron_grid_cards = [
        _entities_card("Stimmung", mood_entities_list),
    ]
    if neuron_14_entities:
        neuron_grid_cards.append(_entities_card("Kontext-Neuronen (14)", neuron_14_entities))
    if media_neuron_entities:
        neuron_grid_cards.append(_entities_card("Media-Neuronen", media_neuron_entities))

    neuron_grid = _grid_card(neuron_grid_cards, columns=2)
    views.append(
        _view("Neuronen", "copilot-neurons", "mdi:head-heart-outline", neuron_grid)
    )

    # ── VIEW 3: BRAIN GRAPH ──────────────────────────────────────────
    brain_entities = _existing_entities(hass, [
        "sensor.ai_home_copilot_brain_graph_summary",
        "sensor.ai_home_copilot_brain_graph",
        "sensor.ai_home_copilot_brain_architecture",
        "sensor.ai_home_copilot_brain_activity",
    ])
    habitus_rule_entities = _existing_entities(hass, [
        "sensor.ai_home_copilot_habitus_rules_summary",
        "sensor.ai_home_copilot_habitus_rules",
        "sensor.ai_home_copilot_habitus_miner_rule_count",
        "sensor.ai_home_copilot_habitus_miner_status",
        "sensor.ai_home_copilot_habitus_miner_top_rule",
    ])

    brain_grid_cards = [
        _entities_card("Brain Graph", brain_entities),
        _entities_card("Habitus Regeln", habitus_rule_entities),
        _entities_card("Core API", core_entities),
    ]
    brain_grid = _grid_card(brain_grid_cards, columns=2)
    views.append(
        _view("Brain Graph", "copilot-brain", "mdi:graph", brain_grid)
    )

    # ── VIEW 4: CORE & API ──────────────────────────────────────────
    views.append(
        _view(
            "Core",
            "copilot-core",
            "mdi:api",
            "\n\n".join(
                [
                    _entities_card("Core-Tools", core_entities),
                    _markdown_card(
                        "Hinweise",
                        f"""
Core-API: [{core_base}/api/v1/events]({core_base}/api/v1/events)

Wenn `/api/v1/events` leer bleibt:
- **Forwarder-Status** pruefen
- ein Licht toggeln, das in einer Habitus-Zone liegt
- **HA-Fehler** holen (Thread-Safety / POST-Fehler)
""",
                    ),
                ]
            ),
        )
    )

    if has_media:
        views.append(
            _view(
                "Media",
                "copilot-media",
                "mdi:speaker",
                _entities_card("Medien (Kontext)", media_entities),
            )
        )

    if has_zones:
        habitus_custom_card = (
            "      - type: custom:ha-copilot-habitus-card\n"
            "        entity: sensor.ai_home_copilot_habitus_zones\n"
            "        title: Habitus-Zonen\n"
        )
        habitus_buttons = _entities_card("Habitus-Steuerung", habitus_entities)

        # HomeKit QR codes per zone
        homekit_cards: list[str] = []
        for z in zones:
            if z.current_state == "disabled":
                continue
            zone_slug = z.zone_id.replace(":", "_").replace(" ", "_")
            qr_url = f"{core_base}/api/v1/homekit/qr/{z.zone_id}.svg"
            homekit_card = _markdown_card(
                f"HomeKit — {z.name} by Styx",
                f"![QR]({qr_url})\n\n"
                f"**Zone:** {z.name}\n"
                f"**Entities:** {len(z.entity_ids) if z.entity_ids else 0}\n\n"
                f"Scanne den QR-Code mit der Apple Home App,\n"
                f"um **{z.name}** zu deinem Zuhause hinzuzufügen.",
            )
            homekit_cards.append(homekit_card)

        homekit_section = ""
        if homekit_cards:
            homekit_section = _grid_card(homekit_cards, columns=2)

        habitus_content = [habitus_custom_card, habitus_buttons]
        if homekit_section:
            habitus_content.append(homekit_section)

        views.append(
            _view(
                "Habitus",
                "copilot-habitus",
                "mdi:layers-outline",
                "\n\n".join(habitus_content),
            )
        )

    # ── VIEW: ML & ENERGY INTELLIGENCE ─────────────────────────────
    ml_entities = _existing_entities(hass, [
        "sensor.ai_home_copilot_energy_insight",
        "sensor.ai_home_copilot_energy_recommendation",
        "sensor.ai_home_copilot_habit_learning",
        "sensor.ai_home_copilot_habit_prediction",
        "sensor.ai_home_copilot_sequence_prediction",
        "sensor.ai_home_copilot_anomaly_alert",
        "sensor.ai_home_copilot_alert_history",
        "sensor.ai_home_copilot_predictive_automation",
        "sensor.ai_home_copilot_predictive_automation_details",
    ])
    if ml_entities:
        views.append(
            _view(
                "ML & Energie",
                "copilot-ml",
                "mdi:brain",
                _entities_card("ML Intelligence", ml_entities),
            )
        )

    # Entwicklung / Dev Surface (immer nuetzlich, bewusst leichtgewichtig)
    views.append(
        _view(
            "Entwicklung",
            "copilot-dev",
            "mdi:bug-outline",
            _entities_card("Dev Surface", dev_entities),
        )
    )

    now = dt_util.now()
    ts = now.strftime("%Y%m%d_%H%M%S")

    content = (
        "# Generiert von PilotSuite\n"
        "# Governance-first: Diese Datei wird NICHT automatisch in Lovelace importiert.\n"
        "# In deiner YAML-Dashboard-Konfig referenzierst du die stabile `pilotsuite_dashboard_latest.yaml`.\n"
        "# Daher reicht in der Regel: **Generate** drücken + Dashboard neu laden.\n\n"
        "title: PilotSuite\n"
        "views:\n"
        + "\n".join(views)
    )

    primary_out_dir = Path(hass.config.path(PRIMARY_DASHBOARD_DIR))
    legacy_out_dir = Path(hass.config.path(LEGACY_DASHBOARD_DIR))
    out_path = primary_out_dir / f"pilotsuite_dashboard_{ts}.yaml"
    latest_path = primary_out_dir / "pilotsuite_dashboard_latest.yaml"
    legacy_latest_path = legacy_out_dir / "pilotsuite_dashboard_latest.yaml"

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
                f"PilotSuite-Dashboard YAML generiert:\n{out_path}\n\n"
                f"Latest (stabil):\n{latest_path}\n\n"
                f"Legacy mirror:\n{legacy_latest_path}\n\n"
                "Hinweis: In der Regel reicht **Generate** + Browser-Reload (das Dashboard referenziert die latest-Datei)."
            ),
            title="PilotSuite Dashboard",
            notification_id="ai_home_copilot_pilotsuite_dashboard",
        )

    _LOGGER.info("Generated PilotSuite dashboard at %s", out_path)
    return out_path


async def async_publish_last_pilotsuite_dashboard(hass: HomeAssistant) -> str:
    st = await async_get_state(hass)

    if not st.last_path:
        raise FileNotFoundError("No PilotSuite dashboard generated yet")

    # Publish stable latest file, and keep timestamped archive locally.
    primary_dir = Path(hass.config.path(PRIMARY_DASHBOARD_DIR))
    legacy_dir = Path(hass.config.path(LEGACY_DASHBOARD_DIR))
    primary_latest = primary_dir / "pilotsuite_dashboard_latest.yaml"
    legacy_latest = legacy_dir / "pilotsuite_dashboard_latest.yaml"
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
    dst = www_primary_dir / "pilotsuite_dashboard_latest.yaml"
    legacy_dst = www_legacy_dir / "pilotsuite_dashboard_latest.yaml"

    await hass.async_add_executor_job(_copy, src, dst)
    await hass.async_add_executor_job(_copy, src, legacy_dst)

    st.last_published_path = str(dst)
    await async_set_state(hass, st)

    url = f"/local/{PRIMARY_DASHBOARD_DIR}/{dst.name}"
    persistent_notification.async_create(
        hass,
        (
            f"PilotSuite dashboard published (stable). Open: {url}\n\n"
            f"Legacy URL: /local/{LEGACY_DASHBOARD_DIR}/{dst.name}"
        ),
        title="PilotSuite Dashboard Download",
        notification_id="ai_home_copilot_pilotsuite_dashboard_download",
    )

    _LOGGER.info("Published PilotSuite dashboard to %s (url=%s)", dst, url)
    return url
