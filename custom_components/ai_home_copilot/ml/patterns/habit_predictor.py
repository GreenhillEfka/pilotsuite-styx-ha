"""Habit Prediction Module - Predicts user routines and patterns."""

import time
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import numpy as np
from datetime import datetime, timedelta


class HabitPredictor:
    """
    Predicts user habits and routines based on historical patterns.
    
    Features:
    - Time-based pattern detection
    - Device usage prediction
    - Activity sequence modeling
    - Confidence scoring
    """
    
    def __init__(
        self,
        min_samples_per_pattern: int = 3,
        prediction_horizon_hours: int = 12,
        confidence_threshold: float = 0.7,
        enabled: bool = True,
    ):
        """
        Initialize the habit predictor.
        
        Args:
            min_samples_per_pattern: Minimum occurrences to recognize a pattern
            prediction_horizon_hours: How far ahead to predict
            confidence_threshold: Minimum confidence for predictions
            enabled: Whether the predictor is active
        """
        self.min_samples_per_pattern = min_samples_per_pattern
        self.prediction_horizon_hours = prediction_horizon_hours
        self.confidence_threshold = confidence_threshold
        self.enabled = enabled
        
        # Pattern storage
        self.device_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self.sequence_patterns: Dict[str, List[List[str]]] = defaultdict(list)
        self.time_patterns: Dict[str, Dict[int, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        # Statistics
        self.pattern_confidence: Dict[str, float] = {}
        self.last_prediction_time: Dict[str, float] = {}
        
        self._is_initialized = False
        
    def observe(
        self,
        device_id: str,
        event_type: str,
        timestamp: Optional[float] = None,
        context: Dict[str, Any] = None,
    ) -> None:
        """
        Observe a device event and update patterns.
        
        Args:
            device_id: ID of the device
            event_type: Type of event (on, off, state_change, etc.)
            timestamp: When the event occurred
            context: Additional context (location, user, etc.)
        """
        if not self.enabled:
            return
            
        if timestamp is None:
            timestamp = time.time()
            
        if context is None:
            context = {}
            
        # Update device patterns
        self._update_device_pattern(device_id, event_type, timestamp)
        
        # Update time patterns
        self._update_time_pattern(device_id, event_type, timestamp)
        
        # Update sequence patterns if we have device chain
        if context.get("device_chain"):
            self._update_sequence_pattern(
                device_id,
                context["device_chain"],
                timestamp,
            )
        
        self._is_initialized = True
        
    def _update_device_pattern(
        self,
        device_id: str,
        event_type: str,
        timestamp: float,
    ) -> None:
        """Update device event pattern."""
        self.device_patterns[device_id].append({
            "event_type": event_type,
            "timestamp": timestamp,
        })
        
        # Keep only recent events (30 days)
        cutoff = timestamp - (30 * 24 * 3600)
        self.device_patterns[device_id] = [
            p for p in self.device_patterns[device_id]
            if p["timestamp"] >= cutoff
        ]
        
    def _update_time_pattern(
        self,
        device_id: str,
        event_type: str,
        timestamp: float,
    ) -> None:
        """Update time-based patterns."""
        dt = datetime.fromtimestamp(timestamp)
        hour = dt.hour
        day_of_week = dt.weekday()
        
        pattern_key = f"{device_id}_{event_type}"
        self.time_patterns[pattern_key][hour].append(timestamp)
        self.time_patterns[pattern_key][f"day_{day_of_week}"].append(timestamp)
        
    def _update_sequence_pattern(
        self,
        device_id: str,
        device_chain: List[str],
        timestamp: float,
    ) -> None:
        """Update sequence patterns for device chains."""
        pattern_key = device_chain[0]  # Start device as key
        
        # Limit sequence length
        sequence = device_chain[:10]
        self.sequence_patterns[pattern_key].append(sequence)
        
        # Keep only recent sequences
        cutoff = timestamp - (30 * 24 * 3600)
        self.sequence_patterns[pattern_key] = [
            seq for seq in self.sequence_patterns[pattern_key]
            if self._sequence_timestamp(seq, timestamp) >= cutoff
        ]
        
    def _sequence_timestamp(
        self,
        sequence: List[str],
        current_time: float,
    ) -> float:
        """Get approximate timestamp for a sequence."""
        # Simple heuristic: sequence happened progressively over last minute
        return current_time - (len(sequence) * 5)
        
    def predict(
        self,
        device_id: str,
        event_type: str,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Predict the likelihood of a pattern occurring.
        
        Args:
            device_id: ID of the device
            event_type: Type of event to predict
            timestamp: When the event would occur
            
        Returns:
            Prediction dictionary with confidence and details
        """
        if not self.enabled or not self._is_initialized:
            return {
                "predicted": False,
                "confidence": 0.0,
                "details": {},
            }
            
        if timestamp is None:
            timestamp = time.time()
            
        pattern_key = f"{device_id}_{event_type}"
        
        # Get prediction
        prediction = self._predict_pattern(pattern_key, timestamp)
        
        return {
            "predicted": prediction["predicted"],
            "confidence": prediction["confidence"],
            "details": prediction["details"],
            "device_id": device_id,
            "event_type": event_type,
        }
        
    def _predict_pattern(
        self,
        pattern_key: str,
        timestamp: float,
    ) -> Dict[str, Any]:
        """Predict pattern occurrence."""
        patterns = self.time_patterns.get(pattern_key, {})
        dt = datetime.fromtimestamp(timestamp)
        hour = dt.hour
        day_of_week = dt.weekday()
        
        hour_times = patterns.get(hour, [])
        day_times = patterns.get(f"day_{day_of_week}", [])
        
        # Calculate confidence based on historical occurrences
        total_samples = len(hour_times) + len(day_times)
        
        if total_samples < self.min_samples_per_pattern:
            return {
                "predicted": False,
                "confidence": 0.0,
                "details": {
                    "samples": total_samples,
                    "min_required": self.min_samples_per_pattern,
                },
            }
            
        # Calculate time-based confidence
        hour_confidence = self._calculate_time_confidence(hour_times, hour)
        day_confidence = self._calculate_time_confidence(day_times, day_of_week)
        
        # Weight by recency
        hour_weight = 0.6
        day_weight = 0.4
        confidence = hour_weight * hour_confidence + day_weight * day_confidence
        
        self.pattern_confidence[pattern_key] = confidence
        
        return {
            "predicted": confidence >= self.confidence_threshold,
            "confidence": confidence,
            "details": {
                "samples": total_samples,
                "hour_samples": len(hour_times),
                "day_samples": len(day_times),
                "hour_confidence": hour_confidence,
                "day_confidence": day_confidence,
            },
        }
        
    def _calculate_time_confidence(
        self,
        times: List[float],
        target_time: int,
    ) -> float:
        """Calculate confidence based on historical timing."""
        if not times:
            return 0.0
            
        # Calculate time distribution
        recent_times = [t for t in times if t > time.time() - (7 * 24 * 3600)]
        
        if not recent_times:
            return 0.0
            
        # Calculate variance
        times_array = np.array(recent_times)
        variance = np.var(times_array)
        
        # Higher confidence for consistent timing
        if variance < 3600:  # Less than 1 hour variance
            return 0.9
        elif variance < 7200:  # Less than 2 hours variance
            return 0.7
        elif variance < 14400:  # Less than 4 hours variance
            return 0.5
        else:
            return 0.3
            
    def predict_sequence(
        self,
        start_device: str,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Predict device sequence based on learned patterns.
        
        Args:
            start_device: Starting device
            timestamp: When the sequence would start
            
        Returns:
            Sequence prediction
        """
        if not self.enabled or not self._is_initialized:
            return {"predicted": False, "sequence": [], "confidence": 0.0}
            
        sequences = self.sequence_patterns.get(start_device, [])
        
        if not sequences:
            return {"predicted": False, "sequence": [], "confidence": 0.0}
            
        # Find most common sequence
        sequence_counts = defaultdict(int)
        for seq in sequences:
            sequence_counts[tuple(seq)] += 1
            
        most_common = max(sequence_counts.items(), key=lambda x: x[1])
        
        confidence = most_common[1] / len(sequences)
        
        return {
            "predicted": confidence >= self.confidence_threshold,
            "sequence": list(most_common[0]),
            "confidence": confidence,
            "occurrences": most_common[1],
            "total_sequences": len(sequences),
        }
        
    def get_habit_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get summary of detected habits.
        
        Args:
            hours: Time window to analyze
            
        Returns:
            Dictionary with habit statistics
        """
        cutoff = time.time() - (hours * 3600)
        
        device_events = {}
        for device_id, events in self.device_patterns.items():
            recent_events = [e for e in events if e["timestamp"] >= cutoff]
            device_events[device_id] = {
                "count": len(recent_events),
                "event_types": list(set(e["event_type"] for e in recent_events)),
            }
            
        return {
            "device_patterns": device_events,
            "total_patterns": len(self.device_patterns),
            "time_patterns": {
                k: len(v) for k, v in self.time_patterns.items()
            },
            "sequences": {
                k: len(v) for k, v in self.sequence_patterns.items()
            },
        }
        
    def reset(self) -> None:
        """Reset the predictor state."""
        self.device_patterns.clear()
        self.sequence_patterns.clear()
        self.time_patterns.clear()
        self.pattern_confidence.clear()
        self._is_initialized = False


class ContextAwareHabitPredictor(HabitPredictor):
    """
    Extended habit predictor with multi-user awareness.
    
    Tracks separate patterns per user and provides
    personalized habit predictions.
    """
    
    def __init__(self, **kwargs):
        """Initialize context-aware habit predictor."""
        super().__init__(**kwargs)
        self.user_patterns: Dict[str, Dict[str, Any]] = {}
        self.user_sequences: Dict[str, List[List[str]]] = defaultdict(list)
        
    def observe_user(
        self,
        user_id: str,
        device_id: str,
        event_type: str,
        timestamp: Optional[float] = None,
    ) -> None:
        """
        Observe user-specific device event.
        
        Args:
            user_id: ID of the user
            device_id: ID of the device
            event_type: Type of event
            timestamp: When the event occurred
        """
        if not self.enabled:
            return
            
        # Track user-specific pattern
        pattern_key = f"{user_id}_{device_id}_{event_type}"
        self.user_patterns.setdefault(user_id, {}).setdefault(
            pattern_key, []
        ).append(timestamp or time.time())
        
        # Track sequence with user context
        # (would need user device chain in real implementation)
        
    def predict_for_user(
        self,
        user_id: str,
        device_id: str,
        event_type: str,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Predict pattern for a specific user.
        
        Args:
            user_id: ID of the user
            device_id: ID of the device
            event_type: Type of event to predict
            timestamp: When the event would occur
            
        Returns:
            User-specific prediction
        """
        if user_id not in self.user_patterns:
            return {
                "predicted": False,
                "confidence": 0.0,
                "details": {"user": user_id, "pattern": "none"},
            }
            
        pattern_key = f"{user_id}_{device_id}_{event_type}"
        
        if pattern_key not in self.user_patterns[user_id]:
            return {
                "predicted": False,
                "confidence": 0.0,
                "details": {"user": user_id, "pattern": "none"},
            }
            
        # Get pattern
        pattern = self.user_patterns[user_id][pattern_key]
        
        if len(pattern) < self.min_samples_per_pattern:
            return {
                "predicted": False,
                "confidence": 0.0,
                "details": {
                    "user": user_id,
                    "pattern": pattern_key,
                    "samples": len(pattern),
                },
            }
            
        # Calculate confidence
        confidence = min(0.9, 0.5 + 0.1 * len(pattern))
        
        return {
            "predicted": confidence >= self.confidence_threshold,
            "confidence": confidence,
            "details": {
                "user": user_id,
                "pattern": pattern_key,
                "samples": len(pattern),
            },
        }
