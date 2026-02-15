"""Quick Search Module - Entity, Automation, and Service Search for AI Home CoPilot.

Features:
- Entity Search: Search all HA entities by name, state, domain
- Automation Search: Search automations by name, trigger, action
- Service Search: Search available services by domain, service name
- Quick actions: Direct access to commonly used entities/services
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.entity import get_entity_id

from ..core.module import CopilotModule, ModuleContext
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result."""
    type: str  # entity, automation, service
    id: str
    title: str
    description: str = ""
    icon: str = "mdi:magnify"
    actions: list[dict[str, str]] = field(default_factory=list)
    score: float = 0.0


@dataclass
class SearchResults:
    """Container for search results."""
    query: str
    results: list[SearchResult] = field(default_factory=list)
    total: int = 0
    execution_time_ms: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "results": [
                {
                    "type": r.type,
                    "id": r.id,
                    "title": r.title,
                    "description": r.description,
                    "icon": r.icon,
                    "actions": r.actions,
                    "score": r.score,
                }
                for r in self.results
            ],
            "total": self.total,
            "execution_time_ms": self.execution_time_ms,
        }


class QuickSearchModule(CopilotModule):
    """Quick Search Module for HA Entities, Automations, and Services."""
    
    @property
    def name(self) -> str:
        return "quick_search"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the quick search module."""
        _LOGGER.info("Setting up Quick Search Module")
        
        # Store search data in hass.data
        hass_data = ctx.hass.data.setdefault(DOMAIN, {}).setdefault("quick_search", {})
        hass_data["initialized"] = True
        
        # Register services for direct search access
        self._register_services(ctx.hass)
        
        _LOGGER.info("Quick Search Module initialized")
    
    def _register_services(self, hass: HomeAssistant) -> None:
        """Register search services."""
        
        async def search_entities_service(call):
            """Service to search entities."""
            query = call.data.get("query", "")
            domain_filter = call.data.get("domain", None)
            limit = call.data.get("limit", 20)
            
            results = self.search_entities(hass, query, domain_filter, limit)
            return results.to_dict()
        
        async def search_automations_service(call):
            """Service to search automations."""
            query = call.data.get("query", "")
            limit = call.data.get("limit", 20)
            
            results = self.search_automations(hass, query, limit)
            return results.to_dict()
        
        async def search_services_service(call):
            """Service to search services."""
            query = call.data.get("query", "")
            domain_filter = call.data.get("domain", None)
            
            results = self.search_services(hass, query, domain_filter)
            return results.to_dict()
        
        async def quick_action_service(call):
            """Execute a quick action on an entity."""
            entity_id = call.data.get("entity_id")
            action = call.data.get("action", "toggle")
            
            # Handle the action
            if action == "toggle":
                await hass.services.async_call(
                    "homeassistant", "toggle", {"entity_id": entity_id}
                )
            elif action == "turn_on":
                await hass.services.async_call(
                    "homeassistant", "turn_on", {"entity_id": entity_id}
                )
            elif action == "turn_off":
                await hass.services.async_call(
                    "homeassistant", "turn_off", {"entity_id": entity_id}
                )
            
            return {"success": True, "entity_id": entity_id, "action": action}
        
        # Register services
        hass.services.async_register(DOMAIN, "search_entities", search_entities_service)
        hass.services.async_register(DOMAIN, "search_automations", search_automations_service)
        hass.services.async_register(DOMAIN, "search_services", search_services_service)
        hass.services.async_register(DOMAIN, "quick_action", quick_action_service)
    
    def search_entities(
        self,
        hass: HomeAssistant,
        query: str,
        domain_filter: Optional[str] = None,
        limit: int = 20,
    ) -> SearchResults:
        """Search entities by name, state, or domain."""
        import time
        start_time = time.time()
        
        query_lower = query.lower().strip()
        results = []
        
        # Get all states
        all_states = hass.states.async_all()
        
        # Filter by domain if specified
        if domain_filter:
            all_states = [s for s in all_states if s.domain == domain_filter]
        
        for state in all_states:
            entity_id = state.entity_id
            name = state.name or entity_id
            state_value = state.state
            
            # Calculate relevance score
            score = 0.0
            
            # Exact match on entity_id
            if query_lower == entity_id.lower():
                score = 100.0
            # Exact match on name
            elif query_lower == name.lower():
                score = 90.0
            # Starts with query
            elif entity_id.lower().startswith(query_lower):
                score = 70.0
            elif name.lower().startswith(query_lower):
                score = 60.0
            # Contains query
            elif query_lower in entity_id.lower():
                score = 40.0
            elif query_lower in name.lower():
                score = 30.0
            # Match on state
            elif query_lower in state_value.lower():
                score = 20.0
            
            if score > 0:
                # Get icon from attributes or use default
                icon = state.attributes.get("icon", self._get_domain_icon(state.domain))
                
                results.append(SearchResult(
                    type="entity",
                    id=entity_id,
                    title=name,
                    description=f"{state.domain}: {state_value}",
                    icon=icon,
                    score=score,
                    actions=[
                        {"action": "toggle", "label": "Toggle"},
                        {"action": "turn_on", "label": "On"},
                        {"action": "turn_off", "label": "Off"},
                    ],
                ))
        
        # Sort by score and limit
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:limit]
        
        execution_time = (time.time() - start_time) * 1000
        
        return SearchResults(
            query=query,
            results=results,
            total=len(results),
            execution_time_ms=execution_time,
        )
    
    def search_automations(
        self,
        hass: HomeAssistant,
        query: str,
        limit: int = 20,
    ) -> SearchResults:
        """Search automations by name, trigger, or action."""
        import time
        start_time = time.time()
        
        query_lower = query.lower().strip()
        results = []
        
        # Get all automation states
        automation_states = hass.states.async_all("automation")
        
        for automation in automation_states:
            entity_id = automation.entity_id
            name = automation.name or automation.attributes.get("friendly_name", entity_id)
            state = automation.state
            
            # Get triggers and actions from attributes
            triggers = automation.attributes.get("triggers", [])
            actions = automation.attributes.get("actions", [])
            mode = automation.attributes.get("mode", "single")
            
            # Calculate relevance score
            score = 0.0
            
            # Match on name
            if query_lower == name.lower():
                score = 100.0
            elif name.lower().startswith(query_lower):
                score = 70.0
            elif query_lower in name.lower():
                score = 50.0
            
            # Match on triggers
            if triggers:
                triggers_str = str(triggers).lower()
                if query_lower in triggers_str:
                    score = max(score, 40.0)
            
            # Match on actions
            if actions:
                actions_str = str(actions).lower()
                if query_lower in actions_str:
                    score = max(score, 30.0)
            
            # Boost for enabled automations
            if state == "on":
                score *= 1.1
            
            if score > 0:
                # Format description
                trigger_count = len(triggers) if triggers else 0
                action_count = len(actions) if actions else 0
                description = f"Triggers: {trigger_count}, Actions: {action_count}, Mode: {mode}"
                
                results.append(SearchResult(
                    type="automation",
                    id=entity_id,
                    title=name,
                    description=description,
                    icon="mdi:robot",
                    score=score,
                    actions=[
                        {"action": "trigger", "label": "Trigger"},
                        {"action": "disable", "label": "Disable"} if state == "on" else {"action": "enable", "label": "Enable"},
                    ],
                ))
        
        # Sort by score and limit
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:limit]
        
        execution_time = (time.time() - start_time) * 1000
        
        return SearchResults(
            query=query,
            results=results,
            total=len(results),
            execution_time_ms=execution_time,
        )
    
    def search_services(
        self,
        hass: HomeAssistant,
        query: str,
        domain_filter: Optional[str] = None,
    ) -> SearchResults:
        """Search available services."""
        import time
        start_time = time.time()
        
        query_lower = query.lower().strip()
        results = []
        
        # Get all services
        services = hass.services.async_services()
        
        for domain, domain_services in services.items():
            # Filter by domain if specified
            if domain_filter and domain != domain_filter:
                continue
            
            for service_name, service in domain_services.items():
                service_id = f"{domain}.{service_name}"
                
                # Calculate relevance score
                score = 0.0
                
                # Match on service name
                if query_lower == service_name:
                    score = 100.0
                elif service_name.startswith(query_lower):
                    score = 70.0
                elif query_lower in service_name:
                    score = 50.0
                # Match on domain
                elif query_lower in domain:
                    score = 30.0
                
                if score > 0:
                    # Get description from service
                    description = service.get("description", "")
                    
                    results.append(SearchResult(
                        type="service",
                        id=service_id,
                        title=service_name,
                        description=description or f"Domain: {domain}",
                        icon=self._get_service_icon(domain),
                        score=score,
                        actions=[
                            {"action": "call", "label": "Call"},
                        ],
                    ))
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        
        execution_time = (time.time() - start_time) * 1000
        
        return SearchResults(
            query=query,
            results=results,
            total=len(results),
            execution_time_ms=execution_time,
        )
    
    def _get_domain_icon(self, domain: str) -> str:
        """Get icon for entity domain."""
        icon_map = {
            "light": "mdi:lightbulb",
            "switch": "mdi:toggle-switch",
            "sensor": "mdi:sensor",
            "binary_sensor": "mdi:motion-sensor",
            "climate": "mdi:thermostat",
            "media_player": "mdi:play-circle",
            "camera": "mdi:camera",
            "cover": "mdi:blinds",
            "fan": "mdi:fan",
            "lock": "mdi:lock",
            "alarm_control_panel": "mdi:alarm",
            "scene": "mdi:palette",
            "script": "mdi:script-text",
            "automation": "mdi:robot",
            "input_boolean": "mdi:toggle-switch",
            "input_number": "mdi:numeric",
            "input_text": "mdi:textbox",
            "timer": "mdi:timer",
            "zone": "mdi:map-marker",
            "person": "mdi:account",
            "device_tracker": "mdi:crosshairs-gps",
            "group": "mdi:group",
        }
        return icon_map.get(domain, "mdi:entity")
    
    def _get_service_icon(self, domain: str) -> str:
        """Get icon for service domain."""
        icon_map = {
            "homeassistant": "mdi:home-automation",
            "light": "mdi:lightbulb",
            "switch": "mdi:toggle-switch",
            "script": "mdi:script-text",
            "automation": "mdi:robot",
            "climate": "mdi:thermostat",
            "media_player": "mdi:play-circle",
            "notify": "mdi:bell",
            "input_boolean": "mdi:toggle-switch",
            "scene": "mdi:palette",
        }
        return icon_map.get(domain, "mdi:service")
    
    def generate_automation_suggestions(
        self,
        hass: HomeAssistant,
        query: str,
        search_results: SearchResults,
    ) -> dict[str, Any]:
        """Generate automation suggestions from search results.
        
        Maps:
        - Search results → automation suggestions
        - Entity search → candidate generation
        """
        suggestions = []
        candidates = []
        
        for result in search_results.results:
            result_type = result.type
            result_id = result.id
            result_title = result.title
            score = result.score
            
            if result_type == "entity":
                # Generate automation candidates based on entity
                entity_domain = result_id.split(".")[0] if "." in result_id else ""
                
                # Suggest relevant automations
                candidate = {
                    "type": "entity_candidate",
                    "entity_id": result_id,
                    "entity_name": result_title,
                    "domain": entity_domain,
                    "score": score,
                    "suggested_automations": self._get_domain_automation_suggestions(entity_domain, result_title),
                }
                candidates.append(candidate)
                
                # Also add as general suggestion
                suggestions.append({
                    "type": "automation_suggestion",
                    "title": f"Automation für {result_title}",
                    "description": f"Entität {result_id} in Automation nutzen",
                    "entity_id": result_id,
                    "score": score * 0.8,
                })
            
            elif result_type == "service":
                # Generate service-based suggestions
                service_domain = result_id.split(".")[0] if "." in result_id else ""
                
                candidate = {
                    "type": "service_candidate",
                    "service_id": result_id,
                    "service_name": result_title,
                    "domain": service_domain,
                    "score": score,
                    "suggested_automations": [
                        f"Automation mit Service {result_id} erstellen",
                    ],
                }
                candidates.append(candidate)
            
            elif result_type == "automation":
                # Suggest improvements to existing automation
                suggestions.append({
                    "type": "automation_improvement",
                    "title": f"Automation verbessern: {result_title}",
                    "description": result.description,
                    "automation_id": result_id,
                    "score": score * 0.9,
                })
        
        # Sort by score
        suggestions.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        return {
            "query": query,
            "suggestions": suggestions[:10],
            "candidates": candidates[:10],
            "total_suggestions": len(suggestions),
            "total_candidates": len(candidates),
        }
    
    def _get_domain_automation_suggestions(self, domain: str, entity_name: str) -> list[str]:
        """Get automation suggestions based on entity domain."""
        suggestions_map = {
            "light": [
                f"Licht {entity_name} bei Sonnenuntergang einschalten",
                f"Bewegungsgesteuerte Beleuchtung für {entity_name}",
                f"{entity_name} automatisch dimmen",
            ],
            "switch": [
                f"Schalter {entity_name} zeitgesteuert schalten",
                f"{entity_name} bei Abwesenheit ausschalten",
            ],
            "sensor": [
                f"Automation basierend auf {entity_name} Wert erstellen",
                f"Benachrichtigung bei Schwellenwert von {entity_name}",
            ],
            "binary_sensor": [
                f"Automation bei Änderung von {entity_name}",
                f"{entity_name} für Sicherheits-Automation nutzen",
            ],
            "climate": [
                f"Temperatur-Automation für {entity_name}",
                f"Smart Climate Steuerung für {entity_name}",
            ],
            "media_player": [
                f"Medien-Automation für {entity_name}",
                f"{entity_name} automatisch steuern",
            ],
            "camera": [
                f"Kamera-Automation für {entity_name}",
                f"Bewegungserkennung mit {entity_name}",
            ],
            "cover": [
                f"Rollladen-Automation für {entity_name}",
                f"Sonnenstandsabhängige Steuerung für {entity_name}",
            ],
            "lock": [
                f"Schloss-Automation für {entity_name}",
                f"Zugangskontrolle mit {entity_name}",
            ],
        }
        
        return suggestions_map.get(domain, [f"Automation für {entity_name} erstellen"])
    
    async def async_generate_suggestions(
        self,
        hass: HomeAssistant,
        query: str,
    ) -> dict[str, Any]:
        """Generate automation suggestions from a search query.
        
        Combines entity, automation, and service search to generate
        comprehensive automation suggestions.
        """
        # Perform multiple searches in parallel
        entity_results = self.search_entities(hass, query, limit=10)
        automation_results = self.search_automations(hass, query, limit=10)
        service_results = self.search_services(hass, query, limit=10)
        
        # Combine results
        combined_results = SearchResults(
            query=query,
            results=entity_results.results + automation_results.results + service_results.results,
            total=entity_results.total + automation_results.total + service_results.total,
            execution_time_ms=entity_results.execution_time_ms + automation_results.execution_time_ms + service_results.execution_time_ms,
        )
        
        # Sort combined results by score
        combined_results.results.sort(key=lambda x: x.score, reverse=True)
        
        # Generate suggestions
        return self.generate_automation_suggestions(hass, query, combined_results)
    
    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the module."""
        # Remove services
        ctx.hass.services.async_remove(DOMAIN, "search_entities")
        ctx.hass.services.async_remove(DOMAIN, "search_automations")
        ctx.hass.services.async_remove(DOMAIN, "search_services")
        ctx.hass.services.async_remove(DOMAIN, "quick_action")
        
        _LOGGER.info("Quick Search Module unloaded")
        return True
