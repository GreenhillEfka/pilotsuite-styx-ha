"""PilotSuite sidebar panel registration.

Registers a dedicated "PilotSuite" sidebar panel in Home Assistant
that embeds the Core add-on dashboard via ingress iframe.

This provides a unified management experience directly in the HA sidebar
without requiring the user to navigate to the Supervisor add-on page.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.frontend import (
    async_register_built_in_panel,
    async_remove_panel,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .connection_config import resolve_core_connection
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PANEL_URL_NAME = "pilotsuite"
PANEL_TITLE = "PilotSuite"
PANEL_ICON = "mdi:robot-outline"

# The Core add-on slug used by HA Supervisor for ingress
CORE_ADDON_SLUG = "copilot_core"


async def _resolve_ingress_url(hass: HomeAssistant) -> str | None:
    """Resolve the ingress URL for the Core add-on via Supervisor API."""
    try:
        from homeassistant.components.hassio import async_get_addon_info

        addon_info = await async_get_addon_info(hass, CORE_ADDON_SLUG)
        if addon_info and isinstance(addon_info, dict):
            ingress_url = addon_info.get("ingress_url")
            if ingress_url:
                _LOGGER.debug("Resolved Core ingress URL: %s", ingress_url)
                return ingress_url
    except (ImportError, Exception):
        _LOGGER.debug("Could not resolve ingress URL via Supervisor API", exc_info=True)

    # Fallback: try known ingress path pattern
    try:
        hassio_data = hass.data.get("hassio")
        if hassio_data and isinstance(hassio_data, dict):
            ingress_panels = hassio_data.get("ingress_panels", {})
            for slug, panel_info in ingress_panels.items():
                if CORE_ADDON_SLUG in slug:
                    return panel_info.get("url") or f"/api/hassio_ingress/{slug}"
    except Exception:
        _LOGGER.debug("Could not resolve ingress URL from hassio data", exc_info=True)

    return None


def _build_core_dashboard_url(host: str, port: int) -> str:
    """Build a direct URL to the Core dashboard."""
    return f"http://{host}:{port}/"


async def async_setup_panel(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Register the PilotSuite sidebar panel.

    Tries in order:
    1. Supervisor ingress URL (best UX, authenticated via HA)
    2. Direct Core URL (fallback, requires network access)

    Returns True if panel was registered.
    """
    panel_url = None

    # Strategy 1: Supervisor ingress (preferred)
    ingress_url = await _resolve_ingress_url(hass)
    if ingress_url:
        panel_url = ingress_url
        _LOGGER.info("Using Supervisor ingress for PilotSuite panel: %s", panel_url)

    # Strategy 2: Direct Core URL
    if not panel_url:
        host, port, _token = resolve_core_connection(entry)
        if host and port:
            panel_url = _build_core_dashboard_url(host, port)
            _LOGGER.info("Using direct Core URL for PilotSuite panel: %s", panel_url)

    if not panel_url:
        _LOGGER.warning(
            "Could not determine Core dashboard URL. "
            "PilotSuite sidebar panel will not be registered."
        )
        return False

    try:
        async_register_built_in_panel(
            hass,
            component_name="iframe",
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            frontend_url_path=PANEL_URL_NAME,
            config={"url": panel_url},
            require_admin=False,
        )
        _LOGGER.info("PilotSuite sidebar panel registered at /%s", PANEL_URL_NAME)
        return True
    except Exception:
        _LOGGER.exception("Failed to register PilotSuite sidebar panel")
        return False


async def async_remove_panel_entry(hass: HomeAssistant) -> None:
    """Remove the PilotSuite sidebar panel."""
    try:
        async_remove_panel(hass, PANEL_URL_NAME)
        _LOGGER.info("PilotSuite sidebar panel removed")
    except Exception:
        _LOGGER.debug("Could not remove PilotSuite panel (may not exist)", exc_info=True)
