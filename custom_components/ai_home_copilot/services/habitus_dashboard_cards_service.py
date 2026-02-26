"""Service for fetching habitus_dashboard_cards patterns from core API."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_GET_DASHBOARD_PATTERNS = "get_dashboard_patterns"
DASHBOARD_CARDS_ENDPOINT = "/api/v1/habitus/dashboard_cards"

GET_DASHBOARD_PATTERNS_SCHEMA = vol.Schema(
    {
        vol.Optional("pattern_type", default="all"): cv.string,
        vol.Optional("format", default="json"): cv.string,
    }
)


async def async_setup_habitus_dashboard_cards_services(hass: HomeAssistant) -> None:
    """Set up habitus_dashboard_cards services."""

    async def handle_get_dashboard_patterns(call: ServiceCall) -> dict[str, Any]:
        """Handle the get_dashboard_patterns service call."""
        pattern_type = call.data.get("pattern_type", "all")
        output_format = call.data.get("format", "json")

        # Get API client from integration data
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.error("No AI Home Copilot config entry found")
            return {"error": "No config entry"}

        entry = entries[0]
        data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
        api = data.get("api") if isinstance(data, dict) else None

        if not api:
            _LOGGER.error("API client not available")
            return {"error": "API not available"}

        try:
            # Call core API endpoint
            url = f"{DASHBOARD_CARDS_ENDPOINT}?type={pattern_type}&format={output_format}"
            result = await api.async_get(url)
            
            if not result:
                return {"error": "No response from core API"}

            return result

        except Exception as ex:
            _LOGGER.error("Failed to get dashboard patterns: %s", ex)
            return {"error": str(ex)}

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DASHBOARD_PATTERNS,
        handle_get_dashboard_patterns,
        schema=GET_DASHBOARD_PATTERNS_SCHEMA,
    )

    _LOGGER.info("Habitus Dashboard Cards services registered")
