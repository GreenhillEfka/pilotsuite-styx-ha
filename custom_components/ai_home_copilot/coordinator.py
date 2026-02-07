from __future__ import annotations

from datetime import timedelta
import re
from urllib.parse import urlparse

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CopilotApiClient, CopilotApiError, CopilotStatus
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_WATCHDOG_ENABLED,
    CONF_WATCHDOG_INTERVAL_SECONDS,
    DEFAULT_WATCHDOG_ENABLED,
    DEFAULT_WATCHDOG_INTERVAL_SECONDS,
    DOMAIN,
)


def _normalize_base_url(host: str, port: int) -> str:
    """Build a usable base URL from user input.

    Users sometimes paste a full URL (e.g. "http://192.168.30.18:8909").
    We accept that and normalize it to avoid double schemes like "http://http://...".
    """

    raw = (host or "").strip().rstrip("/")

    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        return raw

    # Strip any accidental path.
    raw = raw.split("/", 1)[0]

    # If host already includes a port (e.g. "192.168.30.18:8909"), keep it.
    if re.match(r"^[^\[]+:[0-9]+$", raw) and raw.count(":") == 1:
        return f"http://{raw}".rstrip("/")

    return f"http://{raw}:{int(port)}".rstrip("/")


class CopilotDataUpdateCoordinator(DataUpdateCoordinator[CopilotStatus]):
    def __init__(self, hass: HomeAssistant, config: dict):
        self._hass = hass
        self._config = config
        session = async_get_clientsession(hass)
        base_url = _normalize_base_url(
            str(config.get(CONF_HOST, "")),
            int(config.get(CONF_PORT, 0) or 0),
        )
        token = config.get(CONF_TOKEN)
        self.api = CopilotApiClient(session=session, base_url=base_url, token=token)

        watchdog_enabled = config.get(CONF_WATCHDOG_ENABLED, DEFAULT_WATCHDOG_ENABLED)
        watchdog_interval = config.get(
            CONF_WATCHDOG_INTERVAL_SECONDS, DEFAULT_WATCHDOG_INTERVAL_SECONDS
        )

        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=f"{DOMAIN}-{config.get(CONF_HOST)}:{config.get(CONF_PORT)}",
            update_interval=timedelta(seconds=watchdog_interval) if watchdog_enabled else None,
        )

    async def _async_update_data(self) -> CopilotStatus:
        try:
            return await self.api.async_get_status()
        except CopilotApiError as err:
            raise UpdateFailed(str(err)) from err
