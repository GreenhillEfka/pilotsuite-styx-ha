"""Lovelace dashboard wiring helper for PilotSuite.

This module keeps dashboard YAML files and Lovelace wiring aligned:
- writes a stable include snippet file under `ai_home_copilot/`
- auto-appends a minimal Lovelace block only when `configuration.yaml` has no `lovelace:` section
- falls back to a clear manual instruction when merge is required
"""

from __future__ import annotations

import logging
from pathlib import Path
import re
from typing import Any

try:
    from homeassistant.components import persistent_notification
    from homeassistant.core import HomeAssistant
except ImportError:  # pragma: no cover - test fallback when HA runtime is not installed
    HomeAssistant = Any  # type: ignore[misc,assignment]

    class _PersistentNotificationStub:
        @staticmethod
        def async_create(*_args: Any, **_kwargs: Any) -> None:
            return None

    persistent_notification = _PersistentNotificationStub()  # type: ignore[assignment]


_LOGGER = logging.getLogger(__name__)

SNIPPET_REL_PATH = "ai_home_copilot/lovelace_pilotsuite_dashboards.yaml"
_DASHBOARD_FILE_MARKERS = (
    "ai_home_copilot/pilotsuite_dashboard_latest.yaml",
    "ai_home_copilot/habitus_zones_dashboard_latest.yaml",
)
_AUTOMATED_BLOCK_MARKER = "# PilotSuite dashboard wiring (managed by ai_home_copilot)"
_NOTIFICATION_ID = "ai_home_copilot_dashboard_wiring"


def _snippet_content() -> str:
    return (
        "copilot-pilotsuite:\n"
        "  mode: yaml\n"
        "  title: \"PilotSuite - Styx\"\n"
        "  icon: mdi:robot-outline\n"
        "  show_in_sidebar: true\n"
        "  filename: \"ai_home_copilot/pilotsuite_dashboard_latest.yaml\"\n"
        "\n"
        "copilot-habitus-zones:\n"
        "  mode: yaml\n"
        "  title: \"PilotSuite - Habitus Zones\"\n"
        "  icon: mdi:layers-outline\n"
        "  show_in_sidebar: true\n"
        "  filename: \"ai_home_copilot/habitus_zones_dashboard_latest.yaml\"\n"
    )


def _include_block() -> str:
    return (
        f"{_AUTOMATED_BLOCK_MARKER}\n"
        "lovelace:\n"
        f"  dashboards: !include {SNIPPET_REL_PATH}\n"
    )


def _manual_help_message(config_path: Path) -> str:
    return (
        "PilotSuite hat die Dashboard-Dateien automatisch erzeugt, "
        "aber deine `configuration.yaml` enthaelt bereits einen `lovelace:`-Block.\n\n"
        "Bitte ergaenze dort **unter `lovelace:`**:\n"
        f"```\n"
        f"dashboards: !include {SNIPPET_REL_PATH}\n"
        f"```\n\n"
        f"Die Include-Datei wurde erstellt:\n`{config_path.parent / SNIPPET_REL_PATH}`\n\n"
        "Alternativ kannst du die Dashboard-Definitionen direkt einfuegen:\n"
        "```yaml\n"
        "dashboards:\n"
        f"{_snippet_content()}"
        "```\n\n"
        "Danach Home Assistant neu starten."
    )


def _has_lovelace_root(config_text: str) -> bool:
    return bool(re.search(r"(?m)^\s*lovelace\s*:", config_text))


def _is_dashboard_wired(config_text: str) -> bool:
    lowered = config_text.lower()
    if SNIPPET_REL_PATH.lower() in lowered:
        return True
    return all(marker.lower() in lowered for marker in _DASHBOARD_FILE_MARKERS)


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _append_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    with path.open("a", encoding="utf-8") as handle:
        if current and not current.endswith("\n"):
            handle.write("\n")
        if current and not current.endswith("\n\n"):
            handle.write("\n")
        handle.write(content)


async def async_ensure_lovelace_dashboard_wiring(hass: HomeAssistant) -> str:
    """Ensure Lovelace can load PilotSuite YAML dashboards.

    Returns:
        One of: "wired", "auto_appended", "manual_required", "error"
    """

    config_path = Path(hass.config.path("configuration.yaml"))
    snippet_path = Path(hass.config.path(SNIPPET_REL_PATH))
    include_block = _include_block()

    try:
        await hass.async_add_executor_job(_write_text, snippet_path, _snippet_content())

        config_text = await hass.async_add_executor_job(_read_text, config_path)
        if _is_dashboard_wired(config_text):
            return "wired"

        if not _has_lovelace_root(config_text):
            if _AUTOMATED_BLOCK_MARKER not in config_text:
                await hass.async_add_executor_job(_append_text, config_path, include_block)
                persistent_notification.async_create(
                    hass,
                    (
                        "PilotSuite hat Lovelace-Dashboard-Wiring automatisch ergaenzt.\n\n"
                        f"Datei: `{config_path}`\n\n"
                        "Bitte Home Assistant neu starten, damit die Sidebar-Dashboards erscheinen."
                    ),
                    title="PilotSuite Dashboard Wiring",
                    notification_id=_NOTIFICATION_ID,
                )
            return "auto_appended"

        persistent_notification.async_create(
            hass,
            _manual_help_message(config_path),
            title="PilotSuite Dashboard Wiring",
            notification_id=_NOTIFICATION_ID,
        )
        return "manual_required"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Failed to ensure PilotSuite Lovelace dashboard wiring")
        return "error"
