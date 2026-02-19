"""
Proactive Context Engine -- Non-intrusive contextual suggestions.

Generates smart suggestions when users move between zones, based on:
- Time of day
- Zone context (what media was playing, what devices are there)
- User preferences (from conversation memory + user profiles)
- Household context (who else is home, children present?)

Suggestions are delivered via TTS, notification, or chat --
configurable per user. The engine is intentionally NON-PENETRANT:
it respects cooldown periods, quiet hours, and user dismissals.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

import requests

_LOGGER = logging.getLogger(__name__)

SUPERVISOR_API = os.environ.get("SUPERVISOR_API", "http://supervisor/core/api")

# Cooldown: don't suggest again for the same zone within this many seconds
ZONE_COOLDOWN_SECONDS = int(os.environ.get("PROACTIVE_COOLDOWN", "1800"))  # 30 min

# Quiet hours: no proactive suggestions during these hours
QUIET_START = int(os.environ.get("QUIET_HOUR_START", "23"))
QUIET_END = int(os.environ.get("QUIET_HOUR_END", "7"))


class ProactiveContextEngine:
    """Generate context-aware suggestions on zone entry.

    Non-intrusive by design: respects cooldowns, quiet hours, user
    dismissals, and household context.  Suggestions are templates
    that can be delivered via TTS, persistent notification, or chat.
    """

    def __init__(self, media_zone_manager=None, mood_service=None,
                 household_profile=None, conversation_memory=None):
        self._media_mgr = media_zone_manager
        self._mood_svc = mood_service
        self._household = household_profile
        self._conv_memory = conversation_memory
        self._lock = threading.Lock()
        # Track last suggestion time per (person, zone)
        self._cooldowns: Dict[str, float] = {}
        # Track dismissed suggestion types per person
        self._dismissed: Dict[str, set] = {}
        _LOGGER.info("ProactiveContextEngine initialized")

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def on_zone_entry(self, person_id: str, zone_id: str,
                      context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate suggestions when a person enters a zone.

        Parameters
        ----------
        person_id : str
            HA person entity (e.g. person.alice).
        zone_id : str
            Zone entered (e.g. living_room, kitchen).
        context : dict, optional
            Extra context (time, devices, media state, etc.).

        Returns
        -------
        list[dict]
            Suggestions with type, message, action, priority.
            Empty list if suppressed (cooldown, quiet hours, etc.).
        """
        # Check quiet hours
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        local_hour = (now.hour + int(os.environ.get("TZ_OFFSET", "1"))) % 24
        if QUIET_START <= 23 and (local_hour >= QUIET_START or local_hour < QUIET_END):
            return []

        # Check cooldown
        key = f"{person_id}:{zone_id}"
        with self._lock:
            last = self._cooldowns.get(key, 0)
            if time.time() - last < ZONE_COOLDOWN_SECONDS:
                return []
            self._cooldowns[key] = time.time()

        # Build context
        ctx = context or {}
        ctx.setdefault("person_id", person_id)
        ctx.setdefault("zone_id", zone_id)
        ctx.setdefault("hour", local_hour)
        ctx.setdefault("is_evening", 18 <= local_hour <= 23)
        ctx.setdefault("is_morning", 6 <= local_hour <= 10)

        # Get media state for zone
        if self._media_mgr:
            try:
                media_state = self._media_mgr.get_zone_media_state(zone_id)
                ctx["media_state"] = media_state
            except Exception:
                pass

        # Get mood for zone
        if self._mood_svc:
            try:
                mood = self._mood_svc.get_zone_mood(zone_id)
                ctx["mood"] = mood
            except Exception:
                pass

        # Get household context
        if self._household:
            try:
                ctx["household"] = self._household.to_dict()
                ctx["children_home"] = self._household.is_any_child_home()
            except Exception:
                pass

        # Generate suggestions
        suggestions = []
        suggestions.extend(self._media_suggestions(ctx))
        suggestions.extend(self._comfort_suggestions(ctx))
        suggestions.extend(self._routine_suggestions(ctx))

        # Filter dismissed types
        person_dismissed = self._dismissed.get(person_id, set())
        suggestions = [s for s in suggestions
                       if s.get("type") not in person_dismissed]

        return suggestions

    # ------------------------------------------------------------------
    # Suggestion generators
    # ------------------------------------------------------------------

    def _media_suggestions(self, ctx: dict) -> List[Dict[str, Any]]:
        """Suggest media actions based on zone + time context."""
        suggestions = []
        zone = ctx.get("zone_id", "")
        hour = ctx.get("hour", 12)
        media = ctx.get("media_state", {})
        person = ctx.get("person_id", "")

        # Evening + living room + no media playing → suggest TV/music
        if ctx.get("is_evening") and "wohnzimmer" in zone.lower() or "living" in zone.lower():
            if media.get("state") != "playing":
                suggestions.append({
                    "type": "media_suggest",
                    "priority": "low",
                    "message": f"Du bist im Wohnzimmer. Soll ich Netflix auf dem Apple TV starten?",
                    "message_en": f"You're in the living room. Want me to start Netflix on Apple TV?",
                    "action": {
                        "service": "media_player.select_source",
                        "data": {"source": "Netflix"},
                    },
                    "zone_id": zone,
                    "dismissible": True,
                })

        # Music was playing in another zone → offer Musikwolke
        if self._media_mgr:
            sessions = self._media_mgr.get_musikwolke_sessions()
            for s in sessions:
                if s.get("person_id") == person and zone not in s.get("active_zones", []):
                    suggestions.append({
                        "type": "musikwolke_extend",
                        "priority": "low",
                        "message": f"Deine Musik laeuft noch. Soll ich sie hierher mitnehmen?",
                        "message_en": "Your music is still playing. Want me to bring it here?",
                        "action": {
                            "musikwolke_session": s.get("session_id"),
                            "extend_to_zone": zone,
                        },
                        "zone_id": zone,
                        "dismissible": True,
                    })

        return suggestions

    def _comfort_suggestions(self, ctx: dict) -> List[Dict[str, Any]]:
        """Suggest comfort adjustments."""
        suggestions = []
        zone = ctx.get("zone_id", "")
        mood = ctx.get("mood", {})

        # Low comfort score → suggest adjustment
        if mood.get("comfort", 0.5) < 0.3:
            suggestions.append({
                "type": "comfort_adjust",
                "priority": "medium",
                "message": "Der Komfort in diesem Raum ist niedrig. Soll ich die Beleuchtung anpassen?",
                "action": {"service": "light.turn_on",
                           "data": {"brightness_pct": 60}},
                "zone_id": zone,
                "dismissible": True,
            })

        return suggestions

    def _routine_suggestions(self, ctx: dict) -> List[Dict[str, Any]]:
        """Suggest based on known routines / time patterns."""
        suggestions = []
        zone = ctx.get("zone_id", "")
        hour = ctx.get("hour", 12)

        # Morning + kitchen → suggest coffee / morning routine
        if ctx.get("is_morning") and ("kueche" in zone.lower() or "kitchen" in zone.lower()):
            suggestions.append({
                "type": "morning_routine",
                "priority": "low",
                "message": "Guten Morgen! Soll ich die Morgenroutine starten?",
                "action": {"scene": "scene.morning_routine"},
                "zone_id": zone,
                "dismissible": True,
            })

        return suggestions

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    def deliver_suggestion(self, suggestion: dict,
                           method: str = "notification") -> dict:
        """Deliver a suggestion to the user.

        Methods: 'notification' (persistent), 'tts', 'chat'.
        """
        token = os.environ.get("SUPERVISOR_TOKEN", "")
        if not token:
            return {"ok": False, "error": "No SUPERVISOR_TOKEN"}

        headers = {"Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"}
        message = suggestion.get("message", "")

        if method == "tts":
            # Use TTS service
            zone = suggestion.get("zone_id", "")
            # Get media players in zone for TTS target
            tts_entity = None
            if self._media_mgr:
                players = self._media_mgr.get_zone_players(zone)
                if players:
                    tts_entity = players[0]["entity_id"]
            if tts_entity:
                try:
                    requests.post(
                        f"{SUPERVISOR_API}/services/tts/speak",
                        json={"entity_id": tts_entity,
                              "message": message,
                              "cache": True},
                        headers=headers, timeout=10,
                    )
                    return {"ok": True, "method": "tts", "entity": tts_entity}
                except Exception as exc:
                    _LOGGER.warning("TTS delivery failed: %s", exc)

        # Fallback: persistent notification
        try:
            requests.post(
                f"{SUPERVISOR_API}/services/notify/persistent_notification",
                json={"message": message, "title": "Styx"},
                headers=headers, timeout=10,
            )
            return {"ok": True, "method": "notification"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # User feedback
    # ------------------------------------------------------------------

    def dismiss_type(self, person_id: str, suggestion_type: str) -> None:
        """User dismisses a suggestion type -- don't show again."""
        self._dismissed.setdefault(person_id, set()).add(suggestion_type)
        _LOGGER.info("Person %s dismissed suggestion type: %s",
                      person_id, suggestion_type)

    def reset_dismissals(self, person_id: str) -> None:
        """Reset all dismissals for a person."""
        self._dismissed.pop(person_id, None)
