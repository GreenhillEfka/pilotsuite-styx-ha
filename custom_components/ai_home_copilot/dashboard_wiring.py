"""Lovelace dashboard wiring helper for PilotSuite.

This module keeps dashboard YAML files and Lovelace wiring aligned:
- writes a stable include snippet file under `pilotsuite-styx/`
- auto-appends a minimal Lovelace block only when `configuration.yaml` has no `lovelace:` section
- falls back to a clear manual instruction when merge is required
"""

from __future__ import annotations

import logging
from pathlib import Path
import re
from typing import Any

from .const import LEGACY_DASHBOARD_DIR, PRIMARY_DASHBOARD_DIR

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

SNIPPET_REL_PATH = f"{PRIMARY_DASHBOARD_DIR}/lovelace_pilotsuite_dashboards.yaml"
_LEGACY_SNIPPET_REL_PATH = f"{LEGACY_DASHBOARD_DIR}/lovelace_pilotsuite_dashboards.yaml"
_DASHBOARD_FILE_MARKERS = (
    f"{PRIMARY_DASHBOARD_DIR}/pilotsuite_dashboard_latest.yaml",
    f"{PRIMARY_DASHBOARD_DIR}/habitus_zones_dashboard_latest.yaml",
)
_LEGACY_DASHBOARD_FILE_MARKERS = (
    f"{LEGACY_DASHBOARD_DIR}/pilotsuite_dashboard_latest.yaml",
    f"{LEGACY_DASHBOARD_DIR}/habitus_zones_dashboard_latest.yaml",
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
        f"  filename: \"{PRIMARY_DASHBOARD_DIR}/pilotsuite_dashboard_latest.yaml\"\n"
        "\n"
        "copilot-habitus-zones:\n"
        "  mode: yaml\n"
        "  title: \"PilotSuite - Habitus Zones\"\n"
        "  icon: mdi:layers-outline\n"
        "  show_in_sidebar: true\n"
        f"  filename: \"{PRIMARY_DASHBOARD_DIR}/habitus_zones_dashboard_latest.yaml\"\n"
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
    if SNIPPET_REL_PATH.lower() in lowered or _LEGACY_SNIPPET_REL_PATH.lower() in lowered:
        return True
    if all(marker.lower() in lowered for marker in _DASHBOARD_FILE_MARKERS):
        return True
    return all(marker.lower() in lowered for marker in _LEGACY_DASHBOARD_FILE_MARKERS)


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


def _merge_dashboards_into_existing_lovelace(config_text: str) -> tuple[str, bool]:
    """Try to inject missing PilotSuite dashboards into an existing lovelace:dashboards map.

    Returns (new_text, changed). If no safe merge is possible, changed=False.
    """
    lines = config_text.splitlines()
    if not lines:
        return config_text, False

    lovelace_idx: int | None = None
    lovelace_indent = 0
    for idx, line in enumerate(lines):
        m = re.match(r"^(\s*)lovelace\s*:\s*(?:#.*)?$", line)
        if m:
            lovelace_idx = idx
            lovelace_indent = len(m.group(1))
            break
    if lovelace_idx is None:
        return config_text, False

    dashboards_idx: int | None = None
    dashboards_indent = lovelace_indent + 2
    for idx in range(lovelace_idx + 1, len(lines)):
        line = lines[idx]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= lovelace_indent:
            break
        m = re.match(r"^\s*dashboards\s*:\s*(.*)$", stripped)
        if indent == lovelace_indent + 2 and m:
            dashboards_idx = idx
            dashboards_indent = indent
            # Keep include-based dashboard maps untouched (manual merge required).
            if "!include" in (m.group(1) or ""):
                return config_text, False
            break
    if dashboards_idx is None:
        return config_text, False

    # Find end of current dashboards block.
    block_end = len(lines)
    for idx in range(dashboards_idx + 1, len(lines)):
        stripped = lines[idx].strip()
        if not stripped:
            continue
        indent = len(lines[idx]) - len(lines[idx].lstrip(" "))
        if indent <= dashboards_indent:
            block_end = idx
            break

    key_indent = " " * (dashboards_indent + 2)
    field_indent = " " * (dashboards_indent + 4)
    existing_keys: set[str] = set()
    key_pattern = re.compile(rf"^\s{{{dashboards_indent + 2}}}([A-Za-z0-9_-]+)\s*:\s*(?:#.*)?$")
    for idx in range(dashboards_idx + 1, block_end):
        m = key_pattern.match(lines[idx])
        if m:
            existing_keys.add(m.group(1))

    inserts: list[str] = []
    if "copilot-pilotsuite" not in existing_keys:
        inserts.extend(
            [
                f"{key_indent}copilot-pilotsuite:",
                f"{field_indent}mode: yaml",
                f'{field_indent}title: "PilotSuite - Styx"',
                f"{field_indent}icon: mdi:robot-outline",
                f"{field_indent}show_in_sidebar: true",
                f'{field_indent}filename: "{PRIMARY_DASHBOARD_DIR}/pilotsuite_dashboard_latest.yaml"',
            ]
        )
    if "copilot-habitus-zones" not in existing_keys:
        if inserts:
            inserts.append("")
        inserts.extend(
            [
                f"{key_indent}copilot-habitus-zones:",
                f"{field_indent}mode: yaml",
                f'{field_indent}title: "PilotSuite - Habitus Zones"',
                f"{field_indent}icon: mdi:layers-outline",
                f"{field_indent}show_in_sidebar: true",
                f'{field_indent}filename: "{PRIMARY_DASHBOARD_DIR}/habitus_zones_dashboard_latest.yaml"',
            ]
        )

    if not inserts:
        return config_text, False

    merged_lines = [*lines[:block_end], *inserts, *lines[block_end:]]
    merged = "\n".join(merged_lines)
    if config_text.endswith("\n"):
        merged += "\n"
    return merged, True


async def async_ensure_lovelace_dashboard_wiring(hass: HomeAssistant) -> str:
    """Ensure Lovelace can load PilotSuite YAML dashboards.

    Returns:
        One of: "wired", "auto_appended", "auto_merged", "manual_required", "error"
    """

    config_path = Path(hass.config.path("configuration.yaml"))
    snippet_path = Path(hass.config.path(SNIPPET_REL_PATH))
    legacy_snippet_path = Path(hass.config.path(_LEGACY_SNIPPET_REL_PATH))
    include_block = _include_block()

    try:
        await hass.async_add_executor_job(_write_text, snippet_path, _snippet_content())
        await hass.async_add_executor_job(_write_text, legacy_snippet_path, _snippet_content())

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

        merged_text, changed = _merge_dashboards_into_existing_lovelace(config_text)
        if changed:
            await hass.async_add_executor_job(_write_text, config_path, merged_text)
            persistent_notification.async_create(
                hass,
                (
                    "PilotSuite hat fehlende Dashboard-Eintraege in deinem bestehenden "
                    "`lovelace: dashboards:`-Block automatisch ergänzt.\n\n"
                    f"Datei: `{config_path}`\n\n"
                    "Bitte Home Assistant neu starten, damit die Sidebar-Dashboards erscheinen."
                ),
                title="PilotSuite Dashboard Wiring",
                notification_id=_NOTIFICATION_ID,
            )
            return "auto_merged"

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
