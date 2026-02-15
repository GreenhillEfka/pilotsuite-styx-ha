"""
Zone Detection Module
=====================

Provides automatic zone detection via device_tracker/person entities.
Supports:
- Automatic zone detection based on person/device presence
- Zone templates for common scenarios (home, work, away, etc.)
- Multi-user zone clustering ("zusammen sein" pattern)

Zonen-Templates:
- home: Standard-Zuhause-Zone (basierend auf person.entities)
- work: Arbeitszone (standortbasiert oder manuell konfiguriert)
- away: Abwesenheits-Zone (niemand zu Hause)
- shared: Gemeinsame Anwesenheit (mehrere Personen zu Hause)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback, State
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components.device_tracker import DOMAIN as DEVICE_TRACKER_DOMAIN
from homeassistant.components.person import DOMAIN as PERSON_DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

# Standard-Zonenvorlagen
ZONE_TEMPLATES = {
    "home": {
        "name": "Zuhause",
        "description": "Standard-Zuhause-Zone",
        "trigger_entities": ["person", "device_tracker"],
        "mode": "any",
    },
    "work": {
        "name": "Arbeit",
        "description": "Arbeitszone (Standortbasiert)",
        "trigger_entities": ["device_tracker"],
        "mode": "any",
    },
    "away": {
        "name": "Abwesenheit",
        "description": "Niemand zu Hause",
        "trigger_entities": [],
        "mode": "none",
    },
    "shared": {
        "name": "Gemeinsam",
        "description": "Mehrere Personen zu Hause",
        "trigger_entities": ["person"],
        "mode": "multiple",
        "min_users": 2,
    },
    "sleep": {
        "name": "Schlafenszeit",
        "description": "Nachts zu Hause",
        "trigger_entities": ["person"],
        "mode": "time_based",
        "start_time": "22:00",
        "end_time": "08:00",
    },
}


@dataclass
class DetectedZone:
    """Ein erkannte Zone."""
    zone_id: str
    zone_name: str
    detected_at: datetime
    detected_by: list[str]  # List of entity_ids
    confidence: float
    users: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ZoneConfig:
    """Konfiguration für eine Zone."""
    zone_id: str
    name: str
    description: str
    trigger_entities: list[str]
    mode: str  # any, none, multiple, time_based
    min_users: int = 1
    start_time: str | None = None
    end_time: str | None = None
    enabled: bool = True


class ZoneDetector:
    """
    Automatic Zone Detection via device_tracker/person entities.
    
    Features:
    - Automatic zone detection based on person/device presence
    - Zone templates for common scenarios
    - Multi-user zone clustering ("zusammen sein" pattern)
    - Time-based zone detection (e.g., sleep mode)
    """
    
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the zone detector."""
        self.hass = hass
        self.config_entry = config_entry
        
        # Config
        self._enabled = True
        self._detection_interval = 30  # seconds
        self._zone_timeout = 300  # seconds (5 min) before switching zones
        
        # Internal state
        self._zones: dict[str, ZoneConfig] = {}
        self._current_zones: dict[str, DetectedZone] = {}  # user_id -> current zone
        self._person_entities: list[str] = []
        self._device_entities: list[str] = []
        self._unsub_trackers: list[Any] = []
        
        # Load zone templates
        self._load_zone_templates()
        
    def _load_zone_templates(self) -> None:
        """Load zone templates into zone configurations."""
        for template_id, template in ZONE_TEMPLATES.items():
            self._zones[template_id] = ZoneConfig(
                zone_id=template_id,
                name=template["name"],
                description=template["description"],
                trigger_entities=template["trigger_entities"],
                mode=template["mode"],
                min_users=template.get("min_users", 1),
                start_time=template.get("start_time"),
                end_time=template.get("end_time"),
                enabled=True,
            )
        _LOGGER.info("Loaded %d zone templates", len(self._zones))
        
    async def async_setup(self) -> None:
        """Set up the zone detector."""
        _LOGGER.info("Setting up Zone Detector")
        
        # Discover person and device_tracker entities
        await self._async_discover_entities()
        
        # Subscribe to entity state changes
        await self._async_subscribe_entities()
        
        # Start periodic zone checking
        self.hass.async_create_task(self._async_periodic_zone_check())
        
        _LOGGER.info(
            "Zone Detector initialized: %d zones, %d persons, %d device_trackers",
            len(self._zones),
            len(self._person_entities),
            len(self._device_entities),
        )
        
    async def async_unload(self) -> None:
        """Unload the zone detector."""
        for unsub in self._unsub_trackers:
            unsub()
        self._unsub_trackers.clear()
        
    async def _async_discover_entities(self) -> None:
        """Discover person and device_tracker entities."""
        self._person_entities = []
        self._device_entities = []
        
        # Person entities
        for state in self.hass.states.async_all(PERSON_DOMAIN):
            self._person_entities.append(state.entity_id)
            
        # Device tracker entities
        for state in self.hass.states.async_all(DEVICE_TRACKER_DOMAIN):
            self._device_entities.append(state.entity_id)
            
        _LOGGER.info(
            "Discovered entities: %d persons, %d device_trackers",
            len(self._person_entities),
            len(self._device_entities),
        )
        
    async def _async_subscribe_entities(self) -> None:
        """Subscribe to person and device_tracker state changes."""
        watched = self._person_entities + self._device_entities
        
        @callback
        def _on_state_change(event) -> None:
            """Handle entity state change."""
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            
            if new_state:
                self.hass.async_create_task(self._async_check_zones())
                
        self._unsub_trackers.append(
            async_track_state_change_event(self.hass, watched, _on_state_change)
        )
        
    async def _async_periodic_zone_check(self) -> None:
        """Periodically check and update zones."""
        while self._enabled:
            await self._async_check_zones()
            await asyncio.sleep(self._detection_interval)
            
    async def _async_check_zones(self) -> None:
        """Check and update zones for all users."""
        current_time = datetime.now()
        
        for person_entity in self._person_entities:
            state = self.hass.states.get(person_entity)
            if not state:
                continue
                
            user_id = person_entity
            user_zone = await self._detect_zone_for_user(user_id, state, current_time)
            
            if user_zone:
                self._current_zones[user_id] = user_zone
                _LOGGER.debug(
                    "User %s detected in zone %s (confidence: %.2f)",
                    user_id,
                    user_zone.zone_id,
                    user_zone.confidence,
                )
                
    async def _detect_zone_for_user(
        self,
        user_id: str,
        state: State,
        current_time: datetime,
    ) -> DetectedZone | None:
        """Detect zone for a specific user."""
        if not state:
            return None
            
        # Get current state
        entity_id = state.entity_id
        zone_state = state.state
        
        # Check each zone template
        best_zone = None
        best_confidence = 0.0
        
        for zone_id, zone_config in self._zones.items():
            if not zone_config.enabled:
                continue
                
            confidence = await self._calculate_zone_confidence(
                zone_config, state, current_time
            )
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_zone = zone_id
                
        if best_zone and best_confidence > 0.5:
            return DetectedZone(
                zone_id=best_zone,
                zone_name=self._zones[best_zone].name,
                detected_at=current_time,
                detected_by=[entity_id],
                confidence=best_confidence,
                users=[user_id],
            )
            
        return None
        
    async def _calculate_zone_confidence(
        self,
        zone_config: ZoneConfig,
        state: State,
        current_time: datetime,
    ) -> float:
        """Calculate confidence for a zone detection."""
        if not state:
            return 0.0
            
        confidence = 0.0
        
        # Mode-based confidence calculation
        if zone_config.mode == "any":
            # Zone detected if any trigger entity is active
            if zone_config.trigger_entities:
                entity_domain = state.entity_id.split(".", 1)[0]
                if entity_domain in zone_config.trigger_entities:
                    confidence = 0.8 if state.state == "home" else 0.2
                    
        elif zone_config.mode == "none":
            # Zone detected if NO entities are active (away mode)
            active_entities = sum(
                1 for e in self._person_entities
                if self.hass.states.get(e) and self.hass.states.get(e).state == "home"
            )
            confidence = 0.9 if active_entities == 0 else 0.1
            
        elif zone_config.mode == "multiple":
            # Zone detected if MIN_USERS are present
            active_users = sum(
                1 for e in self._person_entities
                if self.hass.states.get(e) and self.hass.states.get(e).state == "home"
            )
            if active_users >= zone_config.min_users:
                confidence = min(0.95, 0.6 + 0.1 * active_users)
                
        elif zone_config.mode == "time_based":
            # Zone detected based on time
            if zone_config.start_time and zone_config.end_time:
                start_hour = int(zone_config.start_time.split(":")[0])
                end_hour = int(zone_config.end_time.split(":")[0])
                current_hour = current_time.hour
                
                # Handle overnight ranges (e.g., 22:00-08:00)
                if start_hour > end_hour:
                    if current_hour >= start_hour or current_hour < end_hour:
                        confidence = 0.85
                else:
                    if start_hour <= current_hour < end_hour:
                        confidence = 0.85
                        
        return confidence
        
    def get_user_zone(self, user_id: str) -> DetectedZone | None:
        """Get current zone for a user."""
        return self._current_zones.get(user_id)
        
    def get_all_zones(self) -> dict[str, DetectedZone]:
        """Get all current zones."""
        return self._current_zones.copy()
        
    def get_active_users_in_zone(self, zone_id: str) -> list[str]:
        """Get all users currently in a specific zone."""
        return [
            user_id for user_id, zone in self._current_zones.items()
            if zone.zone_id == zone_id
        ]
        
    def is_together(self, user_ids: list[str]) -> bool:
        """Check if specified users are in the same zone."""
        if len(user_ids) < 2:
            return False
            
        zones = [self._current_zones.get(uid) for uid in user_ids]
        if not all(zones):
            return False
            
        return len(set(z.zone_id for z in zones)) == 1
        
    def get_zone_summary(self) -> dict[str, Any]:
        """Get a summary of all zones and their occupants."""
        summary = {}
        
        for zone_id, zone_config in self._zones.items():
            users = self.get_active_users_in_zone(zone_id)
            summary[zone_id] = {
                "name": zone_config.name,
                "users": users,
                "user_count": len(users),
                    "together": len(users) >= 2,
            }
            
        return summary
