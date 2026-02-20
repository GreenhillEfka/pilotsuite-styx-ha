"""Base ML Model Interface for PilotSuite."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseMLModel(ABC):
    """Abstract base class for all ML models."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize base model.
        
        Args:
            name: Model name for logging and identification
            config: Optional configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self._is_fitted = False
    
    @abstractmethod
    def fit(self, X, y=None):
        """Train the model with training data.
        
        Args:
            X: Training features
            y: Optional target labels
            
        Returns:
            self for method chaining
        """
        pass
    
    @abstractmethod
    def update(self, X, y=None):
        """Update model with new data (incremental learning).
        
        Args:
            X: New features
            y: Optional new labels
            
        Returns:
            self for method chaining
        """
        pass
    
    @abstractmethod
    def reset(self):
        """Reset model to initial untrained state."""
        pass
    
    @abstractmethod
    def get_model_summary(self) -> Dict[str, Any]:
        """Return model metadata and statistics.
        
        Returns:
            Dictionary with model info including:
            - name: Model name
            - is_fitted: Training status
            - config: Current configuration
            - Additional model-specific metrics
        """
        pass
    
    @property
    def is_fitted(self) -> bool:
        """Check if model is trained.
        
        Returns:
            True if model has been fitted
        """
        return self._is_fitted
    
    @is_fitted.setter
    def is_fitted(self, value: bool):
        """Set fitted status.
        
        Args:
            value: New fitted status
        """
        self._is_fitted = value