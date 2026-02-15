"""Multi-User Behavior Learning Module - Learns preferences per user."""

import time
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import numpy as np


class MultiUserLearner:
    """
    Learns and predicts behavior patterns for multiple users.
    
    Features:
    - Per-user preference learning
    - User presence detection
    - Preference adaptation
    - User clustering
    """
    
    def __init__(
        self,
        min_samples_per_user: int = 5,
        preference_decay_hours: float = 168,  # 1 week
        similarity_threshold: float = 0.7,
        enabled: bool = True,
    ):
        """
        Initialize the multi-user learner.
        
        Args:
            min_samples_per_user: Minimum observations per user
            preference_decay_hours: How long preferences persist
            similarity_threshold: Minimum similarity for user clustering
            enabled: Whether the learner is active
        """
        self.min_samples_per_user = min_samples_per_user
        self.preference_decay_hours = preference_decay_hours
        self.similarity_threshold = similarity_threshold
        self.enabled = enabled
        
        # User data storage
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
        self.user_behavior: Dict[str, List[Dict]] = defaultdict(list)
        self.user_presence: Dict[str, Dict[str, Any]] = {}
        
        # User clustering
        self.user_clusters: Dict[str, List[str]] = defaultdict(list)
        self._cluster_ready = False
        
        self._is_initialized = False
        
    def record_user_event(
        self,
        user_id: str,
        event_type: str,
        context: Dict[str, Any] = None,
        timestamp: Optional[float] = None,
    ) -> None:
        """
        Record an event for a specific user.
        
        Args:
            user_id: ID of the user
            event_type: Type of event (arrive, leave, setting_change, etc.)
            context: Event context (location, device, value, etc.)
            timestamp: When the event occurred
        """
        if not self.enabled:
            return
            
        if timestamp is None:
            timestamp = time.time()
            
        if context is None:
            context = {}
            
        event = {
            "event_type": event_type,
            "context": context,
            "timestamp": timestamp,
        }
        
        self.user_behavior[user_id].append(event)
        
        # Update presence
        if event_type == "arrive":
            self.user_presence[user_id] = {
                "present": True,
                "location": context.get("location"),
                "timestamp": timestamp,
            }
        elif event_type == "leave":
            self.user_presence[user_id] = {
                "present": False,
                "last_location": context.get("location"),
                "timestamp": timestamp,
            }
            
        # Learn preferences from setting changes
        if event_type == "setting_change":
            self._update_preference(user_id, context)
            
        self._is_initialized = True
        
    def _update_preference(
        self,
        user_id: str,
        context: Dict[str, Any],
    ) -> None:
        """Update user preferences from setting changes."""
        if "device" not in context or "value" not in context:
            return
            
        device = context["device"]
        value = context["value"]
        
        # Initialize user preferences if needed
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {
                "settings": defaultdict(list),
                "created_at": time.time(),
            }
            
        # Record preference
        preference = {
            "device": device,
            "value": value,
            "timestamp": time.time(),
        }
        
        self.user_preferences[user_id]["settings"][device].append(preference)
        
        # Keep only recent preferences (decay window)
        cutoff = time.time() - self.preference_decay_hours
        self.user_preferences[user_id]["settings"][device] = [
            p for p in self.user_preferences[user_id]["settings"][device]
            if p["timestamp"] >= cutoff
        ]
        
    def get_user_preference(
        self,
        user_id: str,
        device: str,
    ) -> Optional[float]:
        """
        Get predicted preference value for a device.
        
        Args:
            user_id: ID of the user
            device: Device identifier
            
        Returns:
            Predicted preference value or None
        """
        if not self._is_initialized:
            return None
            
        if user_id not in self.user_preferences:
            return None
            
        user_prefs = self.user_preferences[user_id]
        
        if device not in user_prefs["settings"]:
            return None
            
        preferences = user_prefs["settings"][device]
        
        if not preferences:
            return None
            
        # Return most recent value
        recent = sorted(preferences, key=lambda p: p["timestamp"], reverse=True)
        return recent[0]["value"]
        
    def get_user_status(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get current status for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            User status dictionary
        """
        presence = self.user_presence.get(user_id, {})
        
        # Calculate activity score
        behavior = self.user_behavior.get(user_id, [])
        if behavior:
            recent = [b for b in behavior if b["timestamp"] > time.time() - 3600]
            activity_score = min(1.0, len(recent) / 5)
        else:
            activity_score = 0.0
            
        return {
            "present": presence.get("present", False),
            "location": presence.get("location"),
            "last_seen": presence.get("timestamp"),
            "activity_score": activity_score,
            "event_count": len(behavior),
        }
        
    def find_similar_users(
        self,
        user_id: str,
    ) -> List[Tuple[str, float]]:
        """
        Find users with similar behavior patterns.
        
        Args:
            user_id: ID of the reference user
            
        Returns:
            List of (similar_user_id, similarity_score) tuples
        """
        if user_id not in self.user_preferences:
            return []
            
        user_prefs = self.user_preferences[user_id]
        
        if not user_prefs.get("settings"):
            return []
            
        similar_users = []
        
        for other_id, other_prefs in self.user_preferences.items():
            if other_id == user_id or not other_prefs.get("settings"):
                continue
                
            similarity = self._calculate_similarity(
                user_prefs["settings"],
                other_prefs["settings"],
            )
            
            if similarity >= self.similarity_threshold:
                similar_users.append((other_id, similarity))
                
        return sorted(similar_users, key=lambda x: x[1], reverse=True)
        
    def _calculate_similarity(
        self,
        settings1: Dict[str, List],
        settings2: Dict[str, List],
    ) -> float:
        """Calculate similarity between two users' settings."""
        all_devices = set(settings1.keys()) | set(settings2.keys())
        
        if not all_devices:
            return 0.0
            
        similarities = []
        
        for device in all_devices:
            prefs1 = settings1.get(device, [])
            prefs2 = settings2.get(device, [])
            
            if not prefs1 or not prefs2:
                continue
                
            # Calculate value similarity
            values1 = [p["value"] for p in prefs1]
            values2 = [p["value"] for p in prefs2]
            
            mean1 = np.mean(values1)
            mean2 = np.mean(values2)
            
            # Normalize difference
            max_val = max(values1 + values2)
            min_val = min(values1 + values2)
            range_val = max_val - min_val if max_val != min_val else 1.0
            
            diff = abs(mean1 - mean2) / range_val
            similarity = 1 - min(1.0, diff)
            
            similarities.append(similarity)
            
        if not similarities:
            return 0.0
            
        return np.mean(similarities)
        
    def get_cluster_for_user(
        self,
        user_id: str,
    ) -> Optional[str]:
        """
        Get the cluster ID for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Cluster ID or None
        """
        if not self._cluster_ready:
            self._build_clusters()
            
        for cluster_id, members in self.user_clusters.items():
            if user_id in members:
                return cluster_id
                
        return None
        
    def _build_clusters(self) -> None:
        """Build user clusters based on similarity."""
        if len(self.user_preferences) < 2:
            return
            
        # Initialize each user in their own cluster
        for user_id in self.user_preferences:
            self.user_clusters[f"cluster_{user_id}"] = [user_id]
            
        # Merge similar clusters
        user_ids = list(self.user_preferences.keys())
        merged = True
        
        while merged:
            merged = False
            cluster_ids = list(self.user_clusters.keys())
            
            for i, cluster1 in enumerate(cluster_ids):
                for cluster2 in cluster_ids[i + 1:]:
                    users1 = self.user_clusters[cluster1]
                    users2 = self.user_clusters[cluster2]
                    
                    # Check if any users are similar
                    for u1 in users1:
                        for u2 in users2:
                            similarity = self._calculate_user_cluster_similarity(
                                u1, u2
                            )
                            
                            if similarity >= self.similarity_threshold:
                                # Merge clusters
                                self.user_clusters[cluster1] = users1 + users2
                                del self.user_clusters[cluster2]
                                merged = True
                                break
                        if merged:
                            break
                if merged:
                    break
                    
        self._cluster_ready = True
        
    def _calculate_user_cluster_similarity(
        self,
        user1: str,
        user2: str,
    ) -> float:
        """Calculate similarity between two users."""
        if user1 not in self.user_preferences or user2 not in self.user_preferences:
            return 0.0
            
        return self._calculate_similarity(
            self.user_preferences[user1]["settings"],
            self.user_preferences[user2]["settings"],
        )
        
    def get_multi_user_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get summary of multi-user behavior.
        
        Args:
            hours: Time window
            
        Returns:
            Summary dictionary
        """
        cutoff = time.time() - (hours * 3600)
        
        user_summaries = {}
        for user_id, behavior in self.user_behavior.items():
            recent = [b for b in behavior if b["timestamp"] >= cutoff]
            
            if not recent:
                continue
                
            event_types = defaultdict(int)
            for event in recent:
                event_types[event["event_type"]] += 1
                
            user_summaries[user_id] = {
                "event_count": len(recent),
                "event_types": dict(event_types),
                "present": user_id in self.user_presence and self.user_presence[user_id].get("present", False),
            }
            
        return {
            "total_users": len(user_summaries),
            "present_users": sum(1 for s in user_summaries.values() if s["present"]),
            "user_summaries": user_summaries,
            "clusters": dict(self.user_clusters),
        }
        
    def reset(self) -> None:
        """Reset the learner state."""
        self.user_preferences.clear()
        self.user_behavior.clear()
        self.user_presence.clear()
        self.user_clusters.clear()
        self._cluster_ready = False
        self._is_initialized = False


class ContextAwareMultiUserLearner(MultiUserLearner):
    """
    Extended multi-user learner with context awareness.
    
    Considers spatial context, time patterns,
    and shared preferences for better learning.
    """
    
    def __init__(
        self,
        spatial_threshold_meters: float = 10.0,
        **kwargs,
    ):
        """
        Initialize context-aware multi-user learner.
        
        Args:
            spatial_threshold_meters: Distance threshold for location matching
            **kwargs: Arguments for parent MultiUserLearner
        """
        super().__init__(**kwargs)
        self.spatial_threshold = spatial_threshold_meters
        self.location_history: Dict[str, List[Dict]] = defaultdict(list)
        self.shared_preferences: Dict[str, Any] = {}
        
    def record_location(
        self,
        user_id: str,
        latitude: float,
        longitude: float,
        timestamp: Optional[float] = None,
    ) -> None:
        """
        Record user location.
        
        Args:
            user_id: ID of the user
            latitude: GPS latitude
            longitude: GPS longitude
            timestamp: When location was recorded
        """
        if timestamp is None:
            timestamp = time.time()
            
        self.location_history[user_id].append({
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": timestamp,
        })
        
    def get_user_location(
        self,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get current location for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Location dictionary or None
        """
        if user_id not in self.location_history:
            return None
            
        history = self.location_history[user_id]
        
        if not history:
            return None
            
        # Return most recent
        return sorted(history, key=lambda x: x["timestamp"], reverse=True)[0]
        
    def are_users_together(
        self,
        user_ids: List[str],
        time_window_minutes: int = 10,
    ) -> bool:
        """
        Check if multiple users are at the same location.
        
        Args:
            user_ids: List of user IDs
            time_window_minutes: Time window to check
            
        Returns:
            True if users are together
        """
        if len(user_ids) < 2:
            return False
            
        cutoff = time.time() - (time_window_minutes * 60)
        
        # Get recent locations for each user
        recent_locations = {}
        for user_id in user_ids:
            history = self.location_history.get(user_id, [])
            recent = [
                loc for loc in history
                if loc["timestamp"] >= cutoff
            ]
            
            if recent:
                recent_locations[user_id] = recent[-1]
                
        if len(recent_locations) < 2:
            return False
            
        # Check distance between users
        locations = list(recent_locations.values())
        
        for i, loc1 in enumerate(locations):
            for loc2 in locations[i + 1:]:
                distance = self._calculate_distance(
                    loc1["latitude"],
                    loc1["longitude"],
                    loc2["latitude"],
                    loc2["longitude"],
                )
                
                if distance > self.spatial_threshold:
                    return False
                    
        return True
        
    def _calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Calculate distance between two GPS coordinates."""
        # Simple Euclidean distance (for demonstration)
        # In production, use Haversine formula
        return np.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) * 111000  # Convert to meters
