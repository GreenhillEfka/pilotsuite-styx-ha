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

if TYPE_CHECKING:
    from .user_preference_module import UserPreferenceModule

logger = logging.getLogger(__name__)


class MoodContextModule:
    """Async mood context tracker from Core API."""
    
    def __init__(self, hass: HomeAssistant, core_api_base_url: str, api_token: str):
        """Initialize mood context module.
        
        Args:
            hass: Home Assistant instance
            core_api_base_url: Base URL of Core API (e.g., http://localhost:8099)
            api_token: Auth token for Core API
        """
        self.hass = hass
        self.core_api_base_url = core_api_base_url
        self.api_token = api_token
        
        self._zone_moods: Dict[str, Dict[str, Any]] = {}
        self._last_update: Optional[datetime] = None
        self._update_task: Optional[asyncio.Task] = None
        self._polling_interval_seconds = 30  # Update every 30s
        self._enabled = True
        
        logger.info(f"MoodContextModule initialized (Core: {core_api_base_url})")
    
    async def async_start(self) -> None:
        """Start polling Core mood API."""
        if self._update_task:
            return
        
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
    
    async def _polling_loop(self) -> None:
        """Continuous polling loop."""
        first_run = True
        while self._enabled:
            try:
                if first_run:
                    # Initial delay to let Core start
                    await asyncio.sleep(10)
                    first_run = False
                else:
                    await asyncio.sleep(self._polling_interval_seconds)
                
                if self._enabled:
                    await self._fetch_moods()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"MoodContextModule polling error: {e}")
    
    async def _fetch_moods(self) -> None:
        """Fetch mood data from Core API."""
        try:
            session = async_get_clientsession(self.hass)
            url = f"{self.core_api_base_url}/api/v1/mood"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"Core mood API returned {resp.status}")
                    return
                
                data = await resp.json()
                moods = data.get("moods", {})
                
                # Update local cache
                self._zone_moods = moods
                self._last_update = datetime.now()
                
                logger.debug(f"Updated moods for {len(moods)} zones")
        
        except asyncio.TimeoutError:
            logger.warning("Core mood API timeout")
        except Exception as e:
            logger.error(f"Error fetching moods: {e}")
    
    def get_zone_mood(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """Get mood snapshot for a specific zone."""
        return self._zone_moods.get(zone_id)

    def _clamp(self, value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    def _get_user_preference(self, user_id: str, zone_id: str) -> Optional[Dict[str, Any]]:
        if not user_id or not zone_id:
            return None

        try:
            from .user_preference_module import UserPreferenceModule  # type: ignore
        except Exception:  # noqa: BLE001
            return None

        dom = self.hass.data.get(DOMAIN, {})
        module = dom.get("user_preference_module")
        if isinstance(module, UserPreferenceModule):
            return module.get_user_preference(user_id, zone_id)

        # Fallback: search entry data for a registered module.
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
        
        # Suppress if entertai ment is happening
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
