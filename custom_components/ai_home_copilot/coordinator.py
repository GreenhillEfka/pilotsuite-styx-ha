"""HA Integration for AI Home CoPilot - Coordinator with Neural System."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_TOKEN

_LOGGER = logging.getLogger(__name__)


class CopilotApiClient:
    """Client for Copilot Core API with neural system support."""
    
    def __init__(self, session, base_url: str, token: str):
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token = token
    
    async def async_get_status(self) -> Dict[str, Any]:
        """Get basic status."""
        url = f"{self._base_url}/api/v1/status"
        headers = {"Authorization": f"Bearer {self._token}"}
        
        async with self._session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise CopilotApiError(f"API error: {resp.status}")
            return await resp.json()
    
    async def async_get_mood(self) -> Dict[str, Any]:
        """Get current mood from neural system."""
        url = f"{self._base_url}/api/v1/neurons/mood"
        headers = {"Authorization": f"Bearer {self._token}"}
        
        try:
            async with self._session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # API returns {success: true, data: {...}}
                    # Extract the data part
                    return data.get("data", data)
        except Exception as e:
            _LOGGER.debug("Mood API not available: %s", e)
        return {"mood": "unknown", "confidence": 0.0}
    
    async def async_get_neurons(self) -> Dict[str, Any]:
        """Get all neuron states."""
        url = f"{self._base_url}/api/v1/neurons"
        headers = {"Authorization": f"Bearer {self._token}"}
        
        try:
            async with self._session.get(url, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # API returns {success: true, data: {...}}
                    return data.get("data", data)
        except Exception as e:
            _LOGGER.debug("Neurons API not available: %s", e)
        return {"neurons": {}}
    
    async def async_evaluate_neurons(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate neural pipeline with HA states."""
        url = f"{self._base_url}/api/v1/neurons/evaluate"
        headers = {"Authorization": f"Bearer {self._token}"}
        
        try:
            async with self._session.post(url, json=context, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", data)
        except Exception as e:
            _LOGGER.warning("Neural evaluation failed: %s", e)
        return {}


class CopilotApiError(Exception):
    """API error."""
    pass


class CopilotDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator with neural system integration."""
    
    def __init__(self, hass: HomeAssistant, config: dict):
        self._hass = hass
        self._config = config
        session = async_get_clientsession(hass)
        
        host = str(config.get(CONF_HOST, ""))
        port = int(config.get(CONF_PORT, 0) or 0)
        base_url = f"http://{host}:{port}" if port else f"http://{host}"
        
        token = config.get(CONF_TOKEN, "")
        self.api = CopilotApiClient(session, base_url, token)
        
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=30),
        )
    
    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API."""
        try:
            # Get basic status
            status = await self.api.async_get_status()
            
            # Get mood from neural system
            mood_data = await self.api.async_get_mood()
            
            # Get neuron states
            neurons_data = await self.api.async_get_neurons()
            
            # Combine all data
            return {
                "ok": status.get("ok", True),
                "version": status.get("version", "unknown"),
                "mood": mood_data,
                "neurons": neurons_data.get("neurons", {}),
                "dominant_mood": mood_data.get("mood", "unknown"),
                "mood_confidence": mood_data.get("confidence", 0.0),
            }
        except Exception as err:
            _LOGGER.error("Error fetching Copilot data: %s", err)
            raise UpdateFailed(str(err)) from err
    
    @callback
    def async_get_mood(self) -> Dict[str, Any]:
        """Get cached mood data."""
        return self.data.get("mood", {}) if self.data else {}
    
    @callback
    def async_get_neurons(self) -> Dict[str, Any]:
        """Get cached neuron states."""
        return self.data.get("neurons", {}) if self.data else {}
    
    async def async_evaluate_with_states(self) -> Dict[str, Any]:
        """Evaluate neural pipeline with current HA states."""
        # Build context from HA states
        context = {
            "states": {},
            "time": {},
            "weather": {},
            "presence": {},
        }
        
        # Get relevant states
        entity_patterns = [
            "person.", "binary_sensor.", "sensor.temperature", 
            "sensor.humidity", "sensor.light", "sensor.illuminance",
            "weather.", "light.", "media_player."
        ]
        
        for entity_id in self._hass.states.async_entity_ids():
            for pattern in entity_patterns:
                if entity_id.startswith(pattern):
                    state = self._hass.states.get(entity_id)
                    if state:
                        context["states"][entity_id] = {
                            "state": state.state,
                            "attributes": dict(state.attributes)
                        }
                    break
        
        # Evaluate
        return await self.api.async_evaluate_neurons(context)