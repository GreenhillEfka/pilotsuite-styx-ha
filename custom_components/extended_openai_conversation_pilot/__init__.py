"""
PilotSuite Conversation - Extended OpenAI Conversation compatible component

This component provides OpenAI-compatible conversation endpoint
for use with Extended OpenAI Conversation custom component.

It connects to PilotSuite Core Add-on for AI processing.
"""

import logging
import os
import async_timeout
import aiohttp
import json

from homeassistant.components import http
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_API_KEY,
    DEFAULT_BASE_URL,
    DEFAULT_API_KEY,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = []


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the PilotSuite Conversation component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pilot config entry."""
    
    base_url = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
    api_key = entry.data.get(CONF_API_KEY, DEFAULT_API_KEY)
    
    hass.data[DOMAIN][entry.entry_id] = {
        "base_url": base_url,
        "api_key": api_key,
    }
    
    # Register HTTP endpoint for OpenAI-compatible API
    # This acts as a proxy to PilotSuite Core
    hass.http.register_view(PilotSuiteConversationView(hass, entry))
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove HTTP view
    hass.http.views.pop(f"{DOMAIN}_{entry.entry_id}", None)
    
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id)
    
    return True


class PilotSuiteConversationView(http.HomeAssistantView):
    """OpenAI-compatible conversation view."""
    
    url = "/api/pilot_conversation"
    name = "api:pilot_conversation"
    
    def __init__(self, hass: HomeAssistantType, entry: ConfigEntry) -> None:
        self.hass = hass
        self.base_url = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
        self.api_key = entry.data.get(CONF_API_KEY, DEFAULT_API_KEY)
    
    async def post(self, request):
        """Handle POST request for chat completions."""
        hass = request.app["hass"]
        
        try:
            body = await request.json()
        except Exception:
            return self.json_message("Invalid JSON", status_code=400)
        
        # Forward to PilotSuite Core
        core_url = f"{self.base_url}/api/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(30):
                    async with session.post(core_url, json=body, headers=headers) as resp:
                        response_data = await resp.json()
                        return self.json(response_data, status_code=resp.status)
                        
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to PilotSuite Core: %s", err)
            return self.json_message(
                f"Error connecting to PilotSuite Core: {err}",
                status_code=503
            )
        except Exception as err:
            _LOGGER.exception("Unexpected error: %s", err)
            return self.json_message(str(err), status_code=500)
