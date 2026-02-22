from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from .coordinator import CopilotDataUpdateCoordinator


def _load_integration_version() -> str:
    manifest = Path(__file__).resolve().parent / "manifest.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return "unknown"
    version = data.get("version")
    return str(version) if version else "unknown"


VERSION = _load_integration_version()


class CopilotBaseEntity(CoordinatorEntity["CopilotDataUpdateCoordinator"]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._host = coordinator._config.get("host")
        self._port = coordinator._config.get("port")

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("ai_home_copilot", f"{self._host}:{self._port}")},
            name="PilotSuite",
            manufacturer="PilotSuite",
            model="HACS Integration",
            sw_version=VERSION,
        )
