"""Dashboard Cards Module - Lazy Loading.

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

# Lazy loading pattern - import from submodules only when needed
# This reduces startup time by deferring imports of large modules


def __getattr__(name: str):
    """Lazy import from dashboard card modules."""
    
    # Existing cards
    if name == "create_energy_distribution_card":
        from .energy_distribution_card import create_energy_distribution_card
        return create_energy_distribution_card
    if name == "create_media_context_card":
        from .media_context_card import create_media_context_card
        return create_media_context_card
    if name == "create_zone_context_card":
        from .zone_context_card import create_zone_context_card
        return create_zone_context_card
    if name == "ZoneContextData":
        from .zone_context_card import ZoneContextData
        return ZoneContextData
    if name == "create_user_together_card":
        from .user_together_card import create_user_together_card
        return create_user_together_card
    if name == "create_mesh_network_health_card":
        from .mesh_monitoring_card import create_mesh_network_health_card
        return create_mesh_network_health_card
    if name == "create_battery_overview_card":
        from .mesh_monitoring_card import create_battery_overview_card
        return create_battery_overview_card
    if name == "get_mesh_data_from_hass":
        from .mesh_monitoring_card import get_mesh_data_from_hass
        return get_mesh_data_from_hass
    if name == "MeshNetworkData":
        from .mesh_monitoring_card import MeshNetworkData
        return MeshNetworkData
    
    # Comprehensive dashboard - imports from split modules
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
    if name == "create_dashboard_overview_card":
        from .overview_cards import create_dashboard_overview_card
        return create_dashboard_overview_card
    if name == "create_presence_card":
        from .presence_activity_cards import create_presence_card
        return create_presence_card
    if name == "create_activity_card":
        from .presence_activity_cards import create_activity_card
        return create_activity_card
    if name == "create_energy_card":
        from .energy_media_cards import create_energy_card
        return create_energy_card
    if name == "create_media_card":
        from .energy_media_cards import create_media_card
        return create_media_card
    if name == "create_weather_card":
        from .weather_calendar_cards import create_weather_card
        return create_weather_card
    if name == "create_calendar_card":
        from .weather_calendar_cards import create_calendar_card
        return create_calendar_card
    if name == "create_complete_dashboard":
        from .complete_dashboard import create_complete_dashboard
        return create_complete_dashboard
    if name == "create_mobile_dashboard":
        from .complete_dashboard import create_mobile_dashboard
        return create_mobile_dashboard
    if name == "dashboard_to_yaml":
        from .complete_dashboard import dashboard_to_yaml
        return dashboard_to_yaml
    
    # Interactive dashboard
    if name == "create_neuron_detail_card":
        from .interactive_dashboard import create_neuron_detail_card
        return create_neuron_detail_card
    if name == "create_neuron_grid_card":
        from .interactive_dashboard import create_neuron_grid_card
        return create_neuron_grid_card
    if name == "create_filter_card":
        from .interactive_dashboard import create_filter_card
        return create_filter_card
    if name == "create_zone_filter_card":
        from .interactive_dashboard import create_zone_filter_card
        return create_zone_filter_card
    if name == "create_status_filter_card":
        from .interactive_dashboard import create_status_filter_card
        return create_status_filter_card
    if name == "create_neuron_detail_view":
        from .interactive_dashboard import create_neuron_detail_view
        return create_neuron_detail_view
    if name == "create_zone_detail_view":
        from .interactive_dashboard import create_zone_detail_view
        return create_zone_detail_view
    if name == "create_info_modal":
        from .interactive_dashboard import create_info_modal
        return create_info_modal
    if name == "create_confirm_dialog":
        from .interactive_dashboard import create_confirm_dialog
        return create_confirm_dialog
    if name == "create_filterable_dashboard":
        from .interactive_dashboard import create_filterable_dashboard
        return create_filterable_dashboard
    
    # Mobile responsive dashboard
    if name == "ResponsiveConfig":
        from .mobile_responsive_dashboard import ResponsiveConfig
        return ResponsiveConfig
    if name == "create_responsive_grid":
        from .mobile_responsive_dashboard import create_responsive_grid
        return create_responsive_grid
    if name == "create_adaptive_card":
        from .mobile_responsive_dashboard import create_adaptive_card
        return create_adaptive_card
    if name == "create_adaptive_stat_card":
        from .mobile_responsive_dashboard import create_adaptive_stat_card
        return create_adaptive_stat_card
    if name == "get_theme_colors":
        from .mobile_responsive_dashboard import get_theme_colors
        return get_theme_colors
    if name == "apply_theme_styles":
        from .mobile_responsive_dashboard import apply_theme_styles
        return apply_theme_styles
    if name == "create_touch_card":
        from .mobile_responsive_dashboard import create_touch_card
        return create_touch_card
    if name == "create_swipeable_card":
        from .mobile_responsive_dashboard import create_swipeable_card
        return create_swipeable_card
    if name == "create_mobile_overview_layout":
        from .mobile_responsive_dashboard import create_mobile_overview_layout
        return create_mobile_overview_layout
    if name == "create_mobile_dashboard_layout":
        from .mobile_responsive_dashboard import create_mobile_dashboard_layout
        return create_mobile_dashboard_layout
    if name == "create_responsive_sensor_card":
        from .mobile_responsive_dashboard import create_responsive_sensor_card
        return create_responsive_sensor_card
    if name == "create_complete_mobile_dashboard":
        from .mobile_responsive_dashboard import create_complete_mobile_dashboard
        return create_complete_mobile_dashboard
    if name == "create_theme_switcher_card":
        from .mobile_responsive_dashboard import create_theme_switcher_card
        return create_theme_switcher_card
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Explicit exports for static analysis and IDE support
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
