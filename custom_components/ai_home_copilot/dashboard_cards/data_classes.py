"""Data classes for comprehensive dashboard.

These data classes represent the dashboard's internal data structures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

# Import types from context modules
try:
    from .energy_context import EnergySnapshot
    from .weather_context import WeatherSnapshot
    from .calendar_context import CalendarContext
    from .media_context import MediaContextData
except ImportError:
    # Fallback if context modules not available
    EnergySnapshot = Any
    WeatherSnapshot = Any
    CalendarContext = Any
    MediaContextData = Any


@dataclass
class NeuronStatus:
    """Single neuron status."""
    name: str
    entity_id: str
    status: str  # "active", "inactive", "warning", "error"
    value: Any = None
    icon: str = "mdi:brain"
    last_update: datetime | None = None


@dataclass
class PresenceData:
    """Presence data for users."""
    users: dict[str, dict[str, Any]] = field(default_factory=dict)  # user_id -> {name, zone, status, last_seen}
    guest_count: int = 0
    total_presence: int = 0


@dataclass
class ActivityData:
    """Activity data for zones."""
    zones: dict[str, dict[str, Any]] = field(default_factory=dict)  # zone_id -> {activity_score, entities, last_activity}
    overall_activity: float = 0.0  # 0.0 - 1.0


@dataclass
class SystemHealthData:
    """System health data."""
    health_score: int = 100  # 0-100
    active_neurons: int = 0
    total_neurons: int = 0
    alerts: list[dict[str, Any]] = field(default_factory=list)
    last_reload: datetime | None = None


@dataclass
class DashboardData:
    """Complete dashboard data."""
    # Overview
    neurons: list[NeuronStatus] = field(default_factory=list)
    mood: dict[str, Any] = field(default_factory=dict)
    system_health: SystemHealthData = field(default_factory=SystemHealthData)
    
    # Detailed areas
    presence: PresenceData = field(default_factory=PresenceData)
    activity: ActivityData = field(default_factory=ActivityData)
    energy: Optional[Any] = None  # EnergySnapshot | None
    media: Optional[Any] = None  # MediaContextData | None
    weather: Optional[Any] = None  # WeatherSnapshot | None
    calendar: Optional[Any] = None  # CalendarContext | None
    
    # Meta
    last_update: datetime = field(default_factory=datetime.now)


__all__ = [
    "NeuronStatus",
    "PresenceData",
    "ActivityData",
    "SystemHealthData",
    "DashboardData",
]
