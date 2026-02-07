from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_TEST_LIGHT, DEFAULT_TEST_LIGHT, DOMAIN
from .entity import CopilotBaseEntity
from .suggest import async_offer_demo_candidate


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    cfg = entry.data | entry.options
    async_add_entities(
        [
            CopilotToggleLightButton(
                coordinator, cfg.get(CONF_TEST_LIGHT, DEFAULT_TEST_LIGHT)
            ),
            CopilotCreateDemoSuggestionButton(coordinator, entry.entry_id),
        ],
        True,
    )


class CopilotToggleLightButton(CopilotBaseEntity, ButtonEntity):
    _attr_name = "Toggle test light"
    _attr_unique_id = "toggle_test_light"
    _attr_icon = "mdi:light-switch"

    def __init__(self, coordinator, entity_id: str):
        super().__init__(coordinator)
        self._light_entity_id = entity_id

    async def async_press(self) -> None:
        await self.hass.services.async_call(
            "light",
            "toggle",
            {"entity_id": self._light_entity_id},
            blocking=False,
        )


class CopilotCreateDemoSuggestionButton(CopilotBaseEntity, ButtonEntity):
    _attr_name = "Create demo suggestion"
    _attr_unique_id = "create_demo_suggestion"
    _attr_icon = "mdi:lightbulb-on-outline"

    def __init__(self, coordinator, entry_id: str):
        super().__init__(coordinator)
        self._entry_id = entry_id

    async def async_press(self) -> None:
        await async_offer_demo_candidate(self.hass, self._entry_id)
