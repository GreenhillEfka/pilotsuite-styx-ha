"""
Dashboard Cards Module
======================

Lovelace UI card generators for AI Home Copilot:

Comprehensive Dashboard:
- Dashboard Overview Card (Neuronen Status, Mood, Zones, System Health)
- Detailed Cards: Presence, Activity, Energy, Media, Weather, Calendar
- Complete All-in-One Dashboard
- Mobile Responsive Dashboard

Interactive Elements:
- Clickable Neuron Cards
- Detail View Cards
- Filter Cards

Mobile Features:
- Responsive Grid Layout
- Adaptive Cards
- Dark/Light Mode Support
- Touch-Optimized Controls

Path: /config/.openclaw/workspace/ai_home_copilot_hacs_repo/custom_components/ai_home_copilot/dashboard_cards/
"""

from __future__ import annotations

# Existing cards
from .energy_distribution_card import create_energy_distribution_card
from .media_context_card import create_media_context_card
from .zone_context_card import create_zone_context_card, ZoneContextData
from .user_together_card import create_user_together_card
from .mesh_monitoring_card import (
    create_mesh_network_health_card,
    create_battery_overview_card,
    get_mesh_data_from_hass,
    MeshNetworkData,
)

# New comprehensive dashboard
from .comprehensive_dashboard import (
    # Data classes
    NeuronStatus,
    PresenceData,
    ActivityData,
    SystemHealthData,
    DashboardData,
    # Overview
    create_dashboard_overview_card,
    # Detailed cards
    create_presence_card,
    create_activity_card,
    create_energy_card,
    create_media_card,
    create_weather_card,
    create_calendar_card,
    # Complete dashboards
    create_complete_dashboard,
    create_mobile_dashboard,
    # YAML export
    dashboard_to_yaml,
)

# Interactive dashboard
from .interactive_dashboard import (
    create_neuron_detail_card,
    create_neuron_grid_card,
    create_filter_card,
    create_zone_filter_card,
    create_status_filter_card,
    create_neuron_detail_view,
    create_zone_detail_view,
    create_info_modal,
    create_confirm_dialog,
    create_filterable_dashboard,
)

# Mobile responsive dashboard
from .mobile_responsive_dashboard import (
    ResponsiveConfig,
    create_responsive_grid,
    create_adaptive_card,
    create_adaptive_stat_card,
    get_theme_colors,
    apply_theme_styles,
    create_touch_card,
    create_swipeable_card,
    create_mobile_overview_layout,
    create_mobile_dashboard_layout,
    create_responsive_sensor_card,
    create_complete_mobile_dashboard,
    create_theme_switcher_card,
)


__all__ = [
    # === Existing cards ===
    "create_energy_distribution_card",
    "create_media_context_card",
    "create_zone_context_card",
    "create_zone_context_data",
    "create_user_together_card",
    "create_mesh_network_health_card",
    "create_battery_overview_card",
    "get_mesh_data_from_hass",
    "MeshNetworkData",
    
    # === Comprehensive Dashboard ===
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
    
    # === Interactive Dashboard ===
    "create_neuron_detail_card",
    "create_neuron_grid_card",
    "create_filter_card",
    "create_zone_filter_card",
    "create_status_filter_card",
    "create_neuron_detail_view",
    "create_zone_detail_view",
    "create_info_modal",
    "create_confirm_dialog",
    "create_filterable_dashboard",
    
    # === Mobile Responsive Dashboard ===
    "ResponsiveConfig",
    "create_responsive_grid",
    "create_adaptive_card",
    "create_adaptive_stat_card",
    "get_theme_colors",
    "apply_theme_styles",
    "create_touch_card",
    "create_swipeable_card",
    "create_mobile_overview_layout",
    "create_mobile_dashboard_layout",
    "create_responsive_sensor_card",
    "create_complete_mobile_dashboard",
    "create_theme_switcher_card",
]
