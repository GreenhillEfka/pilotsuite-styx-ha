"""Quick Search Integration for AI Home CoPilot.

Provides HA entity search capabilities:
- Search entities, automations, scripts, scenes, services
- Filter by domain, state, area
- Index management via HA event forwarding

Services:
- ai_home_copilot.search - Perform search
- ai_home_copilot.index_search - Update search index
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv

from .api import CopilotApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SEARCH_SERVICE_SCHEMA = cv.make_entity_service_schema(
    {
        cv.Optional("query"): cv.string,
        cv.Optional("types"): cv.ensure_list,
        cv.Optional("limit"): cv.positive_int,
    }
)

INDEX_SERVICE_SCHEMA = cv.make_entity_service_schema({})


class QuickSearchIntegration:
    """Quick search integration for HA."""
    
    def __init__(self, hass: HomeAssistant, api_client: CopilotApiClient):
        self._hass = hass
        self._api = api_client
        self._entity_registry = er.async_get(hass)
    
    async def async_search(
        self,
        query: str,
        types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Perform search via Core API."""
        try:
            params = {"q": query, "limit": limit}
            if types:
                params["types"] = ",".join(types)
            
            response = await self._api.async_get(f"/api/v1/search?{params}")
            return response.get("data", {})
        except Exception as e:
            _LOGGER.error("Search error: %s", e)
            return {"results": [], "error": str(e)}
    
    async def async_filter_entities(
        self,
        domain: Optional[str] = None,
        state: Optional[str] = None,
        area: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Filter entities by criteria."""
        try:
            params = {"limit": limit}
            if domain:
                params["domain"] = domain
            if state:
                params["state"] = state
            if area:
                params["area"] = area
            
            response = await self._api.async_get(f"/api/v1/search/entities?{params}")
            return response.get("data", {}).get("results", [])
        except Exception as e:
            _LOGGER.error("Entity filter error: %s", e)
            return []
    
    async def async_update_index(self) -> Dict[str, Any]:
        """Update search index with current HA data."""
        try:
            # Get all states
            states = {}
            for state in self._hass.states.async_all():
                states[state.entity_id] = {
                    "state": state.state,
                    "attributes": dict(state.attributes),
                }
            
            # Get automations
            automations = {}
            for entity in self._hass.entity_registry.entities.values():
                if entity.domain == "automation":
                    config = self._hass.states.get(entity.entity_id)
                    if config:
                        automations[entity.entity_id] = {
                            "alias": config.name,
                            "enabled": config.state == "on",
                            "last_triggered": config.last_changed.isoformat(),
                        }
            
            # Get scripts
            scripts = {}
            for entity in self._hass.entity_registry.entities.values():
                if entity.domain == "script":
                    config = self._hass.states.get(entity.entity_id)
                    if config:
                        scripts[entity.entity_id] = {
                            "alias": config.name,
                        }
            
            # Get scenes
            scenes = {}
            for entity in self._hass.entity_registry.entities.values():
                if entity.domain == "scene":
                    config = self._hass.states.get(entity.entity_id)
                    if config:
                        scenes[entity.entity_id] = {
                            "alias": config.name,
                        }
            
            # Update index
            payload = {
                "entities": states,
                "automations": automations,
                "scripts": scripts,
                "scenes": scenes,
            }
            
            response = await self._api.async_post("/api/v1/search/index", payload)
            return response.get("data", {})
        except Exception as e:
            _LOGGER.error("Index update error: %s", e)
            return {"error": str(e)}
    
    async def async_get_stats(self) -> Dict[str, Any]:
        """Get search index statistics."""
        try:
            response = await self._api.async_get("/api/v1/search/stats")
            return response.get("data", {})
        except Exception as e:
            _LOGGER.error("Stats error: %s", e)
            return {}


async def async_register_services(hass: HomeAssistant) -> None:
    """Register search services."""
    
    async def search_service(call: ServiceCall) -> Dict[str, Any]:
        """Handle search service call."""
        api = hass.data.get(DOMAIN, {}).get("api_client")
        if not api:
            return {"error": "API not available"}
        
        integration = QuickSearchIntegration(hass, api)
        
        query = call.data.get("query", "")
        types = call.data.get("types")
        limit = call.data.get("limit", 20)
        
        return await integration.async_search(query, types, limit)
    
    async def index_service(call: ServiceCall) -> Dict[str, Any]:
        """Handle index update service call."""
        api = hass.data.get(DOMAIN, {}).get("api_client")
        if not api:
            return {"error": "API not available"}
        
        integration = QuickSearchIntegration(hass, api)
        return await integration.async_update_index()
    
    async def filter_service(call: ServiceCall) -> List[Dict[str, Any]]:
        """Handle entity filter service call."""
        api = hass.data.get(DOMAIN, {}).get("api_client")
        if not api:
            return []
        
        integration = QuickSearchIntegration(hass, api)
        
        domain = call.data.get("domain")
        state = call.data.get("state")
        area = call.data.get("area")
        limit = call.data.get("limit", 50)
        
        return await integration.async_filter_entities(domain, state, area, limit)
    
    # Register services
    hass.services.async_register(
        DOMAIN,
        "search",
        search_service,
        SEARCH_SERVICE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "index_search",
        index_service,
        INDEX_SERVICE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "filter_entities",
        filter_service,
        SEARCH_SERVICE_SCHEMA,
    )
    
    _LOGGER.info("Quick search services registered")


__all__ = ["async_register_services", "QuickSearchIntegration"]
