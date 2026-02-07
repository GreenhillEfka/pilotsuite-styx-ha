from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import CopilotDataUpdateCoordinator


class CopilotBaseEntity(CoordinatorEntity[CopilotDataUpdateCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._host = coordinator._config.get("host")
        self._port = coordinator._config.get("port")

    @property
    def device_info(self):
        return {
            "identifiers": {("ai_home_copilot", f"{self._host}:{self._port}")},
            "name": "AI Home CoPilot Core",
            "manufacturer": "Custom",
            "model": "MVP Core",
        }
