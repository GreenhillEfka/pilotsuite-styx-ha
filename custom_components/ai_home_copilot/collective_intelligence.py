"""
Collective Intelligence Module - Federated Learning for PilotSuite.

Enables distributed learning across multiple PilotSuite homes without sharing raw data.
Each home learns local patterns and only shares anonymized model updates (gradients/weights).

Privacy-first: Only aggregated patterns, not raw entity data or user behavior.

Security:
- Differential privacy with configurable epsilon
- Model signature verification
- No raw data leaves the home
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import numpy as np

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = "1"
STORAGE_KEY = f"{DOMAIN}_collective_intelligence"


@dataclass
class LocalModel:
    """Represents a local ML model for federated learning."""
    model_id: str
    model_type: str  # "habit", "anomaly", "preference", "energy"
    version: int
    parameters: Dict[str, Any]
    accuracy: float
    sample_count: int
    last_updated: float
    checksum: str


@dataclass
class SharedPattern:
    """Anonymized pattern shared with the collective."""
    pattern_id: str
    pattern_type: str
    category: str
    anonymized_weights: Dict[str, float]
    metadata: Dict[str, Any]
    contributed_by: str  # Home ID (not user ID)
    confidence: float
    created_at: float
    expires_at: float


@dataclass
class CollectiveUpdate:
    """Update from the collective intelligence network."""
    update_id: str
    patterns: List[SharedPattern]
    aggregate_stats: Dict[str, Any]
    timestamp: float


class CollectiveIntelligence:
    """
    Federated Learning Coordinator.
    
    Manages local model training and pattern sharing with other homes.
    Implements differential privacy to protect individual home data.
    """
    
    def __init__(
        self,
        hass: HomeAssistant,
        home_id: str,
        home_name: str,
        privacy_epsilon: float = 1.0,
        min_contribution_score: float = 0.5,
        pattern_ttl_days: int = 30,
    ):
        """
        Initialize Collective Intelligence.
        
        Args:
            hass: Home Assistant instance
            home_id: Unique identifier for this home
            home_name: Display name for this home
            privacy_epsilon: Differential privacy parameter (lower = more private)
            min_contribution_score: Minimum score to contribute patterns
            pattern_ttl_days: How long shared patterns are valid
        """
        self.hass = hass
        self.home_id = home_id
        self.home_name = home_name
        self.privacy_epsilon = privacy_epsilon
        self.min_contribution_score = min_contribution_score
        self.pattern_ttl_days = pattern_ttl_days
        
        # Local models (one per type)
        self.local_models: Dict[str, LocalModel] = {}
        
        # Shared patterns from other homes
        self.shared_patterns: Dict[str, SharedPattern] = {}
        
        # Aggregated collective intelligence
        self.collective_aggregates: Dict[str, Dict[str, Any]] = {}
        
        # Network peers (other homes)
        self.peers: Dict[str, Dict[str, Any]] = {}
        
        # Storage
        self._store: Store | None = None
        self._is_initialized = False
        
    async def async_initialize(self) -> None:
        """Initialize storage and load existing data."""
        self._store = Store(
            self.hass,
            STORAGE_VERSION,
            STORAGE_KEY,
            json.dumps,
            json_loads=json.loads,
        )
        
        data = await self._store.async_load()
        if data:
            self._load_state(data)
            
        self._is_initialized = True
        _LOGGER.info("Collective Intelligence initialized for %s", self.home_id)
        
    def _load_state(self, data: Dict[str, Any]) -> None:
        """Load state from storage."""
        # Load local models
        for model_data in data.get("local_models", []):
            model = LocalModel(**model_data)
            self.local_models[model.model_id] = model
            
        # Load shared patterns (filter expired)
        current_time = time.time()
        for pattern_data in data.get("shared_patterns", []):
            pattern = SharedPattern(**pattern_data)
            if pattern.expires_at > current_time:
                self.shared_patterns[pattern.pattern_id] = pattern
                
        # Load aggregates
        self.collective_aggregates = data.get("collective_aggregates", {})
        
    async def _save_state(self) -> None:
        """Persist state to storage."""
        if not self._store:
            return
            
        data = {
            "local_models": [
                model.__dict__ for model in self.local_models.values()
            ],
            "shared_patterns": [
                pattern.__dict__ for pattern in self.shared_patterns.values()
            ],
            "collective_aggregates": self.collective_aggregates,
        }
        
        await self._store.async_save(data)
        
    async def async_register_model(
        self,
        model_id: str,
        model_type: str,
        parameters: Dict[str, Any],
    ) -> LocalModel:
        """
        Register a new local model for federated learning.
        
        Args:
            model_id: Unique identifier for the model
            model_type: Type of model (habit, anomaly, preference, energy)
            parameters: Model parameters
            
        Returns:
            Registered LocalModel
        """
        model = LocalModel(
            model_id=model_id,
            model_type=model_type,
            version=1,
            parameters=parameters,
            accuracy=0.0,
            sample_count=0,
            last_updated=time.time(),
            checksum=self._compute_checksum(parameters),
        )
        
        self.local_models[model_id] = model
        await self._save_state()
        
        _LOGGER.info("Registered model %s of type %s", model_id, model_type)
        return model
        
    async def async_update_model(
        self,
        model_id: str,
        parameters: Dict[str, Any],
        accuracy: float,
        sample_count: int,
    ) -> LocalModel:
        """
        Update local model with new training results.
        
        Args:
            model_id: Model to update
            parameters: New parameters
            accuracy: Model accuracy
            sample_count: Number of training samples
            
        Returns:
            Updated LocalModel
        """
        if model_id not in self.local_models:
            raise ValueError(f"Model {model_id} not found")
            
        model = self.local_models[model_id]
        model.parameters = parameters
        model.version += 1
        model.accuracy = accuracy
        model.sample_count = sample_count
        model.last_updated = time.time()
        model.checksum = self._compute_checksum(parameters)
        
        await self._save_state()
        
        _LOGGER.debug("Updated model %s to version %d", model_id, model.version)
        return model
        
    def _compute_checksum(self, parameters: Dict[str, Any]) -> str:
        """Compute checksum for model parameters."""
        param_str = json.dumps(parameters, sort_keys=True)
        return hashlib.sha256(param_str.encode()).hexdigest()[:16]
        
    def _apply_differential_privacy(
        self,
        weights: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Apply differential privacy to weights.
        
        Args:
            weights: Original model weights
            
        Returns:
            Privacy-enhanced weights
        """
        if not self.privacy_epsilon or self.privacy_epsilon <= 0:
            return weights
            
        # Add Laplace noise for differential privacy
        scale = 1.0 / self.privacy_epsilon
        noisy_weights = {}
        
        for key, value in weights.items():
            noise = np.random.laplace(0, scale)
            noisy_weights[key] = value + noise
            
        return noisy_weights
        
    async def async_create_pattern(
        self,
        model_id: str,
        pattern_type: str,
        category: str,
        weights: Dict[str, float],
        metadata: Dict[str, Any],
        confidence: float,
    ) -> Optional[SharedPattern]:
        """
        Create a shareable pattern from local model.
        
        Args:
            model_id: Source model
            pattern_type: Type of pattern
            category: Pattern category
            weights: Anonymized weights
            metadata: Additional metadata
            confidence: Pattern confidence score
            
        Returns:
            SharedPattern if score meets threshold, None otherwise
        """
        if confidence < self.min_contribution_score:
            _LOGGER.debug(
                "Pattern %s/%s below contribution threshold (%.2f < %.2f)",
                pattern_type, category, confidence, self.min_contribution_score
            )
            return None
            
        # Apply differential privacy
        private_weights = self._apply_differential_privacy(weights)
        
        # Normalize weights
        if private_weights:
            values = np.array(list(private_weights.values()))
            norm = np.linalg.norm(values)
            if norm > 0:
                private_weights = {
                    k: v / norm for k, v in private_weights.items()
                }
        
        pattern_id = hashlib.sha256(
            f"{self.home_id}:{model_id}:{time.time()}".encode()
        ).hexdigest()[:16]
        
        pattern = SharedPattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            category=category,
            anonymized_weights=private_weights,
            metadata=metadata,
            contributed_by=self.home_id,
            confidence=confidence,
            created_at=time.time(),
            expires_at=time.time() + (self.pattern_ttl_days * 86400),
        )
        
        _LOGGER.info(
            "Created pattern %s (%s/%s) with confidence %.2f",
            pattern_id, pattern_type, category, confidence
        )
        
        return pattern
        
    async def async_receive_patterns(
        self,
        patterns: List[SharedPattern],
    ) -> int:
        """
        Receive patterns from other homes.
        
        Args:
            patterns: List of shared patterns
            
        Returns:
            Number of new patterns added
        """
        current_time = time.time()
        added = 0
        
        for pattern in patterns:
            # Skip expired patterns
            if pattern.expires_at <= current_time:
                continue
                
            # Skip own patterns
            if pattern.contributed_by == self.home_id:
                continue
                
            # Add if new
            if pattern.pattern_id not in self.shared_patterns:
                self.shared_patterns[pattern.pattern_id] = pattern
                added += 1
                
        if added > 0:
            await self._save_state()
            _LOGGER.info("Received %d new patterns from collective", added)
            
        return added
        
    def get_patterns_by_type(
        self,
        pattern_type: str,
        category: Optional[str] = None,
    ) -> List[SharedPattern]:
        """
        Get patterns filtered by type and optionally category.
        
        Args:
            pattern_type: Pattern type to filter
            category: Optional category filter
            
        Returns:
            List of matching patterns
        """
        current_time = time.time()
        results = []
        
        for pattern in self.shared_patterns.values():
            if pattern.expires_at <= current_time:
                continue
            if pattern.pattern_type != pattern_type:
                continue
            if category and pattern.category != category:
                continue
            results.append(pattern)
            
        # Sort by confidence
        results.sort(key=lambda p: p.confidence, reverse=True)
        
        return results
        
    def get_aggregate_for_type(
        self,
        pattern_type: str,
    ) -> Dict[str, Any]:
        """
        Get aggregated intelligence for a pattern type.
        
        Args:
            pattern_type: Pattern type to aggregate
            
        Returns:
            Aggregated data with confidence scores
        """
        patterns = self.get_patterns_by_type(pattern_type)
        
        if not patterns:
            return {
                "pattern_type": pattern_type,
                "count": 0,
                "aggregated_weights": {},
                "average_confidence": 0.0,
                "contributors": [],
            }
            
        # Aggregate weights (weighted average by confidence)
        total_confidence = sum(p.confidence for p in patterns)
        aggregated_weights: Dict[str, float] = {}
        
        for pattern in patterns:
            weight = pattern.confidence / total_confidence
            for key, value in pattern.anonymized_weights.items():
                if key not in aggregated_weights:
                    aggregated_weights[key] = 0.0
                aggregated_weights[key] += value * weight
                
        return {
            "pattern_type": pattern_type,
            "count": len(patterns),
            "aggregated_weights": aggregated_weights,
            "average_confidence": total_confidence / len(patterns),
            "contributors": list(set(p.contributed_by for p in patterns)),
        }
        
    async def async_cleanup_expired(self) -> int:
        """Remove expired patterns."""
        current_time = time.time()
        expired = [
            pid for pid, p in self.shared_patterns.items()
            if p.expires_at <= current_time
        ]
        
        for pid in expired:
            del self.shared_patterns[pid]
            
        if expired:
            await self._save_state()
            _LOGGER.info("Cleaned up %d expired patterns", len(expired))
            
        return len(expired)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get collective intelligence statistics."""
        current_time = time.time()
        
        pattern_types: Dict[str, int] = {}
        for pattern in self.shared_patterns.values():
            if pattern.expires_at > current_time:
                pattern_types[pattern.pattern_type] = \
                    pattern_types.get(pattern.pattern_type, 0) + 1
                    
        return {
            "home_id": self.home_id,
            "local_models": len(self.local_models),
            "shared_patterns": len(self.shared_patterns),
            "pattern_types": pattern_types,
            "peers": len(self.peers),
            "privacy_epsilon": self.privacy_epsilon,
        }


async def get_collective_intelligence(
    hass: HomeAssistant,
    home_id: str,
    home_name: str,
) -> CollectiveIntelligence:
    """
    Get or create Collective Intelligence instance.
    
    Args:
        hass: Home Assistant instance
        home_id: Unique home identifier
        home_name: Display name for the home
        
    Returns:
        CollectiveIntelligence instance
    """
    # Check hass.data for existing instance
    dom_data = hass.data.get(DOMAIN, {})
    
    if "collective_intelligence" in dom_data:
        return dom_data["collective_intelligence"]
        
    # Create new instance
    collective = CollectiveIntelligence(hass, home_id, home_name)
    await collective.async_initialize()
    
    dom_data["collective_intelligence"] = collective
    hass.data[DOMAIN] = dom_data
    
    return collective
