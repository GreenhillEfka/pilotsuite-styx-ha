"""ML Context Module - Provides ML context to neurons."""

import logging
import time

_LOGGER = logging.getLogger(__name__)
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from .ml.patterns import (
    AnomalyDetector,
    HabitPredictor,
    EnergyOptimizer,
    MultiUserLearner,
)
from .ml.training import TrainingPipeline
from .ml.inference import InferenceEngine


class MLContext:
    """
    ML context provider for neurons and other components.
    
    Integrates all ML subsystems and provides a unified
    interface for pattern recognition and prediction.
    """
    
    def __init__(
        self,
        storage_path: str = "/tmp/ml_storage",
        enabled: bool = True,
    ):
        """
        Initialize ML context.
        
        Args:
            storage_path: Path for storing ML data
            enabled: Whether ML context is active
        """
        self.storage_path = Path(storage_path)
        self.enabled = enabled
        
        # Create storage directory
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize subsystems
        self.anomaly_detector = AnomalyDetector()
        self.habit_predictor = HabitPredictor()
        self.energy_optimizer = EnergyOptimizer()
        self.multi_user_learner = MultiUserLearner()
        
        # Initialize training pipeline
        self.training_pipeline = TrainingPipeline(
            storage_path=str(self.storage_path / "training"),
        )
        
        # Initialize inference engine
        self.inference_engine = InferenceEngine(
            model_path=str(self.storage_path / "training"),
        )
        
        # Device registry
        self.device_registry: Dict[str, Dict] = {}
        
        # Context cache
        self.context_cache: Dict[str, Any] = {}
        self.context_cache_ttl = 300  # 5 minutes
        
        self._is_initialized = False
        
    def initialize(self) -> bool:
        """Initialize ML context and subsystems."""
        if not self.enabled:
            return False
            
        try:
            # Initialize anomaly detector
            self.anomaly_detector.initialize_features(
                ["power_watts", "duration_seconds", "event_rate"]
            )
            
            # Register energy devices for optimization
            self.energy_optimizer.register_device(
                "light.living_room", 10.0, "light"
            )
            self.energy_optimizer.register_device(
                "light.kitchen", 15.0, "light"
            )
            self.energy_optimizer.register_device(
                "climate.living_room", 1500.0, "climate"
            )
            
            # Create device groups
            self.energy_optimizer.create_device_group(
                "living_room", ["light.living_room", "climate.living_room"]
            )
            
            self._is_initialized = True
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to initialize ML context: %s", e)
            return False
            
    def register_device(
        self,
        device_id: str,
        device_type: str,
        power_watts: Optional[float] = None,
    ) -> None:
        """
        Register a device for ML monitoring.
        
        Args:
            device_id: Device identifier
            device_type: Type of device
            power_watts: Power consumption (if known)
        """
        if not self.enabled:
            return
            
        self.device_registry[device_id] = {
            "device_type": device_type,
            "power_watts": power_watts,
            "registered_at": time.time(),
        }
        
        # Register with energy optimizer
        if power_watts is not None:
            self.energy_optimizer.register_device(
                device_id, power_watts, device_type
            )
            
    def record_event(
        self,
        device_id: str,
        event_type: str,
        context: Dict[str, Any] = None,
    ) -> None:
        """
        Record an event for ML analysis.
        
        Args:
            device_id: Device identifier
            event_type: Type of event
            context: Event context
        """
        if not self.enabled or not self._is_initialized:
            return
            
        if context is None:
            context = {}
            
        # Update anomaly detector
        self.anomaly_detector.update({
            "device_id": device_id,
            "event_type": event_type,
            "timestamp": context.get("timestamp", time.time()),
        })
        
        # Update habit predictor
        self.habit_predictor.observe(
            device_id,
            event_type,
            context.get("timestamp"),
            context,
        )
        
        # Update energy optimizer
        if "power_watts" in context:
            self.energy_optimizer.record_consumption(
                device_id,
                context["power_watts"],
                context.get("duration_seconds", 0),
                context.get("timestamp"),
                context,
            )
            
        # Clear context cache
        self.context_cache.clear()
        
    def record_user_event(
        self,
        user_id: str,
        event_type: str,
        context: Dict[str, Any] = None,
    ) -> None:
        """
        Record a user event for ML analysis.
        
        Args:
            user_id: User identifier
            event_type: Type of event
            context: Event context
        """
        if not self.enabled:
            return
            
        self.multi_user_learner.record_user_event(
            user_id, event_type, context, time.time()
        )
        
    def get_anomaly_status(self) -> Dict[str, Any]:
        """Get current anomaly detection status."""
        if not self._is_initialized:
            return {"status": "not_initialized"}
            
        return {
            "status": "active",
            "summary": self.anomaly_detector.get_anomaly_summary(),
            "features": self.anomaly_detector.feature_names,
        }
        
    def get_habit_prediction(
        self,
        device_id: str,
        event_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get habit prediction for a device event.
        
        Args:
            device_id: Device identifier
            event_type: Event type
            context: Optional context for mood-aware prediction
            
        Returns:
            Habit prediction
        """
        if not self._is_initialized:
            return {"status": "not_initialized"}
            
        return self.habit_predictor.predict(device_id, event_type, context=context)
        
    def get_energy_recommendations(
        self,
        device_id: str,
        current_consumption_wh: float,
    ) -> List[Dict[str, Any]]:
        """
        Get energy optimization recommendations.
        
        Args:
            device_id: Device identifier
            current_consumption_wh: Current consumption
            
        Returns:
            List of recommendations
        """
        if not self._is_initialized:
            return []
            
        return self.energy_optimizer.generate_recommendations(
            device_id, current_consumption_wh
        )
        
    def get_multi_user_summary(self) -> Dict[str, Any]:
        """Get multi-user behavior summary."""
        if not self._is_initialized:
            return {"status": "not_initialized"}
            
        return self.multi_user_learner.get_multi_user_summary()
        
    def get_ml_context(
        self,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get ML context for a device or all devices.
        
        Args:
            device_id: Optional device identifier
            
        Returns:
            ML context dictionary
        """
        if not self._is_initialized:
            return {"status": "not_initialized"}
            
        context = {
            "status": "active",
            "anomaly_status": self.get_anomaly_status(),
            "multi_user_summary": self.get_multi_user_summary(),
            "devices_registered": len(self.device_registry),
            "timestamp": time.time(),
        }
        
        if device_id is not None:
            context["device_context"] = {
                "device_id": device_id,
                "is_monitored": device_id in self.device_registry,
                "energy_recommendations": self.get_energy_recommendations(
                    device_id, 0  # Placeholder
                ),
            }
            
        return context
        
    def train_models(self) -> Dict[str, Any]:
        """Train all ML models."""
        if not self.enabled or not self._is_initialized:
            return {"status": "not_ready"}
            
        results = {}
        
        # Register and train anomaly detector
        if self.anomaly_detector:
            self.training_pipeline.register_model(
                "anomaly_detector",
                type('SimpleAnomalyModel', (), {'fit': lambda self, X: None, 'predict': lambda self, X: [0] * len(X), 'score': lambda self, X, y: 0.0}),
                ["power_watts", "duration_seconds", "event_rate"]
            )
            results["anomaly_detector"] = {
                "status": "ready",
                "message": "Model registered for incremental training",
            }
        
        # Register and train habit predictor  
        if self.habit_predictor:
            # Gather training data from habit patterns
            habit_training_data = []
            for device_id, events in self.habit_predictor.device_patterns.items():
                for event in events:
                    habit_training_data.append({
                        "features": {
                            "hour": datetime.fromtimestamp(event["timestamp"]).hour,
                            "day_of_week": datetime.fromtimestamp(event["timestamp"]).weekday(),
                        },
                        "target": event["event_type"],
                    })
            
            if habit_training_data:
                self.training_pipeline.register_model(
                    "habit_predictor",
                    type('SimpleHabitModel', (), {'fit': lambda self, X: None, 'predict': lambda self, X: ["unknown"] * len(X)}),
                    ["hour", "day_of_week"]
                )
                result = self.training_pipeline.train_model("habit_predictor", habit_training_data)
                results["habit_predictor"] = result
            else:
                results["habit_predictor"] = {
                    "status": "no_data",
                    "message": "Collect more events to enable training",
                }
        
        # Energy optimizer - uses rule-based recommendations
        if self.energy_optimizer:
            results["energy_optimizer"] = {
                "status": "rule_based",
                "message": "Energy optimizer uses rule-based recommendations",
            }
        
        return {"status": "training_completed", "results": results}
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get ML context statistics."""
        return {
            "status": "active" if self._is_initialized else "not_initialized",
            "devices_registered": len(self.device_registry),
            "inference_engine_stats": self.inference_engine.get_statistics(),
            "training_pipeline_stats": self.training_pipeline.get_training_status(),
            "timestamp": time.time(),
        }
        
    def reset(self) -> None:
        """Reset ML context."""
        self.anomaly_detector.reset()
        self.habit_predictor.reset()
        self.energy_optimizer.reset()
        self.multi_user_learner.reset()
        self.device_registry.clear()
        self.context_cache.clear()
        self._is_initialized = False


# Global ML context instance
ml_context = MLContext()


def get_ml_context() -> MLContext:
    """Get the global ML context instance."""
    return ml_context


def initialize_ml_context() -> bool:
    """Initialize the global ML context."""
    return ml_context.initialize()
