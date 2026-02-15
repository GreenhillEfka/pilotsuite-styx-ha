"""Comprehensive Dashboard Cards Module - Lazy Loading Facade.

This module is a lazy-loading facade that imports card builders from
individual modules for better code organization and maintainability.

All-in-One Dashboard for AI Home CoPilot with:
- Dashboard Overview Card (Neuronen Status, Mood, Zones, System Health)
- Detailed Cards: Presence, Activity, Energy, Media, Weather, Calendar
- Interactive Elements (Clickable neurons, detail views, filters)
- Mobile Responsive (Grid layout, adaptive cards, dark/light mode)

Path: /config/.openclaw/workspace/ai_home_copilot_hacs_repo/custom_components/ai_home_copilot/dashboard_cards/
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

# Lazy imports for better performance
if TYPE_CHECKING:
    from .data_classes import (
        NeuronStatus,
        PresenceData,
        ActivityData,
        SystemHealthData,
        DashboardData,
    )

_LOGGER = logging.getLogger(__name__)


def __getattr__(name: str):
    """Lazy import from split modules."""
    
    # Data classes
    if name == "NeuronStatus":
        from .data_classes import NeuronStatus
        return NeuronStatus
    if name == "PresenceData":
        from .data_classes import PresenceData
        return PresenceData
    if name == "ActivityData":
        from .data_classes import ActivityData
        return ActivityData
    if name == "SystemHealthData":
        from .data_classes import SystemHealthData
        return SystemHealthData
    if name == "DashboardData":
        from .data_classes import DashboardData
        return DashboardData
    
    # Overview cards
    if name == "create_dashboard_overview_card":
        from .overview_cards import create_dashboard_overview_card
        return create_dashboard_overview_card
    
    # Presence/Activity cards
    if name == "create_presence_card":
        from .presence_activity_cards import create_presence_card
        return create_presence_card
    if name == "create_activity_card":
        from .presence_activity_cards import create_activity_card
        return create_activity_card
    
    # Energy/Media cards
    if name == "create_energy_card":
        from .energy_media_cards import create_energy_card
        return create_energy_card
    if name == "create_media_card":
        from .energy_media_cards import create_media_card
        return create_media_card
    
    # Weather/Calendar cards
    if name == "create_weather_card":
        from .weather_calendar_cards import create_weather_card
        return create_weather_card
    if name == "create_calendar_card":
        from .weather_calendar_cards import create_calendar_card
        return create_calendar_card
    
    # Complete dashboards
    if name == "create_complete_dashboard":
        from .complete_dashboard import create_complete_dashboard
        return create_complete_dashboard
    if name == "create_mobile_dashboard":
        from .complete_dashboard import create_mobile_dashboard
        return create_mobile_dashboard
    if name == "dashboard_to_yaml":
        from .complete_dashboard import dashboard_to_yaml
        return dashboard_to_yaml
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Explicit exports for static analysis and IDE support
__all__ = [
    # Data classes
    "NeuronStatus",
    "PresenceData",
    "ActivityData",
    "SystemHealthData",
    "DashboardData",
    
    # Overview
    "create_dashboard_overview_card",
    
    # Detailed cards
    "create_presence_card",
    "create_activity_card",
    "create_energy_card",
    "create_media_card",
    "create_weather_card",
    "create_calendar_card",
    
    # Complete dashboards
    "create_complete_dashboard",
    "create_mobile_dashboard",
    
    # Export
    "dashboard_to_yaml",
]
