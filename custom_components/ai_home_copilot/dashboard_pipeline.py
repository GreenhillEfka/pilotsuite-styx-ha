"""Unified Dashboard Pipeline — single entry point for dashboard generation.

Replaces the scattered dashboard generation calls in __init__.py with
one orchestrator that:
  1. Loads zones from HabitusZoneStoreV2 (or zones_config.json fallback)
  2. Generates the 3-tab Lovelace YAML via pilotsuite_3tab_generator
  3. Writes YAML to pilotsuite-styx/ and legacy ai_home_copilot/ paths
  4. Optionally notifies the user via persistent_notification

Path: custom_components/ai_home_copilot/dashboard_pipeline.py
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_OUTPUT_DIR = "pilotsuite-styx"
_LEGACY_OUTPUT_DIR = "ai_home_copilot"
_DASHBOARD_FILENAME = "pilotsuite_dashboard_latest.yaml"
_COMPAT_FILENAME = "habitus_zones_dashboard_latest.yaml"


async def async_generate_unified_dashboard(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    notify: bool = False,
) -> Path | None:
    """Generate the unified 3-tab PilotSuite dashboard.

    1. Load zones from ZoneStore V2 or zones_config.json
    2. Discover person entities dynamically from hass.states
    3. Discover infrastructure entities for Hausverwaltung tab
    4. Generate full dashboard YAML dict
    5. Write to pilotsuite-styx/ and legacy compat path
    6. Optionally send a persistent notification

    Returns the primary output path, or None on failure.
    """
    try:
        zones = _load_zones(hass, entry)
        persons = _discover_persons(hass)
        infra = _discover_infrastructure(hass)

        from .dashboard_cards.pilotsuite_3tab_generator import generate_full_dashboard
        dashboard = generate_full_dashboard(
            zones=zones,
            persons=persons,
            infrastructure=infra,
        )

        primary_path = await _write_dashboard_yaml(hass, dashboard)

        if notify and primary_path:
            try:
                from homeassistant.components.persistent_notification import async_create
                async_create(
                    hass,
                    f"PilotSuite Dashboard generiert: `{primary_path}`",
                    title="PilotSuite Dashboard",
                    notification_id="pilotsuite_dashboard_generated",
                )
            except Exception:
                _LOGGER.debug("Could not send dashboard notification")

        _LOGGER.info("Unified dashboard generated: %s", primary_path)
        return primary_path

    except Exception:
        _LOGGER.exception("Failed to generate unified dashboard")
        return None


def _load_zones(hass: HomeAssistant, entry: ConfigEntry) -> list[dict[str, Any]]:
    """Load zones from ZoneStore V2, falling back to zones_config.json."""
    # Try ZoneStore V2 first
    try:
        entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
        if isinstance(entry_data, dict):
            store = entry_data.get("habitus_zones_store_v2")
            if store and hasattr(store, "async_get_zones_v2"):
                from .habitus_zones_store_v2 import HabitusZoneV2
                zones_v2 = store.async_get_zones_v2()
                if zones_v2:
                    return [_zone_v2_to_dict(z) for z in zones_v2]
    except Exception:
        _LOGGER.debug("Could not load zones from ZoneStore V2, falling back")

    # Fallback: zones_config.json
    import json
    zones_path = Path(__file__).resolve().parent / "data" / "zones_config.json"
    try:
        raw = json.loads(zones_path.read_text(encoding="utf-8"))
        return raw.get("zones", []) if isinstance(raw, dict) else []
    except Exception:
        _LOGGER.debug("Could not load zones_config.json")
        return []


def _zone_v2_to_dict(zone: Any) -> dict[str, Any]:
    """Convert a HabitusZoneV2 dataclass to a plain dict."""
    if hasattr(zone, "__dict__"):
        return {
            "zone_id": getattr(zone, "zone_id", ""),
            "name": getattr(zone, "name", ""),
            "entities": dict(getattr(zone, "entities", {})),
        }
    return dict(zone) if isinstance(zone, dict) else {}


def _discover_persons(hass: HomeAssistant) -> list[dict[str, str]]:
    """Discover person.* entities dynamically from HA states."""
    persons: list[dict[str, str]] = []
    for state in hass.states.async_all("person"):
        name = state.attributes.get("friendly_name", state.entity_id.split(".")[-1])
        persons.append({"entity_id": state.entity_id, "name": name})
    return sorted(persons, key=lambda p: p["name"])


def _discover_infrastructure(hass: HomeAssistant) -> dict[str, list[dict[str, str]]]:
    """Discover infrastructure entities for Hausverwaltung tab.

    Groups entities by category: energy, heating, security, devices,
    network, weather. Uses domain + device_class + entity_id heuristics.
    """
    infra: dict[str, list[dict[str, str]]] = {
        "energy": [],
        "heating": [],
        "security": [],
        "devices": [],
        "network": [],
        "weather": [],
    }

    for state in hass.states.async_all():
        eid = state.entity_id
        attrs = state.attributes or {}
        device_class = attrs.get("device_class", "")
        friendly = attrs.get("friendly_name", eid)

        # Energy
        if device_class in ("energy", "power") or "electric_consumption" in eid or "electric_production" in eid:
            infra["energy"].append({"entity_id": eid, "name": friendly})
        # Heating
        elif eid.startswith("climate.") or "heat_generator" in eid or "heizmodus" in eid:
            infra["heating"].append({"entity_id": eid, "name": friendly})
        # Security: smoke, door/window binary sensors, cameras
        elif device_class in ("smoke", "door", "window", "opening") and eid.startswith("binary_sensor."):
            infra["security"].append({"entity_id": eid, "name": friendly})
        elif eid.startswith("camera."):
            infra["security"].append({"entity_id": eid, "name": friendly})
        # Weather
        elif eid.startswith("weather."):
            infra["weather"].append({"entity_id": eid, "name": friendly})
        # Network
        elif "dream_machine" in eid or "unifi" in eid.lower():
            infra["network"].append({"entity_id": eid, "name": friendly})

    return infra


async def _write_dashboard_yaml(
    hass: HomeAssistant,
    dashboard: dict[str, Any],
) -> Path | None:
    """Write dashboard dict as YAML to config directory."""
    import yaml

    config_dir = Path(hass.config.path())

    # Primary output
    primary_dir = config_dir / _OUTPUT_DIR
    primary_dir.mkdir(parents=True, exist_ok=True)
    primary_path = primary_dir / _DASHBOARD_FILENAME

    yaml_content = yaml.dump(dashboard, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def _write() -> None:
        primary_path.write_text(yaml_content, encoding="utf-8")
        # Compat copy
        compat_path = primary_dir / _COMPAT_FILENAME
        compat_path.write_text(yaml_content, encoding="utf-8")
        # Legacy directory mirror
        legacy_dir = config_dir / _LEGACY_OUTPUT_DIR
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / _DASHBOARD_FILENAME).write_text(yaml_content, encoding="utf-8")
        (legacy_dir / _COMPAT_FILENAME).write_text(yaml_content, encoding="utf-8")

    await hass.async_add_executor_job(_write)
    return primary_path
