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
        lines.append("          - entity: sensor.time")
        lines.append("            name: (no entities)")
    else:
        for eid in entities:
            lines.append(f"          - entity: {eid}")
    return "\n".join(lines)


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

    operations_entities = [
        # These buttons are kept enabled by default.
        "button.ai_home_copilot_reload_config_entry",
        "button.ai_home_copilot_generate_config_snapshot",
        "button.ai_home_copilot_download_config_snapshot",
        "button.ai_home_copilot_generate_ha_overview",
        "button.ai_home_copilot_download_ha_overview",
    ]

    # Advanced health/fixer tools are disabled-by-default; keep them out of the default dashboard.
    health_entities: list[str] = []

    core_entities = [
        "button.ai_home_copilot_fetch_core_capabilities",
        "button.ai_home_copilot_fetch_core_events",
    ]

    habitus_entities = [
        "button.ai_home_copilot_validate_habitus_zones",
        "button.ai_home_copilot_generate_habitus_dashboard",
        "button.ai_home_copilot_download_habitus_dashboard",
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
    dev_entities = [
        "button.ai_home_copilot_devlogs_fetch",
    ]

    views: list[str] = []

    cards = []
    cards.append(_entities_card("AI Home CoPilot — Overview", overview_entities))
    cards.append(_entities_card("AI Home CoPilot — Operations", operations_entities))
    if health_entities:
        cards.append(_entities_card("AI Home CoPilot — Health", health_entities))
    views.append(_view("CoPilot", "copilot", "mdi:robot-outline", "\n\n".join(cards)))

    # Core view always exists (safe even if endpoint returns 404).
    views.append(
        _view(
            "Core", "copilot-core", "mdi:api", _entities_card("Copilot-Core tools", core_entities)
        )
    )

    if has_media:
        views.append(
            _view(
                "Media",
                "copilot-media",
                "mdi:speaker",
                _entities_card("MediaContext", media_entities),
            )
        )

    if has_zones:
        views.append(
            _view(
                "Habitus",
                "copilot-habitus",
                "mdi:layers-outline",
                _entities_card("Habitus zones", habitus_entities),
            )
        )

    # Dev view: always useful; keep it lightweight.
    views.append(
        _view(
            "Dev",
            "copilot-dev",
            "mdi:bug-outline",
            _entities_card("Dev surface", dev_entities),
        )
    )

    now = dt_util.now()
    ts = now.strftime("%Y%m%d_%H%M%S")

    content = (
        "# Generated by AI Home CoPilot (PilotSuite)\n"
        "# Governance-first: this file is NOT auto-imported into Lovelace.\n"
        "# Import as a YAML dashboard, or copy/paste views into your existing dashboard.\n\n"
        "title: AI Home CoPilot — PilotSuite\n"
        "views:\n"
        + "\n".join(views)
    )

    out_dir = Path(hass.config.path("ai_home_copilot"))
    out_path = out_dir / f"pilotsuite_dashboard_{ts}.yaml"

    await hass.async_add_executor_job(_write_text, out_path, content)

    st = await async_get_state(hass)
    st.last_path = str(out_path)
    await async_set_state(hass, st)

    persistent_notification.async_create(
        hass,
        f"Generated PilotSuite dashboard YAML at: {out_path}",
        title="AI Home CoPilot PilotSuite dashboard",
        notification_id="ai_home_copilot_pilotsuite_dashboard",
    )

    _LOGGER.info("Generated PilotSuite dashboard at %s", out_path)
    return out_path


async def async_publish_last_pilotsuite_dashboard(hass: HomeAssistant) -> str:
    st = await async_get_state(hass)

    if not st.last_path:
        raise FileNotFoundError("No PilotSuite dashboard generated yet")

    src = Path(st.last_path)
    if not src.exists():
        raise FileNotFoundError(str(src))

    www_dir = Path(hass.config.path("www")) / "ai_home_copilot"
    dst = www_dir / src.name

    await hass.async_add_executor_job(_copy, src, dst)

    st.last_published_path = str(dst)
    await async_set_state(hass, st)

    url = f"/local/ai_home_copilot/{dst.name}"
    persistent_notification.async_create(
        hass,
        f"PilotSuite dashboard published. Open: {url}",
        title="AI Home CoPilot PilotSuite dashboard download",
        notification_id="ai_home_copilot_pilotsuite_dashboard_download",
    )

    _LOGGER.info("Published PilotSuite dashboard to %s (url=%s)", dst, url)
    return url
