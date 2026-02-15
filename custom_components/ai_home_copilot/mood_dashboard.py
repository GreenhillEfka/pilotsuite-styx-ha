"""Mood Dashboard Card - Visualisierung der aktuellen Stimmung.

Features:
- Aktueller Mood mit Icon
- Confidence-Anzeige
- Top-Contributing Neuronen
- "Warum?" Button für Erklärung
- Timeline der Mood-Änderungen
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Mood Icons (Material Design Icons)
MOOD_ICONS = {
    "relax": "mdi:sofa",
    "focus": "mdi:target",
    "active": "mdi:run",
    "sleep": "mdi:sleep",
    "away": "mdi:home-export-outline",
    "alert": "mdi:alert",
    "social": "mdi:account-group",
    "recovery": "mdi:heart-pulse",
    "neutral": "mdi:robot-outline",
}

MOOD_COLORS = {
    "relax": "#4CAF50",   # Green
    "focus": "#2196F3",   # Blue
    "active": "#FF9800",  # Orange
    "sleep": "#9C27B0",   # Purple
    "away": "#607D8B",    # Gray
    "alert": "#F44336",   # Red
    "social": "#E91E63",  # Pink
    "recovery": "#00BCD4", # Cyan
    "neutral": "#9E9E9E", # Gray
}

MOOD_NAMES_DE = {
    "relax": "Entspannung",
    "focus": "Fokus",
    "active": "Aktiv",
    "sleep": "Schlaf",
    "away": "Abwesend",
    "alert": "Alarm",
    "social": "Sozial",
    "recovery": "Erholung",
    "neutral": "Neutral",
}


@dataclass
class MoodScore:
    """A single mood score with context."""
    mood_type: str
    value: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    source: str = "neuron"  # neuron, manual, learned
    timestamp: datetime = field(default_factory=dt_util.utcnow)
    
    # Contributing factors
    factors: list[dict[str, Any]] = field(default_factory=list)
    # [{"entity": "light.living_room", "weight": 0.3, "reason": "dimmed"}]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "mood_type": self.mood_type,
            "mood_value": self.value,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "factors": self.factors,
            "icon": MOOD_ICONS.get(self.mood_type, "mdi:help"),
            "color": MOOD_COLORS.get(self.mood_type, "#9E9E9E"),
            "name_de": MOOD_NAMES_DE.get(self.mood_type, self.mood_type),
        }


@dataclass
class MoodHistory:
    """History of mood changes."""
    entries: list[MoodScore] = field(default_factory=list)
    max_entries: int = 100
    
    def add(self, score: MoodScore) -> None:
        self.entries.insert(0, score)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[:self.max_entries]
    
    def get_recent(self, hours: int = 24) -> list[MoodScore]:
        cutoff = dt_util.utcnow() - timedelta(hours=hours)
        return [e for e in self.entries if e.timestamp > cutoff]
    
    def get_trend(self) -> str:
        """Get mood trend: rising, falling, stable."""
        if len(self.entries) < 3:
            return "stable"
        
        recent = self.entries[:3]
        values = [e.value for e in recent]
        
        if values[0] > values[-1] + 0.1:
            return "rising"
        elif values[0] < values[-1] - 0.1:
            return "falling"
        return "stable"


class MoodDashboardEntity(SensorEntity):
    """Sensor entity for current mood state."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:robot-happy"
    
    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_mood_dashboard"
        self._attr_name = "CoPilot Mood"
        self._mood_score: MoodScore | None = None
        self._history = MoodHistory()
        self._top_factors: list[dict[str, Any]] = []
        
    @property
    def native_value(self) -> str:
        if self._mood_score:
            return self._mood_score.mood_type
        return "neutral"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self._mood_score:
            return {
                "mood_value": 0.0,
                "confidence": 0.0,
                "icon": MOOD_ICONS["neutral"],
                "color": MOOD_COLORS["neutral"],
                "name_de": MOOD_NAMES_DE["neutral"],
                "top_factors": [],
                "history_count": len(self._history.entries),
                "trend": "stable",
            }
        
        return {
            "mood_value": self._mood_score.value,
            "confidence": self._mood_score.confidence,
            "icon": MOOD_ICONS.get(self._mood_score.mood_type, "mdi:help"),
            "color": MOOD_COLORS.get(self._mood_score.mood_type, "#9E9E9E"),
            "name_de": MOOD_NAMES_DE.get(self._mood_score.mood_type, self._mood_score.mood_type),
            "top_factors": self._top_factors[:5],
            "history_count": len(self._history.entries),
            "trend": self._history.get_trend(),
            "source": self._mood_score.source,
            "timestamp": self._mood_score.timestamp.isoformat(),
        }
    
    def update_mood(self, score: MoodScore) -> None:
        """Update the mood score."""
        self._mood_score = score
        self._history.add(score)
        self._top_factors = score.factors
        self._attr_icon = MOOD_ICONS.get(score.mood_type, "mdi:robot-outline")
        self.async_write_ha_state()


class MoodHistoryEntity(SensorEntity):
    """Sensor entity for mood history."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:history"
    
    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_mood_history"
        self._attr_name = "CoPilot Mood History"
        self._history = MoodHistory()
    
    @property
    def native_value(self) -> int:
        return len(self._history.entries)
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        recent = self._history.get_recent(24)
        return {
            "recent_count": len(recent),
            "last_24h": [e.to_dict() for e in recent[:10]],
            "trend": self._history.get_trend(),
        }
    
    def set_history(self, history: MoodHistory) -> None:
        self._history = history
        self.async_write_ha_state()


class MoodExplanationEntity(SensorEntity):
    """Sensor providing explanation of current mood."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:help-circle"
    
    def __init__(self, entry_id: str) -> None:
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_mood_explanation"
        self._attr_name = "CoPilot Mood Explanation"
        self._explanation: str = ""
        self._factors: list[dict[str, Any]] = []
    
    @property
    def native_value(self) -> str:
        return self._explanation[:255] if self._explanation else "Keine Mood-Daten verfügbar"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "explanation": self._explanation,
            "factors": self._factors,
            "factors_count": len(self._factors),
        }
    
    def update_explanation(self, mood_score: MoodScore | None) -> None:
        """Generate explanation from mood score."""
        if not mood_score:
            self._explanation = "Keine Mood-Daten verfügbar"
            self._factors = []
            return
        
        # Build explanation
        mood_name = MOOD_NAMES_DE.get(mood_score.mood_type, mood_score.mood_type)
        confidence_pct = int(mood_score.confidence * 100)
        value_pct = int(mood_score.value * 100)
        
        lines = [
            f"Aktuelle Stimmung: {mood_name} ({value_pct}%)",
            f"Konfidenz: {confidence_pct}%",
        ]
        
        if mood_score.factors:
            lines.append("\nEinflussfaktoren:")
            for i, factor in enumerate(mood_score.factors[:5], 1):
                entity = factor.get("entity", "Unbekannt")
                weight = factor.get("weight", 0)
                reason = factor.get("reason", "")
                lines.append(f"  {i}. {entity}: {weight:.0%} ({reason})")
        
        # Add trend info
        if mood_score.source == "neuron":
            lines.append("\nQuelle: Neuronen-System")
        elif mood_score.source == "learned":
            lines.append("\nQuelle: Gelerntes Muster")
        
        self._explanation = "\n".join(lines)
        self._factors = mood_score.factors
        self.async_write_ha_state()


# --- Dashboard Card Generator ---

def generate_mood_card_config(entry_id: str) -> dict[str, Any]:
    """Generate Lovelace card configuration for mood dashboard."""
    return {
        "type": "vertical-stack",
        "cards": [
            {
                "type": "custom:mushroom-entity-card",
                "entity": f"sensor.{entry_id}_copilot_mood",
                "name": "CoPilot Mood",
                "icon_color": f"{{{{ state_attr('sensor.{entry_id}_copilot_mood', 'color') }}}}",
                "primary_info": "name",
                "secondary_info": "last-changed",
            },
            {
                "type": "markdown",
                "content": f"""
## {{{{ state_attr('sensor.{entry_id}_copilot_mood', 'name_de') }}}}

**Wert:** {{{{ (state_attr('sensor.{entry_id}_copilot_mood', 'mood_value') * 100) | round(0) }}}}%
**Konfidenz:** {{{{ (state_attr('sensor.{entry_id}_copilot_mood', 'confidence') * 100) | round(0) }}}}%
**Trend:** {{{{ state_attr('sensor.{entry_id}_copilot_mood', 'trend') }}}}

### Top-Faktoren
{{% for factor in state_attr('sensor.{entry_id}_copilot_mood', 'top_factors')[:5] %}}
- {{{{ factor.entity }}}}: {{{{ (factor.weight * 100) | round(0) }}}}% ({{{{ factor.reason }}}})
{{% endfor %}}
""",
            },
            {
                "type": "conditional",
                "conditions": [
                    {
                        "entity": f"sensor.{entry_id}_copilot_mood",
                        "state_not": "neutral",
                    }
                ],
                "card": {
                    "type": "markdown",
                    "title": "Warum?",
                    "content": f"{{{{ state_attr('sensor.{entry_id}_copilot_mood_explanation', 'explanation') }}}}",
                },
            },
        ],
    }


def generate_suggestion_queue_card(entry_id: str) -> dict[str, Any]:
    """Generate Lovelace card for suggestion queue."""
    return {
        "type": "custom:mushroom-template-card",
        "primary": "CoPilot Vorschläge",
        "secondary": "{{ state_attr('sensor.{entry_id}_suggestion_queue', 'pending_count') }} ausstehend",
        "icon": "mdi:lightbulb-outline",
        "icon_color": "amber",
        "tap_action": {
            "action": "more-info",
            "entity": f"sensor.{entry_id}_suggestion_queue",
        },
    }


# --- Setup ---

async def async_setup_mood_dashboard(
    hass: HomeAssistant,
    entry_id: str,
    async_add_entities: AddEntitiesCallback,
) -> list[MoodDashboardEntity]:
    """Setup mood dashboard entities.
    
    Also sets up listeners for:
    - Module Connector mood alerts
    - Notification patterns
    """
    
    entities = [
        MoodDashboardEntity(entry_id),
        MoodHistoryEntity(entry_id),
        MoodExplanationEntity(entry_id),
    ]
    
    async_add_entities(entities)
    
    # Store for updates
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry_id, {})
    hass.data[DOMAIN][entry_id]["mood_entities"] = entities
    
    # Set up listener for mood alerts from module connector
    async def on_mood_alert(event):
        """Handle mood alert from module connector."""
        alert_data = event.data
        
        alert_type = alert_data.get("alert_type", "")
        severity = alert_data.get("severity", "normal")
        message = alert_data.get("message", "")
        factors = alert_data.get("factors", [])
        
        # Convert alert type to mood type
        mood_type_map = {
            "focus": "focus",
            "stress": "alert",
            "relax": "relax",
            "social": "social",
        }
        
        mood_type = mood_type_map.get(alert_type, "neutral")
        
        # Calculate value based on severity
        value_map = {
            "low": 0.3,
            "normal": 0.5,
            "high": 0.7,
            "critical": 0.9,
        }
        value = value_map.get(severity, 0.5)
        
        # Add factors
        all_factors = factors + [
            {"source": "notification", "alert_type": alert_type, "severity": severity}
        ]
        
        # Update mood
        await async_update_mood_from_neuron(
            hass,
            entry_id,
            mood_type,
            value,
            0.8,  # confidence
            all_factors,
        )
        
        _LOGGER.debug("Mood updated from notification alert: %s (%s)", mood_type, severity)
    
    # Listen for mood alerts
    hass.bus.async_listen(f"{DOMAIN}_mood_alert", on_mood_alert)
    
    return entities


async def async_update_mood_from_neuron(
    hass: HomeAssistant,
    entry_id: str,
    mood_type: str,
    value: float,
    confidence: float,
    factors: list[dict[str, Any]],
) -> None:
    """Update mood dashboard from neuron evaluation."""
    
    entities = hass.data.get(DOMAIN, {}).get(entry_id, {}).get("mood_entities", [])
    
    if not entities:
        return
    
    score = MoodScore(
        mood_type=mood_type,
        value=value,
        confidence=confidence,
        source="neuron",
        factors=factors,
    )
    
    # Update main mood entity
    if isinstance(entities[0], MoodDashboardEntity):
        entities[0].update_mood(score)
    
    # Update explanation entity
    if isinstance(entities[2], MoodExplanationEntity):
        entities[2].update_explanation(score)
    
    # Fire event for dashboard refresh
    hass.bus.async_fire(f"{DOMAIN}_mood_updated", score.to_dict())