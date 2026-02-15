"""Energy Service - Energy monitoring, anomaly detection, and load shifting.

Provides:
- Energy consumption monitoring and baselines
- Anomaly detection for unusual patterns
- Load shifting opportunity detection
- Suggestion explainability
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ..api.security import require_api_key

logger = logging.getLogger(__name__)


@dataclass
class EnergySnapshot:
    """Complete energy status snapshot."""
    timestamp: str
    total_consumption_today: float  # kWh
    total_production_today: float  # kWh (solar/PV)
    current_power: float  # Watts
    peak_power_today: float  # Watts
    anomalies_detected: int
    shifting_opportunities: int
    baselines: dict[str, float]  # device_type -> avg kWh/day


@dataclass
class EnergyAnomaly:
    """Detected energy anomaly."""
    id: str
    timestamp: str
    device_id: str
    device_type: str
    expected_value: float
    actual_value: float
    deviation_percent: float
    severity: str  # low, medium, high
    description: str


@dataclass
class ShiftingOpportunity:
    """Load shifting opportunity."""
    id: str
    timestamp: str
    device_type: str
    reason: str  # e.g., "solar_oversupply", "off_peak_pricing"
    current_cost: float  # €/kWh
    optimal_cost: float  # €/kWh
    savings_estimate: float  # €
    suggested_time_window: tuple[str, str]  # start, end
    confidence: float  # 0-1


class EnergyService:
    """Service for energy monitoring and optimization."""
    
    def __init__(self, hass=None):
        """Initialize energy service."""
        self.hass = hass
        self._cache: dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_update = 0.0
        
        # Baselines (would be learned over time)
        self._baselines: dict[str, dict[str, float]] = {
            "washer": {"daily_kwh": 1.5, "peak_watts": 500},
            "dryer": {"daily_kwh": 3.5, "peak_watts": 3000},
            "dishwasher": {"daily_kwh": 1.4, "peak_watts": 1200},
            "ev_charger": {"daily_kwh": 10.0, "peak_watts": 7700},
            "heat_pump": {"daily_kwh": 15.0, "peak_watts": 2500},
            "hvac": {"daily_kwh": 8.0, "peak_watts": 2000},
        }
        
        # Anomaly thresholds
        self._anomaly_thresholds = {
            "low": 0.15,      # 15% deviation
            "medium": 0.30,   # 30% deviation
            "high": 0.50,     # 50% deviation
        }
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        return (time.time() - self._last_update) < self._cache_ttl
    
    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        return datetime.utcnow().isoformat() + "Z"
    
    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID."""
        import hashlib
        timestamp = str(time.time()).encode()
        hash_val = hashlib.md5(timestamp).hexdigest()[:8]
        return f"{prefix}_{hash_val}"
    
    def _get_all_energy_entities(self) -> list[str]:
        """Get all energy-related entities from HA."""
        if not self.hass:
            return []
        
        energy_entities = []
        try:
            # Get all entity states
            states = self.hass.states.async_all()
            for state in states:
                entity_id = state.entity_id
                # Check for energy-related domains
                if any(domain in entity_id for domain in [
                    "sensor.energy", "sensor.power", "sensor.utility_meter",
                    "sensor.pv", "sensor.solar", "sensor.inverter"
                ]):
                    energy_entities.append(entity_id)
        except Exception as e:
            logger.error(f"Error fetching energy entities: {e}")
        
        return energy_entities
    
    def _get_consumption_today(self) -> float:
        """Get total energy consumption for today."""
        # Simplified: would query HA history in real implementation
        if not self.hass:
            return 15.0  # Default mock value
        
        try:
            # Look for total consumption sensor
            total_entity = "sensor.energy_consumption_total"
            state = self.hass.states.get(total_entity)
            if state and state.state != "unavailable":
                return float(state.state)
        except Exception as e:
            logger.debug(f"Could not read consumption: {e}")
        
        return 15.0  # Default
    
    def _get_production_today(self) -> float:
        """Get total energy production (solar/PV) for today."""
        if not self.hass:
            return 5.0  # Default mock value
        
        try:
            # Look for production sensor
            prod_entities = [
                "sensor.energy_production_total",
                "sensor.solar_production_total",
                "sensor.pv_production_total"
            ]
            for entity in prod_entities:
                state = self.hass.states.get(entity)
                if state and state.state != "unavailable":
                    return float(state.state)
        except Exception as e:
            logger.debug(f"Could not read production: {e}")
        
        return 5.0  # Default
    
    def _get_current_power(self) -> float:
        """Get current power draw in Watts."""
        if not self.hass:
            return 850.0  # Default mock value
        
        try:
            # Look for current power sensor
            power_entity = "sensor.power_consumption_now"
            state = self.hass.states.get(power_entity)
            if state and state.state != "unavailable":
                return float(state.state)
        except Exception as e:
            logger.debug(f"Could not read power: {e}")
        
        return 850.0  # Default
    
    @require_api_key
    def get_energy_snapshot(self) -> EnergySnapshot:
        """Get complete energy snapshot."""
        if self._is_cache_valid():
            return self._cache.get("snapshot")
        
        entities = self._get_all_energy_entities()
        
        snapshot = EnergySnapshot(
            timestamp=self._get_timestamp(),
            total_consumption_today=self._get_consumption_today(),
            total_production_today=self._get_production_today(),
            current_power=self._get_current_power(),
            peak_power_today=self._get_peak_power_today(),
            anomalies_detected=len(self._detect_anomalies()),
            shifting_opportunities=len(self._detect_shifting_opportunities()),
            baselines=self._get_baselines()
        )
        
        self._cache["snapshot"] = snapshot
        self._last_update = time.time()
        
        return snapshot
    
    def _get_peak_power_today(self) -> float:
        """Get peak power draw today."""
        # Simplified: would query HA history in real implementation
        return 2500.0  # Default mock value
    
    def _get_baselines(self) -> dict[str, float]:
        """Get energy baselines per device type."""
        return {
            device: data["daily_kwh"] 
            for device, data in self._baselines.items()
        }
    
    @require_api_key
    def detect_anomalies(self) -> list[EnergyAnomaly]:
        """Detect energy consumption anomalies."""
        return self._detect_anomalies()
    
    def _detect_anomalies(self) -> list[EnergyAnomaly]:
        """Internal anomaly detection."""
        anomalies = []
        
        # Check each device type against baselines
        current_consumption = self._get_consumption_today()
        expected_total = sum(b["daily_kwh"] for b in self._baselines.values())
        
        # Calculate total expected (simplified)
        expected_total = expected_total * 0.6  # Assume 60% of baseline devices active
        
        if expected_total > 0:
            deviation = (current_consumption - expected_total) / expected_total
            
            if abs(deviation) >= self._anomaly_thresholds["high"]:
                severity = "high"
            elif abs(deviation) >= self._anomaly_thresholds["medium"]:
                severity = "medium"
            elif abs(deviation) >= self._anomaly_thresholds["low"]:
                severity = "low"
            else:
                severity = None
            
            if severity:
                anomaly = EnergyAnomaly(
                    id=self._generate_id("anomaly"),
                    timestamp=self._get_timestamp(),
                    device_id="total_consumption",
                    device_type="aggregate",
                    expected_value=expected_total,
                    actual_value=current_consumption,
                    deviation_percent=deviation * 100,
                    severity=severity,
                    description=f"Consumption {abs(deviation)*100:.1f}% {'above' if deviation > 0 else 'below'} expected"
                )
                anomalies.append(anomaly)
        
        # Check for device-specific anomalies
        device_checks = [
            ("washer", "sensor.washer_energy"),
            ("dryer", "sensor.dryer_energy"),
            ("dishwasher", "sensor.dishwasher_energy"),
            ("ev_charger", "sensor.ev_charger_energy"),
        ]
        
        for device_type, entity_id in device_checks:
            if self.hass:
                state = self.hass.states.get(entity_id)
                if state and state.state != "unavailable":
                    try:
                        current = float(state.state)
                        expected = self._baselines.get(device_type, {}).get("daily_kwh", 0)
                        if expected > 0:
                            deviation = (current - expected) / expected
                            if abs(deviation) >= self._anomaly_thresholds["medium"]:
                                severity = "high" if abs(deviation) >= self._anomaly_thresholds["high"] else "medium"
                                anomaly = EnergyAnomaly(
                                    id=self._generate_id("anomaly"),
                                    timestamp=self._get_timestamp(),
                                    device_id=entity_id,
                                    device_type=device_type,
                                    expected_value=expected,
                                    actual_value=current,
                                    deviation_percent=deviation * 100,
                                    severity=severity,
                                    description=f"{device_type} consumption {abs(deviation)*100:.1f}% {'above' if deviation > 0 else 'below'} expected"
                                )
                                anomalies.append(anomaly)
                    except (ValueError, TypeError):
                        pass
        
        return anomalies
    
    @require_api_key
    def detect_shifting_opportunities(self) -> list[ShiftingOpportunity]:
        """Detect load shifting opportunities."""
        return self._detect_shifting_opportunities()
    
    def _detect_shifting_opportunities(self) -> list[ShiftingOpportunity]:
        """Internal load shifting detection."""
        opportunities = []
        now = datetime.utcnow()
        current_hour = now.hour
        
        # Solar oversupply detection
        production = self._get_production_today()
        consumption = self._get_consumption_today()
        
        # High production relative to consumption = shifting opportunity
        if production > consumption * 1.5:
            opp = ShiftingOpportunity(
                id=self._generate_id("shift"),
                timestamp=self._get_timestamp(),
                device_type="dishwasher",
                reason="solar_oversupply",
                current_cost=0.30,  # €/kWh
                optimal_cost=0.0,  # Free during solar
                savings_estimate=0.42,  # ~1.4 kWh * 0.30€
                suggested_time_window=(
                    now.isoformat(),
                    (now + timedelta(hours=3)).isoformat()
                ),
                confidence=0.85
            )
            opportunities.append(opp)
        
        # Off-peak pricing windows (simplified)
        off_peak_hours = [0, 1, 2, 3, 4, 5, 22, 23]
        peak_hours = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
        
        if current_hour in off_peak_hours:
            # Suggest running high-power devices now
            opp = ShiftingOpportunity(
                id=self._generate_id("shift"),
                timestamp=self._get_timestamp(),
                device_type="ev_charger",
                reason="off_peak_pricing",
                current_cost=0.22,  # Off-peak rate
                optimal_cost=0.35,  # Peak rate
                savings_estimate=1.00,  # 10kWh * 0.10€
                suggested_time_window=(
                    now.isoformat(),
                    (now + timedelta(hours=6)).isoformat()
                ),
                confidence=0.90
            )
            opportunities.append(opp)
        
        elif current_hour in peak_hours:
            # Suggest delaying
            opp = ShiftingOpportunity(
                id=self._generate_id("shift"),
                timestamp=self._get_timestamp(),
                device_type="washer",
                reason="avoid_peak_pricing",
                current_cost=0.35,  # Peak rate
                optimal_cost=0.22,  # Off-peak rate
                savings_estimate=0.33,  # 1.5kWh * 0.10€
                suggested_time_window=(
                    (now + timedelta(hours=5)).isoformat(),
                    (now + timedelta(hours=10)).isoformat()
                ),
                confidence=0.75
            )
            opportunities.append(opp)
        
        return opportunities
    
    @require_api_key
    def explain_suggestion(self, suggestion_id: str) -> dict[str, Any]:
        """Explain why an energy suggestion was made."""
        anomalies = self._detect_anomalies()
        opportunities = self._detect_shifting_opportunities()
        
        # Find matching anomaly
        for anomaly in anomalies:
            if suggestion_id in anomaly.id or suggestion_id == "anomaly":
                return {
                    "suggestion_id": suggestion_id,
                    "type": "anomaly",
                    "title": f"Hoher Energieverbrauch erkannt",
                    "description": anomaly.description,
                    "details": {
                        "expected_kwh": anomaly.expected_value,
                        "actual_kwh": anomaly.actual_value,
                        "deviation_percent": anomaly.deviation_percent,
                        "severity": anomaly.severity
                    },
                    "actions": [
                        "Überprüfe ob alle Geräte ausgeschaltet sind",
                        "Prüfe Standby-Verbrauch",
                        "Analysiere Verbrauchsmuster der letzten Woche"
                    ]
                }
        
        # Find matching opportunity
        for opp in opportunities:
            if suggestion_id in opp.id or suggestion_id == "opportunity":
                return {
                    "suggestion_id": suggestion_id,
                    "type": "shifting",
                    "title": f"Load Shifting: {opp.device_type}",
                    "description": opp.reason.replace("_", " ").title(),
                    "details": {
                        "current_cost_per_kwh": opp.current_cost,
                        "optimal_cost_per_kwh": opp.optimal_cost,
                        "savings_estimate": opp.savings_estimate,
                        "suggested_window": opp.suggested_time_window,
                        "confidence": opp.confidence
                    },
                    "actions": [
                        f"Starte {opp.device_type} im vorgeschlagenen Zeitfenster",
                        f"Geschätzte Ersparnis: {opp.savings_estimate:.2f}€"
                    ]
                }
        
        return {
            "suggestion_id": suggestion_id,
            "type": "unknown",
            "title": "Vorschlag nicht gefunden",
            "description": "Die Anfrage konnte keinem bekannten Vorschlag zugeordnet werden."
        }
    
    @require_api_key
    def get_suppression_status(self) -> dict[str, Any]:
        """Check if energy suggestions should be suppressed."""
        anomalies = self._detect_anomalies()
        high_severity_anomalies = [a for a in anomalies if a.severity == "high"]
        
        return {
            "suppressed": len(high_severity_anomalies) > 0,
            "reason": f"{len(high_severity_anomalies)} high-severity anomalies detected" if high_severity_anomalies else None,
            "suppress_until": None,
            "recommendations": [
                "Address high-severity anomalies before new suggestions" if high_severity_anomalies else None
            ]
        }
    
    @require_api_key
    def get_health(self) -> dict[str, Any]:
        """Get service health status."""
        return {
            "status": "healthy",
            "cache_valid": self._is_cache_valid(),
            "last_update": self._last_update,
            "baselines_configured": len(self._baselines),
            "anomaly_thresholds": self._anomaly_thresholds
        }
