"""
Mood Context Module — HA Integration's consumer of Core Mood service.

Polls Core mood API and maintains local cache of zone mood states.
Used to contextualize automation suggestions (don't suggest energy-saving during entertainment).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING, Union

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ...const import DOMAIN
from ...connection_config import resolve_core_connection
from .module import CopilotModule, ModuleContext

if TYPE_CHECKING:
    from .user_preference_module import UserPreferenceModule

logger = logging.getLogger(__name__)


class MoodContextModule(CopilotModule):
    """Async mood context tracker from Core API with local persistence."""

    def __init__(
        self,
        hass: HomeAssistant | None = None,
        core_api_base_url: str | None = None,
        api_token: str | None = None,
    ) -> None:
        """Initialize mood context module.

        Args:
            hass: Home Assistant instance
            core_api_base_url: Base URL of Core API (e.g., http://localhost:8909)
            api_token: Auth token for Core API
        """
        self.hass = hass
        self._entry_id: str | None = None
        self.core_api_base_url = str(core_api_base_url or "")
        self.api_token = str(api_token or "")

        self._zone_moods: Dict[str, Dict[str, Any]] = {}
        self._last_update: Optional[datetime] = None
        self._update_task: Optional[asyncio.Task] = None
        self._polling_interval_seconds = 30  # Update every 30s
        self._enabled = True
        self._using_cache = False  # True when serving from HA local cache

        logger.info("MoodContextModule initialized (Core: %s)", core_api_base_url)

    @property
    def name(self) -> str:
        return "mood_context"

    async def async_start(self) -> None:
        """Start polling Core mood API. Pre-loads from local cache first."""
        if self.hass is None:
            return
        if self._update_task:
            return

        # Pre-load from HA persistent cache so mood context is available immediately
        try:
            from ...mood_store import async_load_moods
            cached = await async_load_moods(self.hass)
            if cached:
                self._zone_moods = cached
                self._using_cache = True
                logger.info("MoodContextModule: Pre-loaded %d zones from HA cache", len(cached))
        except Exception:
            logger.debug("MoodContextModule: No cached moods available", exc_info=True)

        logger.info("MoodContextModule: Starting polling")
        self._update_task = asyncio.create_task(self._polling_loop())
    
    async def async_stop(self) -> None:
        """Stop polling Core mood API."""
        self._enabled = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None
        
        logger.info("MoodContextModule: Stopped")

    async def async_setup_entry(self, ctx: ModuleContext) -> bool:
        """Runtime-compatible module setup."""
        host, port, token = resolve_core_connection(ctx.entry)
        self.hass = ctx.hass
        self._entry_id = ctx.entry.entry_id
        self.core_api_base_url = f"http://{host}:{port}"
        self.api_token = token
        self._enabled = True

        dom = ctx.hass.data.setdefault(DOMAIN, {})
        entry_data = dom.setdefault(ctx.entry.entry_id, {})
        if isinstance(entry_data, dict):
            entry_data["mood_context_module"] = self

        await self.async_start()
        return True

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Runtime-compatible module unload."""
        await self.async_stop()
        dom = ctx.hass.data.get(DOMAIN, {})
        entry_data = dom.get(ctx.entry.entry_id, {})
        if isinstance(entry_data, dict):
            entry_data.pop("mood_context_module", None)
        self.hass = None
        self._entry_id = None
        return True
    
    async def _polling_loop(self) -> None:
        """Continuous polling loop with exponential backoff on errors."""
        first_run = True
        consecutive_errors = 0
        base_interval = self._polling_interval_seconds
        max_backoff = 300  # Max 5 minutes backoff
        
        while self._enabled:
            try:
                if first_run:
                    # Initial delay to let Core start
                    await asyncio.sleep(10)
                    first_run = False
                
                if self._enabled:
                    await self._fetch_moods()
                    # Reset error count on success
                    consecutive_errors = 0
                
                # Normal interval between polls
                await asyncio.sleep(base_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"MoodContextModule polling error ({consecutive_errors}x): {e}")
                
                # Exponential backoff
                backoff = min(base_interval * (2 ** consecutive_errors), max_backoff)
                logger.debug(f"Backing off for {backoff}s before retry")
                await asyncio.sleep(backoff)
    
    async def _fetch_moods(self) -> None:
        """Fetch mood data from Core API and persist to HA cache."""
        try:
            session = async_get_clientsession(self.hass)
            url = f"{self.core_api_base_url}/api/v1/mood"
            headers = {"Authorization": f"Bearer {self.api_token}"}

            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning("Core mood API returned %s", resp.status)
                    return

                data = await resp.json()
                moods = data.get("moods", {})

                # Update in-memory cache
                self._zone_moods = moods
                self._last_update = datetime.now()
                self._using_cache = False

                # Persist to HA local storage for restart resilience
                try:
                    from ...mood_store import async_save_moods
                    await async_save_moods(self.hass, moods)
                except Exception:
                    logger.debug("Failed to persist moods to HA cache", exc_info=True)

                logger.debug("Updated moods for %d zones", len(moods))

        except asyncio.TimeoutError:
            logger.warning("Core mood API timeout — using cached moods")
        except Exception as e:
            logger.error("Error fetching moods: %s", e)
    
    def get_zone_mood(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """Get mood snapshot for a specific zone."""
        return self._zone_moods.get(zone_id)

    def _clamp(self, value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    def _get_user_preference(self, user_id: str, zone_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get user preference from UserPreferenceModule.
        
        Args:
            user_id: The user ID to get preferences for
            zone_id: Optional zone ID for zone-specific preferences
            
        Returns:
            User preferences dict with bias values, or None if not found
        """
        if not user_id:
            return None

        # Use cached import to avoid repeated imports
        if not hasattr(self, "_user_pref_module_class"):
            try:
                from .user_preference_module import UserPreferenceModule
                self._user_pref_module_class = UserPreferenceModule
            except ImportError as e:
                logger.debug(f"Could not import UserPreferenceModule: {e}")
                return None
        
        UserPreferenceModule = self._user_pref_module_class
        
        dom = self.hass.data.get(DOMAIN, {})
        
        # Try to get module directly from hass.data
        module = dom.get("user_preference_module")
        if isinstance(module, UserPreferenceModule):
            return module.get_user_preference(user_id, zone_id)

        # Fallback: search entry data for a registered module
        for entry_data in dom.values():
            if isinstance(entry_data, dict):
                candidate = entry_data.get("user_preference_module")
                if isinstance(candidate, UserPreferenceModule):
                    return candidate.get_user_preference(user_id, zone_id)

        return None

    def get_mood_for_user(self, user_id: str, zone_id: str) -> Optional[Dict[str, Any]]:
        """Get user-weighted mood for a zone.

        Falls back to zone mood if no user preference exists.
        """
        mood = self.get_zone_mood(zone_id)
        if not mood:
            return None

        pref = self._get_user_preference(user_id, zone_id)
        if not pref:
            return dict(mood)

        comfort = float(mood.get("comfort", 0.5))
        frugality = float(mood.get("frugality", 0.5))
        joy = float(mood.get("joy", 0.5))

        comfort_bias = float(pref.get("comfort_bias", 0.0))
        frugality_bias = float(pref.get("frugality_bias", 0.0))
        joy_bias = float(pref.get("joy_bias", 0.0))

        weighted = dict(mood)
        weighted["comfort"] = self._clamp(comfort + comfort_bias)
        weighted["frugality"] = self._clamp(frugality + frugality_bias)
        weighted["joy"] = self._clamp(joy + joy_bias)
        return weighted
    
    def get_all_moods(self) -> Dict[str, Dict[str, Any]]:
        """Get all cached zone moods."""
        return dict(self._zone_moods)
    
    def should_suppress_energy_saving(self, zone_id: str) -> bool:
        """Check if energy-saving should be suppressed in this zone.
        
        Returns True if:
        - User is likely enjoying entertainment (joy > 0.6)
        - Comfort is prioritized over frugality (comfort > 0.7 and frugality < 0.5)
        """
        mood = self.get_zone_mood(zone_id)
        if not mood:
            return False  # No mood data, allow energy-saving
        
        # Suppress if entertainment is happening
        if mood.get("joy", 0) > 0.6:
            return True
        
        # Suppress if comfort is prioritized
        comfort = mood.get("comfort", 0.5)
        frugality = mood.get("frugality", 0.5)
        if comfort > 0.7 and frugality < 0.5:
            return True
        
        return False
    
    def get_suggestion_context(self, zone_id: str) -> Dict[str, Any]:
        """Get mood context for suggestion weighting.
        
        Returns a dict with suggestion type → relevance multiplier.
        """
        mood = self.get_zone_mood(zone_id)
        if not mood:
            return {
                "energy_saving": 1.0,
                "comfort": 1.0,
                "entertainment": 1.0,
                "security": 1.0,
            }
        
        joy = mood.get("joy", 0.5)
        comfort = mood.get("comfort", 0.5)
        frugality = mood.get("frugality", 0.5)
        
        return {
            "energy_saving": max(0.0, (1 - joy) * frugality),
            "comfort": comfort,
            "entertainment": joy,
            "security": 1.0,  # Always relevant
            "raw_mood": {
                "comfort": round(comfort, 2),
                "frugality": round(frugality, 2),
                "joy": round(joy, 2),
                "media_active": mood.get("media_active", False),
                "time_of_day": mood.get("time_of_day", "unknown"),
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all zone moods."""
        moods = list(self._zone_moods.values())
        if not moods:
            return {
                "zones_tracked": 0,
                "last_update": None,
                "average_comfort": 0.5,
                "average_frugality": 0.5,
                "average_joy": 0.5,
            }
        
        avg_comfort = sum(m.get("comfort", 0.5) for m in moods) / len(moods)
        avg_frugality = sum(m.get("frugality", 0.5) for m in moods) / len(moods)
        avg_joy = sum(m.get("joy", 0.5) for m in moods) / len(moods)
        
        return {
            "zones_tracked": len(moods),
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "average_comfort": round(avg_comfort, 2),
            "average_frugality": round(avg_frugality, 2),
            "average_joy": round(avg_joy, 2),
            "zones_with_media": sum(1 for m in moods if m.get("media_active", False)),
        }
    
    # ===== Character System Integration =====
    
    def get_character_mood_context(self, zone_id: str, character_id: Optional[str] = None) -> Dict[str, Any]:
        """Get mood context formatted for Character System consumption.
        
        Args:
            zone_id: The zone to get mood context for
            character_id: Optional character ID for user-specific mood weighting
            
        Returns:
            Dict with mood values formatted for character responses
        """
        # Get base mood for zone
        if character_id:
            mood = self.get_mood_for_user(character_id, zone_id)
        else:
            mood = self.get_zone_mood(zone_id)
        
        if not mood:
            return {
                "zone_active": False,
                "energy_level": "neutral",
                "preferred_suggestions": [],
                "mood_summary": "unknown",
            }
        
        joy = mood.get("joy", 0.5)
        comfort = mood.get("comfort", 0.5)
        frugality = mood.get("frugality", 0.5)
        media_active = mood.get("media_active", False)
        time_of_day = mood.get("time_of_day", "unknown")
        
        # Determine energy level
        if media_active or joy > 0.6:
            energy_level = "high"
        elif joy < 0.3 and comfort < 0.4:
            energy_level = "low"
        else:
            energy_level = "neutral"
        
        # Determine preferred suggestion types
        preferred = []
        if joy > 0.5:
            preferred.append("entertainment")
        if comfort > 0.6:
            preferred.append("comfort")
        if frugality > 0.6 and joy < 0.4:
            preferred.append("energy_saving")
        preferred.append("security")  # Always relevant
        
        # Create mood summary for character
        if joy > 0.7:
            mood_summary = "happy"
        elif joy < 0.3:
            mood_summary = "low"
        elif comfort > 0.7:
            mood_summary = "relaxed"
        elif frugality > 0.7:
            mood_summary = "focused"
        else:
            mood_summary = "neutral"
        
        return {
            "zone_active": media_active or joy > 0.3,
            "energy_level": energy_level,
            "preferred_suggestions": preferred,
            "mood_summary": mood_summary,
            "values": {
                "joy": round(joy, 2),
                "comfort": round(comfort, 2),
                "frugality": round(frugality, 2),
            },
            "context": {
                "media_active": media_active,
                "time_of_day": time_of_day,
            },
        }
    
    def should_character_speak(self, zone_id: str, character_id: Optional[str] = None) -> bool:
        """Determine if the character should initiate a conversation in this zone.
        
        Args:
            zone_id: The zone to check
            character_id: Optional character/user ID for preferences
            
        Returns:
            True if character should speak, False otherwise
        """
        context = self.get_character_mood_context(zone_id, character_id)
        
        # Don't interrupt high-energy activities
        if context.get("energy_level") == "high" and context.get("context", {}).get("media_active"):
            return False
        
        # Check if zone is active (someone present)
        if not context.get("zone_active", False):
            return False
        
        return True
    
    def get_conversation_starter(self, zone_id: str, character_id: Optional[str] = None) -> Optional[str]:
        """Get an appropriate conversation starter based on current mood.
        
        Args:
            zone_id: The zone to get context for
            character_id: Optional character/user ID for personalized starters
            
        Returns:
            A suggestion type string or None if no good starter available
        """
        context = self.get_character_mood_context(zone_id, character_id)
        
        if not context.get("zone_active"):
            return None
        
        mood_summary = context.get("mood_summary", "neutral")
        
        # Return suggestion types based on mood
        starters = {
            "happy": "entertainment",
            "relaxed": "comfort",
            "focused": "energy_saving",
            "low": "comfort",
            "neutral": None,  # No specific starter
        }
        
        return starters.get(mood_summary)
