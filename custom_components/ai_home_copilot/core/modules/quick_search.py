"""Quick Search Module - Entity, Automation, and Service Search for PilotSuite.

Features:
- Entity Search: Search all HA entities by name, state, domain
- Automation Search: Search automations by name, trigger, action
- Service Search: Search available services by domain, service name
- Quick actions: Direct access to commonly used entities/services
- Character System Integration: voice_tone aware suggestions
- Suggestions Integration: Generate automation suggestions from search
"""
from __future__ import annotations

import logging
import time
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from homeassistant.core import HomeAssistant, State

from ..core.module import CopilotModule, ModuleContext
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# Precompiled regex patterns for faster matching
_DOMAIN_PATTERN = re.compile(r'^(\w+)\.')
_EXT_MATCH = re.compile(r'\b(exact|starts|contains|state)\b')


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
    domain: str = ""


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
            "results": [r.__dict__ for r in self.results],
            "total": self.total,
            "execution_time_ms": self.execution_time_ms,
        }
    
    def filter_by_type(self, result_type: str) -> "SearchResults":
        """Filter results by type."""
        filtered = [r for r in self.results if r.type == result_type]
        return SearchResults(
            query=self.query,
            results=filtered,
            total=len(filtered),
            execution_time_ms=self.execution_time_ms,
        )


class QuickSearchModule(CopilotModule):
    """Quick Search Module for HA Entities, Automations, and Services."""
    
    # Domain icon mapping (class-level for reuse)
    DOMAIN_ICONS = {
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
        "vacuum": "mdi:robot-vacuum",
        "humidifier": "mdi:water-percent",
        "water_heater": "mdi:water-boiler",
        "lightbulb": "mdi:lightbulb-group",
    }
    
    # Service domain icons
    SERVICE_ICONS = {
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
        "tts": "mdi:text-to-speech",
    }
    
    # Domain automation suggestions
    DOMAIN_SUGGESTIONS = {
        "light": [
            "Licht bei Sonnenuntergang einschalten",
            "Bewegungsgesteuerte Beleuchtung",
            "Automatisch dimmen",
        ],
        "switch": [
            "Zeitgesteuert schalten",
            "Bei Abwesenheit ausschalten",
        ],
        "sensor": [
            "Automation basierend auf Wert",
            "Benachrichtigung bei Schwellenwert",
        ],
        "binary_sensor": [
            "Bei Änderung aktivieren",
            "Sicherheits-Automation",
        ],
        "climate": [
            "Temperatur-Automation",
            "Smart Climate Steuerung",
        ],
        "media_player": [
            "Medien-Automation",
            "Automatische Steuerung",
        ],
        "camera": [
            "Kamera-Automation",
            "Bewegungserkennung",
        ],
        "cover": [
            "Rollladen-Automation",
            "Sonnenstandsabhängige Steuerung",
        ],
        "lock": [
            "Schloss-Automation",
            "Zugangskontrolle",
        ],
    }
    
    def __init__(self):
        self._character_service = None
        self._cached_states = {}
        self._cache_valid = False
    
    @property
    def name(self) -> str:
        return "quick_search"
    
    @property
    def version(self) -> str:
        return "1.1.0"
    
    def set_character_service(self, service) -> None:
        """Set character service for voice_tone integration."""
        self._character_service = service
    
    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the quick search module."""
        _LOGGER.info("Setting up Quick Search Module v%s", self.version)
        
        # Get character service if available
        try:
            if hasattr(ctx, 'coordinator') and ctx.coordinator:
                self._character_service = getattr(ctx.coordinator, 'character_service', None)
        except Exception as e:
            _LOGGER.debug("Character service not available: %s", e)
        
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
            
            result = await self._execute_action(hass, entity_id, action)
            return result
        
        async def combined_search_service(call):
            """Combined search across all types."""
            query = call.data.get("query", "")
            limit = call.data.get("limit", 20)
            
            results = await self.async_combined_search(hass, query, limit)
            return results.to_dict()
        
        # Register services
        hass.services.async_register(DOMAIN, "search_entities", search_entities_service)
        hass.services.async_register(DOMAIN, "search_automations", search_automations_service)
        hass.services.async_register(DOMAIN, "search_services", search_services_service)
        hass.services.async_register(DOMAIN, "quick_action", quick_action_service)
        hass.services.async_register(DOMAIN, "combined_search", combined_search_service)
    
    async def _execute_action(self, hass: HomeAssistant, entity_id: str, action: str) -> dict:
        """Execute an action on an entity."""
        action_map = {
            "toggle": "homeassistant.toggle",
            "turn_on": "homeassistant.turn_on",
            "turn_off": "homeassistant.turn_off",
            "trigger": "automation.trigger",
            "enable": "automation.turn_on",
            "disable": "automation.turn_off",
            "call": "homeassistant.turn_on",  # For services
        }
        
        service = action_map.get(action, "homeassistant.toggle")
        domain = service.split(".")[0]
        
        try:
            await hass.services.async_call(domain, service.split(".")[-1] if "." in service else service, 
                                           {"entity_id": entity_id})
            return {"success": True, "entity_id": entity_id, "action": action}
        except Exception as e:
            _LOGGER.error("Action error: %s", e)
            return {"success": False, "entity_id": entity_id, "action": action, "error": str(e)}
    
    def _extract_domain(self, entity_id: str) -> str:
        """Extract domain from entity ID."""
        match = _DOMAIN_PATTERN.match(entity_id)
        return match.group(1) if match else ""
    
    def search_entities(
        self,
        hass: HomeAssistant,
        query: str,
        domain_filter: Optional[str] = None,
        limit: int = 20,
    ) -> SearchResults:
        """Search entities by name, state, or domain."""
        start_time = time.perf_counter()
        
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
            domain = state.domain
            
            # Calculate relevance score
            score = self._calculate_entity_score(entity_id, name, state_value, query_lower)
            
            if score > 0:
                icon = state.attributes.get("icon", self.DOMAIN_ICONS.get(domain, "mdi:entity"))
                
                results.append(SearchResult(
                    type="entity",
                    id=entity_id,
                    title=name,
                    description=f"{domain}: {state_value}",
                    icon=icon,
                    score=score,
                    domain=domain,
                    actions=self._get_entity_actions(domain),
                ))
        
        # Sort by score and limit
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:limit]
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        return SearchResults(
            query=query,
            results=results,
            total=len(results),
            execution_time_ms=execution_time,
        )
    
    def _calculate_entity_score(self, entity_id: str, name: str, state_value: str, query: str) -> float:
        """Calculate relevance score for an entity."""
        entity_lower = entity_id.lower()
        name_lower = name.lower()
        
        # Exact match on entity_id (highest priority)
        if query == entity_lower:
            return 100.0
        # Exact match on name
        if query == name_lower:
            return 90.0
        # Starts with query
        if entity_lower.startswith(query):
            return 70.0
        if name_lower.startswith(query):
            return 60.0
        # Contains query
        if query in entity_lower:
            return 40.0
        if query in name_lower:
            return 30.0
        # Match on state
        if query in state_value.lower():
            return 20.0
        
        return 0.0
    
    def _get_entity_actions(self, domain: str) -> list[dict[str, str]]:
        """Get available actions for an entity domain."""
        base_actions = [
            {"action": "toggle", "label": "Toggle"},
            {"action": "turn_on", "label": "An"},
            {"action": "turn_off", "label": "Aus"},
        ]
        
        domain_specific = {
            "automation": [
                {"action": "trigger", "label": "Trigger"},
                {"action": "disable", "label": "Disable"},
            ],
            "scene": [
                {"action": "activate", "label": "Aktivieren"},
            ],
            "script": [
                {"action": "run", "label": "Ausführen"},
            ],
        }
        
        return domain_specific.get(domain, base_actions)
    
    def search_automations(
        self,
        hass: HomeAssistant,
        query: str,
        limit: int = 20,
    ) -> SearchResults:
        """Search automations by name, trigger, or action."""
        start_time = time.perf_counter()
        
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
            score = self._calculate_automation_score(name, triggers, actions, query_lower)
            
            # Boost for enabled automations
            if state == "on":
                score *= 1.1
            
            if score > 0:
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
                    domain="automation",
                    actions=[
                        {"action": "trigger", "label": "Trigger"},
                        {"action": "disable", "label": "Disable"} if state == "on" else {"action": "enable", "label": "Enable"},
                    ],
                ))
        
        # Sort by score and limit
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:limit]
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        return SearchResults(
            query=query,
            results=results,
            total=len(results),
            execution_time_ms=execution_time,
        )
    
    def _calculate_automation_score(self, name: str, triggers: list, actions: list, query: str) -> float:
        """Calculate relevance score for an automation."""
        # Match on name
        if query == name.lower():
            return 100.0
        if name.lower().startswith(query):
            return 70.0
        if query in name.lower():
            return 50.0
        
        # Match on triggers
        if triggers:
            triggers_str = str(triggers).lower()
            if query in triggers_str:
                return 40.0
        
        # Match on actions
        if actions:
            actions_str = str(actions).lower()
            if query in actions_str:
                return 30.0
        
        return 0.0
    
    def search_services(
        self,
        hass: HomeAssistant,
        query: str,
        domain_filter: Optional[str] = None,
    ) -> SearchResults:
        """Search available services."""
        start_time = time.perf_counter()
        
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
                score = self._calculate_service_score(service_name, domain, query_lower)
                
                if score > 0:
                    description = service.get("description", "") or f"Domain: {domain}"
                    
                    results.append(SearchResult(
                        type="service",
                        id=service_id,
                        title=service_name,
                        description=description,
                        icon=self.SERVICE_ICONS.get(domain, "mdi:service"),
                        score=score,
                        domain=domain,
                        actions=[
                            {"action": "call", "label": "Call"},
                        ],
                    ))
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        
        execution_time = (time.perf_counter() - start_time) * 1000
        
        return SearchResults(
            query=query,
            results=results,
            total=len(results),
            execution_time_ms=execution_time,
        )
    
    def _calculate_service_score(self, service_name: str, domain: str, query: str) -> float:
        """Calculate relevance score for a service."""
        # Match on service name
        if query == service_name:
            return 100.0
        if service_name.startswith(query):
            return 70.0
        if query in service_name:
            return 50.0
        # Match on domain
        if query in domain:
            return 30.0
        
        return 0.0
    
    async def async_combined_search(
        self,
        hass: HomeAssistant,
        query: str,
        limit: int = 20,
    ) -> SearchResults:
        """Combined search across entities, automations, and services."""
        # Perform searches
        entity_results = self.search_entities(hass, query, limit=limit)
        automation_results = self.search_automations(hass, query, limit=limit)
        service_results = self.search_services(hass, query, limit=limit)
        
        # Combine results
        all_results = (
            entity_results.results + 
            automation_results.results + 
            service_results.results
        )
        
        # Sort by score
        all_results.sort(key=lambda x: x.score, reverse=True)
        all_results = all_results[:limit]
        
        # Calculate total execution time
        total_time = (
            entity_results.execution_time_ms + 
            automation_results.execution_time_ms + 
            service_results.execution_time_ms
        )
        
        return SearchResults(
            query=query,
            results=all_results,
            total=len(all_results),
            execution_time_ms=total_time,
        )
    
    def _get_domain_automation_suggestions(self, domain: str, entity_name: str) -> list[str]:
        """Get automation suggestions based on entity domain."""
        base_suggestions = self.DOMAIN_SUGGESTIONS.get(domain, [f"Automation für {entity_name} erstellen"])
        return [s.format(entity_name=entity_name) if "{entity_name}" in s else s for s in base_suggestions]
    
    def generate_automation_suggestions(
        self,
        hass: HomeAssistant,
        query: str,
        search_results: Optional[SearchResults] = None,
    ) -> dict[str, Any]:
        """Generate automation suggestions from search results.
        
        Integrates with Character System for voice_tone aware formatting.
        """
        if search_results is None:
            search_results = self.search_entities(hass, query, limit=10)
        
        suggestions = []
        candidates = []
        
        for result in search_results.results:
            result_type = result.type
            result_id = result.id
            result_title = result.title
            score = result.score
            domain = result.domain
            
            if result_type == "entity":
                # Generate automation candidates based on entity
                entity_suggestions = self._get_domain_automation_suggestions(domain, result_title)
                
                candidate = {
                    "type": "entity_candidate",
                    "entity_id": result_id,
                    "entity_name": result_title,
                    "domain": domain,
                    "score": score,
                    "suggested_automations": entity_suggestions,
                }
                candidates.append(candidate)
                
                # Format suggestion text with character voice if available
                suggestion_text = f"Automation für {result_title}"
                if self._character_service:
                    suggestion_text = self._character_service.format_suggestion(suggestion_text)
                
                suggestions.append({
                    "type": "automation_suggestion",
                    "title": f"Automation für {result_title}",
                    "description": f"Entität {result_id} in Automation nutzen",
                    "entity_id": result_id,
                    "score": score * 0.8,
                    "formatted_text": suggestion_text,
                })
            
            elif result_type == "service":
                service_domain = domain
                
                candidate = {
                    "type": "service_candidate",
                    "service_id": result_id,
                    "service_name": result_title,
                    "domain": service_domain,
                    "score": score,
                    "suggested_automations": [f"Service {result_id} in Automation nutzen"],
                }
                candidates.append(candidate)
            
            elif result_type == "automation":
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
    
    async def async_generate_suggestions(
        self,
        hass: HomeAssistant,
        query: str,
    ) -> dict[str, Any]:
        """Generate automation suggestions from a search query.
        
        Combines entity, automation, and service search to generate
        comprehensive automation suggestions.
        """
        # Perform combined search
        combined_results = await self.async_combined_search(hass, query, limit=10)
        
        # Generate suggestions
        return self.generate_automation_suggestions(hass, query, combined_results)
    
    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the module."""
        # Remove services
        ctx.hass.services.async_remove(DOMAIN, "search_entities")
        ctx.hass.services.async_remove(DOMAIN, "search_automations")
        ctx.hass.services.async_remove(DOMAIN, "search_services")
        ctx.hass.services.async_remove(DOMAIN, "quick_action")
        ctx.hass.services.async_remove(DOMAIN, "combined_search")
        
        _LOGGER.info("Quick Search Module unloaded")
        return True
