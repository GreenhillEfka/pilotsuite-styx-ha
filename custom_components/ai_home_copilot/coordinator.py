from __future__ import annotations

from datetime import timedelta

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


class CopilotDataUpdateCoordinator(DataUpdateCoordinator[CopilotStatus]):
    def __init__(self, hass: HomeAssistant, config: dict):
        self._hass = hass
        self._config = config
        session = async_get_clientsession(hass)
        base_url = f"http://{config[CONF_HOST]}:{config[CONF_PORT]}"
        token = config.get(CONF_TOKEN)
        self.api = CopilotApiClient(session=session, base_url=base_url, token=token)

        watchdog_enabled = config.get(CONF_WATCHDOG_ENABLED, DEFAULT_WATCHDOG_ENABLED)
        watchdog_interval = config.get(
            CONF_WATCHDOG_INTERVAL_SECONDS, DEFAULT_WATCHDOG_INTERVAL_SECONDS
        )

        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=f"{DOMAIN}-{config[CONF_HOST]}:{config[CONF_PORT]}",
            update_interval=timedelta(seconds=watchdog_interval) if watchdog_enabled else None,
        )

    async def _async_update_data(self) -> CopilotStatus:
        try:
            return await self.api.async_get_status()
        except CopilotApiError as err:
            raise UpdateFailed(str(err)) from err
