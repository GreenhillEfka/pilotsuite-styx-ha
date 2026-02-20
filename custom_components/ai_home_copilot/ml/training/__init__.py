"""ML Training Pipeline - On-device training for pattern models."""

import logging
import time

_LOGGER = logging.getLogger(__name__)
from typing import Dict, List, Optional, Any
from pathlib import Path
import pickle
import json
import numpy as np


class TrainingPipeline:
    """
    On-device training pipeline for ML models.
    
    Features:
    - Incremental learning
    - Model persistence
    - Training data management
    - Performance tracking
    """
    
    def __init__(
        self,
        storage_path: str = "/tmp/ml_training",
        max_training_data: int = 10000,
        auto_save: bool = True,
        enabled: bool = True,
    ):
        """
        Initialize the training pipeline.
        
        Args:
            storage_path: Path for storing training data
            max_training_data: Maximum samples to retain
            auto_save: Whether to auto-save after training
            enabled: Whether training is active
        """
        self.storage_path = Path(storage_path)
        self.max_training_data = max_training_data
        self.auto_save = auto_save
        self.enabled = enabled
        
        # Create storage directory
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Training data storage
        self.training_data: Dict[str, List[Dict]] = {}
        self.model_metrics: Dict[str, Dict] = {}
        self.training_history: List[Dict] = []
        
        # Model storage
        self.models: Dict[str, Any] = {}
        self._model_classes: Dict[str, Any] = {}
        
        self._is_initialized = False
        
    def register_model(
        self,
        model_name: str,
        model_class: Any,
        feature_names: List[str],
        **hyperparams,
    ) -> None:
        """
        Register a model for training.
        
        Args:
            model_name: Name identifier for the model
            model_class: Class to instantiate
            feature_names: List of feature names
            **hyperparams: Hyperparameters for model
        """
        if not self.enabled:
            return
            
        self._model_classes[model_name] = {
            "class": model_class,
            "feature_names": feature_names,
            "hyperparams": hyperparams,
        }
        
        self.training_data[model_name] = []
        self.model_metrics[model_name] = {
            "samples": 0,
            "last_trained": None,
            "last_trained_epoch": 0,
        }
        
    def add_training_data(
        self,
        model_name: str,
        features: Dict[str, Any],
        target: Optional[Any] = None,
        context: Dict[str, Any] = None,
    ) -> bool:
        """
        Add training data for a model.
        
        Args:
            model_name: Name of the model
            features: Feature dictionary
            target: Target value (for supervised learning)
            context: Additional context
            
        Returns:
            True if data was added successfully
        """
        if not self.enabled:
            return False
            
        if model_name not in self._model_classes:
            return False
            
        if context is None:
            context = {}
            
        data_point = {
            "features": features,
            "target": target,
            "context": context,
            "timestamp": time.time(),
        }
        
        self.training_data[model_name].append(data_point)
        
        # Limit training data size
        if len(self.training_data[model_name]) > self.max_training_data:
            self.training_data[model_name] = self.training_data[model_name][-self.max_training_data:]
            
        self.model_metrics[model_name]["samples"] = len(self.training_data[model_name])
        
        if self.auto_save:
            self._save_training_data(model_name)
            
        return True
        
    def train_model(
        self,
        model_name: str,
        data: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Train a model using stored or provided data.
        
        Args:
            model_name: Name of the model
            data: Optional override data
            
        Returns:
            Training metrics
        """
        if not self.enabled:
            return {"status": "disabled"}
            
        if model_name not in self._model_classes:
            return {"status": "error", "message": f"Model {model_name} not registered"}
            
        # Get data
        if data is None:
            data = self.training_data.get(model_name, [])
            
        if not data:
            return {"status": "error", "message": "No training data available"}
            
        # Extract features and targets
        feature_names = self._model_classes[model_name]["feature_names"]
        
        X, y = self._prepare_data(data, feature_names)
        
        if X is None or y is None:
            return {"status": "error", "message": "Failed to prepare training data"}
            
        # Create and train model
        model_class = self._model_classes[model_name]["class"]
        hyperparams = self._model_classes[model_name]["hyperparams"]
        
        model = model_class(**hyperparams)
        
        try:
            model.fit(X)
            
            # Store model
            self.models[model_name] = model
            
            # Update metrics
            self.model_metrics[model_name].update({
                "status": "trained",
                "last_trained": time.time(),
                "last_trained_epoch": self.model_metrics[model_name].get("last_trained_epoch", 0) + 1,
                "training_samples": len(data),
                "training_time_seconds": 0.0,  # Would need timing wrapper in production
            })
            
            # Save model
            if self.auto_save:
                self._save_model(model_name)
                
            # Log training
            self.training_history.append({
                "model_name": model_name,
                "samples": len(data),
                "timestamp": time.time(),
                "status": "success",
            })
            
            return {
                "status": "success",
                "model_name": model_name,
                "samples": len(data),
                "metrics": self.model_metrics[model_name],
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
            }
            
    def _prepare_data(
        self,
        data: List[Dict],
        feature_names: List[str],
    ) -> tuple:
        """Prepare data for training."""
        X = []
        y = []
        
        for point in data:
            # Extract features in order
            features = []
            for name in feature_names:
                value = point["features"].get(name)
                if value is None:
                    break
                try:
                    features.append(float(value))
                except (ValueError, TypeError):
                    break
            else:
                # Only add if all features present
                X.append(features)
                if point.get("target") is not None:
                    y.append(point["target"])
                    
        if not X:
            return None, None
            
        return np.array(X), np.array(y) if y else None
        
    def _save_training_data(self, model_name: str) -> None:
        """Save training data to disk."""
        try:
            path = self.storage_path / f"{model_name}_training_data.pkl"
            with open(path, "wb") as f:
                pickle.dump(self.training_data[model_name], f)
        except Exception as e:
            _LOGGER.error("Failed to save training data for %s: %s", model_name, e)
            
    def _save_model(self, model_name: str) -> None:
        """Save model to disk."""
        if model_name not in self.models:
            return
            
        try:
            path = self.storage_path / f"{model_name}_model.pkl"
            with open(path, "wb") as f:
                pickle.dump(self.models[model_name], f)
                
            # Save metadata
            meta_path = self.storage_path / f"{model_name}_metadata.json"
            with open(meta_path, "w") as f:
                json.dump({
                    "model_name": model_name,
                    "saved_at": time.time(),
                    "metrics": self.model_metrics[model_name],
                }, f)
        except Exception as e:
            _LOGGER.error("Failed to save model %s: %s", model_name, e)
            
    def load_model(self, model_name: str) -> Optional[Any]:
        """Load a trained model from disk."""
        try:
            path = self.storage_path / f"{model_name}_model.pkl"
            if not path.exists():
                return None
                
            with open(path, "rb") as f:
                model = pickle.load(f)
                
            self.models[model_name] = model
            return model
            
        except Exception as e:
            _LOGGER.error("Failed to load model %s: %s", model_name, e)
            return None
            
    def get_training_status(self) -> Dict[str, Any]:
        """Get overall training status."""
        return {
            "models_registered": len(self._model_classes),
            "models_trained": sum(
                1 for m in self.model_metrics.values()
                if m.get("status") == "trained"
            ),
            "total_training_samples": sum(
                m.get("samples", 0) for m in self.model_metrics.values()
            ),
            "training_history": self.training_history[-10:],  # Last 10
        }
        
    def reset(self) -> None:
        """Reset training pipeline."""
        self.training_data.clear()
        self.model_metrics.clear()
        self.models.clear()
        self.training_history.clear()
        self._is_initialized = False


class IncrementalTrainingPipeline(TrainingPipeline):
    """
    Training pipeline with incremental learning support.
    
    Updates models without retraining from scratch.
    """
    
    def __init__(self, **kwargs):
        """Initialize incremental training pipeline."""
        super().__init__(**kwargs)
        self._incremental_models: Dict[str, bool] = {}
        
    def register_incremental_model(
        self,
        model_name: str,
        model_class: Any,
        feature_names: List[str],
        **hyperparams,
    ) -> None:
        """
        Register a model with incremental learning support.
        
        Args:
            model_name: Name identifier for the model
            model_class: Class to instantiate
            feature_names: List of feature names
            **hyperparams: Hyperparameters for model
        """
        super().register_model(model_name, model_class, feature_names, **hyperparams)
        self._incremental_models[model_name] = True
        
    def incremental_update(
        self,
        model_name: str,
        features: Dict[str, Any],
        target: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Perform incremental update on a model.
        
        Args:
            model_name: Name of the model
            features: New feature values
            target: Target value (optional)
            
        Returns:
            Update metrics
        """
        if not self.enabled:
            return {"status": "disabled"}
            
        if model_name not in self._incremental_models:
            return {"status": "error", "message": "Model does not support incremental learning"}
            
        # Add data
        added = self.add_training_data(model_name, features, target)
        if not added:
            return {"status": "error", "message": "Failed to add training data"}
            
        # Get current model
        model = self.models.get(model_name)
        
        if model is None:
            return {"status": "error", "message": "No existing model found"}
            
        try:
            # Prepare single sample
            feature_names = self._model_classes[model_name]["feature_names"]
            X = [float(features.get(name)) for name in feature_names]
            X = np.array(X).reshape(1, -1)
            
            # Partial fit (if supported)
            if hasattr(model, "partial_fit"):
                y = [target] if target is not None else None
                model.partial_fit(X, y)
            else:
                # Fallback: retrain on recent data
                recent_data = self.training_data[model_name][-100:]
                self._train_model_from_data(model_name, recent_data)
                
            return {
                "status": "success",
                "model_name": model_name,
                "samples_seen": len(self.training_data[model_name]),
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
    def _train_model_from_data(
        self,
        model_name: str,
        data: List[Dict],
    ) -> None:
        """Train model from data (internal helper)."""
        feature_names = self._model_classes[model_name]["feature_names"]
        model_class = self._model_classes[model_name]["class"]
        hyperparams = self._model_classes[model_name]["hyperparams"]
        
        X, _ = self._prepare_data(data, feature_names)
        
        if X is None:
            return
            
        model = model_class(**hyperparams)
        model.fit(X)
        self.models[model_name] = model
