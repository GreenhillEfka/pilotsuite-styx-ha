from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any, Mapping

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from .coordinator import CopilotDataUpdateCoordinator
from .const import DOMAIN, LEGACY_MAIN_DEVICE_IDENTIFIERS, MAIN_DEVICE_IDENTIFIER


def _load_integration_version() -> str:
    manifest = Path(__file__).resolve().parent / "manifest.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return "unknown"
    version = data.get("version")
    return str(version) if version else "unknown"


VERSION = _load_integration_version()


def build_main_device_identifiers(config: Mapping[str, Any]) -> set[tuple[str, str]]:
    """Build stable + backward-compatible device identifiers."""
    identifiers: set[tuple[str, str]] = {(DOMAIN, MAIN_DEVICE_IDENTIFIER)}
    for legacy_id in LEGACY_MAIN_DEVICE_IDENTIFIERS:
        identifiers.add((DOMAIN, legacy_id))
    host = str(config.get("host", "") or "").strip()
    port = str(config.get("port", "") or "").strip()
    if host and port:
        # Legacy identifier used by previous releases.
        identifiers.add((DOMAIN, f"{host}:{port}"))
    return identifiers


class CopilotBaseEntity(CoordinatorEntity["CopilotDataUpdateCoordinator"]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: CopilotDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._host = coordinator._config.get("host")
        self._port = coordinator._config.get("port")

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers=build_main_device_identifiers(self.coordinator._config),
            name="PilotSuite - Styx",
            manufacturer="PilotSuite",
            model="Home Assistant Integration",
            sw_version=VERSION,
        )
