from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import re
from urllib.parse import urlparse

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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

_LOGGER = logging.getLogger(__name__)


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
    """Status coordinator with basic scaling guardrails.

    - Prevent overlapping updates via an asyncio.Lock (single-writer for coordinator.data).
    - Bound upstream concurrency via a small semaphore.
    - Apply a simple exponential backoff on repeated failures to reduce load.
    """

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

        watchdog_enabled = bool(config.get(CONF_WATCHDOG_ENABLED, DEFAULT_WATCHDOG_ENABLED))
        watchdog_interval = int(
            config.get(CONF_WATCHDOG_INTERVAL_SECONDS, DEFAULT_WATCHDOG_INTERVAL_SECONDS)
        )

        # Coordinator cadence guardrails: avoid overly aggressive polls.
        watchdog_interval = max(5, min(watchdog_interval, 3600))

        self._base_interval: timedelta | None = (
            timedelta(seconds=watchdog_interval) if watchdog_enabled else None
        )
        self._failure_streak: int = 0

        # Thread-safety / concurrency.
        self._update_lock = asyncio.Lock()
        self._req_sem = asyncio.Semaphore(2)

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-{config.get(CONF_HOST)}:{config.get(CONF_PORT)}",
            update_interval=self._base_interval,
        )

    def _apply_backoff(self) -> None:
        """Apply a bounded exponential backoff by adjusting update_interval."""

        if self._base_interval is None:
            return

        factor = 2 ** max(0, self._failure_streak - 1)
        base_s = int(self._base_interval.total_seconds())
        seconds = base_s * factor
        seconds = max(base_s, min(seconds, 600))
        new_interval = timedelta(seconds=seconds)

        if new_interval != self.update_interval:
            self.update_interval = new_interval
            _LOGGER.debug(
                "Coordinator backoff: failure_streak=%s interval=%ss",
                self._failure_streak,
                seconds,
            )

    def _reset_backoff(self) -> None:
        if self._base_interval is None:
            return
        if self.update_interval != self._base_interval:
            self.update_interval = self._base_interval
            _LOGGER.debug(
                "Coordinator backoff reset: interval=%ss",
                int(self._base_interval.total_seconds()),
            )

    async def _async_update_data(self) -> CopilotStatus:
        async with self._update_lock:
            try:
                async with self._req_sem:
                    data = await self.api.async_get_status()
                self._failure_streak = 0
                self._reset_backoff()
                return data
            except CopilotApiError as err:
                self._failure_streak += 1
                self._apply_backoff()
                raise UpdateFailed(str(err)) from err
