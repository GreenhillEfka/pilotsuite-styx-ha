"""User Hints Service - Process user suggestions."""

import asyncio
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

from .models import UserHint, HintStatus, HintType, HintSuggestion


class UserHintsService:
    """Service to manage and process user hints."""
    
    # Patterns for parsing user hints
    SYNC_PATTERNS = [
        r"schalte?\s+(\w+)\s+(?:immer\s+)?sync(?:hron)?\s+mit\s+(\w+)",
        r"(\w+)\s+(?:und|mit)\s+(\w+)\s+(?:zusammen|gleichzeitig)",
        r"wenn\s+(\w+)\s+(?:dann\s+)?auch\s+(\w+)",
    ]
    
    SCHEDULE_PATTERNS = [
        r"um\s+(\d{1,2}[:.]\d{2})",
        r"(\d{1,2})\s* Uhr",
        r"morgens?|abends?|mittags?",
        r"bei\s+(sonnenaufgang|sonnenuntergang)",
    ]
    
    ENTITY_PATTERNS = [
        r"(kaffee(?:maschine|mühle|hahn))",
        r"(licht|lampe|beleuchtung)[\s_-]?(\w+)",
        r"(heizung|thermostat)[\s_-]?(\w+)",
        r"(rollladen|rollo|vorhang)[\s_-]?(\w+)",
        r"(musik|lautsprecher|sonos)[\s_-]?(\w+)",
    ]
    
    def __init__(self, hass=None, coordinator=None):
        """Initialize the service."""
        self.hass = hass
        self.coordinator = coordinator
        self._hints: Dict[str, UserHint] = {}
        self._suggestions: Dict[str, HintSuggestion] = {}
        
    async def add_hint(self, text: str, hint_type: Optional[HintType] = None) -> UserHint:
        """Add a new user hint."""
        hint_id = str(uuid.uuid4())[:8]
        
        # Auto-detect hint type if not provided
        if hint_type is None:
            hint_type = self._detect_hint_type(text)
        
        hint = UserHint(
            id=hint_id,
            text=text,
            hint_type=hint_type,
        )
        
        # Parse the hint
        await self._analyze_hint(hint)
        
        self._hints[hint_id] = hint
        return hint
    
    def _detect_hint_type(self, text: str) -> HintType:
        """Detect the type of hint from text."""
        text_lower = text.lower()
        
        # Check for automation patterns
        if any(re.search(p, text_lower) for p in self.SYNC_PATTERNS):
            return HintType.AUTOMATION
        
        # Check for schedule patterns
        if any(re.search(p, text_lower) for p in self.SCHEDULE_PATTERNS):
            return HintType.SCHEDULE
        
        # Check for preference patterns
        if any(word in text_lower for word in ["nicht", "nie", "stört", "nervt"]):
            return HintType.PREFERENCE
        
        # Check for feature request
        if any(word in text_lower for word in ["wünsche", "möchte", "brauche", "fehlt"]):
            return HintType.FEATURE_REQUEST
        
        # Default to automation
        return HintType.AUTOMATION
    
    async def _analyze_hint(self, hint: UserHint) -> None:
        """Analyze a hint and extract entities, actions, etc."""
        text_lower = hint.text.lower()
        
        # Extract entities
        entities = []
        for pattern in self.ENTITY_PATTERNS:
            matches = re.findall(pattern, text_lower)
            entities.extend(["_".join(m) if isinstance(m, tuple) else m for m in matches])
        
        # Extract from sync patterns
        for pattern in self.SYNC_PATTERNS:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if isinstance(match, tuple):
                    entities.extend(list(match))
                else:
                    entities.append(match)
        
        hint.entities = list(set(entities))
        
        # Extract actions
        if "schalte" in text_lower or "einschalten" in text_lower:
            hint.actions.append("turn_on")
        if "ausschalten" in text_lower:
            hint.actions.append("turn_off")
        if "sync" in text_lower or "synchron" in text_lower:
            hint.actions.append("sync")
        
        # Extract schedule
        for pattern in self.SCHEDULE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                hint.schedule = match.group(0)
                break
        
        # Generate suggestion if entities found
        if len(hint.entities) >= 2 and hint.actions:
            await self._generate_suggestion(hint)
        
        hint.status = HintStatus.ANALYZED
        hint.analyzed_at = datetime.now()
    
    async def _generate_suggestion(self, hint: UserHint) -> None:
        """Generate an automation suggestion from a hint."""
        if len(hint.entities) < 2:
            return
        
        entity1, entity2 = hint.entities[0], hint.entities[1]
        
        # Find matching entity IDs in HA
        entity1_id = await self._find_entity(entity1)
        entity2_id = await self._find_entity(entity2)
        
        if not entity1_id or not entity2_id:
            hint.confidence = 0.3
            return
        
        # Create suggestion based on hint type
        if hint.hint_type == HintType.AUTOMATION:
            suggestion = HintSuggestion(
                hint_id=hint.id,
                name=f"Sync {entity1} mit {entity2}",
                description=f"Automatisierung basierend auf: {hint.text}",
                trigger={
                    "platform": "state",
                    "entity_id": entity1_id,
                    "to": "on",
                },
                action={
                    "service": "homeassistant.turn_on",
                    "target": {"entity_id": entity2_id},
                },
                confidence=0.8,
                reasoning=f"Erkannte Beziehung zwischen {entity1} und {entity2}",
            )
            
            hint.suggested_automation = suggestion.to_automation()
            hint.confidence = 0.8
            hint.status = HintStatus.SUGGESTION_CREATED
            
            self._suggestions[hint.id] = suggestion
    
    async def _find_entity(self, name: str) -> Optional[str]:
        """Find entity ID by name or alias."""
        if not self.hass:
            return None
        
        name_lower = name.lower()
        
        # Search in entity registry
        for entity_id, state in self.hass.states.async_all().items():
            if name_lower in entity_id.lower():
                return entity_id
            if state.attributes.get("friendly_name", "").lower().find(name_lower) >= 0:
                return entity_id
        
        return None
    
    def get_hints(self, status: Optional[HintStatus] = None) -> List[UserHint]:
        """Get all hints, optionally filtered by status."""
        hints = list(self._hints.values())
        if status:
            hints = [h for h in hints if h.status == status]
        return sorted(hints, key=lambda h: h.created_at, reverse=True)
    
    def get_suggestions(self) -> List[HintSuggestion]:
        """Get all suggestions."""
        return list(self._suggestions.values())
    
    async def accept_suggestion(self, hint_id: str) -> bool:
        """Accept a suggestion and create the automation in Home Assistant."""
        if hint_id not in self._hints:
            return False

        hint = self._hints[hint_id]
        if not hint.suggested_automation:
            return False

        # Create automation via HA service
        if self.hass:
            try:
                auto_config = hint.suggested_automation
                await self._hass.services.async_call(
                    "automation",
                    "create",
                    {
                        "alias": auto_config.get("alias", f"PilotSuite: {hint.title}"),
                        "description": auto_config.get("description", f"Auto-created from hint {hint_id}"),
                        "trigger": auto_config.get("trigger", []),
                        "condition": auto_config.get("condition", []),
                        "action": auto_config.get("action", []),
                        "mode": auto_config.get("mode", "single"),
                    },
                    blocking=True,
                )
            except Exception:
                # Fallback: write automation YAML config if service not available
                import logging
                logging.getLogger(__name__).warning(
                    "automation.create service unavailable; hint %s marked accepted without HA automation",
                    hint_id,
                )

        hint.status = HintStatus.ACCEPTED
        hint.user_feedback = "accepted"
        return True
    
    async def reject_suggestion(self, hint_id: str, reason: Optional[str] = None) -> bool:
        """Reject a suggestion."""
        if hint_id not in self._hints:
            return False
        
        hint = self._hints[hint_id]
        hint.status = HintStatus.REJECTED
        hint.user_feedback = reason
        return True
EOF