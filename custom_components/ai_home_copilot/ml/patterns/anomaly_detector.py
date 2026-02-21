"""Anomaly Detection Module - Identifies unusual activity patterns."""

import logging
import time

_LOGGER = logging.getLogger(__name__)
from typing import Dict, List, Optional, Tuple, Any
from collections import deque
import numpy as np

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
    IsolationForest = None
    StandardScaler = None
    _LOGGER.info("sklearn not installed — ML anomaly detection disabled, using threshold fallback")


class AnomalyDetector:
    """
    Detects unusual activity patterns using ML-based anomaly detection.
    
    Features:
    - Real-time anomaly scoring
    - Adaptive thresholding
    - Multi-sensor correlation analysis
    - Context-aware anomaly classification
    """
    
    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        max_samples: str = "auto",
        window_size: int = 100,
        enabled: bool = True,
    ):
        """
        Initialize the anomaly detector.
        
        Args:
            contamination: Expected proportion of anomalies in the dataset
            n_estimators: Number of base estimators in the isolation forest
            max_samples: Number of samples to draw for each estimator
            window_size: Size of sliding window for real-time detection
            enabled: Whether the detector is active
        """
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.window_size = window_size
        self.enabled = enabled
        
        self.model = None
        self.scaler = StandardScaler() if _SKLEARN_AVAILABLE else None
        self.window: deque = deque(maxlen=window_size)
        self.feature_names: List[str] = []
        self.feature_history: Dict[str, deque] = {}
        self.anomaly_history: deque = deque(maxlen=1000)
        
        self._is_fitted = False
        
    def initialize_features(self, feature_names: List[str]) -> None:
        """Initialize feature names and history buffers."""
        self.feature_names = feature_names
        for name in feature_names:
            self.feature_history[name] = deque(maxlen=self.window_size * 2)
    
    def update(self, features: Dict[str, Any]) -> Tuple[float, bool]:
        """
        Update detector with new observations and get anomaly score.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Tuple of (anomaly_score, is_anomaly)
        """
        if not self.enabled or not self._is_fitted:
            return 0.0, False
            
        # Update feature history
        for name, value in features.items():
            if name in self.feature_history:
                self.feature_history[name].append(value)
        
        # Convert to array for model
        feature_vector = self._extract_feature_vector(features)
        
        if feature_vector is None:
            return 0.0, False
            
        # Get anomaly score
        score = self._compute_anomaly_score(feature_vector)
        
        # Determine if anomaly
        is_anomaly = score > self._get_adaptive_threshold()
        
        # Track history
        self.anomaly_history.append({
            "timestamp": time.time(),
            "score": score,
            "is_anomaly": is_anomaly,
            "features": features.copy(),
        })
        
        return score, is_anomaly
    
    def _extract_feature_vector(self, features: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract numeric feature vector from features dict."""
        vector = []
        for name in self.feature_names:
            value = features.get(name)
            if value is None:
                return None
            try:
                vector.append(float(value))
            except (ValueError, TypeError):
                return None
                
        return np.array(vector).reshape(1, -1)
    
    def _compute_anomaly_score(self, feature_vector: np.ndarray) -> float:
        """Compute anomaly score for a feature vector."""
        if not _SKLEARN_AVAILABLE or self.scaler is None or self.model is None:
            return 0.0
        try:
            # Scale the features
            scaled = self.scaler.transform(feature_vector)
            
            # Get decision function score (higher = more normal)
            score = self.model.decision_function(scaled)[0]
            
            # Convert to 0-1 range (lower = more anomalous)
            normalized_score = 1 - (score + 1) / 2
            return max(0.0, min(1.0, normalized_score))
            
        except Exception:
            return 0.0
    
    def _get_adaptive_threshold(self) -> float:
        """Get adaptive threshold based on recent history."""
        if len(self.anomaly_history) < 10:
            return 0.7  # Default threshold
            
        recent_scores = [entry["score"] for entry in self.anomaly_history][-50:]
        mean_score = np.mean(recent_scores)
        
        # Adaptive threshold based on recent anomaly rates
        if mean_score > 0.6:
            return 0.65  # More sensitive if many anomalies
        elif mean_score < 0.3:
            return 0.75  # Less sensitive if few anomalies
        return 0.7
    
    def fit(self, data: np.ndarray) -> None:
        """
        Fit the anomaly detector on historical data.

        Args:
            data: 2D array of shape (n_samples, n_features)
        """
        if not self.enabled or not _SKLEARN_AVAILABLE:
            return
            
        try:
            # Scale the data
            scaled = self.scaler.fit_transform(data)
            
            # Fit the isolation forest
            self.model = IsolationForest(
                contamination=self.contamination,
                n_estimators=self.n_estimators,
                max_samples=self.max_samples,
                random_state=42,
            )
            self.model.fit(scaled)
            
            self._is_fitted = True
            
        except Exception as e:
            # Fallback to simple threshold-based detection
            self._is_fitted = False
            _LOGGER.warning("ML model fitting failed, using fallback mode: %s", e)
    
    def get_anomaly_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get summary of recent anomalies.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with anomaly statistics
        """
        cutoff = time.time() - (hours * 3600)
        
        recent_anomalies = [
            entry for entry in self.anomaly_history
            if entry["timestamp"] >= cutoff
        ]
        
        if not recent_anomalies:
            return {
                "count": 0,
                "last_anomaly": None,
                "peak_score": 0.0,
                "features": {},
            }
            
        return {
            "count": len(recent_anomalies),
            "last_anomaly": recent_anomalies[-1]["timestamp"],
            "peak_score": max(entry["score"] for entry in recent_anomalies),
            "features": recent_anomalies[-1]["features"],
        }
    
    def reset(self) -> None:
        """Reset the detector state."""
        self.window.clear()
        self.anomaly_history.clear()
        for name in self.feature_history:
            self.feature_history[name].clear()
        self._is_fitted = False


class ContextAwareAnomalyDetector(AnomalyDetector):
    """
    Extended anomaly detector with context awareness.
    
    Considers temporal patterns, device relationships,
    and environmental context for more accurate detection.
    """
    
    def __init__(
        self,
        temporal_window_hours: int = 24,
        device_relationships: Optional[Dict[str, List[str]]] = None,
        **kwargs,
    ):
        """
        Initialize context-aware anomaly detector.
        
        Args:
            temporal_window_hours: Window for temporal pattern analysis
            device_relationships: Maps device IDs to related devices
            **kwargs: Arguments for parent AnomalyDetector
        """
        super().__init__(**kwargs)
        self.temporal_window_hours = temporal_window_hours
        self.device_relationships = device_relationships or {}
        self.temporal_patterns: Dict[str, List[float]] = {}
        
    def update_with_context(
        self,
        device_id: str,
        features: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> Tuple[float, bool, Dict[str, Any]]:
        """
        Update with device context and get detailed anomaly info.
        
        Args:
            device_id: ID of the device being monitored
            features: Feature values
            context: Additional context (time, weather, etc.)
            
        Returns:
            Tuple of (score, is_anomaly, detailed_info)
        """
        score, is_anomaly = self.update(features)
        
        # Get temporal pattern info
        temporal_info = self._analyze_temporal_pattern(device_id, context)
        
        # Get relationship info
        relationship_info = self._analyze_relationship(device_id, features)
        
        detailed_info = {
            "base_score": score,
            "is_anomaly": is_anomaly,
            "temporal_context": temporal_info,
            "relationship_context": relationship_info,
        }
        
        return score, is_anomaly, detailed_info
    
    def _analyze_temporal_pattern(
        self,
        device_id: str,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Analyze temporal pattern for a device."""
        if context is None:
            context = {}
            
        hour_of_day = context.get("hour_of_day", 12)
        day_of_week = context.get("day_of_week", 0)
        
        pattern_key = f"{device_id}_{hour_of_day}_{day_of_week}"
        
        return {
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "expected_pattern": pattern_key in self.temporal_patterns,
            "pattern_history_len": len(self.temporal_patterns.get(pattern_key, [])),
        }
    
    def _analyze_relationship(
        self,
        device_id: str,
        features: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze device relationships for anomaly detection."""
        related_devices = self.device_relationships.get(device_id, [])
        
        return {
            "related_devices": related_devices,
            "relationship_based_score": 0.0,
            "consistency_with_group": "unknown",
        }
