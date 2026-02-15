"""ML Context Module - Provides ML context to neurons and sensors."""

import asyncio
import logging
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .module import CopilotModule, ModuleContext
from ...ml_context import MLContext, initialize_ml_context, get_ml_context

_LOGGER = logging.getLogger(__name__)


class MLContextModule(CopilotModule):
    """
    ML Context module for pattern recognition and prediction.
    
    Provides unified interface to:
    - AnomalyDetector: Real-time anomaly detection
    - HabitPredictor: Time-based pattern prediction
    - EnergyOptimizer: Device energy optimization
    - MultiUserLearner: Multi-user behavior tracking
    """
    
    MODULE_NAME = "ml_context"
    
    def __init__(self, context: ModuleContext):
        """Initialize ML context module."""
        super().__init__(context)
        self._ml_context: Optional[MLContext] = None
        self._enabled = False
        self._update_interval = 60  # seconds
        self._unsub: Optional[Any] = None
        
    @property
    def ml_context(self) -> Optional[MLContext]:
        """Get the ML context instance."""
        return self._ml_context
        
    async def async_setup_entry(self, entry: ConfigEntry) -> bool:
        """Set up ML context module."""
        config = entry.options or entry.data
        
        # Check if ML is enabled (default: false for now)
        self._enabled = config.get("ml_enabled", False)
        
        if not self._enabled:
            _LOGGER.info("ML Context module disabled")
            return True
            
        # Initialize ML context in executor (CPU-bound)
        try:
            self._ml_context = await self.hass.async_add_executor_job(
                self._init_ml_context
            )
            
            if self._ml_context:
                _LOGGER.info("ML Context module initialized")
                
                # Register with hass.data for other modules
                if self.entry.entry_id not in self.hass.data.get("ai_home_copilot", {}):
                    self.hass.data.setdefault("ai_home_copilot", {})
                    self.hass.data["ai_home_copilot"][self.entry.entry_id] = {}
                self.hass.data["ai_home_copilot"][self.entry.entry_id]["ml_context"] = self._ml_context
                
                # Start periodic update
                self._unsub = asyncio.create_task(self._periodic_update())
                
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to initialize ML context: %s", e)
            return False
            
    def _init_ml_context(self) -> Optional[MLContext]:
        """Initialize ML context (CPU-bound, run in executor)."""
        try:
            ml_ctx = MLContext(
                storage_path="/config/.storage/ai_home_copilot/ml",
                enabled=True,
            )
            if ml_ctx.initialize():
                return ml_ctx
        except Exception as e:
            _LOGGER.error("ML context init error: %s", e)
        return None
        
    async def _periodic_update(self) -> None:
        """Periodically update ML context from HA states."""
        while self._enabled and self._ml_context:
            try:
                # Sync entity states to ML context
                await self._sync_entity_states()
                
                # Wait for next update
                await asyncio.sleep(self._update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.warning("ML periodic update error: %s", e)
                await asyncio.sleep(30)
                
    async def _sync_entity_states(self) -> None:
        """Sync relevant HA entity states to ML context."""
        if not self._ml_context:
            return
            
        # Get entities from config
        config = self.entry.options or self.entry.data
        ml_entities = config.get("ml_entities", [])
        
        for entity_id in ml_entities:
            state = self.hass.states.get(entity_id)
            if state:
                self._ml_context.record_event(
                    device_id=entity_id,
                    event_type=state.state,
                    context={
                        "timestamp": state.last_updated.timestamp(),
                        "attributes": dict(state.attributes),
                    }
                )
                
    async def async_unload_entry(self, entry: ConfigEntry) -> bool:
        """Unload ML context module."""
        self._enabled = False
        
        if self._unsub:
            self._unsub.cancel()
            try:
                await self._unsub
            except asyncio.CancelledError:
                pass
            
        if self._ml_context:
            self._ml_context.reset()
            
        _LOGGER.info("ML Context module unloaded")
        return True
        
    async def async_reload_entry(self, entry: ConfigEntry) -> bool:
        """Reload ML context module."""
        await self.async_unload_entry(entry)
        return await self.async_setup_entry(entry)
        
    def get_anomaly_status(self) -> Dict[str, Any]:
        """Get current anomaly detection status."""
        if not self._ml_context:
            return {"status": "disabled"}
        return self._ml_context.get_anomaly_status()
        
    def get_habit_prediction(
        self,
        device_id: str,
        event_type: str,
    ) -> Dict[str, Any]:
        """Get habit prediction for a device event."""
        if not self._ml_context:
            return {"status": "disabled"}
        return self._ml_context.get_habit_prediction(device_id, event_type)
        
    def get_energy_recommendations(
        self,
        device_id: str,
        current_consumption_wh: float,
    ) -> list:
        """Get energy optimization recommendations."""
        if not self._ml_context:
            return []
        return self._ml_context.get_energy_recommendations(
            device_id, current_consumption_wh
        )
        
    def get_ml_context_for_device(
        self,
        device_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get ML context for a device or all devices."""
        if not self._ml_context:
            return {"status": "disabled"}
        return self._ml_context.get_ml_context(device_id)


def get_ml_module(hass: HomeAssistant, entry_id: str) -> Optional[MLContextModule]:
    """Get the ML context module for an entry."""
    entry_data = hass.data.get("ai_home_copilot", {}).get(entry_id, {})
    return entry_data.get("ml_context_module")