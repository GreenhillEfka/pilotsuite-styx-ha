from __future__ import annotations

import logging
import json
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any, Mapping

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from .coordinator import CopilotDataUpdateCoordinator
from .const import DOMAIN, LEGACY_MAIN_DEVICE_IDENTIFIERS, MAIN_DEVICE_IDENTIFIER
from .core_endpoint import DEFAULT_CORE_PORT, build_base_url

_LOGGER = logging.getLogger(__name__)


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

    def _core_base_url(self) -> str:
        """Return best available Core endpoint URL."""
        api = getattr(self.coordinator, "api", None)
        active_url = getattr(api, "_active_base_url", None)
        if isinstance(active_url, str) and active_url.strip():
            return active_url.rstrip("/")

        host = str(self.coordinator._config.get("host") or self._host or "").strip()
        try:
            port = int(self.coordinator._config.get("port") or self._port or DEFAULT_CORE_PORT)
        except (TypeError, ValueError):
            port = DEFAULT_CORE_PORT
        return build_base_url(host, port).rstrip("/")

    def _core_headers(self, *, content_type: str | None = None) -> dict[str, str]:
        """Return auth headers compatible with Core API."""
        headers: dict[str, str] = {}
        token = str(
            self.coordinator._config.get("token")
            or self.coordinator._config.get("auth_token")
            or ""
        ).strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["X-Auth-Token"] = token
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def _fetch(self, path: str, *, timeout_s: float = 10.0) -> dict[str, Any] | None:
        """Fetch JSON from Core API with configured auth and resilient URL handling."""
        import aiohttp

        normalized = path if path.startswith("/") else f"/{path}"
        url = f"{self._core_base_url()}{normalized}"
        headers = self._core_headers()
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout_s),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Core fetch failed for %s: %s", normalized, err)
        return None

    @property
    def device_info(self) -> DeviceInfo:
        config_url = None
        try:
            host = str(self.coordinator._config.get("host") or "").strip()
            port = int(self.coordinator._config.get("port") or DEFAULT_CORE_PORT)
            if host:
                config_url = f"http://{host}:{port}/"
        except (TypeError, ValueError):
            pass
        return DeviceInfo(
            identifiers=build_main_device_identifiers(self.coordinator._config),
            name="PilotSuite - Styx",
            manufacturer="PilotSuite",
            model="Home Assistant Integration",
            sw_version=VERSION,
            configuration_url=config_url,
        )
