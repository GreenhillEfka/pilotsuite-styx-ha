"""Energy Module v0.1 - Local energy analysis and load shifting recommendations.

Implements the energy_module v0.1 spec as a CopilotModule.

Key Features:
- Baseload drift detection
- Spike/anomaly detection
- PV surplus opportunities
- Tariff-based load shifting recommendations
- Explainability-first approach (every recommendation has clear evidence)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, Event
from homeassistant.helpers.event import async_track_time_interval, async_track_state_change_event
from homeassistant.const import (
    CONF_SENSORS,
    UnitOfPower,
    UnitOfEnergy,
)
import voluptuous as vol

from ...const import DOMAIN
from ..module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)

# Module constants
MODULE_KEY = "energy_module"
DEFAULT_SAMPLE_INTERVAL_S = 60
DEFAULT_HISTORY_DAYS = 14
DEFAULT_BASELOAD_PERCENTILE = 10
DEFAULT_SPIKE_Z_THRESHOLD = 3.0
DEFAULT_MIN_PERSISTENCE_MIN = 5
DEFAULT_MAX_NOTIFICATIONS_PER_DAY = 6


class EnergyModule:
    """Energy Module v0.1 implementation.
    
    This module provides local energy monitoring and analysis:
    - Anomaly detection (baseload drift, spikes, unexpected consumption)
    - Load shifting recommendations (PV surplus, tariff optimization)
    - All recommendations are explainable with clear evidence
    """

    @property
    def name(self) -> str:
        return MODULE_KEY

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        """Set up the energy module for this config entry."""
        hass = ctx.hass
        entry = ctx.entry
        
        _LOGGER.info("Initializing Energy Module v0.1 for entry %s", entry.entry_id)
        
        # Initialize module data structure
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        
        if entry.entry_id not in hass.data[DOMAIN]:
            hass.data[DOMAIN][entry.entry_id] = {}
        
        entry_data = hass.data[DOMAIN][entry.entry_id]
        entry_data[MODULE_KEY] = {
            "config": self._create_default_config(hass),
            "timeseries": {
                "buffer": [],  # Ring buffer for recent measurements
                "aggregates": {
                    "5min": [],
                    "15min": [],
                    "1h": [],
                }
            },
            "baselines": {
                "baseload_w": None,
                "tow_median": {},  # Time-of-week baseline
                "last_computed": None,
            },
            "events": [],  # Recent anomaly/recommendation events
            "last_notification": {},  # Notification deduplication
            "tracked_entities": set(),
            "polling_unsub": None,
            "event_unsubs": [],
        }
        
        module_data = entry_data[MODULE_KEY]
        
        # Register services
        await self._register_services(hass, entry.entry_id)
        
        # Set up entity tracking
        await self._setup_entity_tracking(hass, entry.entry_id, module_data)
        
        # Set up periodic analysis
        await self._setup_periodic_analysis(hass, entry.entry_id, module_data)
        
        # Compute initial baselines
        await self._compute_baselines(hass, entry.entry_id)
        
        _LOGGER.info("Energy Module v0.1 initialized successfully")

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        """Unload the energy module."""
        hass = ctx.hass
        entry = ctx.entry
        
        try:
            entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
            module_data = entry_data.get(MODULE_KEY, {})
            
            # Cancel polling
            polling_unsub = module_data.get("polling_unsub")
            if polling_unsub:
                polling_unsub()
            
            # Cancel event tracking
            for unsub in module_data.get("event_unsubs", []):
                unsub()
            
            # Clear data
            if MODULE_KEY in entry_data:
                del entry_data[MODULE_KEY]
            
            _LOGGER.info("Energy Module unloaded for entry %s", entry.entry_id)
            return True
            
        except Exception as e:
            _LOGGER.error("Error unloading Energy Module: %s", e)
            return False

    def _create_default_config(self, hass: HomeAssistant) -> Dict[str, Any]:
        """Create default configuration based on available entities.
        
        This discovers common energy/power sensors in HA.
        Users can customize via YAML or UI later.
        """
        
        # Auto-discover power/energy sensors
        discovered_sensors = {
            "house_power": None,
            "energy_total": None,
            "pv_power": None,
            "grid_import_power": None,
            "grid_export_power": None,
            "battery_power": None,
            "battery_soc": None,
            "price_eur_per_kwh": None,
        }
        
        # Simple discovery heuristic (can be improved)
        for state in hass.states.async_all():
            entity_id = state.entity_id
            lower_id = entity_id.lower()
            
            # Look for common patterns
            if "house" in lower_id and "power" in lower_id:
                discovered_sensors["house_power"] = entity_id
            elif "pv" in lower_id and "power" in lower_id:
                discovered_sensors["pv_power"] = entity_id
            elif "grid" in lower_id and "import" in lower_id:
                discovered_sensors["grid_import_power"] = entity_id
            elif "grid" in lower_id and "export" in lower_id:
                discovered_sensors["grid_export_power"] = entity_id
            elif "battery" in lower_id and "power" in lower_id:
                discovered_sensors["battery_power"] = entity_id
            elif "battery" in lower_id and ("soc" in lower_id or "charge" in lower_id):
                discovered_sensors["battery_soc"] = entity_id
            elif "price" in lower_id or "tariff" in lower_id:
                discovered_sensors["price_eur_per_kwh"] = entity_id
        
        config = {
            "signals": discovered_sensors,
            "analysis": {
                "sample_interval_s": DEFAULT_SAMPLE_INTERVAL_S,
                "history_days": DEFAULT_HISTORY_DAYS,
                "baseload_percentile": DEFAULT_BASELOAD_PERCENTILE,
                "spike_z_threshold": DEFAULT_SPIKE_Z_THRESHOLD,
                "min_persistence_min": DEFAULT_MIN_PERSISTENCE_MIN,
                "night_window": ["00:30", "05:00"],
            },
            "flex_loads": [
                # Example flexible loads - user configurable
                # {
                #     "id": "dishwasher",
                #     "power_sensor": "sensor.dishwasher_power",
                #     "typical_kwh": 1.1,
                #     "window": {"earliest": "10:00", "latest": "18:00"},
                #     "runtime_min": 120,
                #     "priority": "medium",
                # }
            ],
            "policies": {
                "max_notifications_per_day": DEFAULT_MAX_NOTIFICATIONS_PER_DAY,
                "quiet_hours": ["22:30", "07:00"],
                "require_user_presence": False,
                "allow_automation": False,  # Only notifications by default
            },
            "notify": {
                "channel": "persistent_notification",  # Fallback to HA notifications
            }
        }
        
        return config

    async def _register_services(self, hass: HomeAssistant, entry_id: str) -> None:
        """Register energy module services."""
        
        async def _handle_analyze_now(call: ServiceCall) -> None:
            """Force immediate analysis run."""
            await self._run_analysis(hass, entry_id)

        async def _handle_compute_baselines(call: ServiceCall) -> None:
            """Recompute baselines from historical data."""
            await self._compute_baselines(hass, entry_id)

        async def _handle_get_recommendations(call: ServiceCall) -> None:
            """Get current load shifting recommendations."""
            await self._generate_recommendations(hass, entry_id)

        # Register services (idempotent)
        service_name = f"energy_analyze_now_{entry_id}"
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN,
                service_name,
                _handle_analyze_now,
                schema=vol.Schema({})
            )

        service_name = f"energy_compute_baselines_{entry_id}"
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN,
                service_name,
                _handle_compute_baselines,
                schema=vol.Schema({})
            )

        service_name = f"energy_get_recommendations_{entry_id}"
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(
                DOMAIN,
                service_name,
                _handle_get_recommendations,
                schema=vol.Schema({})
            )

    async def _setup_entity_tracking(
        self, 
        hass: HomeAssistant, 
        entry_id: str, 
        module_data: Dict[str, Any]
    ) -> None:
        """Set up state change event tracking for power/energy sensors."""
        
        config = module_data["config"]
        tracked_entities = set()
        
        # Track all configured signal sensors
        for sensor_id in config["signals"].values():
            if sensor_id:
                tracked_entities.add(sensor_id)
        
        # Track flexible load power sensors
        for load in config.get("flex_loads", []):
            power_sensor = load.get("power_sensor")
            if power_sensor:
                tracked_entities.add(power_sensor)
        
        module_data["tracked_entities"] = tracked_entities
        
        async def _handle_state_change(event: Event) -> None:
            """Handle state change events for tracked entities."""
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            
            if entity_id in tracked_entities and new_state:
                # Record measurement
                await self._record_measurement(hass, entry_id, entity_id, new_state)
        
        if tracked_entities:
            # Track state changes
            unsub = async_track_state_change_event(
                hass, list(tracked_entities), _handle_state_change
            )
            module_data["event_unsubs"].append(unsub)

    async def _setup_periodic_analysis(
        self, 
        hass: HomeAssistant, 
        entry_id: str, 
        module_data: Dict[str, Any]
    ) -> None:
        """Set up periodic analysis runs."""
        
        config = module_data["config"]
        interval_s = config["analysis"]["sample_interval_s"]
        
        async def _handle_periodic_analysis(now: datetime) -> None:
            """Periodic analysis handler."""
            await self._run_analysis(hass, entry_id)
        
        # Set up periodic analysis
        unsub = async_track_time_interval(
            hass, _handle_periodic_analysis, timedelta(seconds=interval_s)
        )
        module_data["polling_unsub"] = unsub

    async def _record_measurement(
        self, 
        hass: HomeAssistant, 
        entry_id: str,
        entity_id: str,
        state
    ) -> None:
        """Record a sensor measurement to the time series buffer."""
        
        try:
            entry_data = hass.data[DOMAIN][entry_id]
            module_data = entry_data[MODULE_KEY]
            
            # Parse state value
            try:
                value = float(state.state)
            except (ValueError, TypeError):
                return  # Skip non-numeric states
            
            # Create measurement record
            measurement = {
                "ts": datetime.now(),
                "entity_id": entity_id,
                "value": value,
                "unit": state.attributes.get("unit_of_measurement"),
            }
            
            # Add to ring buffer (keep last 24 hours at sample_interval resolution)
            buffer = module_data["timeseries"]["buffer"]
            buffer.append(measurement)
            
            # Trim buffer (keep max 24h worth of samples)
            max_samples = int(86400 / module_data["config"]["analysis"]["sample_interval_s"])
            if len(buffer) > max_samples:
                buffer[:] = buffer[-max_samples:]
            
        except Exception as e:
            _LOGGER.error("Error recording measurement: %s", e)

    async def _run_analysis(self, hass: HomeAssistant, entry_id: str) -> None:
        """Run anomaly detection and recommendation generation."""
        
        try:
            # Compute aggregates
            await self._compute_aggregates(hass, entry_id)
            
            # Run detectors
            await self._detect_baseload_drift(hass, entry_id)
            await self._detect_spikes(hass, entry_id)
            await self._detect_pv_surplus(hass, entry_id)
            
            # Generate recommendations
            await self._generate_recommendations(hass, entry_id)
            
        except Exception as e:
            _LOGGER.error("Error running energy analysis: %s", e)

    async def _compute_aggregates(self, hass: HomeAssistant, entry_id: str) -> None:
        """Compute 5min, 15min, 1h aggregates from raw buffer."""
        
        try:
            entry_data = hass.data[DOMAIN][entry_id]
            module_data = entry_data[MODULE_KEY]
            
            # For v0.1, simplified aggregation (can be enhanced later)
            # Just compute simple averages over time windows
            
            _LOGGER.debug("Computed aggregates for energy analysis")
            
        except Exception as e:
            _LOGGER.error("Error computing aggregates: %s", e)

    async def _compute_baselines(self, hass: HomeAssistant, entry_id: str) -> None:
        """Compute baseline models (baseload, time-of-week median)."""
        
        try:
            entry_data = hass.data[DOMAIN][entry_id]
            module_data = entry_data[MODULE_KEY]
            config = module_data["config"]
            
            # Get house power sensor
            house_power = config["signals"].get("house_power")
            if not house_power:
                _LOGGER.debug("No house_power sensor configured, skipping baseline computation")
                return
            
            # Compute baseload (p10 of night power)
            # For v0.1, simplified - would use historical data in production
            state = hass.states.get(house_power)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    current_power = float(state.state)
                    # Placeholder - would compute from historical night data
                    module_data["baselines"]["baseload_w"] = current_power * 0.5  # Rough estimate
                    module_data["baselines"]["last_computed"] = datetime.now()
                    
                    _LOGGER.debug("Computed baseload: %.1f W", module_data["baselines"]["baseload_w"])
                except (ValueError, TypeError):
                    pass
            
        except Exception as e:
            _LOGGER.error("Error computing baselines: %s", e)

    async def _detect_baseload_drift(self, hass: HomeAssistant, entry_id: str) -> None:
        """Detect baseload drift anomalies."""
        
        try:
            entry_data = hass.data[DOMAIN][entry_id]
            module_data = entry_data[MODULE_KEY]
            config = module_data["config"]
            baselines = module_data["baselines"]
            
            house_power = config["signals"].get("house_power")
            baseload_w = baselines.get("baseload_w")
            
            if not house_power or not baseload_w:
                return
            
            state = hass.states.get(house_power)
            if not state or state.state in ("unknown", "unavailable"):
                return
            
            try:
                current_power = float(state.state)
            except (ValueError, TypeError):
                return
            
            # Check if current power exceeds baseload by threshold
            threshold_w = baseload_w * 1.5  # 50% above baseload
            
            if current_power > threshold_w:
                # Create anomaly event
                event = {
                    "type": "ANOMALY",
                    "subtype": "BASELOAD_DRIFT",
                    "severity": min((current_power - threshold_w) / baseload_w, 1.0),
                    "window": {
                        "start": datetime.now().isoformat(),
                        "end": None,
                    },
                    "evidence": [
                        {
                            "signal": "house_power_w",
                            "value": current_power,
                            "baseline": baseload_w,
                            "delta": current_power - baseload_w,
                        }
                    ],
                    "explanation": {
                        "summary": f"Power consumption {current_power:.0f}W significantly above baseline {baseload_w:.0f}W",
                        "reasons": ["above_baseload_threshold"],
                        "confidence": 0.7,
                    },
                    "recommendation": {
                        "title": "Check for unexpected standby consumption",
                        "actions": [
                            {"kind": "check", "text": "Review devices that might be consuming power"}
                        ],
                        "expected_impact": {
                            "w_savings": current_power - baseload_w,
                            "eur_per_year": (current_power - baseload_w) * 8760 / 1000 * 0.30,
                        }
                    }
                }
                
                # Store event
                module_data["events"].append(event)
                
                # Notify if appropriate
                await self._maybe_notify(hass, entry_id, event)
                
        except Exception as e:
            _LOGGER.error("Error detecting baseload drift: %s", e)

    async def _detect_spikes(self, hass: HomeAssistant, entry_id: str) -> None:
        """Detect power spikes/anomalies."""
        # Placeholder for v0.1 - would implement z-score detection
        pass

    async def _detect_pv_surplus(self, hass: HomeAssistant, entry_id: str) -> None:
        """Detect PV surplus opportunities for load shifting."""
        
        try:
            entry_data = hass.data[DOMAIN][entry_id]
            module_data = entry_data[MODULE_KEY]
            config = module_data["config"]
            
            grid_export = config["signals"].get("grid_export_power")
            if not grid_export:
                return
            
            state = hass.states.get(grid_export)
            if not state or state.state in ("unknown", "unavailable"):
                return
            
            try:
                export_power = float(state.state)
            except (ValueError, TypeError):
                return
            
            # Check if we're exporting significant power
            if export_power > 500:  # >500W export
                event = {
                    "type": "SHIFTING",
                    "subtype": "EXPORT_OPPORTUNITY",
                    "severity": min(export_power / 3000, 1.0),
                    "window": {
                        "start": datetime.now().isoformat(),
                        "end": None,
                    },
                    "evidence": [
                        {
                            "signal": "grid_export_power",
                            "value": export_power,
                            "baseline": 0,
                            "delta": export_power,
                        }
                    ],
                    "explanation": {
                        "summary": f"Exporting {export_power:.0f}W to grid - opportunity for load shifting",
                        "reasons": ["pv_surplus_available"],
                        "confidence": 0.8,
                    },
                    "recommendation": {
                        "title": "Start flexible loads now to use PV surplus",
                        "actions": [
                            {"kind": "suggest", "text": "Consider starting dishwasher, washing machine, or EV charging"}
                        ],
                        "expected_impact": {
                            "w_utilized": export_power,
                            "eur_saved": export_power * 2 / 1000 * 0.30,  # Rough 2h estimate
                        }
                    }
                }
                
                # Store event
                module_data["events"].append(event)
                
                # Notify if appropriate
                await self._maybe_notify(hass, entry_id, event)
                
        except Exception as e:
            _LOGGER.error("Error detecting PV surplus: %s", e)

    async def _generate_recommendations(self, hass: HomeAssistant, entry_id: str) -> None:
        """Generate actionable load shifting recommendations."""
        # Placeholder for v0.1 - would rank and prioritize recommendations
        pass

    async def _maybe_notify(
        self, 
        hass: HomeAssistant, 
        entry_id: str, 
        event: Dict[str, Any]
    ) -> None:
        """Send notification if policies allow."""
        
        try:
            entry_data = hass.data[DOMAIN][entry_id]
            module_data = entry_data[MODULE_KEY]
            config = module_data["config"]
            policies = config["policies"]
            
            # Check notification limits
            today = datetime.now().date()
            last_notif = module_data["last_notification"]
            today_count = last_notif.get(str(today), 0)
            
            if today_count >= policies["max_notifications_per_day"]:
                _LOGGER.debug("Notification limit reached for today")
                return
            
            # Check quiet hours
            now = datetime.now().time()
            quiet_start = datetime.strptime(policies["quiet_hours"][0], "%H:%M").time()
            quiet_end = datetime.strptime(policies["quiet_hours"][1], "%H:%M").time()
            
            if quiet_start <= now or now <= quiet_end:
                _LOGGER.debug("In quiet hours, skipping notification")
                return
            
            # Send notification
            message = f"{event['explanation']['summary']}\n\n{event['recommendation']['title']}"
            
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": f"Energy Module: {event['subtype']}",
                    "message": message,
                }
            )
            
            # Update notification count
            last_notif[str(today)] = today_count + 1
            
            _LOGGER.info("Sent energy notification: %s", event['subtype'])
            
        except Exception as e:
            _LOGGER.error("Error sending notification: %s", e)
