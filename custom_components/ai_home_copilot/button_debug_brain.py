from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components import persistent_notification
from homeassistant.helpers.entity import EntityCategory

from .brain_graph_panel import async_publish_brain_graph_panel
from .brain_graph_viz import async_publish_brain_graph_viz
from .core_v1 import async_call_core_api
from .entity import CopilotBaseEntity


class CopilotPublishBrainGraphVizButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = True
    _attr_entity_category = None
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot publish brain graph viz"
    _attr_unique_id = "ai_home_copilot_publish_brain_graph_viz"
    _attr_icon = "mdi:graph"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_publish_brain_graph_viz(self.hass, self.coordinator)


class CopilotPublishBrainGraphPanelButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = True
    _attr_entity_category = None
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot publish brain graph panel (Phase 5)"
    _attr_unique_id = "ai_home_copilot_publish_brain_graph_panel"
    _attr_icon = "mdi:graph"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_publish_brain_graph_panel(self.hass, self.coordinator)


class CopilotBrainGraphPanelVizButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot brain graph panel (v0.8)"
    _attr_unique_id = "ai_home_copilot_brain_graph_panel"
    _attr_icon = "mdi:graph-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_publish_brain_graph_panel(self.hass, self.coordinator)


class CopilotBrainDashboardSummaryButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = True
    _attr_entity_category = None
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot brain dashboard summary"
    _attr_unique_id = "ai_home_copilot_brain_dashboard_summary"
    _attr_icon = "mdi:brain"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        try:
            dashboard_data = await async_call_core_api(
                self.hass, self._entry, "GET", "/api/v1/dashboard/brain-summary"
            )

            if not dashboard_data:
                raise Exception("No response from Core Add-on")

            brain_stats = dashboard_data.get("brain_graph", {})
            activity = dashboard_data.get("activity", {})
            health = dashboard_data.get("health", {})
            recommendations = dashboard_data.get("recommendations", [])

            nodes = brain_stats.get("nodes", 0)
            edges = brain_stats.get("edges", 0)
            events_24h = activity.get("events_24h", 0)
            active_entities = activity.get("active_entities", 0)
            health_score = health.get("score", 0)
            status = health.get("status", "Unknown")

            summary_lines = [
                f"**Brain Graph Status: {status} ({health_score}/100)**",
                f"📊 Nodes: {nodes}, Edges: {edges}",
                f"⚡ Activity: {events_24h} events, {active_entities} entities (24h)",
            ]

            if recommendations:
                summary_lines.append("**Recommendations:**")
                for rec in recommendations[:3]:
                    summary_lines.append(f"• {rec}")

            summary_text = "\n".join(summary_lines)

            persistent_notification.async_create(
                self.hass,
                summary_text,
                title="🧠 Brain Dashboard Summary",
                notification_id="ai_home_copilot_brain_dashboard_summary",
            )

        except Exception as err:  # noqa: BLE001
            persistent_notification.async_create(
                self.hass,
                f"Failed to fetch brain dashboard summary: {str(err)}",
                title="AI Home CoPilot Brain Dashboard",
                notification_id="ai_home_copilot_brain_dashboard_error",
            )
