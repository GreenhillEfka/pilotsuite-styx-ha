"""Mood sensor entities v3.0 for PilotSuite Styx.

Exposes the unified mood system to Home Assistant:
- MoodSensor: discrete state (relax/focus/active/night/away/neutral)
- MoodConfidenceSensor: inference confidence (0–100%)
- MoodComfortSensor: comfort dimension (0–100%)
- MoodJoySensor: joy dimension (0–100%)
- MoodEnergySensor: energy dimension (0–100%)
- MoodStressSensor: stress dimension (0–100%)
- MoodFrugalitySensor: frugality dimension (0–100%)
- NeuronActivitySensor: active neuron count + activity grid

All dimensions are exposed as separate sensors for automation triggers,
while the main MoodSensor carries the full profile in its attributes.
"""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import CopilotDataUpdateCoordinator
from ..entity import CopilotBaseEntity

_LOGGER = logging.getLogger(__name__)

# Mood icon mapping
_MOOD_ICONS = {
    "relax": "mdi:sofa",
    "focus": "mdi:head-lightbulb",
    "active": "mdi:run-fast",
    "night": "mdi:weather-night",
    "away": "mdi:home-export-outline",
    "neutral": "mdi:robot-happy",
    "unknown": "mdi:help-circle",
}

_MAX_MOOD_HISTORY = 20


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class MoodSensor(CoordinatorEntity, SensorEntity):
    """Primary mood sensor — discrete state with full profile attributes."""

    _attr_name = "PilotSuite Mood"
    _attr_unique_id = "ai_home_copilot_mood"
    _attr_icon = "mdi:robot-happy"
    _attr_should_poll = False

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_native_value = "unknown"
        self._mood_history: deque[str] = deque(maxlen=_MAX_MOOD_HISTORY)
        self._last_mood: str | None = None
        self._mood_since: str | None = None

    def _current_mood(self) -> str:
        if not self.coordinator.data:
            return "unknown"
        mood_data = self.coordinator.data.get("mood", {})
        if not isinstance(mood_data, dict):
            return "unknown"
        return str(mood_data.get("mood", mood_data.get("state", "unknown")) or "unknown")

    @property
    def native_value(self) -> str:
        current = self._current_mood()
        if current != self._last_mood:
            self._mood_history.append(current)
            self._mood_since = datetime.now(timezone.utc).isoformat()
            self._last_mood = current
        return current

    @property
    def icon(self) -> str:
        return _MOOD_ICONS.get(self._current_mood(), "mdi:robot-happy")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if not self.coordinator.data:
            return {}

        mood_data = self.coordinator.data.get("mood", {})
        if not isinstance(mood_data, dict):
            return {}
        dims = mood_data.get("dimensions", {})
        if not isinstance(dims, dict):
            dims = {}
        features = mood_data.get("features", {})
        if not isinstance(features, dict):
            features = {}

        # Emotions for ha-copilot-mood-card compatibility
        emotions = mood_data.get("emotions", [])
        if not emotions and mood_data.get("contributing_neurons"):
            emotions = [
                {"name": n.get("name", "unknown"), "value": n.get("value", 0.0)}
                for n in mood_data.get("contributing_neurons", [])
                if isinstance(n, dict)
            ]

        # Mood stability
        stability = 0.0
        if self._mood_history:
            current = self._current_mood()
            matching = sum(1 for m in self._mood_history if m == current)
            stability = round(matching / len(self._mood_history), 2)

        # State probabilities
        probs = mood_data.get("state_probabilities", {})

        return {
            "confidence": mood_data.get("confidence", 0.0),
            "emotions": emotions,
            "zone": mood_data.get("zone", mood_data.get("zone_id", "unknown")),
            "last_update": mood_data.get("last_update", mood_data.get("timestamp")),
            "contributing_neurons": mood_data.get("contributing_neurons", []),
            "contributing_entities": mood_data.get("contributing_entities", []),
            # Continuous dimensions
            "comfort": dims.get("comfort", features.get("comfort_index", 0.5)),
            "frugality": dims.get("frugality", 0.5),
            "joy": dims.get("joy", 0.5),
            "energy": dims.get("energy", features.get("energy_level", 0.5)),
            "stress": dims.get("stress", features.get("stress_index", 0.0)),
            # Context
            "time_of_day": mood_data.get("time_of_day", ""),
            "occupancy_level": mood_data.get("occupancy_level", ""),
            "media_playing": mood_data.get("media_playing", False),
            "motion_recent": mood_data.get("motion_recent", False),
            "ambient_dark": mood_data.get("ambient_dark", False),
            "quiet_hours": mood_data.get("quiet_hours", False),
            # Stability
            "mood_since": self._mood_since,
            "mood_stability": stability,
            # Softmax probabilities
            "state_probabilities": probs,
            "reasons": mood_data.get("reasons", []),
        }

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class MoodConfidenceSensor(CoordinatorEntity, SensorEntity):
    """Mood inference confidence (0–100%)."""

    _attr_name = "PilotSuite Mood Confidence"
    _attr_unique_id = "ai_home_copilot_mood_confidence"
    _attr_icon = "mdi:gauge"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_native_value = 0

    @property
    def native_value(self) -> int:
        if not self.coordinator.data:
            return 0
        mood_data = self.coordinator.data.get("mood", {})
        if not isinstance(mood_data, dict):
            return 0
        return int(_safe_float(mood_data.get("confidence", 0.0)) * 100)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if not self.coordinator.data:
            return {}
        mood_data = self.coordinator.data.get("mood", {})
        if not isinstance(mood_data, dict):
            return {}
        return {
            "mood": mood_data.get("mood", mood_data.get("state", "unknown")),
            "state_probabilities": mood_data.get("state_probabilities", {}),
        }

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class _MoodDimensionSensor(CoordinatorEntity, SensorEntity):
    """Base class for continuous mood dimension sensors."""

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False
    _dimension_key: str = ""
    _fallback_key: str = ""

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_native_value = 50

    @property
    def native_value(self) -> int:
        if not self.coordinator.data:
            return 50
        mood_data = self.coordinator.data.get("mood", {})
        if not isinstance(mood_data, dict):
            return 50
        dims = mood_data.get("dimensions", {})
        if not isinstance(dims, dict):
            dims = {}
        features = mood_data.get("features", {})
        if not isinstance(features, dict):
            features = {}
        raw = dims.get(self._dimension_key, features.get(self._fallback_key, 0.5))
        return int(_safe_float(raw, 0.5) * 100)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if not self.coordinator.data:
            return {}
        mood_data = self.coordinator.data.get("mood", {})
        if not isinstance(mood_data, dict):
            return {}
        value = self.native_value
        return {
            "mood": mood_data.get("mood", mood_data.get("state", "unknown")),
            "zone": mood_data.get("zone", mood_data.get("zone_id", "")),
            "raw_value": value / 100.0,
        }

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class MoodComfortSensor(_MoodDimensionSensor):
    """Comfort dimension (0–100%)."""

    _attr_name = "PilotSuite Mood Comfort"
    _attr_unique_id = "ai_home_copilot_mood_comfort"
    _attr_icon = "mdi:sofa-outline"
    _dimension_key = "comfort"
    _fallback_key = "comfort_index"


class MoodJoySensor(_MoodDimensionSensor):
    """Joy dimension (0–100%)."""

    _attr_name = "PilotSuite Mood Joy"
    _attr_unique_id = "ai_home_copilot_mood_joy"
    _attr_icon = "mdi:emoticon-happy-outline"
    _dimension_key = "joy"
    _fallback_key = "joy"


class MoodEnergySensor(_MoodDimensionSensor):
    """Energy dimension (0–100%)."""

    _attr_name = "PilotSuite Mood Energy"
    _attr_unique_id = "ai_home_copilot_mood_energy"
    _attr_icon = "mdi:lightning-bolt"
    _dimension_key = "energy"
    _fallback_key = "energy_level"


class MoodStressSensor(_MoodDimensionSensor):
    """Stress dimension (0–100%)."""

    _attr_name = "PilotSuite Mood Stress"
    _attr_unique_id = "ai_home_copilot_mood_stress"
    _attr_icon = "mdi:alert-circle-outline"
    _dimension_key = "stress"
    _fallback_key = "stress_index"


class MoodFrugalitySensor(_MoodDimensionSensor):
    """Frugality/energy-saving preference (0–100%)."""

    _attr_name = "PilotSuite Mood Frugality"
    _attr_unique_id = "ai_home_copilot_mood_frugality"
    _attr_icon = "mdi:leaf"
    _dimension_key = "frugality"
    _fallback_key = "frugality"


class NeuronActivitySensor(CoordinatorEntity, SensorEntity):
    """Active neurons count + activity grid for Lovelace card."""

    _attr_name = "PilotSuite Neuron Activity"
    _attr_unique_id = "ai_home_copilot_neuron_activity"
    _attr_icon = "mdi:brain"
    _attr_should_poll = False

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_native_value = 0
        self._history: list[dict] = []

    @property
    def native_value(self) -> int:
        if not self.coordinator.data:
            return 0
        neurons = self.coordinator.data.get("neurons", {})
        if not isinstance(neurons, dict):
            return 0
        return sum(
            1 for n in neurons.values()
            if isinstance(n, dict) and n.get("active", False)
        )

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if not self.coordinator.data:
            return {}

        neurons = self.coordinator.data.get("neurons", {})
        if not isinstance(neurons, dict):
            return {}
        activity = [
            {
                "name": name,
                "active": bool(n.get("active", False)),
                "value": n.get("value", 0),
                "confidence": n.get("confidence", 0),
            }
            for name, n in neurons.items()
            if isinstance(n, dict)
        ]

        active_neurons = [a for a in activity if a["active"]]
        return {
            "activity": activity,
            "active_neurons": active_neurons,
            "total_neurons": len(neurons),
            "history": list(self._history),
        }

    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data:
            neurons = self.coordinator.data.get("neurons", {})
            if isinstance(neurons, dict):
                current_active = sum(
                    1 for n in neurons.values()
                    if isinstance(n, dict) and n.get("active", False)
                )
                self._history.append({"value": current_active})
                if len(self._history) > 24:
                    self._history = self._history[-24:]
        self.async_write_ha_state()


def _safe_entity_float(hass: HomeAssistant, entity_id: str, default: float = 0.0) -> float:
    """Safely get a float value from an entity state."""
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable", ""):
        return default
    try:
        return float(state.state)
    except (ValueError, TypeError):
        return default


class LiveMoodDimensionSensor(SensorEntity):
    """Base class for live mood dimension sensors (Comfort/Joy/Frugality).

    Reads from hass.data live_mood dict populated by LiveMoodEngineModule.
    """

    _attr_should_poll = True
    _attr_native_unit_of_measurement = "%"

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        dimension: str,
        name: str,
        icon: str,
    ) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._dimension = dimension
        self._attr_name = name
        self._attr_unique_id = f"ai_home_copilot_mood_{dimension}"
        self._attr_icon = icon

    @property
    def native_value(self) -> int:
        """Return the mood dimension as percentage (0-100)."""
        live_mood = (
            self.hass.data.get(DOMAIN, {})
            .get(self._entry_id, {})
            .get("live_mood", {})
        )
        if not live_mood:
            return 0
        # Average across all zones
        values = [
            z.get(self._dimension, 0.0)
            for z in live_mood.values()
            if isinstance(z, dict)
        ]
        if not values:
            return 0
        return int(sum(values) / len(values) * 100)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return per-zone breakdown."""
        live_mood = (
            self.hass.data.get(DOMAIN, {})
            .get(self._entry_id, {})
            .get("live_mood", {})
        )
        if not live_mood:
            return {}
        per_zone = {}
        for zone_id, moods in live_mood.items():
            if isinstance(moods, dict):
                per_zone[zone_id] = round(moods.get(self._dimension, 0.0), 3)
        return {"per_zone": per_zone, "zone_count": len(per_zone)}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up mood sensors from a config entry."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("coordinator")
    if coordinator is None:
        return

    sensors: list[SensorEntity] = [
        MoodSensor(coordinator),
        MoodConfidenceSensor(coordinator),
        MoodComfortSensor(coordinator),
        MoodJoySensor(coordinator),
        MoodEnergySensor(coordinator),
        MoodStressSensor(coordinator),
        MoodFrugalitySensor(coordinator),
        NeuronActivitySensor(coordinator),
        LiveMoodDimensionSensor(
            hass, entry.entry_id, "comfort", "PilotSuite Mood Comfort", "mdi:sofa"
        ),
        LiveMoodDimensionSensor(
            hass, entry.entry_id, "joy", "PilotSuite Mood Joy", "mdi:emoticon-happy"
        ),
        LiveMoodDimensionSensor(
            hass, entry.entry_id, "frugality", "PilotSuite Mood Frugality", "mdi:leaf"
        ),
    ]

    async_add_entities(sensors)
    _LOGGER.info("Mood sensors v3.0 set up (%d sensors, incl. Comfort/Joy/Frugality) for entry %s", len(sensors), entry.entry_id)
