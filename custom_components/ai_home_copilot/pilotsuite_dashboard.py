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
    DEFAULT_DEVLOG_PUSH_ENABLED,
    DEFAULT_MEDIA_MUSIC_PLAYERS,
    DEFAULT_MEDIA_TV_PLAYERS,
)
from .habitus_zones_store import async_get_zones
from .pilotsuite_dashboard_store import PilotSuiteDashboardState, async_get_state, async_set_state

_LOGGER = logging.getLogger(__name__)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def _entities_card(title: str, entities: list[str]) -> str:
    lines = [
        "      - type: entities",
        f"        title: {title}",
        "        show_header_toggle: false",
        "        entities:",
    ]
    if not entities:
        lines.append("          - type: section")
        lines.append("            label: (no entities)")
    else:
        for eid in entities:
            lines.append(f"          - entity: {eid}")
    return "\n".join(lines)


def _markdown_card(title: str, content: str) -> str:
    return (
        "      - type: markdown\n"
        f"        title: {title}\n"
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
        f"  - title: {title}\n"
        f"    path: {path}\n"
        f"    icon: {icon}\n"
        f"    cards:\n"
        f"{cards_yaml}\n"
    )


async def async_generate_pilotsuite_dashboard(hass: HomeAssistant, entry: ConfigEntry) -> Path:
    """Generate a governance-first Lovelace YAML dashboard.

    PilotSuite goal: give operators a ready-to-import dashboard *without* auto-modifying Lovelace.
    """

    cfg = entry.data | entry.options

    zones = await async_get_zones(hass, entry.entry_id)
    has_zones = len(zones) > 0

    music_players = cfg.get(CONF_MEDIA_MUSIC_PLAYERS, DEFAULT_MEDIA_MUSIC_PLAYERS)
    tv_players = cfg.get(CONF_MEDIA_TV_PLAYERS, DEFAULT_MEDIA_TV_PLAYERS)
    has_media = bool(music_players) or bool(tv_players)

    devlogs_enabled = bool(cfg.get(CONF_DEVLOG_PUSH_ENABLED, DEFAULT_DEVLOG_PUSH_ENABLED))

    # Known entity_ids from this integration (stable unique_ids).
    overview_entities = [
        "binary_sensor.ai_home_copilot_online",
        "sensor.ai_home_copilot_version",
        "sensor.ai_home_copilot_core_api_v1",
        "sensor.ai_home_copilot_habitus_zones_count",
    ]

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

    operations_entities = [
        "button.ai_home_copilot_reload_config_entry",
        "button.ai_home_copilot_forwarder_status",
        "button.ai_home_copilot_fetch_ha_errors",
        "button.ai_home_copilot_generate_config_snapshot",
        "button.ai_home_copilot_download_config_snapshot",
    ]

    # Generate reicht: die Dashboards referenzieren jeweils die stabile `*_latest.yaml` Datei.
    # Download/Publish ist nur für /local-Downloads nötig.
    dashboards_entities = [
        "button.ai_home_copilot_generate_pilotsuite_dashboard",
        "button.ai_home_copilot_generate_habitus_dashboard",
    ]

    core_entities = [
        "button.ai_home_copilot_fetch_core_capabilities",
        "button.ai_home_copilot_fetch_core_events",
    ]

    habitus_entities = [
        "button.ai_home_copilot_validate_habitus_zones",
    ]

    media_entities = [
        "sensor.ai_home_copilot_music_now_playing",
        "sensor.ai_home_copilot_music_primary_area",
        "sensor.ai_home_copilot_music_active_count",
        "sensor.ai_home_copilot_tv_primary_area",
        "sensor.ai_home_copilot_tv_source",
        "sensor.ai_home_copilot_tv_active_count",
    ]

    # Dev push buttons are disabled-by-default; keep the read-only fetch visible.
    # Dev/Fehler-Surface: hier bündeln wir die "sichtbar machen" Buttons.
    dev_entities = [
        "button.ai_home_copilot_fetch_ha_errors",
        "button.ai_home_copilot_devlogs_fetch",
        "button.ai_home_copilot_forwarder_status",
        "button.ai_home_copilot_fetch_core_events",
        "button.ai_home_copilot_fetch_core_capabilities",
    ]

    views: list[str] = []

    host = str(cfg.get("host") or "homeassistant.local")
    port = int(cfg.get("port") or 8909)
    if host.startswith("http://") or host.startswith("https://"):
        core_base = f"{host}:{port}" if ":" not in host.split("//", 1)[1] else host
    else:
        core_base = f"http://{host}:{port}"

    intro = _markdown_card(
        "Übersicht",
        f"""
Dieses Dashboard wird von **AI Home CoPilot** generiert (governance-first).

**Quicklinks (Core):**
- Health: [{core_base}/health]({core_base}/health)
- Version: [{core_base}/version]({core_base}/version)
- Events: [{core_base}/api/v1/events]({core_base}/api/v1/events)

**Hinweis:** In YAML-Dashboards ist der visuelle Editor nicht verfügbar. Änderungen kommen über **Generate** (Buttons) + Browser-Reload.
""",
    )

    grid_cards = [
        _entities_card("Status", overview_entities),
        _entities_card("Betrieb (sicher)", operations_entities),
        _entities_card("Dashboards (Generate)", dashboards_entities),
        _entities_card("Core API", core_entities),
    ]
    if resource_entities:
        grid_cards.append(_entities_card("Systemressourcen", resource_entities))

    grid = _grid_card(grid_cards, columns=2)

    views.append(_view("CoPilot", "copilot", "mdi:robot-outline", "\n\n".join([intro, grid])))

    # Core view
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
                        """
Wenn `/api/v1/events` leer bleibt:
- **Forwarder-Status** prüfen
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
        views.append(
            _view(
                "Habitus",
                "copilot-habitus",
                "mdi:layers-outline",
                _entities_card("Habitus-Zonen", habitus_entities),
            )
        )

    # Entwicklung / Dev Surface (immer nützlich, bewusst leichtgewichtig)
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
        "# Generiert von AI Home CoPilot (PilotSuite)\n"
        "# Governance-first: Diese Datei wird NICHT automatisch in Lovelace importiert.\n"
        "# In deiner YAML-Dashboard-Konfig referenzierst du die stabile `pilotsuite_dashboard_latest.yaml`.\n"
        "# Daher reicht in der Regel: **Generate** drücken + Dashboard neu laden.\n\n"
        "title: AI Home CoPilot — PilotSuite\n"
        "views:\n"
        + "\n".join(views)
    )

    out_dir = Path(hass.config.path("ai_home_copilot"))
    out_path = out_dir / f"pilotsuite_dashboard_{ts}.yaml"
    latest_path = out_dir / "pilotsuite_dashboard_latest.yaml"

    await hass.async_add_executor_job(_write_text, out_path, content)
    await hass.async_add_executor_job(_write_text, latest_path, content)

    st = await async_get_state(hass)
    st.last_path = str(out_path)
    await async_set_state(hass, st)

    persistent_notification.async_create(
        hass,
        (
            f"PilotSuite-Dashboard YAML generiert:\n{out_path}\n\n"
            f"Latest (stabil):\n{latest_path}\n\n"
            "Hinweis: In der Regel reicht **Generate** + Browser-Reload (das Dashboard referenziert die latest-Datei)."
        ),
        title="AI Home CoPilot PilotSuite",
        notification_id="ai_home_copilot_pilotsuite_dashboard",
    )

    _LOGGER.info("Generated PilotSuite dashboard at %s", out_path)
    return out_path


async def async_publish_last_pilotsuite_dashboard(hass: HomeAssistant) -> str:
    st = await async_get_state(hass)

    if not st.last_path:
        raise FileNotFoundError("No PilotSuite dashboard generated yet")

    # Publish stable latest file, and keep timestamped archive locally.
    out_dir = Path(hass.config.path("ai_home_copilot"))
    latest_src = out_dir / "pilotsuite_dashboard_latest.yaml"
    if latest_src.exists():
        src = latest_src
    else:
        src = Path(st.last_path)

    if not src.exists():
        raise FileNotFoundError(str(src))

    www_dir = Path(hass.config.path("www")) / "ai_home_copilot"
    dst = www_dir / "pilotsuite_dashboard_latest.yaml"

    await hass.async_add_executor_job(_copy, src, dst)

    st.last_published_path = str(dst)
    await async_set_state(hass, st)

    url = f"/local/ai_home_copilot/{dst.name}"
    persistent_notification.async_create(
        hass,
        f"PilotSuite dashboard published (stable). Open: {url}",
        title="AI Home CoPilot PilotSuite dashboard download",
        notification_id="ai_home_copilot_pilotsuite_dashboard_download",
    )

    _LOGGER.info("Published PilotSuite dashboard to %s (url=%s)", dst, url)
    return url
