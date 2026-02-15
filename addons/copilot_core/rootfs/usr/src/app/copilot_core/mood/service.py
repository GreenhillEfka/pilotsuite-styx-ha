"""
Mood Service — Per-Zone Comfort/Frugality/Joy Scoring

Synthesizes MediaContext and Habitus signals to provide context-aware
mood metrics that inform automation suggestion quality and relevance.

Mood State:
- comfort: (0–1) how comfortable the zone is (temp, light, activity)
- frugality: (0–1) user preference for resource efficiency (time-of-day, patterns)
- joy: (0–1) entertainment/enjoyment level (music, TV, social context)

Each zone maintains independent mood state updated every 30s or on signal changes.
"""

from __future__ import annotations

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ZoneMoodSnapshot:
    """Single zone's mood state at a point in time."""
    
    zone_id: str
    timestamp: float
    comfort: float  # 0–1, how comfortable the zone feels
    frugality: float  # 0–1, resource-efficiency preference
    joy: float  # 0–1, entertainment/enjoyment level
    
    # Metadata for debugging/explanation
    media_active: bool  # music or TV playing
    media_primary: Optional[str]  # now-playing title
    time_of_day: str  # "morning", "afternoon", "evening", "night"
    occupancy_level: str  # "empty", "low", "medium", "high"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        d = asdict(self)
        d["timestamp"] = int(d["timestamp"])
        return d


class MoodService:
    """Aggregated mood scoring from MediaContext and Habitus signals."""
    
    def __init__(self):
        """Initialize mood service."""
        self._zone_moods: Dict[str, ZoneMoodSnapshot] = {}
        self._last_update: float = 0
        self._update_interval_seconds = 30
        
        logger.info("MoodService initialized")
    
    def update_from_media_context(self, media_snapshot: Dict[str, Any]) -> None:
        """Update mood based on MediaContext snapshot.
        
        Args:
            media_snapshot: {
                "music_active": bool,
                "tv_active": bool,
                "primary_player": {"entity_id", "state", "media_title", "area"},
                "players": [...]
            }
        """
        if not media_snapshot:
            return
        
        # Aggregate music + TV signals
        music_active = media_snapshot.get("music_active", False)
        tv_active = media_snapshot.get("tv_active", False)
        media_active = music_active or tv_active
        
        primary = media_snapshot.get("primary_player")
        if primary:
            area_id = primary.get("area", "unknown")
            media_title = primary.get("media_title", "")
            
            # Boost joy when music is active
            joy_boost = 0.7 if music_active else (0.3 if tv_active else 0.0)
            
            # Update zone mood
            self._update_zone_mood(
                area_id,
                joy=joy_boost,
                media_active=media_active,
                media_primary=media_title
            )
    
    def update_from_habitus(self, habitus_context: Dict[str, Any]) -> None:
        """Update mood based on Habitus patterns.
        
        Args:
            habitus_context: {
                "time_of_day": "morning|afternoon|evening|night",
                "zone_activity_level": "low|medium|high",
                "recent_patterns": [...],
                "frugality_score": 0–1
            }
        """
        if not habitus_context:
            return
        
        time_of_day = habitus_context.get("time_of_day", "afternoon")
        frugality = habitus_context.get("frugality_score", 0.5)
        occupancy = habitus_context.get("zone_activity_level", "low")
        
        # Morning/evening = higher comfort preference
        # Night = lower comfort (sleeping), higher frugality
        comfort_by_time = {
            "morning": 0.6,
            "afternoon": 0.5,
            "evening": 0.8,
            "night": 0.2
        }
        comfort = comfort_by_time.get(time_of_day, 0.5)
        
        # High occupancy + evening = high joy baseline
        joy_baseline = 0.4 if occupancy == "high" else 0.2
        if time_of_day in ("evening", "night"):
            joy_baseline += 0.2
        
        # Update all known zones with time-of-day context
        for zone_id in self._zone_moods.keys():
            self._update_zone_mood(
                zone_id,
                comfort=comfort,
                frugality=frugality,
                joy=joy_baseline,
                time_of_day=time_of_day,
                occupancy_level=occupancy
            )
    
    def _update_zone_mood(
        self,
        zone_id: str,
        comfort: Optional[float] = None,
        frugality: Optional[float] = None,
        joy: Optional[float] = None,
        media_active: Optional[bool] = None,
        media_primary: Optional[str] = None,
        time_of_day: Optional[str] = None,
        occupancy_level: Optional[str] = None,
    ) -> None:
        """Update a single zone's mood, preserving existing values."""
        
        current = self._zone_moods.get(zone_id)
        if not current:
            # Initialize new zone
            current = ZoneMoodSnapshot(
                zone_id=zone_id,
                timestamp=time.time(),
                comfort=0.5,
                frugality=0.5,
                joy=0.5,
                media_active=False,
                media_primary=None,
                time_of_day="afternoon",
                occupancy_level="low"
            )
        
        # Update with new values (exponential smoothing for continuity)
        alpha = 0.3  # smoothing factor
        
        if comfort is not None:
            current.comfort = current.comfort * (1 - alpha) + comfort * alpha
        if frugality is not None:
            current.frugality = current.frugality * (1 - alpha) + frugality * alpha
        if joy is not None:
            current.joy = current.joy * (1 - alpha) + joy * alpha
        
        if media_active is not None:
            current.media_active = media_active
        if media_primary is not None:
            current.media_primary = media_primary
        if time_of_day is not None:
            current.time_of_day = time_of_day
        if occupancy_level is not None:
            current.occupancy_level = occupancy_level
        
        current.timestamp = time.time()
        self._zone_moods[zone_id] = current
        logger.debug(f"Updated {zone_id} mood: comfort={current.comfort:.2f}, "
                    f"frugality={current.frugality:.2f}, joy={current.joy:.2f}")
    
    def get_zone_mood(self, zone_id: str) -> Optional[ZoneMoodSnapshot]:
        """Get current mood snapshot for a zone."""
        return self._zone_moods.get(zone_id)
    
    def get_all_zone_moods(self) -> Dict[str, ZoneMoodSnapshot]:
        """Get all current zone moods."""
        return dict(self._zone_moods)
    
    def should_suppress_energy_saving(self, zone_id: str) -> bool:
        """Check if energy-saving automation should be suppressed in this zone.
        
        Returns True if user is likely enjoying entertainment (joy > 0.6)
        or if comfort is priority (comfort > 0.7).
        """
        mood = self.get_zone_mood(zone_id)
        if not mood:
            return False
        
        # Suppress energy-saving during entertainment
        if mood.joy > 0.6:
            return True
        
        # Suppress if comfort is prioritized
        if mood.comfort > 0.7 and mood.frugality < 0.5:
            return True
        
        return False
    
    def get_suggestion_relevance_multiplier(self, zone_id: str, suggestion_type: str) -> float:
        """Get a multiplier for suggestion relevance based on current mood.
        
        Used to weight candidate suggestions:
        - energy_saving: multiplied by (1 - joy) * frugality
        - comfort: multiplied by comfort
        - entertainment: multiplied by joy
        
        Args:
            zone_id: Target zone
            suggestion_type: "energy_saving", "comfort", "entertainment", "security"
        
        Returns:
            0–1 multiplier for suggestion confidence/relevance
        """
        mood = self.get_zone_mood(zone_id)
        if not mood:
            return 1.0  # Default: fully relevant if no mood data
        
        if suggestion_type == "energy_saving":
            # Less relevant if joy is high or frugality is low
            return max(0.0, (1 - mood.joy) * mood.frugality)
        
        elif suggestion_type == "comfort":
            # More relevant if comfort is priority
            return mood.comfort
        
        elif suggestion_type == "entertainment":
            # More relevant if joy is high
            return mood.joy
        
        elif suggestion_type == "security":
            # Security is always relevant (independent of mood)
            return 1.0
        
        # Default
        return 1.0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary stats across all zones."""
        if not self._zone_moods:
            return {
                "zones": 0,
                "average_comfort": 0.5,
                "average_frugality": 0.5,
                "average_joy": 0.5,
                "zones_with_media": 0
            }
        
        moods = list(self._zone_moods.values())
        avg_comfort = sum(m.comfort for m in moods) / len(moods)
        avg_frugality = sum(m.frugality for m in moods) / len(moods)
        avg_joy = sum(m.joy for m in moods) / len(moods)
        media_zones = sum(1 for m in moods if m.media_active)
        
        return {
            "zones": len(moods),
            "average_comfort": round(avg_comfort, 2),
            "average_frugality": round(avg_frugality, 2),
            "average_joy": round(avg_joy, 2),
            "zones_with_media": media_zones,
            "zone_breakdown": {
                zone_id: mood.to_dict()
                for zone_id, mood in self._zone_moods.items()
            }
        }
