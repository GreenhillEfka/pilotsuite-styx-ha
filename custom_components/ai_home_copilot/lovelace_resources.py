"""Lovelace card resource auto-registration for PilotSuite.

Registers the PilotSuite custom cards JavaScript from the Core Add-on
as a Lovelace resource so they appear in the card picker.

The JS file is served by the Core Add-on at:
  http://{host}:{port}/api/v1/cards/pilotsuite-cards.js
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .connection_config import resolve_core_connection
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_JS_PATH = "/api/v1/cards/pilotsuite-cards.js"


async def async_register_card_resources(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Register PilotSuite Lovelace card resources."""
    host, port, _token = resolve_core_connection(entry)

    if not host:
        _LOGGER.debug("No host configured, skipping Lovelace resource registration")
        return

    card_url = f"http://{host}:{port}{CARD_JS_PATH}"

    try:
        # Use the Lovelace resources API if available
        lovelace = hass.data.get("lovelace")
        if lovelace is None:
            _LOGGER.debug("Lovelace not initialized yet, skipping card registration")
            return

        # Check if resource already registered
        resources = lovelace.get("resources")
        if resources is not None:
            existing = await resources.async_get_items()
            for item in existing:
                if CARD_JS_PATH in (item.get("url") or ""):
                    _LOGGER.debug("PilotSuite card resource already registered")
                    return

            # Register new resource
            await resources.async_create_item({"res_type": "module", "url": card_url})
            _LOGGER.info("PilotSuite Lovelace cards registered: %s", card_url)
        else:
            _LOGGER.info(
                "Lovelace resources API not available. "
                "To use PilotSuite cards, manually add this resource in "
                "Settings > Dashboards > Resources:\n  URL: %s\n  Type: JavaScript Module",
                card_url,
            )
    except Exception as err:
        _LOGGER.warning(
            "Could not auto-register Lovelace cards (%s). "
            "Add manually: URL=%s, Type=JavaScript Module",
            err,
            card_url,
        )
