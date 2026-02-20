"""Graph and brain-related buttons for PilotSuite."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory

from .entity import CopilotBaseEntity
from .brain_graph_viz import async_publish_brain_graph_viz
from .brain_graph_panel import async_publish_brain_graph_panel


class CopilotPublishBrainGraphVizButton(CopilotBaseEntity, ButtonEntity):
    """Publish a minimal local HTML/SVG brain-graph preview."""

    _attr_entity_registry_enabled_default = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "PilotSuite publish brain graph viz"
    _attr_unique_id = "ai_home_copilot_publish_brain_graph_viz"
    _attr_icon = "mdi:graph"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_publish_brain_graph_viz(self.hass, self.coordinator)



class CopilotPublishBrainGraphPanelButton(CopilotBaseEntity, ButtonEntity):
    """Publish an interactive brain graph panel with filtering and zoom."""

    _attr_entity_registry_enabled_default = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "PilotSuite publish brain graph panel"
    _attr_unique_id = "ai_home_copilot_publish_brain_graph_panel"
    _attr_icon = "mdi:graph"

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        await async_publish_brain_graph_panel(self.hass, self.coordinator)

