"""Energy Optimization Module - Optimizes energy consumption patterns."""

import time
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import numpy as np
from datetime import datetime, timedelta


class EnergyOptimizer:
    """
    Optimizes energy consumption patterns in the smart home.
    
    Features:
    - Device energy profiling
    - Consumption pattern analysis
    - Optimization recommendations
    - Real-time energy savings tracking
    """
    
    def __init__(
        self,
        baseline_window_hours: int = 168,  # 1 week default
        optimization_threshold: float = 0.1,  # 10% improvement
        enabled: bool = True,
    ):
        """
        Initialize the energy optimizer.
        
        Args:
            baseline_window_hours: Time window for baseline calculation
            optimization_threshold: Minimum improvement for recommendations
            enabled: Whether the optimizer is active
        """
        self.baseline_window_hours = baseline_window_hours
        self.optimization_threshold = optimization_threshold
        self.enabled = enabled
        
        # Device energy profiles
        self.device_profiles: Dict[str, Dict] = {}
        self.energy_history: Dict[str, List[Dict]] = defaultdict(list)
        
        # Optimization tracking
        self.recommendations: List[Dict] = []
        self.savings_history: List[Dict] = []
        
        # Device relationships
        self.device_groups: Dict[str, List[str]] = defaultdict(list)
        
        self._is_initialized = False
        
    def register_device(
        self,
        device_id: str,
        power_rating_watts: float,
        device_type: str = "unknown",
    ) -> None:
        """
        Register a device for energy optimization.
        
        Args:
            device_id: ID of the device
            power_rating_watts: Rated power consumption in watts
            device_type: Type of device (light, appliance, HVAC, etc.)
        """
        if not self.enabled:
            return
            
        self.device_profiles[device_id] = {
            "power_rating_watts": power_rating_watts,
            "device_type": device_type,
            "created_at": time.time(),
        }
        
        # Initialize energy history
        if device_id not in self.energy_history:
            self.energy_history[device_id] = []
            
    def record_consumption(
        self,
        device_id: str,
        power_watts: float,
        duration_seconds: float,
        timestamp: Optional[float] = None,
        context: Dict[str, Any] = None,
    ) -> None:
        """
        Record energy consumption for a device.
        
        Args:
            device_id: ID of the device
            power_watts: Power consumption in watts
            duration_seconds: Duration of consumption
            timestamp: When consumption occurred
            context: Additional context (cost, energy_source, etc.)
        """
        if not self.enabled:
            return
            
        if timestamp is None:
            timestamp = time.time()
            
        if context is None:
            context = {}
            
        consumption = {
            "power_watts": power_watts,
            "duration_seconds": duration_seconds,
            "energy_wh": (power_watts * duration_seconds) / 3600,
            "timestamp": timestamp,
            "context": context,
        }
        
        self.energy_history[device_id].append(consumption)
        
        # Keep only recent history (baseline window + buffer)
        cutoff = timestamp - (
            self.baseline_window_hours * 3600 + (24 * 3600)
        )
        self.energy_history[device_id] = [
            c for c in self.energy_history[device_id]
            if c["timestamp"] >= cutoff
        ]
        
        self._is_initialized = True
        
    def calculate_baseline(
        self,
        device_id: str,
        hours: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Calculate baseline energy consumption for a device.
        
        Args:
            device_id: ID of the device
            hours: Time window for baseline (default: configured window)
            
        Returns:
            Baseline statistics
        """
        if not self._is_initialized:
            return {
                "mean_wh": 0.0,
                "std_wh": 0.0,
                "min_wh": 0.0,
                "max_wh": 0.0,
                "count": 0,
            }
            
        if hours is None:
            hours = self.baseline_window_hours
            
        history = self.energy_history.get(device_id, [])
        
        if not history:
            return {
                "mean_wh": 0.0,
                "std_wh": 0.0,
                "min_wh": 0.0,
                "max_wh": 0.0,
                "count": 0,
            }
            
        # Filter by time window
        cutoff = time.time() - (hours * 3600)
        recent = [c for c in history if c["timestamp"] >= cutoff]
        
        if not recent:
            return {
                "mean_wh": 0.0,
                "std_wh": 0.0,
                "min_wh": 0.0,
                "max_wh": 0.0,
                "count": 0,
            }
            
        energies = [c["energy_wh"] for c in recent]
        energies_array = np.array(energies)
        
        return {
            "mean_wh": float(np.mean(energies_array)),
            "std_wh": float(np.std(energies_array)),
            "min_wh": float(np.min(energies_array)),
            "max_wh": float(np.max(energies_array)),
            "count": len(energies),
        }
        
    def calculate_total_consumption(
        self,
        hours: int = 24,
        device_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate total energy consumption.
        
        Args:
            hours: Time window
            device_ids: Specific devices (default: all)
            
        Returns:
            Consumption summary
        """
        cutoff = time.time() - (hours * 3600)
        
        if device_ids is None:
            device_ids = list(self.energy_history.keys())
            
        total_wh = 0.0
        device_consumption = {}
        
        for device_id in device_ids:
            history = self.energy_history.get(device_id, [])
            recent = [c for c in history if c["timestamp"] >= cutoff]
            
            device_wh = sum(c["energy_wh"] for c in recent)
            total_wh += device_wh
            
            device_consumption[device_id] = {
                "energy_wh": device_wh,
                "count": len(recent),
            }
            
        return {
            "total_wh": total_wh,
            "total_kwh": total_wh / 1000,
            "device_consumption": device_consumption,
            "hours": hours,
        }
        
    def generate_recommendations(
        self,
        device_id: str,
        current_consumption_wh: float,
    ) -> List[Dict[str, Any]]:
        """
        Generate energy optimization recommendations for a device.
        
        Args:
            device_id: ID of the device
            current_consumption_wh: Current consumption value
            
        Returns:
            List of recommendation dictionaries
        """
        if not self._is_initialized:
            return []
            
        recommendations = []
        
        # Get baseline
        baseline = self.calculate_baseline(device_id)
        
        if baseline["count"] < 5:
            return recommendations  # Not enough data
            
        # Check for high consumption
        if baseline["mean_wh"] > 0:
            ratio = current_consumption_wh / baseline["mean_wh"]
            
            if ratio > 1.5:
                recommendations.append({
                    "type": "high_consumption",
                    "priority": "high",
                    "title": "Hoher Energieverbrauch",
                    "description": f"{device_id} verbraucht {ratio:.1f}x mehr als üblich",
                    "savings_potential_wh": current_consumption_wh - baseline["mean_wh"],
                })
                
        # Check for device group optimization
        for group_id, devices in self.device_groups.items():
            if device_id in devices and len(devices) > 1:
                group_recommendations = self._analyze_group_optimization(
                    group_id, devices
                )
                recommendations.extend(group_recommendations)
                
        return recommendations
        
    def _analyze_group_optimization(
        self,
        group_id: str,
        devices: List[str],
    ) -> List[Dict[str, Any]]:
        """Analyze optimization opportunities for device groups."""
        recommendations = []
        
        # Find devices in the group
        group_consumption = {}
        for device_id in devices:
            baseline = self.calculate_baseline(device_id)
            if baseline["count"] > 0:
                group_consumption[device_id] = baseline["mean_wh"]
                
        if len(group_consumption) < 2:
            return recommendations
            
        # Check for synchronization issues
        avg_consumption = np.mean(list(group_consumption.values()))
        
        for device_id, consumption in group_consumption.items():
            if consumption > avg_consumption * 1.3:
                recommendations.append({
                    "type": "group_optimization",
                    "priority": "medium",
                    "title": f"Gruppenoptimierung: {device_id}",
                    "description": (
                        f"{device_id} verbraucht mehr als Gruppen-Durchschnitt. "
                        f"Prüfen Sie auf gleichzeitigen Betrieb."
                    ),
                    "savings_potential_wh": consumption - avg_consumption,
                })
                
        return recommendations
        
    def get_savings_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get energy savings summary.
        
        Args:
            hours: Time window
            
        Returns:
            Savings statistics
        """
        consumption = self.calculate_total_consumption(hours)
        
        # Calculate potential savings (hypothetical)
        potential_savings = 0.0
        for device_id, data in consumption["device_consumption"].items():
            baseline = self.calculate_baseline(device_id)
            if baseline["mean_wh"] > 0 and data["energy_wh"] > baseline["mean_wh"]:
                potential_savings += data["energy_wh"] - baseline["mean_wh"]
                
        return {
            "total_consumption_kwh": consumption["total_kwh"],
            "potential_savings_kwh": potential_savings / 1000,
            "device_count": len(consumption["device_consumption"]),
            "recommendation_count": len(self.recommendations),
            "hours": hours,
        }
        
    def create_device_group(
        self,
        group_id: str,
        device_ids: List[str],
    ) -> None:
        """
        Create a device group for coordinated optimization.
        
        Args:
            group_id: Group identifier
            device_ids: Devices in the group
        """
        self.device_groups[group_id] = device_ids
        
    def reset(self) -> None:
        """Reset the optimizer state."""
        self.device_profiles.clear()
        self.energy_history.clear()
        self.recommendations.clear()
        self.savings_history.clear()
        self.device_groups.clear()
        self._is_initialized = False


class ContextAwareEnergyOptimizer(EnergyOptimizer):
    """
    Extended energy optimizer with context awareness.
    
    Considers time-of-use pricing, weather,
    and user preferences for optimization decisions.
    """
    
    def __init__(
        self,
        energy_price_per_kwh: float = 0.30,
        pv_production_profile: Optional[Dict[int, float]] = None,
        **kwargs,
    ):
        """
        Initialize context-aware energy optimizer.
        
        Args:
            energy_price_per_kwh: Current energy price
            pv_production_profile: PV production by hour (0-23)
            **kwargs: Arguments for parent EnergyOptimizer
        """
        super().__init__(**kwargs)
        self.energy_price_per_kwh = energy_price_per_kwh
        self.pv_production_profile = pv_production_profile or {}
        self.optimization_targets: Dict[str, Dict] = {}
        
    def set_optimization_target(
        self,
        device_id: str,
        priority: str = "normal",
        cost_threshold: Optional[float] = None,
    ) -> None:
        """
        Set optimization target for a device.
        
        Args:
            device_id: Device identifier
            priority: Priority level (high, normal, low)
            cost_threshold: Maximum acceptable cost
        """
        self.optimization_targets[device_id] = {
            "priority": priority,
            "cost_threshold": cost_threshold,
            "updated_at": time.time(),
        }
        
    def get_optimal_schedule(
        self,
        device_id: str,
        estimated_duration_hours: float,
    ) -> Dict[str, Any]:
        """
        Get optimal scheduling recommendation for a device.
        
        Args:
            device_id: Device identifier
            estimated_duration_hours: Estimated runtime
            
        Returns:
            Schedule recommendation
        """
        if not self.pv_production_profile:
            return {
                "optimal_start_hour": None,
                "reason": "Kein PV-Profilit verfügbar",
                "energy_cost": None,
            }
            
        # Calculate cost by hour
        costs_by_hour = {}
        for hour, production in self.pv_production_profile.items():
            # Lower cost when more PV production
            if production > 0:
                cost = self.energy_price_per_kwh * (1 - min(0.5, production / 1000))
            else:
                cost = self.energy_price_per_kwh
                
            costs_by_hour[hour] = cost
            
        # Find optimal start hour
        best_hour = min(
            costs_by_hour.keys(),
            key=lambda h: costs_by_hour[h]
        )
        
        return {
            "optimal_start_hour": best_hour,
            "reason": f"Niedrigster Preis um {best_hour}:00 Uhr",
            "energy_cost": costs_by_hour[best_hour] * estimated_duration_hours,
            "price_by_hour": costs_by_hour,
        }
        
    def analyze_peak_shaving(
        self,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Analyze peak shaving opportunities.
        
        Args:
            hours: Time window
            
        Returns:
            Peak shaving analysis
        """
        consumption = self.calculate_total_consumption(hours)
        
        # Analyze by time of day
        time_buckets = defaultdict(float)
        
        for device_id, history in self.energy_history.items():
            for entry in history:
                if entry["timestamp"] >= time.time() - (hours * 3600):
                    dt = datetime.fromtimestamp(entry["timestamp"])
                    bucket = dt.hour
                    time_buckets[bucket] += entry["energy_wh"]
                    
        if not time_buckets:
            return {"peak_hour": None, "savings_opportunity": False}
            
        peak_hour = max(time_buckets.keys(), key=lambda h: time_buckets[h])
        avg_consumption = np.mean(list(time_buckets.values()))
        peak_consumption = time_buckets[peak_hour]
        
        return {
            "peak_hour": peak_hour,
            "peak_consumption_wh": peak_consumption,
            "avg_consumption_wh": avg_consumption,
            "savings_opportunity": peak_consumption > avg_consumption * 1.2,
        }
