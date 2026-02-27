"""Suggestion Panel - Dedicated UI for PilotSuite suggestions.

Provides a centralized view for all suggestions with:
- Timeline view of pending suggestions
- Swipe gestures for mobile (Accept/Reject/Snooze)
- Confidence indicator
- "Why?" explanation for each suggestion
- Zone and Mood context display

Based on Deep Research Report recommendations.
"""
from __future__ import annotations

import logging
import voluptuous as vol
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _record_preference_feedback(
    hass: HomeAssistant,
    entry_id: str,
    user: str,
    suggestion_id: str,
    *,
    accepted: bool,
) -> None:
    """Record suggestion feedback locally (MUPL) and push to Core."""
    try:
        entry_data = hass.data.get(DOMAIN, {}).get(entry_id, {})
        if not isinstance(entry_data, dict):
            return
        # Local MUPL learning
        mupl = entry_data.get("user_preference_module")
        if mupl and hasattr(mupl, "learn_pattern"):
            mupl.learn_pattern(
                user=user or "default",
                pattern_type="suggestion_feedback",
                pattern_data={
                    "suggestion_id": suggestion_id,
                    "accepted": accepted,
                },
            )
        # Push feedback to Core (fire-and-forget)
        coordinator = entry_data.get("coordinator")
        if coordinator and hasattr(coordinator, "api"):
            hass.async_create_task(
                _async_push_feedback_to_core(
                    coordinator.api,
                    user or "default",
                    suggestion_id,
                    "accepted" if accepted else "dismissed",
                )
            )
    except Exception:
        _LOGGER.debug("Could not record preference feedback for suggestion %s", suggestion_id)


async def _async_push_feedback_to_core(api, user_id: str, suggestion_id: str, feedback_type: str) -> None:
    """Push MUPL feedback to Core's user preference endpoint."""
    try:
        await api.async_post(
            f"/api/v1/user/{user_id}/feedback",
            {
                "suggestion_id": suggestion_id,
                "feedback_type": feedback_type,
                "pattern": "",
                "confidence_adjustment": 0.5 if feedback_type == "accepted" else -0.3,
            },
        )
    except Exception:
        _LOGGER.debug("Could not push feedback to Core for suggestion %s", suggestion_id)


class SuggestionStatus(str, Enum):
    """Status of a suggestion."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SNOOZED = "snoozed"
    EXPIRED = "expired"


class SuggestionPriority(str, Enum):
    """Priority level for sorting suggestions."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Suggestion:
    """A CoPilot suggestion with full context."""
    
    # Core
    suggestion_id: str
    pattern: str  # "light.kitchen:on → switch.coffee:on"
    confidence: float  # 0.0 - 1.0
    lift: float  # > 1.0 = positive correlation
    support: int  # observation count
    
    # Source
    source: str = "habitus"  # habitus, seed, zone_mining, calendar
    blueprint_url: str = ""
    blueprint_id: str = ""
    
    # Zone context
    zone_id: str = ""
    zone_name: str = ""
    zone_entities: list[str] = field(default_factory=list)
    
    # Mood context
    mood_type: str = ""
    mood_value: float = 0.0
    mood_reason: str = ""
    
    # Risk/Safety
    risk_level: str = "medium"
    safety_critical: bool = False
    requires_confirmation: bool = True
    
    # State
    status: SuggestionStatus = SuggestionStatus.PENDING
    priority: SuggestionPriority = SuggestionPriority.MEDIUM
    
    # Timing
    created_at: datetime = field(default_factory=dt_util.utcnow)
    expires_at: datetime | None = None
    snoozed_until: datetime | None = None
    
    # Evidence
    evidence: list[dict[str, Any]] = field(default_factory=list)
    timing_stats: dict[str, Any] = field(default_factory=dict)
    median_delay_sec: float = 0.0
    
    # User feedback
    accepted_by: str = ""
    rejected_by: str = ""
    rejection_reason: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "suggestion_id": self.suggestion_id,
            "pattern": self.pattern,
            "confidence": self.confidence,
            "lift": self.lift,
            "support": self.support,
            "source": self.source,
            "blueprint_url": self.blueprint_url,
            "blueprint_id": self.blueprint_id,
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "zone_entities": self.zone_entities,
            "mood_type": self.mood_type,
            "mood_value": self.mood_value,
            "mood_reason": self.mood_reason,
            "risk_level": self.risk_level,
            "safety_critical": self.safety_critical,
            "requires_confirmation": self.requires_confirmation,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "snoozed_until": self.snoozed_until.isoformat() if self.snoozed_until else None,
            "evidence": self.evidence,
            "timing_stats": self.timing_stats,
            "median_delay_sec": self.median_delay_sec,
            "accepted_by": self.accepted_by,
            "rejected_by": self.rejected_by,
            "rejection_reason": self.rejection_reason,
        }
    
    def compute_priority(self) -> SuggestionPriority:
        """Compute priority based on confidence, lift, and mood match."""
        score = 0.0
        
        # Confidence weight (0-40 points)
        score += self.confidence * 40
        
        # Lift weight (0-30 points, capped at lift=5)
        score += min(self.lift / 5.0, 1.0) * 30
        
        # Mood match bonus (0-20 points)
        if self.mood_value > 0.5:
            score += self.mood_value * 20
        
        # Safety critical penalty (-10 points)
        if self.safety_critical:
            score -= 10
        
        if score >= 60:
            return SuggestionPriority.HIGH
        elif score >= 30:
            return SuggestionPriority.MEDIUM
        else:
            return SuggestionPriority.LOW


@dataclass
class SuggestionQueue:
    """Queue of suggestions with filtering and sorting."""
    
    suggestions: list[Suggestion] = field(default_factory=list)
    max_pending: int = 50
    max_history: int = 200
    
    def add(self, suggestion: Suggestion) -> None:
        """Add a suggestion to the queue."""
        # Check for duplicates
        existing_ids = {s.suggestion_id for s in self.suggestions}
        if suggestion.suggestion_id in existing_ids:
            return
        
        # Compute priority
        suggestion.priority = suggestion.compute_priority()
        
        # Add to front of pending
        self.suggestions.insert(0, suggestion)
        
        # Trim if needed
        self._trim()
    
    def _trim(self) -> None:
        """Trim queue to size limits."""
        pending = [s for s in self.suggestions if s.status == SuggestionStatus.PENDING]
        history = [s for s in self.suggestions if s.status != SuggestionStatus.PENDING]
        
        # Keep only last N pending
        if len(pending) > self.max_pending:
            pending = pending[:self.max_pending]
        
        # Keep only last M history
        if len(history) > self.max_history:
            history = history[:self.max_history]
        
        self.suggestions = pending + history
    
    def get_pending(self, zone_id: str = "", mood_type: str = "") -> list[Suggestion]:
        """Get pending suggestions, optionally filtered."""
        result = []
        
        for s in self.suggestions:
            if s.status != SuggestionStatus.PENDING:
                continue
            
            # Check snooze
            if s.snoozed_until and s.snoozed_until > dt_util.utcnow():
                continue
            
            # Check expiry
            if s.expires_at and s.expires_at < dt_util.utcnow():
                s.status = SuggestionStatus.EXPIRED
                continue
            
            # Filter by zone
            if zone_id and s.zone_id != zone_id:
                continue
            
            # Filter by mood
            if mood_type and s.mood_type != mood_type:
                continue
            
            result.append(s)
        
        # Sort by priority (high first), then by confidence
        result.sort(key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}[x.priority.value],
            -x.confidence
        ))
        
        return result
    
    def get_by_id(self, suggestion_id: str) -> Suggestion | None:
        """Get a suggestion by ID."""
        for s in self.suggestions:
            if s.suggestion_id == suggestion_id:
                return s
        return None
    
    def accept(self, suggestion_id: str, user: str = "") -> bool:
        """Accept a suggestion."""
        s = self.get_by_id(suggestion_id)
        if not s or s.status != SuggestionStatus.PENDING:
            return False
        
        s.status = SuggestionStatus.ACCEPTED
        s.accepted_by = user
        return True
    
    def reject(self, suggestion_id: str, user: str = "", reason: str = "") -> bool:
        """Reject a suggestion."""
        s = self.get_by_id(suggestion_id)
        if not s or s.status != SuggestionStatus.PENDING:
            return False
        
        s.status = SuggestionStatus.REJECTED
        s.rejected_by = user
        s.rejection_reason = reason
        return True
    
    def snooze(self, suggestion_id: str, duration: timedelta = timedelta(hours=4)) -> bool:
        """Snooze a suggestion."""
        s = self.get_by_id(suggestion_id)
        if not s or s.status != SuggestionStatus.PENDING:
            return False
        
        s.snoozed_until = dt_util.utcnow() + duration
        return True
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "suggestions": [s.to_dict() for s in self.suggestions],
            "pending_count": len([s for s in self.suggestions if s.status == SuggestionStatus.PENDING]),
            "accepted_count": len([s for s in self.suggestions if s.status == SuggestionStatus.ACCEPTED]),
            "rejected_count": len([s for s in self.suggestions if s.status == SuggestionStatus.REJECTED]),
        }


class SuggestionPanelStore:
    """Persistent storage for suggestion panel."""
    
    def __init__(self, hass: HomeAssistant, entry_id: str):
        self.hass = hass
        self.entry_id = entry_id
        self._queue = SuggestionQueue()
    
    async def async_load(self) -> None:
        """Load suggestions from storage."""
        from .storage import async_load_from_store
        
        data = await async_load_from_store(self.hass, self.entry_id, "suggestions")
        if isinstance(data, dict) and "suggestions" in data:
            suggestions = []
            for s in data["suggestions"]:
                try:
                    suggestions.append(Suggestion(
                        suggestion_id=s["suggestion_id"],
                        pattern=s["pattern"],
                        confidence=s.get("confidence", 0.5),
                        lift=s.get("lift", 1.0),
                        support=s.get("support", 0),
                        source=s.get("source", "habitus"),
                        blueprint_url=s.get("blueprint_url", ""),
                        blueprint_id=s.get("blueprint_id", ""),
                        zone_id=s.get("zone_id", ""),
                        zone_name=s.get("zone_name", ""),
                        zone_entities=s.get("zone_entities", []),
                        mood_type=s.get("mood_type", ""),
                        mood_value=s.get("mood_value", 0.0),
                        mood_reason=s.get("mood_reason", ""),
                        risk_level=s.get("risk_level", "medium"),
                        safety_critical=s.get("safety_critical", False),
                        requires_confirmation=s.get("requires_confirmation", True),
                        status=SuggestionStatus(s.get("status", "pending")),
                        priority=SuggestionPriority(s.get("priority", "medium")),
                        created_at=datetime.fromisoformat(s["created_at"]) if s.get("created_at") else dt_util.utcnow(),
                        expires_at=datetime.fromisoformat(s["expires_at"]) if s.get("expires_at") else None,
                        snoozed_until=datetime.fromisoformat(s["snoozed_until"]) if s.get("snoozed_until") else None,
                        evidence=s.get("evidence", []),
                        timing_stats=s.get("timing_stats", {}),
                        median_delay_sec=s.get("median_delay_sec", 0.0),
                        accepted_by=s.get("accepted_by", ""),
                        rejected_by=s.get("rejected_by", ""),
                        rejection_reason=s.get("rejection_reason", ""),
                    ))
                except Exception as err:
                    _LOGGER.warning("Failed to load suggestion %s: %s", s.get("suggestion_id"), err)
            
            self._queue.suggestions = suggestions
            _LOGGER.info("Loaded %d suggestions from storage", len(suggestions))
    
    async def async_save(self) -> None:
        """Save suggestions to storage."""
        from .storage import async_save_to_store
        
        await async_save_to_store(
            self.hass, self.entry_id, "suggestions", self._queue.to_dict()
        )
    
    @property
    def queue(self) -> SuggestionQueue:
        return self._queue


# --- Services ---

async def async_setup_suggestion_services(hass: HomeAssistant, entry_id: str) -> None:
    """Setup suggestion panel services."""
    
    store = SuggestionPanelStore(hass, entry_id)
    await store.async_load()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry_id, {})
    hass.data[DOMAIN][entry_id]["suggestion_store"] = store
    
    @callback
    def handle_accept(call):
        """Handle suggestion accept."""
        suggestion_id = call.data.get("suggestion_id")
        user = call.data.get("user", "")

        if store.queue.accept(suggestion_id, user):
            _LOGGER.info("Accepted suggestion %s", suggestion_id)
            hass.async_create_task(store.async_save())
            hass.bus.async_fire(f"{DOMAIN}_suggestion_accepted", {"suggestion_id": suggestion_id})
            # Feedback to MUPL learning
            _record_preference_feedback(hass, entry_id, user, suggestion_id, accepted=True)

    @callback
    def handle_reject(call):
        """Handle suggestion reject."""
        suggestion_id = call.data.get("suggestion_id")
        user = call.data.get("user", "")
        reason = call.data.get("reason", "")

        if store.queue.reject(suggestion_id, user, reason):
            _LOGGER.info("Rejected suggestion %s", suggestion_id)
            hass.async_create_task(store.async_save())
            hass.bus.async_fire(f"{DOMAIN}_suggestion_rejected", {
                "suggestion_id": suggestion_id,
                "reason": reason
            })
            # Feedback to MUPL learning
            _record_preference_feedback(hass, entry_id, user, suggestion_id, accepted=False)
    
    @callback
    def handle_snooze(call):
        """Handle suggestion snooze."""
        suggestion_id = call.data.get("suggestion_id")
        hours = call.data.get("hours", 4)
        
        if store.queue.snooze(suggestion_id, timedelta(hours=hours)):
            _LOGGER.info("Snoozed suggestion %s for %d hours", suggestion_id, hours)
            hass.async_create_task(store.async_save())
    
    hass.services.async_register(DOMAIN, "suggestion_accept", handle_accept)
    hass.services.async_register(DOMAIN, "suggestion_reject", handle_reject)
    hass.services.async_register(DOMAIN, "suggestion_snooze", handle_snooze)


# --- WebSocket API ---

async def async_setup_suggestion_websocket(hass: HomeAssistant, entry_id: str) -> None:
    """Setup WebSocket API for suggestion panel."""
    
    from homeassistant.components import websocket_api
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}_suggestions_get",
        vol.Optional("zone_id"): str,
        vol.Optional("mood_type"): str,
        vol.Optional("status"): str,
    })
    @websocket_api.async_response
    async def ws_get_suggestions(hass_local, connection, msg):
        """Get suggestions with optional filters."""
        store: SuggestionPanelStore = hass.data[DOMAIN][entry_id].get("suggestion_store")
        if not store:
            connection.send_error(msg["id"], "store_not_found", "Suggestion store not initialized")
            return
        
        zone_id = msg.get("zone_id", "")
        mood_type = msg.get("mood_type", "")
        status = msg.get("status", "pending")
        
        if status == "pending":
            suggestions = store.queue.get_pending(zone_id, mood_type)
        else:
            suggestions = [s for s in store.queue.suggestions if s.status.value == status]
        
        connection.send_result(msg["id"], {
            "suggestions": [s.to_dict() for s in suggestions],
            "total": len(suggestions)
        })
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}_suggestion_action",
        vol.Required("suggestion_id"): str,
        vol.Required("action"): str,  # accept, reject, snooze
        vol.Optional("reason"): str,
        vol.Optional("hours"): int,
    })
    @websocket_api.async_response
    async def ws_suggestion_action(hass_local, connection, msg):
        """Perform action on a suggestion."""
        store: SuggestionPanelStore = hass.data[DOMAIN][entry_id].get("suggestion_store")
        if not store:
            connection.send_error(msg["id"], "store_not_found", "Suggestion store not initialized")
            return
        
        suggestion_id = msg["suggestion_id"]
        action = msg["action"]
        
        success = False
        if action == "accept":
            success = store.queue.accept(suggestion_id)
        elif action == "reject":
            reason = msg.get("reason", "")
            success = store.queue.reject(suggestion_id, reason=reason)
        elif action == "snooze":
            hours = msg.get("hours", 4)
            success = store.queue.snooze(suggestion_id, timedelta(hours=hours))
        
        if success:
            await store.async_save()
            connection.send_result(msg["id"], {"success": True, "action": action})
        else:
            connection.send_error(msg["id"], "action_failed", f"Failed to {action} suggestion")
    
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}_chat_send",
        vol.Required("message"): str,
        vol.Optional("conversation_id"): str,
    })
    @websocket_api.async_response
    async def ws_chat_send(hass_local, connection, msg):
        """Send a chat message to Core Add-on and return the response.

        Uses the coordinator's async_chat_completions() for the API call
        so the request goes through the same auth + retry pipeline.
        """
        entry_data = hass.data.get(DOMAIN, {}).get(entry_id, {})
        coordinator = entry_data.get("coordinator") if isinstance(entry_data, dict) else None
        if not coordinator:
            connection.send_error(msg["id"], "coordinator_not_found",
                                  "Coordinator not initialized")
            return

        user_message = msg["message"]
        conversation_id = msg.get("conversation_id")

        try:
            # Build context-rich system prompt
            messages = []
            try:
                from .conversation_context import async_build_system_prompt
                entry_obj = hass.config_entries.async_get_entry(entry_id)
                if entry_obj:
                    system_prompt = await async_build_system_prompt(
                        hass, entry_obj, language="de",
                    )
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
            except Exception:
                pass  # Fall through without context
            messages.append({"role": "user", "content": user_message})
            result = await coordinator.async_chat_completions(
                messages, conversation_id=conversation_id,
            )
            # Extract assistant reply from OpenAI-compatible response
            choices = result.get("choices", [])
            reply = ""
            if choices:
                reply = choices[0].get("message", {}).get("content", "")

            connection.send_result(msg["id"], {
                "reply": reply,
                "conversation_id": conversation_id,
                "model": result.get("model", ""),
            })
        except Exception as exc:
            _LOGGER.error("Chat WS error: %s", exc)
            connection.send_error(msg["id"], "chat_error", str(exc))

    websocket_api.async_register_command(hass, ws_get_suggestions)
    websocket_api.async_register_command(hass, ws_suggestion_action)
    websocket_api.async_register_command(hass, ws_chat_send)